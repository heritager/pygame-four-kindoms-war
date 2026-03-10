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
    RESOURCE_GOLD_MINE,
)
from ..config.map_presets import DEFAULT_MAP_PRESET
from ..core.game_core import Game


AI_CHOICES = [
    AI_DIFFICULTY_EASY,
    AI_DIFFICULTY_NORMAL,
    AI_DIFFICULTY_HARD,
    AI_DIFFICULTY_LEARNED,
]


def _count_player_mines(game, player):
    mines = 0
    for i in range(game.board.shape[0]):
        for j in range(game.board.shape[1]):
            if game.resource_map[i, j] == RESOURCE_GOLD_MINE and int(game.board[i, j, 0]) == player:
                mines += 1
    return mines


def _build_game(map_preset_id, default_difficulty):
    game = Game(
        game_mode=MODE_SINGLE_AI,
        map_preset_id=map_preset_id,
        ai_difficulty=default_difficulty,
    )
    game.human_players = set()
    game.ai_players = set(game.players)
    return game


def _play_one_game(candidate_difficulty, opponent_difficulty, candidate_player, map_preset_id, max_rounds):
    game = _build_game(map_preset_id, opponent_difficulty)
    per_player_difficulty = {
        player: (candidate_difficulty if player == candidate_player else opponent_difficulty)
        for player in game.players
    }

    move_counter = 0
    max_moves = max(1, max_rounds) * 80

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
        if game.game_over:
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


def main():
    parser = argparse.ArgumentParser(description='Evaluate built-in AI difficulties with a low-memory headless benchmark.')
    parser.add_argument('--candidate', default=AI_DIFFICULTY_LEARNED, choices=AI_CHOICES, help='Difficulty being evaluated')
    parser.add_argument('--opponent', default=AI_DIFFICULTY_NORMAL, choices=AI_CHOICES, help='Difficulty used by the other three players')
    parser.add_argument('--games', type=int, default=12, help='Number of games to benchmark')
    parser.add_argument('--max-rounds', type=int, default=120, help='Round cap before using territory tiebreak')
    parser.add_argument('--map', dest='map_preset_id', default=DEFAULT_MAP_PRESET, help='Map preset id')
    parser.add_argument('--seed', type=int, default=7, help='Random seed')
    args = parser.parse_args()

    summary = evaluate_difficulty(
        args.candidate,
        opponent_difficulty=args.opponent,
        games=args.games,
        map_preset_id=args.map_preset_id,
        max_rounds=args.max_rounds,
        seed=args.seed,
    )
    print(
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
    print('seat_wins=' + ','.join(f'P{player}:{wins}' for player, wins in summary['seat_wins'].items()))


if __name__ == '__main__':
    main()
