import argparse
from pathlib import Path

import numpy as np

from ..config.constants import AI_DIFFICULTY_HARD
from .env import HeadlessGameEnv


class ShardedExpertDatasetWriter:
    def __init__(self, output_dir, shard_size=1024):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.shard_size = max(1, int(shard_size))
        self._reset_buffers()
        self.shard_index = 0

    def _reset_buffers(self):
        self.feature_blocks = []
        self.offsets = [0]
        self.chosen_indices = []
        self.players = []
        self.rounds = []

    def add_sample(self, candidate_features, chosen_index, player, round_count):
        if candidate_features.size == 0:
            return
        candidate_features = np.asarray(candidate_features, dtype=np.float32)
        self.feature_blocks.append(candidate_features)
        self.offsets.append(self.offsets[-1] + candidate_features.shape[0])
        self.chosen_indices.append(int(chosen_index))
        self.players.append(int(player))
        self.rounds.append(int(round_count))
        if len(self.chosen_indices) >= self.shard_size:
            self.flush()

    def flush(self):
        if not self.chosen_indices:
            return None
        shard_path = self.output_dir / f'expert_shard_{self.shard_index:04d}.npz'
        candidate_features = np.concatenate(self.feature_blocks, axis=0)
        np.savez_compressed(
            shard_path,
            candidate_features=candidate_features.astype(np.float32),
            candidate_offsets=np.asarray(self.offsets, dtype=np.int32),
            chosen_indices=np.asarray(self.chosen_indices, dtype=np.int32),
            players=np.asarray(self.players, dtype=np.int8),
            rounds=np.asarray(self.rounds, dtype=np.int16),
        )
        self.shard_index += 1
        self._reset_buffers()
        return shard_path

    def close(self):
        return self.flush()


def record_expert_games(
    output_dir,
    games=10,
    max_decisions_per_game=1500,
    difficulty=AI_DIFFICULTY_HARD,
    shard_size=1024,
):
    writer = ShardedExpertDatasetWriter(output_dir, shard_size=shard_size)
    total_samples = 0
    total_games = 0

    for _ in range(int(games)):
        env = HeadlessGameEnv(ai_difficulty=difficulty, all_ai=True)
        env.reset()
        decisions = 0
        total_games += 1

        while (not env.game.game_over) and decisions < max_decisions_per_game:
            actions, feature_matrix = env.get_legal_action_features()
            if not actions:
                _, _, done, _ = env.pass_turn()
                if done:
                    break
                continue

            chosen_action, _ = env.game.choose_ai_action(env.game.current_player)
            if chosen_action is None:
                _, _, done, _ = env.pass_turn()
                if done:
                    break
                continue

            chosen_index = None
            for idx, action in enumerate(actions):
                if action.from_pos == chosen_action[0] and action.to_pos == chosen_action[1]:
                    chosen_index = idx
                    break

            if chosen_index is None:
                _, _, done, _ = env.pass_turn()
                if done:
                    break
                continue

            writer.add_sample(
                feature_matrix,
                chosen_index,
                player=env.game.current_player,
                round_count=env.game.round_count,
            )
            total_samples += 1
            decisions += 1
            _, _, done, _ = env.step(actions[chosen_index])
            if done:
                break

    writer.close()
    return {
        'games': total_games,
        'samples': total_samples,
        'output_dir': str(Path(output_dir).resolve()),
    }


def main():
    parser = argparse.ArgumentParser(description='Record low-memory expert datasets from the built-in AI.')
    parser.add_argument('output_dir', help='Directory for dataset shards')
    parser.add_argument('--games', type=int, default=10, help='Number of self-play games to record')
    parser.add_argument('--max-decisions', type=int, default=1500, help='Maximum decisions to record per game')
    parser.add_argument('--shard-size', type=int, default=1024, help='Number of state samples per compressed shard')
    parser.add_argument(
        '--difficulty',
        default=AI_DIFFICULTY_HARD,
        choices=['easy', 'normal', 'hard'],
        help='Built-in AI difficulty used as the expert policy',
    )
    args = parser.parse_args()

    summary = record_expert_games(
        args.output_dir,
        games=args.games,
        max_decisions_per_game=args.max_decisions,
        difficulty=args.difficulty,
        shard_size=args.shard_size,
    )
    print(
        'recorded_games={games} recorded_samples={samples} output_dir={output_dir}'.format(
            **summary,
        )
    )


if __name__ == '__main__':
    main()
