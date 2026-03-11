from pathlib import Path

import numpy as np

from .action_encoder import FEATURE_NAMES


def _align_feature_matrix(feature_matrix, expected_dim):
    feature_matrix = np.asarray(feature_matrix, dtype=np.float32)
    if feature_matrix.size == 0:
        return feature_matrix
    actual_dim = feature_matrix.shape[1]
    if actual_dim == expected_dim:
        return feature_matrix
    if actual_dim > expected_dim:
        return feature_matrix[:, :expected_dim]
    padding = np.zeros((feature_matrix.shape[0], expected_dim - actual_dim), dtype=np.float32)
    return np.concatenate([feature_matrix, padding], axis=1)


class LinearActionPolicy:
    """A very small policy that scores legal actions with a single linear layer."""

    def __init__(self, weights):
        self.weights = np.asarray(weights, dtype=np.float32)

    @classmethod
    def load(cls, path):
        data = np.load(Path(path), allow_pickle=False)
        return cls(data['weights'])

    def score_candidates(self, feature_matrix):
        if feature_matrix.size == 0:
            return np.zeros((0,), dtype=np.float32)
        aligned = _align_feature_matrix(feature_matrix, self.weights.shape[0])
        return aligned @ self.weights

    def choose_index(self, feature_matrix):
        scores = self.score_candidates(feature_matrix)
        if scores.size == 0:
            return None, scores
        index = int(np.argmax(scores))
        return index, scores

    def save(self, path):
        np.savez_compressed(
            path,
            model_type=np.asarray('linear'),
            weights=self.weights.astype(np.float32),
            feature_names=np.asarray(FEATURE_NAMES),
        )


class TinyMLPActionPolicy:
    """A small ReLU MLP that stays cheap enough for single-process training and inference."""

    def __init__(self, weights, biases):
        self.weights = [np.asarray(weight, dtype=np.float32) for weight in weights]
        self.biases = [np.asarray(bias, dtype=np.float32) for bias in biases]

    @classmethod
    def load(cls, path):
        data = np.load(Path(path), allow_pickle=False)
        layer_count = int(data['layer_count'])
        weights = [data[f'weight_{index}'] for index in range(layer_count)]
        biases = [data[f'bias_{index}'] for index in range(layer_count)]
        return cls(weights, biases)

    def score_candidates(self, feature_matrix):
        if feature_matrix.size == 0:
            return np.zeros((0,), dtype=np.float32)
        activations = _align_feature_matrix(feature_matrix, self.weights[0].shape[0])
        last_layer = len(self.weights) - 1
        for layer_index, (weight, bias) in enumerate(zip(self.weights, self.biases)):
            activations = activations @ weight + bias
            if layer_index != last_layer:
                activations = np.maximum(activations, 0.0)
        return activations.reshape(-1)

    def choose_index(self, feature_matrix):
        scores = self.score_candidates(feature_matrix)
        if scores.size == 0:
            return None, scores
        index = int(np.argmax(scores))
        return index, scores

    def save(self, path):
        payload = {
            'model_type': np.asarray('mlp'),
            'layer_count': np.asarray(len(self.weights), dtype=np.int32),
            'feature_names': np.asarray(FEATURE_NAMES),
        }
        for index, (weight, bias) in enumerate(zip(self.weights, self.biases)):
            payload[f'weight_{index}'] = weight.astype(np.float32)
            payload[f'bias_{index}'] = bias.astype(np.float32)
        np.savez_compressed(path, **payload)


def load_action_policy(path):
    path = Path(path)
    data = np.load(path, allow_pickle=False)
    model_type_value = data['model_type'] if 'model_type' in data.files else None
    if model_type_value is None:
        model_type = 'linear'
    else:
        model_type = str(model_type_value.item())
    data.close()

    if model_type == 'linear':
        return LinearActionPolicy.load(path)
    if model_type == 'mlp':
        return TinyMLPActionPolicy.load(path)
    raise ValueError(f'Unsupported policy model type: {model_type}')
