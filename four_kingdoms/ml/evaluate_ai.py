import os
import argparse
import random

os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')

import numpy as np

from ..config.constants import (
    AI_DIFFICULTY_EASY,
    AI_DIFFICULTY_HARD,
    AI_DIFFICULTY_LABELS,
    AI_DIFFICULTY_LEARNED,
    AI_DIFFICULTY_NORMAL,
    MODE_SINGLE_AI,
)
from ..config.map_presets import DEFAULT_MAP_PRESET
from ..core.game_core import Game


AI_CHOICES = [
    AI_DIFFICULTY_EASY,
    AI_DIFFICULTY_NORMAL,
    AI_DIFFICULTY_HARD,
    AI_DIFFICULTY_LEARNED,
]

SUITE_CHOICES = [
    AI_DIFFICULTY_EASY,
    AI_DIFFICULTY_NORMAL,
    AI_DIFFICULTY_HARD,
    AI_DIFFICULTY_LEARNED,
]


def _count_player_mines(game, player):
    return sum(1 for i, j in game.gold_mine_positions if int(game.board[i, j, 0]) == player)


def _state_signature(game):
    signature = []
    for player in sorted(game.players):
        capital_pos = game.capitals.get(player)
        capital_owner = None
        if capital_pos is not None:
            capital_owner = int(game.board[capital_pos[0], capital_pos[1], 0])
        signature.append(
            (
                int(player),
                int(game.territory_count.get(player, 0)),
                int(_count_player_mines(game, player)),
                capital_owner,
            )
        )
    return tuple(signature)


def _build_game(map_preset_id, default_difficulty, persist_stats=False):
    game = Game(
        game_mode=MODE_SINGLE_AI,
        map_preset_id=map_preset_id,
        ai_difficulty=default_difficulty,
        headless=not persist_stats,
    )
    game.human_players = set()
    game.ai_players = set(game.players)
    game.ai_search_profile = 'benchmark'
    return game


def _play_one_game(
    candidate_difficulty,
    opponent_difficulty,
    candidate_player,
    map_preset_id,
    max_rounds,
    max_moves=None,
    stagnation_limit=120,
):
    game = _build_game(map_preset_id, opponent_difficulty, persist_stats=False)
    per_player_difficulty = {
        player: (candidate_difficulty if player == candidate_player else opponent_difficulty)
        for player in game.players
    }

    move_counter = 0
    max_moves = int(max_moves) if max_moves is not None else max(80, max(1, max_rounds) * 8)
    state_signature = _state_signature(game)
    stagnant_moves = 0

    while not game.game_over and game.round_count <= max_rounds and move_counter < max_moves:
        if game.current_player not in game.players:
            game.next_player()
            continue

        current_difficulty = per_player_difficulty.get(game.current_player, opponent_difficulty)
        game.set_ai_difficulty(current_difficulty, announce=False)
        action, _ = game.choose_ai_action(game.current_player)

        if action is None:
            game.steps_left = 0
        else:
            success, _ = game.move_soldier(action[0], action[1])
            if not success:
                game.steps_left = 0

        move_counter += 1
        new_signature = _state_signature(game)
        if new_signature == state_signature:
            stagnant_moves += 1
        else:
            stagnant_moves = 0
            state_signature = new_signature

        if game.game_over:
            break
        if stagnant_moves >= stagnation_limit:
            break
        if game.steps_left <= 0:
            game.next_player()

    timed_out = False
    if not game.game_over:
        timed_out = True
        standings = []
        for player in game.players:
            territory = int(game.territory_count.get(player, 0))
            mines = _count_player_mines(game, player)
            standings.append((territory + mines * 4, territory, mines, player))
        standings.sort(reverse=True)
        game.winner = standings[0][3] if standings else None

    winner = game.winner
    candidate_won = winner == candidate_player
    return {
        'winner': winner,
        'candidate_player': candidate_player,
        'candidate_difficulty': candidate_difficulty,
        'opponent_difficulty': opponent_difficulty,
        'candidate_won': candidate_won,
        'rounds': int(game.round_count),
        'timed_out': timed_out,
        'candidate_territory': int(game.territory_count.get(candidate_player, 0)),
        'candidate_mines': _count_player_mines(game, candidate_player),
    }


