import argparse
from pathlib import Path

import numpy as np

from .action_encoder import FEATURE_NAMES
from .policy import TinyMLPActionPolicy
from .train_imitation import _load_shard, iter_shards


def _init_layers(input_size, hidden_sizes, rng):
    layer_sizes = [input_size, *hidden_sizes, 1]
    weights = []
    biases = []
    for in_size, out_size in zip(layer_sizes[:-1], layer_sizes[1:]):
        scale = np.sqrt(2.0 / max(1, in_size))
        weights.append((rng.standard_normal((in_size, out_size)) * scale).astype(np.float32))
        biases.append(np.zeros((out_size,), dtype=np.float32))
    return weights, biases


def _forward(features, weights, biases):
    activations = [np.asarray(features, dtype=np.float32)]
    pre_activations = []
    hidden = activations[0]

    for layer_index, (weight, bias) in enumerate(zip(weights, biases)):
        linear = hidden @ weight + bias
        pre_activations.append(linear)
        if layer_index == len(weights) - 1:
            hidden = linear
        else:
            hidden = np.maximum(linear, 0.0)
        activations.append(hidden)
    return activations, pre_activations


def _backward_batch(activations, pre_activations, weights, probs, chosen_indices, l2):
    grads_w = [None] * len(weights)
    grads_b = [None] * len(weights)

    batch_size = max(1, int(probs.shape[0]))
    delta = probs.astype(np.float32).copy()
    delta[np.arange(batch_size), chosen_indices] -= 1.0
    delta = (delta / batch_size)[..., None]

    last_index = len(weights) - 1
    grads_w[last_index] = np.tensordot(activations[last_index], delta, axes=([0, 1], [0, 1])) + l2 * weights[last_index]
    grads_b[last_index] = np.sum(delta, axis=(0, 1))
    upstream = delta @ weights[last_index].T

    for layer_index in range(last_index - 1, -1, -1):
        relu_grad = (pre_activations[layer_index] > 0).astype(np.float32)
        delta_hidden = upstream * relu_grad
        grads_w[layer_index] = np.tensordot(
            activations[layer_index],
            delta_hidden,
            axes=([0, 1], [0, 1]),
        ) + l2 * weights[layer_index]
        grads_b[layer_index] = np.sum(delta_hidden, axis=(0, 1))
        upstream = delta_hidden @ weights[layer_index].T

    return grads_w, grads_b


def _iter_bucket_batches(candidate_features, offsets, chosen_indices, sample_order, batch_size):
    buckets = {}
    for sample_idx in sample_order:
        start = int(offsets[sample_idx])
        end = int(offsets[sample_idx + 1])
        action_count = end - start
        if action_count <= 0:
            continue
        buckets.setdefault(action_count, []).append((start, end, int(chosen_indices[sample_idx])))

    for action_count, entries in buckets.items():
        for batch_start in range(0, len(entries), batch_size):
            batch_entries = entries[batch_start:batch_start + batch_size]
            feature_batch = np.stack(
                [candidate_features[start:end] for start, end, _ in batch_entries],
                axis=0,
            ).astype(np.float32, copy=False)
            chosen_batch = np.asarray([chosen for _, _, chosen in batch_entries], dtype=np.int32)
            yield action_count, feature_batch, chosen_batch


def train_tiny_mlp_policy(
    dataset_dir,
    output_path,
    hidden_sizes=(64, 32),
    epochs=10,
    learning_rate=0.02,
    batch_size=32,
    l2=1e-4,
    seed=7,
):
    shard_paths = list(iter_shards(dataset_dir))
    if not shard_paths:
        raise FileNotFoundError(f'No dataset shards found under {dataset_dir}')

    first_features, _, _ = _load_shard(shard_paths[0])
    if first_features.size == 0:
        raise ValueError('Dataset shards are empty')

    rng = np.random.default_rng(seed)
    weights, biases = _init_layers(first_features.shape[1], tuple(int(size) for size in hidden_sizes), rng)

    for epoch in range(int(epochs)):
        rng.shuffle(shard_paths)
        sample_count = 0
        correct = 0
        total_loss = 0.0

        for shard_path in shard_paths:
            candidate_features, offsets, chosen_indices = _load_shard(shard_path)
            sample_order = np.arange(len(chosen_indices))
            rng.shuffle(sample_order)

            for _, feature_batch, chosen_batch in _iter_bucket_batches(
                candidate_features,
                offsets,
                chosen_indices,
                sample_order,
                max(1, int(batch_size)),
            ):
                activations, pre_activations = _forward(feature_batch, weights, biases)
                logits = activations[-1].reshape(feature_batch.shape[0], feature_batch.shape[1])
                logits = logits - np.max(logits, axis=1, keepdims=True)
                probs = np.exp(logits)
                probs = probs / np.sum(probs, axis=1, keepdims=True)

                l2_penalty = sum(float(np.sum(weight * weight)) for weight in weights)
                total_loss += float(
                    np.sum(-np.log(np.maximum(probs[np.arange(len(chosen_batch)), chosen_batch], 1e-8)))
                ) + 0.5 * l2 * l2_penalty * len(chosen_batch)
                predicted = np.argmax(probs, axis=1)
                correct += int(np.sum(predicted == chosen_batch))

                grads_w, grads_b = _backward_batch(activations, pre_activations, weights, probs, chosen_batch, l2)
                for layer_index in range(len(weights)):
                    weights[layer_index] -= learning_rate * grads_w[layer_index].astype(np.float32)
                    biases[layer_index] -= learning_rate * grads_b[layer_index].astype(np.float32)
                sample_count += len(chosen_batch)

        avg_loss = total_loss / max(1, sample_count)
        accuracy = correct / max(1, sample_count)
        print(f'epoch={epoch + 1} samples={sample_count} loss={avg_loss:.4f} accuracy={accuracy:.4f}')

    policy = TinyMLPActionPolicy(weights, biases)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    policy.save(output_path)
    return output_path


def main():
    parser = argparse.ArgumentParser(description='Train a tiny NumPy MLP imitation policy from expert shards.')
    parser.add_argument('dataset_dir', help='Directory that contains expert shard .npz files')
    parser.add_argument('output_path', help='Path to save the trained policy')
    parser.add_argument('--hidden-sizes', default='64,32', help='Comma-separated hidden layer sizes')
    parser.add_argument('--epochs', type=int, default=10, help='Training epochs')
    parser.add_argument('--learning-rate', type=float, default=0.02, help='SGD learning rate')
    parser.add_argument('--batch-size', type=int, default=32, help='Mini-batch size within equal-action-count buckets')
    parser.add_argument('--l2', type=float, default=1e-4, help='L2 penalty')
    parser.add_argument('--seed', type=int, default=7, help='Random seed')
    args = parser.parse_args()

    hidden_sizes = tuple(int(item) for item in args.hidden_sizes.split(',') if item.strip())
    if not hidden_sizes:
        raise ValueError('At least one hidden layer size is required')

    output_path = train_tiny_mlp_policy(
        args.dataset_dir,
        args.output_path,
        hidden_sizes=hidden_sizes,
        epochs=args.epochs,
        learning_rate=args.learning_rate,
        batch_size=args.batch_size,
        l2=args.l2,
        seed=args.seed,
    )
    print(f'policy_saved={output_path}')
    print(f'feature_count={len(FEATURE_NAMES)}')
    print('hidden_sizes=' + ','.join(str(size) for size in hidden_sizes))


if __name__ == '__main__':
    main()
