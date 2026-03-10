import argparse
from pathlib import Path

import numpy as np

from .action_encoder import FEATURE_NAMES
from .policy import LinearActionPolicy


def iter_shards(dataset_dir):
    dataset_path = Path(dataset_dir)
    for shard_path in sorted(dataset_path.glob('*.npz')):
        yield shard_path


def _load_shard(shard_path):
    with np.load(shard_path, allow_pickle=False) as data:
        return (
            data['candidate_features'].astype(np.float32),
            data['candidate_offsets'].astype(np.int32),
            data['chosen_indices'].astype(np.int32),
        )


def train_linear_policy(dataset_dir, output_path, epochs=8, learning_rate=0.05, l2=1e-4, seed=7):
    shard_paths = list(iter_shards(dataset_dir))
    if not shard_paths:
        raise FileNotFoundError(f'No dataset shards found under {dataset_dir}')

    first_features, _, _ = _load_shard(shard_paths[0])
    if first_features.size == 0:
        raise ValueError('Dataset shards are empty')

    weights = np.zeros(first_features.shape[1], dtype=np.float32)
    rng = np.random.default_rng(seed)

    for epoch in range(int(epochs)):
        rng.shuffle(shard_paths)
        sample_count = 0
        correct = 0
        total_loss = 0.0

        for shard_path in shard_paths:
            candidate_features, offsets, chosen_indices = _load_shard(shard_path)
            sample_order = np.arange(len(chosen_indices))
            rng.shuffle(sample_order)

            for sample_idx in sample_order:
                start = int(offsets[sample_idx])
                end = int(offsets[sample_idx + 1])
                features = candidate_features[start:end]
                if features.size == 0:
                    continue

                chosen_index = int(chosen_indices[sample_idx])
                logits = features @ weights
                logits = logits - np.max(logits)
                probs = np.exp(logits)
                probs = probs / np.sum(probs)

                total_loss += -np.log(max(float(probs[chosen_index]), 1e-8)) + 0.5 * l2 * float(weights @ weights)
                predicted = int(np.argmax(probs))
                correct += int(predicted == chosen_index)

                probs[chosen_index] -= 1.0
                gradient = features.T @ probs + l2 * weights
                weights -= learning_rate * gradient.astype(np.float32)
                sample_count += 1

        avg_loss = total_loss / max(1, sample_count)
        accuracy = correct / max(1, sample_count)
        print(f'epoch={epoch + 1} samples={sample_count} loss={avg_loss:.4f} accuracy={accuracy:.4f}')

    policy = LinearActionPolicy(weights)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    policy.save(output_path)
    return output_path


def main():
    parser = argparse.ArgumentParser(description='Train a very small linear imitation policy from expert shards.')
    parser.add_argument('dataset_dir', help='Directory that contains expert shard .npz files')
    parser.add_argument('output_path', help='Path to save the trained policy')
    parser.add_argument('--epochs', type=int, default=8, help='Training epochs')
    parser.add_argument('--learning-rate', type=float, default=0.05, help='SGD learning rate')
    parser.add_argument('--l2', type=float, default=1e-4, help='L2 penalty')
    parser.add_argument('--seed', type=int, default=7, help='Random seed')
    args = parser.parse_args()

    output_path = train_linear_policy(
        args.dataset_dir,
        args.output_path,
        epochs=args.epochs,
        learning_rate=args.learning_rate,
        l2=args.l2,
        seed=args.seed,
    )
    print(f'policy_saved={output_path}')
    print(f'feature_count={len(FEATURE_NAMES)}')


if __name__ == '__main__':
    main()