def evaluate_difficulty(
    candidate_difficulty,
    opponent_difficulty=AI_DIFFICULTY_NORMAL,
    games=12,
    map_preset_id=DEFAULT_MAP_PRESET,
    max_rounds=120,
    max_moves=None,
    stagnation_limit=120,
    seed=7,
):
    random.seed(seed)
    np.random.seed(seed)

    summaries = []
    for game_index in range(int(games)):
        candidate_player = (game_index % 4) + 1
        summaries.append(
            _play_one_game(
                candidate_difficulty,
                opponent_difficulty,
                candidate_player,
                map_preset_id,
                max_rounds=max_rounds,
                max_moves=max_moves,
                stagnation_limit=stagnation_limit,
            )
        )

    wins = sum(1 for item in summaries if item['candidate_won'])
    timeouts = sum(1 for item in summaries if item['timed_out'])
    avg_rounds = sum(item['rounds'] for item in summaries) / max(1, len(summaries))
    avg_territory = sum(item['candidate_territory'] for item in summaries) / max(1, len(summaries))
    avg_mines = sum(item['candidate_mines'] for item in summaries) / max(1, len(summaries))
    seat_wins = {player: 0 for player in (1, 2, 3, 4)}
    for item in summaries:
        seat_wins[item['candidate_player']] += int(item['candidate_won'])

    return {
        'candidate_difficulty': candidate_difficulty,
        'opponent_difficulty': opponent_difficulty,
        'games': len(summaries),
        'wins': wins,
        'win_rate': wins / max(1, len(summaries)),
        'timeouts': timeouts,
        'avg_rounds': avg_rounds,
        'avg_territory': avg_territory,
        'avg_mines': avg_mines,
        'seat_wins': seat_wins,
    }


def _format_summary_line(summary):
    return (
        'candidate={candidate} opponent={opponent} games={games} wins={wins} win_rate={win_rate:.3f} '
        'avg_rounds={avg_rounds:.1f} avg_territory={avg_territory:.1f} avg_mines={avg_mines:.2f} '
        'timeouts={timeouts}'.format(
            candidate=AI_DIFFICULTY_LABELS[summary['candidate_difficulty']],
            opponent=AI_DIFFICULTY_LABELS[summary['opponent_difficulty']],
            games=summary['games'],
            wins=summary['wins'],
            win_rate=summary['win_rate'],
            avg_rounds=summary['avg_rounds'],
            avg_territory=summary['avg_territory'],
            avg_mines=summary['avg_mines'],
            timeouts=summary['timeouts'],
        )
    )


def _print_suite_table(summaries):
    header = '{:<8} {:>5} {:>8} {:>10} {:>10} {:>8}'.format('难度', '胜场', '胜率', '平均轮数', '平均领土', '超时')
    print(header)
    print('-' * len(header))
    for summary in summaries:
        print(
            '{:<8} {:>5} {:>8.3f} {:>10.1f} {:>10.1f} {:>8}'.format(
                AI_DIFFICULTY_LABELS[summary['candidate_difficulty']],
                summary['wins'],
                summary['win_rate'],
                summary['avg_rounds'],
                summary['avg_territory'],
                summary['timeouts'],
            )
        )


def main():
    parser = argparse.ArgumentParser(description='Evaluate built-in AI difficulties with a bounded low-memory headless benchmark.')
    parser.add_argument('--candidate', default=AI_DIFFICULTY_LEARNED, choices=AI_CHOICES, help='Difficulty being evaluated')
    parser.add_argument('--opponent', default=AI_DIFFICULTY_NORMAL, choices=AI_CHOICES, help='Difficulty used by the other three players')
    parser.add_argument('--suite', action='store_true', help='Run easy/normal/hard/learned as one comparison table')
    parser.add_argument('--games', type=int, default=4, help='Number of games to benchmark')
    parser.add_argument('--max-rounds', type=int, default=20, help='Round cap before using territory tiebreak')
    parser.add_argument('--max-moves', type=int, default=None, help='Hard cap on total actions per game')
    parser.add_argument('--stagnation-limit', type=int, default=120, help='End the game early if the board signature stops changing for this many actions')
    parser.add_argument('--map', dest='map_preset_id', default=DEFAULT_MAP_PRESET, help='Map preset id')
    parser.add_argument('--seed', type=int, default=7, help='Random seed')
    args = parser.parse_args()

    if args.suite:
        summaries = []
        for index, candidate in enumerate(SUITE_CHOICES):
            summaries.append(
                evaluate_difficulty(
                    candidate,
                    opponent_difficulty=args.opponent,
                    games=args.games,
                    map_preset_id=args.map_preset_id,
                    max_rounds=args.max_rounds,
                    max_moves=args.max_moves,
                    stagnation_limit=args.stagnation_limit,
                    seed=args.seed + index,
                )
            )
        _print_suite_table(summaries)
        for summary in summaries:
            print(_format_summary_line(summary))
        return

    summary = evaluate_difficulty(
        args.candidate,
        opponent_difficulty=args.opponent,
        games=args.games,
        map_preset_id=args.map_preset_id,
        max_rounds=args.max_rounds,
        max_moves=args.max_moves,
        stagnation_limit=args.stagnation_limit,
        seed=args.seed,
    )
    print(_format_summary_line(summary))
    print('seat_wins=' + ','.join(f'P{player}:{wins}' for player, wins in summary['seat_wins'].items()))


if __name__ == '__main__':
    main()
