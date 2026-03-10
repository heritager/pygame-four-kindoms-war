from dataclasses import dataclass

import numpy as np

from ..config.constants import (
    BOARD_SIZE,
    CITY_CAPITAL,
    CITY_MAJOR,
    CITY_SMALL,
    RESOURCE_GOLD_MINE,
    TERRAIN_FOREST,
    TERRAIN_MOUNTAIN,
    TERRAIN_PLAIN,
    TERRAIN_WATER,
)


FEATURE_NAMES = [
    'bias',
    'source_hp',
    'target_hp',
    'survivor_hp',
    'attack_hp_delta',
    'terrain_cost',
    'steps_left',
    'steps_ratio',
    'remaining_move_budget',
    'from_is_capital',
    'to_is_friendly',
    'to_is_neutral',
    'to_is_enemy',
    'to_has_mine',
    'to_city_small',
    'to_city_major',
    'to_city_capital',
    'attacker_survived',
    'defender_survived',
    'captured_city',
    'captured_capital',
    'before_enemy_capital_dist',
    'after_enemy_capital_dist',
    'before_strategic_dist',
    'after_strategic_dist',
    'target_threat_hp',
    'friendly_adjacent',
    'enemy_adjacent',
    'source_plain',
    'source_forest',
    'source_mountain',
    'source_water',
    'target_plain',
    'target_forest',
    'target_mountain',
    'target_water',
]


@dataclass(frozen=True)
class EncodedAction:
    from_pos: tuple[int, int]
    to_pos: tuple[int, int]
    action_id: int


def action_to_id(from_pos, to_pos):
    from_idx = from_pos[0] * BOARD_SIZE + from_pos[1]
    to_idx = to_pos[0] * BOARD_SIZE + to_pos[1]
    return from_idx * BOARD_SIZE * BOARD_SIZE + to_idx


