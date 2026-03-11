import argparse
import json
import os
import shutil
import time
from pathlib import Path

os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')

from ..config.constants import (  # noqa: E402
    AI_DIFFICULTY_EASY,
    AI_DIFFICULTY_HARD,
    AI_DIFFICULTY_LABELS,
    AI_DIFFICULTY_NORMAL,
)
from .dataset_recorder import record_expert_games  # noqa: E402
from .evaluate_ai import evaluate_difficulty  # noqa: E402
from .train_imitation import train_linear_policy  # noqa: E402
from .train_mlp import train_tiny_mlp_policy  # noqa: E402


AI_LEVEL_CHOICES = [AI_DIFFICULTY_EASY, AI_DIFFICULTY_NORMAL, AI_DIFFICULTY_HARD]


def _parse_hidden_sizes(raw_value):
    values = []
    for item in raw_value.split(','):
        item = item.strip()
        if not item:
            continue
        value = int(item)
        if value <= 0:
            raise ValueError('hidden layer size must be positive')
        values.append(value)
    if not values:
        raise ValueError('at least one hidden layer size is required')
    return tuple(values)


def _default_output_path(model_type):
    filename = 'mlp_policy.npz' if model_type == 'mlp' else 'linear_policy.npz'
    return Path('models') / filename


def _runtime_policy_path(model_type):
    filename = 'mlp_policy.npz' if model_type == 'mlp' else 'linear_policy.npz'
    return Path(__file__).resolve().parents[2] / 'models' / filename


def _write_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8') as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
    return path


def run_pipeline(args):
    started_at = time.time()
    output_model = Path(args.output_model) if args.output_model else _default_output_path(args.model_type)
    output_model.parent.mkdir(parents=True, exist_ok=True)
    runtime_policy = _runtime_policy_path(args.model_type)
    runtime_policy.parent.mkdir(parents=True, exist_ok=True)

    print('[1/3] Recording expert dataset...')
    dataset_summary = record_expert_games(
        args.dataset_dir,
        games=args.games,
        max_decisions_per_game=args.max_decisions,
        difficulty=args.expert_difficulty,
        shard_size=args.shard_size,
    )
    print(
        'recorded_games={games} recorded_samples={samples} output_dir={output_dir}'.format(
            **dataset_summary,
        )
    )

    print('[2/3] Training policy model...')
    if args.model_type == 'linear':
        trained_path = train_linear_policy(
            args.dataset_dir,
            output_model,
            epochs=args.epochs,
            learning_rate=args.learning_rate,
            l2=args.l2,
            seed=args.seed,
        )
    else:
        trained_path = train_tiny_mlp_policy(
            args.dataset_dir,
            output_model,
            hidden_sizes=_parse_hidden_sizes(args.hidden_sizes),
            epochs=args.epochs,
            learning_rate=args.learning_rate,
            batch_size=args.batch_size,
            l2=args.l2,
            seed=args.seed,
        )

    trained_path = Path(trained_path).resolve()
    runtime_policy = runtime_policy.resolve()
    if args.update_default_policy and trained_path != runtime_policy:
        shutil.copy2(trained_path, runtime_policy)
        print(f'copied_runtime_policy={runtime_policy}')

    evaluation_summary = None
    if not args.skip_eval:
        if trained_path != runtime_policy and not args.update_default_policy:
            raise ValueError(
                '--skip-eval or --update-default-policy is required when output model is not the default runtime path'
            )
        print('[3/3] Evaluating learned AI...')
        evaluation_summary = evaluate_difficulty(
            'learned',
            opponent_difficulty=args.eval_opponent,
            games=args.eval_games,
            max_rounds=args.eval_max_rounds,
            max_moves=args.eval_max_moves,
            stagnation_limit=args.eval_stagnation_limit,
            seed=args.seed,
        )
        print(
            'candidate={candidate} opponent={opponent} games={games} wins={wins} win_rate={win_rate:.3f}'.format(
                candidate=AI_DIFFICULTY_LABELS[evaluation_summary['candidate_difficulty']],
                opponent=AI_DIFFICULTY_LABELS[evaluation_summary['opponent_difficulty']],
                games=evaluation_summary['games'],
                wins=evaluation_summary['wins'],
                win_rate=evaluation_summary['win_rate'],
            )
        )

    duration_seconds = round(time.time() - started_at, 3)
    payload = {
        'dataset': dataset_summary,
        'model_type': args.model_type,
        'output_model': str(trained_path),
        'runtime_policy_path': str(runtime_policy),
        'updated_runtime_policy': bool(args.update_default_policy),
        'training': {
            'epochs': args.epochs,
            'learning_rate': args.learning_rate,
            'l2': args.l2,
            'batch_size': args.batch_size if args.model_type == 'mlp' else None,
            'hidden_sizes': args.hidden_sizes if args.model_type == 'mlp' else None,
        },
        'evaluation': evaluation_summary,
        'duration_seconds': duration_seconds,
    }

    if args.summary_json:
        summary_path = _write_json(args.summary_json, payload).resolve()
        print(f'summary_json={summary_path}')

    print(f'pipeline_done duration_seconds={duration_seconds} model={trained_path}')
    return payload


def build_parser():
    parser = argparse.ArgumentParser(
        description='One-command training pipeline: record expert data -> train policy -> evaluate learned AI.'
    )
    parser.add_argument('--dataset-dir', default='data/expert_colab', help='Directory used to store expert shards')
    parser.add_argument('--model-type', default='mlp', choices=['mlp', 'linear'], help='Policy model architecture')
    parser.add_argument('--output-model', default=None, help='Path to save trained model')
    parser.add_argument('--summary-json', default='stats/ml_runs/last_run.json', help='Where to save run summary json')
    parser.add_argument('--seed', type=int, default=7, help='Random seed used in training/evaluation')

    parser.add_argument('--games', type=int, default=60, help='Number of self-play games recorded for dataset')
    parser.add_argument('--max-decisions', type=int, default=1500, help='Max recorded decisions per game')
    parser.add_argument('--shard-size', type=int, default=1024, help='Samples stored per dataset shard')
    parser.add_argument(
        '--expert-difficulty',
        default=AI_DIFFICULTY_HARD,
        choices=AI_LEVEL_CHOICES,
        help='Built-in AI difficulty used as expert during dataset recording',
    )

    parser.add_argument('--epochs', type=int, default=12, help='Training epochs')
    parser.add_argument('--learning-rate', type=float, default=0.02, help='Optimizer learning rate')
    parser.add_argument('--l2', type=float, default=1e-4, help='L2 regularization')
    parser.add_argument('--batch-size', type=int, default=64, help='Mini-batch size for MLP training')
    parser.add_argument('--hidden-sizes', default='64,32', help='Comma-separated MLP hidden layer sizes')

    parser.add_argument('--skip-eval', action='store_true', help='Skip post-training benchmark')
    parser.add_argument(
        '--eval-opponent',
        default=AI_DIFFICULTY_NORMAL,
        choices=[AI_DIFFICULTY_EASY, AI_DIFFICULTY_NORMAL, AI_DIFFICULTY_HARD, 'learned'],
        help='Opponent difficulty for learned AI evaluation',
    )
    parser.add_argument('--eval-games', type=int, default=12, help='Number of games for evaluation')
    parser.add_argument('--eval-max-rounds', type=int, default=120, help='Round cap for each benchmark game')
    parser.add_argument('--eval-max-moves', type=int, default=None, help='Hard cap on actions per benchmark game')
    parser.add_argument(
        '--eval-stagnation-limit',
        type=int,
        default=120,
        help='End benchmark game early if board signature stays unchanged for too many actions',
    )
    parser.add_argument(
        '--update-default-policy',
        action='store_true',
        default=True,
        help='Copy the trained model to the runtime default policy path used by learned AI',
    )
    parser.add_argument(
        '--no-update-default-policy',
        action='store_false',
        dest='update_default_policy',
        help='Do not copy the trained model to runtime default policy path',
    )
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    run_pipeline(args)


if __name__ == '__main__':
    main()