def action_from_id(action_id):
    total_tiles = BOARD_SIZE * BOARD_SIZE
    from_idx, to_idx = divmod(int(action_id), total_tiles)
    from_pos = (from_idx // BOARD_SIZE, from_idx % BOARD_SIZE)
    to_pos = (to_idx // BOARD_SIZE, to_idx % BOARD_SIZE)
    return from_pos, to_pos


def enumerate_legal_actions(game):
    actions = []
    current_player = game.current_player
    for from_pos in game.get_player_soldiers(current_player):
        for to_pos in game.get_possible_moves_for(from_pos):
            actions.append(EncodedAction(from_pos=from_pos, to_pos=to_pos, action_id=action_to_id(from_pos, to_pos)))
    return actions


def encode_observation(game):
    current_player = game.current_player
    owners = game.board[:, :, 0]
    hp = game.board[:, :, 1].astype(np.float32)
    cities = game.board[:, :, 2]
    terrain = game.terrain
    move_count = game.move_count_grid.astype(np.float32)

    board = np.zeros((15, BOARD_SIZE, BOARD_SIZE), dtype=np.float32)
    board[0] = (owners == current_player)
    board[1] = ((owners > 0) & (owners != current_player))
    board[2] = (owners == 0)
    board[3] = hp / 99.0
    board[4] = (cities == CITY_SMALL)
    board[5] = (cities == CITY_MAJOR)
    board[6] = (cities == CITY_CAPITAL)
    board[7] = (game.resource_map == RESOURCE_GOLD_MINE)
    board[8] = (terrain == TERRAIN_PLAIN)
    board[9] = (terrain == TERRAIN_FOREST)
    board[10] = (terrain == TERRAIN_MOUNTAIN)
    board[11] = (terrain == TERRAIN_WATER)
    board[12] = move_count / 3.0
    board[13] = ((owners == current_player) & (hp <= 0))
    board[14] = (game.steps_left / max(1, game.steps_per_turn))

    scalars = np.array(
        [
            game.round_count / 50.0,
            game.steps_left / max(1, game.steps_per_turn),
            game.steps_per_turn / 10.0,
            len(game.players) / 4.0,
        ],
        dtype=np.float32,
    )
    return {
        'board': board,
        'scalars': scalars,
    }


def _terrain_one_hot(terrain_type):
    return [
        1.0 if terrain_type == TERRAIN_PLAIN else 0.0,
        1.0 if terrain_type == TERRAIN_FOREST else 0.0,
        1.0 if terrain_type == TERRAIN_MOUNTAIN else 0.0,
        1.0 if terrain_type == TERRAIN_WATER else 0.0,
    ]


def _adjacent_control_counts(game, pos, player):
    x, y = pos
    friendly = 0
    enemy = 0
    for dx, dy in ((0, 1), (1, 0), (0, -1), (-1, 0)):
        nx, ny = x + dx, y + dy
        if not (0 <= nx < BOARD_SIZE and 0 <= ny < BOARD_SIZE):
            continue
        owner = int(game.board[nx, ny, 0])
        if owner == player:
            friendly += 1
        elif owner > 0:
            enemy += 1
    return friendly, enemy


def extract_action_features(game, action, current_analysis=None, turn_steps=None):
    player = game.current_player
    from_pos = action.from_pos
    to_pos = action.to_pos
    if current_analysis is None:
        current_analysis = game.analyze_board_state(player, game.board)
    if turn_steps is None:
        turn_steps = game.calculate_steps_per_turn()

    simulated = game.simulate_ai_move(
        player,
        from_pos,
        to_pos,
        game.board,
        game.move_count_grid,
        game.steps_left,
    )
    if simulated is None:
        raise ValueError(f'Illegal action cannot be encoded: {action}')

    simulated_analysis = game.analyze_board_state(player, simulated['board'])

    x1, y1 = from_pos
    x2, y2 = to_pos
    source_player, source_hp, source_city_type, _ = game.board[x1, y1]
    target_player, target_hp, target_city_type, _ = game.board[x2, y2]
    source_terrain = int(game.terrain[x1][y1])
    target_terrain = int(game.terrain[x2][y2])
    terrain_cost = int(simulated['terrain_cost'])
    move_count = int(game.move_count_grid[x1, y1])
    before_enemy_cap_dist = game.distance_to_nearest_enemy_capital(player, from_pos)
    after_enemy_cap_dist = game.distance_to_nearest_enemy_capital(player, to_pos)
    before_strategic_dist = game.distance_to_nearest_strategic_target(
        player,
        from_pos,
        game.board,
        analysis=current_analysis,
    )
    after_strategic_dist = game.distance_to_nearest_strategic_target(
        player,
        to_pos,
        simulated['board'],
        analysis=simulated_analysis,
    )
    target_threat = game.get_max_enemy_threat_against(
        player,
        to_pos,
        simulated['board'],
        turn_steps,
        analysis=simulated_analysis,
    )
    friendly_adjacent, enemy_adjacent = _adjacent_control_counts(game, to_pos, player)
    target_has_mine = game.resource_map[x2, y2] == RESOURCE_GOLD_MINE

    features = [
        1.0,
        float(source_hp) / 99.0,
        float(target_hp) / 99.0,
        float(simulated['survivor_hp']) / 99.0,
        float(source_hp - target_hp) / 99.0,
        float(terrain_cost) / 2.0,
        float(game.steps_left) / 10.0,
        float(game.steps_left) / max(1, game.steps_per_turn),
        float(3 - move_count) / 3.0,
        1.0 if source_city_type == CITY_CAPITAL else 0.0,
        1.0 if target_player == player else 0.0,
        1.0 if target_player == 0 else 0.0,
        1.0 if target_player > 0 and target_player != player else 0.0,
        1.0 if target_has_mine else 0.0,
        1.0 if target_city_type == CITY_SMALL else 0.0,
        1.0 if target_city_type == CITY_MAJOR else 0.0,
        1.0 if target_city_type == CITY_CAPITAL else 0.0,
        1.0 if simulated['attacker_survived'] else 0.0,
        1.0 if simulated['defender_survived'] else 0.0,
        1.0 if simulated['captured_city'] else 0.0,
        1.0 if simulated['captured_capital'] else 0.0,
        float(before_enemy_cap_dist) / 40.0,
        float(after_enemy_cap_dist) / 40.0,
        float(before_strategic_dist) / 40.0,
        float(after_strategic_dist) / 40.0,
        float(target_threat) / 99.0,
        float(friendly_adjacent) / 4.0,
        float(enemy_adjacent) / 4.0,
    ]
    features.extend(_terrain_one_hot(source_terrain))
    features.extend(_terrain_one_hot(target_terrain))
    return np.asarray(features, dtype=np.float32)
