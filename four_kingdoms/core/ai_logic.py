import random
from pathlib import Path

import numpy as np
import pygame

from ..config.constants import (
    AI_DIFFICULTY_EASY,
    AI_DIFFICULTY_HARD,
    AI_DIFFICULTY_LEARNED,
    AI_DIFFICULTY_LABELS,
    AI_DIFFICULTY_NORMAL,
    BOARD_SIZE,
    CITY_CAPITAL,
    CITY_MAJOR,
    CITY_SMALL,
    RESOURCE_GOLD_MINE,
)
from ..ml.action_encoder import EncodedAction, extract_action_features
from ..ml.policy import load_action_policy


# ========== AI 评分常量 ==========
# 基础收益
SCORE_MOVE_TO_NEUTRAL = 34  # 移动到无主位置的基础收益
SCORE_ATTACK_WIN_BASE = 98  # 攻击获胜基础分
SCORE_ATTACK_WIN_PER_HP = 2  # 攻击获胜每点敌方血量加分（上限 44）
SCORE_ATTACK_WIN_MAX_HP_BONUS = 44
SCORE_ATTACK_LOSS = -52  # 攻击失败扣分
SCORE_ATTACK_DRAW = 24  # 同归于尽加分

# 金矿价值（金矿每轮产 5 血，是重要战略资源，优先级高于普通城市）
SCORE_ENEMY_MINE = 180  # 夺取敌方金矿（+48）
SCORE_NEUTRAL_MINE = 140  # 占领中立金矿（+48）
SCORE_OWN_EMPTY_MINE = 100  # 己方空矿补驻军（+28）
SCORE_MINE_GAIN_PER_HP = 55  # 每点产兵增量价值（+13）
SCORE_MINE_FULL_BONUS = 40  # 满产额外加分（+12）

# 城市/首都价值
SCORE_CAPTURE_CAPITAL = 520  # 占领首都
SCORE_CAPTURE_MAJOR_CITY = 172  # 占领大城市
SCORE_CAPTURE_SMALL_CITY = 98  # 占领小城市

# 距离价值
SCORE_APPROACH_ENEMY_CAPITAL_PER_STEP = 8  # 接近敌方首都每格加分
SCORE_AWAY_FROM_ENEMY_CAPITAL = -3  # 远离敌方首都扣分
SCORE_APPROACH_STRATEGIC_PER_STEP = 7  # 接近战略目标每格加分
SCORE_AWAY_FROM_STRATEGIC = -4  # 远离战略目标扣分

# 连击潜力
SCORE_CHAIN_BASE = 36  # 连击基础分
SCORE_CHAIN_PER_TARGET = 24  # 每个额外目标加分
SCORE_CHAIN_MAX = 96  # 连击加分上限

# 首都保护
SCORE_LEAVE_CAPITAL_PENALTY = -70  # 离开首都驻军扣分
SCORE_DEFEND_CAPITAL_APPROACH = 16  # 回防首都加分
SCORE_DEFEND_CAPITAL_AWAY = -10  # 远离受威胁首都扣分

# 威胁评估风险系数
RISK_FACTOR_ENEMY_CAPITAL = 0.18  # 敌方首都风险系数
RISK_FACTOR_ENEMY_CITY_OR_MINE = 0.42  # 敌方城市/金矿风险系数
RISK_FACTOR_NEUTRAL_CITY_OR_MINE = 0.62  # 中立城市/金矿风险系数
RISK_FACTOR_STRATEGIC = 0.7  # 战略目标风险系数
RISK_FACTOR_DEFAULT = 1.0  # 默认风险系数

# 威胁评估计算
SCORE_THREAT_BASE = 130  # 威胁基础扣分
SCORE_THREAT_PER_HP_DIFF = 8  # 每点血量差扣分
SCORE_THREAT_LOW_PER_DIFF = 4  # 低威胁每点差扣分
SCORE_THREAT_SURVIVOR_FACTOR = 0.6  # 幸存者血量系数

# 行动点效率
SCORE_ACTION_POINT_EFFICIENCY = 9  # 每点额外行动点消耗扣分

# 随机噪声
NOISE_SCALE = 0.2  # 简单/普通难度随机噪声范围

# 学习策略混合决策
LEARNED_POLICY_TOP_K = 8
LEARNED_POLICY_MIN_K = 4
LEARNED_POLICY_PRIOR_WEIGHT = 24
LEARNED_POLICY_FOLLOWUP_WEIGHT = 0.65

# 路径 / 支援 / 反重复
SCORE_PRIORITY_ALIGNMENT = 22
SCORE_CAPITAL_SUPPORT_PER_HP = 5
SCORE_CAPITAL_SUPPORT_STEP = 18
SCORE_CAPITAL_FATAL_THREAT_PENALTY = -180
SCORE_CAPITAL_THREAT_REDUCED = 24
SCORE_ASSET_SUPPORT_STEP = 11
SCORE_ASSET_SUPPORT_PER_HP = 2
SCORE_REVERSE_MOVE_PENALTY = -42
SCORE_IDLE_NEUTRAL_DRIFT = -24
SCORE_FORWARD_PRESSURE = 10


class AIMixin:
    def _load_learned_policy(self):
        if getattr(self, 'learned_policy', None) is not None:
            return self.learned_policy
        policy_paths = getattr(self, 'learned_policy_paths', None)
        if policy_paths is None:
            single_path = getattr(self, 'learned_policy_path', '')
            policy_paths = [single_path] if single_path else []

        existing_paths = [Path(path) for path in policy_paths if Path(path).exists()]
        if not existing_paths:
            display_path = Path(policy_paths[0]) if policy_paths else Path('models/linear_policy.npz')
            self.learned_policy_error = f'未找到学习策略模型: {display_path}'
            return None

        last_error = None
        for policy_path in existing_paths:
            try:
                self.learned_policy = load_action_policy(policy_path)
                self.learned_policy_error = None
                return self.learned_policy
            except Exception as exc:
                last_error = f'{policy_path.name}: {exc}'

        self.learned_policy_error = f'学习策略加载失败: {last_error}' if last_error else '学习策略加载失败'
        return None

    def analyze_board_state(self, player, board_state):
        strategic_targets = []
        own_mines = []
        enemy_units = []

        for i in range(BOARD_SIZE):
            for j in range(BOARD_SIZE):
                owner, hp, city_type, _ = board_state[i, j]
                hp = int(hp)
                has_mine = self.resource_map[i, j] == RESOURCE_GOLD_MINE

                if owner > 0 and owner != player and hp > 0:
                    enemy_units.append((i, j, int(owner), hp))

                if has_mine and owner == player and hp > 0:
                    own_mines.append((i, j))

                is_strategic = False
                if city_type == CITY_CAPITAL and owner > 0 and owner != player:
                    is_strategic = True
                elif city_type in (CITY_MAJOR, CITY_SMALL) and owner != player:
                    is_strategic = True
                elif has_mine and owner != player:
                    is_strategic = True

                if is_strategic:
                    strategic_targets.append((i, j))

        return {
            'strategic_targets': strategic_targets,
            'own_mines': own_mines,
            'enemy_units': enemy_units,
        }

    def get_local_friendly_hp(self, player, center_pos, board_state, radius=2):
        cx, cy = center_pos
        total_hp = 0
        for i in range(max(0, cx - radius), min(BOARD_SIZE, cx + radius + 1)):
            for j in range(max(0, cy - radius), min(BOARD_SIZE, cy + radius + 1)):
                if abs(i - cx) + abs(j - cy) > radius:
                    continue
                owner, hp, _, _ = board_state[i, j]
                if owner == player and hp > 0:
                    total_hp += int(hp)
        return total_hp

    def count_forward_pressure(self, player, pos, board_state):
        x, y = pos
        pressure = 0
        for i in range(max(0, x - 2), min(BOARD_SIZE, x + 3)):
            for j in range(max(0, y - 2), min(BOARD_SIZE, y + 3)):
                if abs(i - x) + abs(j - y) > 2:
                    continue
                owner, hp, city_type, _ = board_state[i, j]
                has_mine = self.resource_map[i, j] == RESOURCE_GOLD_MINE
                if owner > 0 and owner != player and hp > 0:
                    pressure += 1
                elif owner != player and (city_type > 0 or has_mine):
                    pressure += 1
        return pressure

    def iter_priority_objectives(self, player, board_state, analysis=None, turn_steps=None):
        board_analysis = analysis or self.analyze_board_state(player, board_state)
        if turn_steps is None:
            turn_steps = self.calculate_steps_per_turn()

        objectives = []
        seen = set()

        for x, y in board_analysis['strategic_targets']:
            if (x, y) in seen:
                continue
            owner, _, city_type, _ = board_state[x, y]
            has_mine = self.resource_map[x, y] == RESOURCE_GOLD_MINE
            if city_type == CITY_CAPITAL and owner > 0 and owner != player:
                weight = 38
            elif has_mine and owner > 0 and owner != player:
                weight = 28
            elif has_mine and owner == 0:
                weight = 24
            elif city_type == CITY_MAJOR and owner > 0 and owner != player:
                weight = 24
            elif city_type == CITY_MAJOR:
                weight = 18
            elif city_type == CITY_SMALL and owner > 0 and owner != player:
                weight = 15
            elif city_type == CITY_SMALL:
                weight = 11
            else:
                continue
            objectives.append(((x, y), float(weight), 'offense'))
            seen.add((x, y))

        own_capital = self.capitals.get(player)
        if own_capital is not None and board_state[own_capital[0], own_capital[1], 0] == player:
            cap_hp = int(board_state[own_capital[0], own_capital[1], 1])
            cap_threat = self.get_max_enemy_threat_against(
                player,
                own_capital,
                board_state,
                turn_steps,
                analysis=board_analysis,
            )
            if cap_threat > 0:
                weight = 42 + max(0, cap_threat - cap_hp) * 2
                objectives.append((own_capital, float(weight), 'defend_capital'))
                seen.add(own_capital)

        for i in range(BOARD_SIZE):
            for j in range(BOARD_SIZE):
                if (i, j) in seen:
                    continue
                owner, hp, city_type, _ = board_state[i, j]
                if owner != player:
                    continue
                has_mine = self.resource_map[i, j] == RESOURCE_GOLD_MINE
                if city_type == 0 and not has_mine:
                    continue
                threat = self.get_max_enemy_threat_against(
                    player,
                    (i, j),
                    board_state,
                    turn_steps,
                    analysis=board_analysis,
                )
                if threat <= 0:
                    continue
                asset_hp = int(hp)
                if has_mine:
                    base_weight = 22
                elif city_type == CITY_MAJOR:
                    base_weight = 16
                elif city_type == CITY_SMALL:
                    base_weight = 12
                else:
                    continue
                weight = base_weight + max(0, threat - asset_hp)
                objectives.append(((i, j), float(weight), 'defend_asset'))

        return objectives

    def get_priority_alignment(self, player, pos, board_state, analysis=None, turn_steps=None):
        objectives = self.iter_priority_objectives(
            player,
            board_state,
            analysis=analysis,
            turn_steps=turn_steps,
        )
        if not objectives:
            return 0.0

        x, y = pos
        best_alignment = 0.0
        for (tx, ty), weight, _ in objectives:
            distance = abs(x - tx) + abs(y - ty)
            alignment = weight / (distance + 1.0)
            if alignment > best_alignment:
                best_alignment = alignment
        return best_alignment

    def get_player_soldiers_from_state(self, player, board_state, move_count_state):
        soldiers = []
        for i in range(BOARD_SIZE):
            for j in range(BOARD_SIZE):
                owner, hp, _, _ = board_state[i, j]
                if owner == player and hp > 0 and move_count_state[i, j] < 3:
                    soldiers.append((i, j))
        return soldiers

    def get_possible_moves_for_state(self, player, pos, board_state, move_count_state, steps_left):
        x, y = pos
        owner, hp, _, _ = board_state[x, y]
        if owner != player or hp <= 0:
            return []
        if move_count_state[x, y] >= 3:
            return []

        possible_moves = []
        for target in self.get_move_candidates(pos):
            tx, ty = target
            target_player, target_hp, _, _ = board_state[tx, ty]
            if target_player == player and target_hp > 0:
                continue

            terrain_cost, error = self.get_terrain_cost(pos, target)
            if error:
                continue
            if steps_left < terrain_cost:
                continue
            possible_moves.append(target)

        return possible_moves

    def distance_to_nearest_enemy_capital(self, player, pos):
        enemy_caps = [self.capitals[p] for p in self.players if p != player and p in self.capitals]
        if not enemy_caps:
            return 0
        x, y = pos
        return min(abs(x - cx) + abs(y - cy) for cx, cy in enemy_caps)

    def distance_to_nearest_strategic_target(self, player, pos, board_state, analysis=None):
        x, y = pos
        best_distance = 10**9
        board_analysis = analysis or self.analyze_board_state(player, board_state)

        for target_x, target_y in board_analysis['strategic_targets']:
            distance = abs(x - target_x) + abs(y - target_y)
            if distance < best_distance:
                best_distance = distance

        return 0 if best_distance == 10**9 else best_distance

    def count_strategic_targets_in_reach(self, player, from_pos, board_state, steps_left):
        if steps_left <= 0:
            return 0

        count = 0
        for target in self.get_move_candidates(from_pos):
            terrain_cost, error = self.get_terrain_cost(from_pos, target)
            if error or terrain_cost > steps_left:
                continue

            tx, ty = target
            target_owner, _, target_city_type, _ = board_state[tx, ty]
            target_has_mine = self.resource_map[tx, ty] == RESOURCE_GOLD_MINE
            if target_owner == player:
                continue

            if target_city_type > 0 or target_has_mine:
                count += 1

        return count

    def get_max_enemy_threat_against(self, player, target_pos, board_state, enemy_steps, analysis=None):
        target_x, target_y = target_pos
        max_threat_hp = 0
        target_owner, target_hp, _, _ = board_state[target_x, target_y]
        board_analysis = analysis or self.analyze_board_state(player, board_state)

        for enemy_x, enemy_y, enemy_player, enemy_hp in board_analysis['enemy_units']:
            if target_owner == enemy_player and target_hp > 0:
                continue

            terrain_cost, error = self.get_terrain_cost((enemy_x, enemy_y), target_pos)
            if error or terrain_cost > enemy_steps:
                continue
            if enemy_hp > max_threat_hp:
                max_threat_hp = enemy_hp

        return max_threat_hp

    def estimate_mine_production_gain(self, board_state, pos, player):
        x, y = pos
        if self.resource_map[x, y] != RESOURCE_GOLD_MINE:
            return 0

        owner, hp, _, _ = board_state[x, y]
        if owner != player:
            return 0

        if hp > 0:
            return max(0, min(5, 99 - int(hp)))
        return 5

    def simulate_ai_move(self, player, from_pos, to_pos, board_state, move_count_state, steps_left):
        resolved, error = self._resolve_move_on_state(
            board_state,
            move_count_state,
            from_pos,
            to_pos,
            player,
            steps_left,
            copy_state=True,
        )
        if error:
            return None

        x2, y2 = to_pos
        attacker_survived = resolved['attacker_survived']
        target_player = resolved['target_player']
        target_city_type = resolved['target_city_type']
        captured_city = attacker_survived and target_city_type > 0 and target_player != player
        captured_capital = captured_city and target_city_type == CITY_CAPITAL

        return {
            'board': resolved['board'],
            'move_count': resolved['move_count'],
            'steps_left': steps_left - resolved['terrain_cost'],
            'terrain_cost': resolved['terrain_cost'],
            'attacker_survived': attacker_survived,
            'defender_survived': resolved['defender_survived'],
            'survivor_hp': resolved['survivor_hp'],
            'source_hp': resolved['source_hp'],
            'target_player': int(target_player),
            'target_hp': resolved['target_hp'],
            'target_city_type': int(target_city_type),
            'captured_city': captured_city,
            'captured_capital': captured_capital,
            'from_pos': from_pos,
            'to_pos': to_pos,
        }

    def score_ai_move(
        self,
        player,
        from_pos,
        to_pos,
        board_state,
        move_count_state,
        steps_left,
        add_noise=True,
        current_analysis=None,
        turn_steps=None,
    ):
        simulated = self.simulate_ai_move(player, from_pos, to_pos, board_state, move_count_state, steps_left)
        if simulated is None:
            return -10**9, None

        if turn_steps is None:
            turn_steps = self.calculate_steps_per_turn()
        if current_analysis is None:
            current_analysis = self.analyze_board_state(player, board_state)
        simulated_analysis = self.analyze_board_state(player, simulated['board'])

        score = 0.0
        target_player = simulated['target_player']
        target_hp = simulated['target_hp']
        target_city_type = simulated['target_city_type']
        attacker_survived = simulated['attacker_survived']
        defender_survived = simulated['defender_survived']
        target_has_mine = self.resource_map[to_pos[0], to_pos[1]] == RESOURCE_GOLD_MINE
        target_is_enemy_capital = target_city_type == CITY_CAPITAL and target_player > 0 and target_player != player
        target_is_enemy_city = target_city_type in (CITY_MAJOR, CITY_SMALL) and target_player > 0 and target_player != player
        target_is_neutral_city = target_city_type in (CITY_MAJOR, CITY_SMALL) and target_player == 0
        target_is_enemy_mine = target_has_mine and target_player > 0 and target_player != player
        target_is_neutral_mine = target_has_mine and target_player == 0
        target_is_strategic = (
            target_is_enemy_capital
            or target_is_enemy_city
            or target_is_neutral_city
            or target_is_enemy_mine
            or target_is_neutral_mine
        )

        # 扩张/进攻基础收益
        if target_player == 0:
            score += SCORE_MOVE_TO_NEUTRAL
        elif target_player != player and target_hp > 0:
            if attacker_survived:
                score += SCORE_ATTACK_WIN_BASE + min(SCORE_ATTACK_WIN_MAX_HP_BONUS, target_hp * SCORE_ATTACK_WIN_PER_HP)
            elif defender_survived:
                score += SCORE_ATTACK_LOSS
            else:
                score += SCORE_ATTACK_DRAW

        # 金矿价值：按”下一轮预期产兵增量”打分，优先高产矿。
        if target_has_mine:
            mine_gain = self.estimate_mine_production_gain(simulated['board'], to_pos, player)
            if attacker_survived and mine_gain > 0:
                if target_is_enemy_mine:
                    score += SCORE_ENEMY_MINE
                elif target_is_neutral_mine:
                    score += SCORE_NEUTRAL_MINE
                else:
                    # 己方空矿补驻军同样有价值
                    score += SCORE_OWN_EMPTY_MINE
                score += mine_gain * SCORE_MINE_GAIN_PER_HP
                if mine_gain == 5:
                    score += SCORE_MINE_FULL_BONUS

        # 城市/首都价值
        if simulated['captured_capital']:
            score += SCORE_CAPTURE_CAPITAL
        elif simulated['captured_city']:
            if target_city_type == CITY_MAJOR:
                score += SCORE_CAPTURE_MAJOR_CITY
            elif target_city_type == CITY_SMALL:
                score += SCORE_CAPTURE_SMALL_CITY

        # 接近敌方首都的长期价值
        before_dist = self.distance_to_nearest_enemy_capital(player, from_pos)
        after_dist = self.distance_to_nearest_enemy_capital(player, to_pos)
        if after_dist < before_dist:
            score += (before_dist - after_dist) * SCORE_APPROACH_ENEMY_CAPITAL_PER_STEP
        elif after_dist > before_dist:
            score += SCORE_AWAY_FROM_ENEMY_CAPITAL

        # 接近战略目标（城市/首都/金矿）的价值
        before_obj_dist = self.distance_to_nearest_strategic_target(
            player,
            from_pos,
            board_state,
            analysis=current_analysis,
        )
        after_obj_dist = self.distance_to_nearest_strategic_target(
            player,
            to_pos,
            simulated['board'],
            analysis=simulated_analysis,
        )
        if after_obj_dist < before_obj_dist:
            score += (before_obj_dist - after_obj_dist) * SCORE_APPROACH_STRATEGIC_PER_STEP
        elif after_obj_dist > before_obj_dist:
            score += SCORE_AWAY_FROM_STRATEGIC

        # 朝“当前最高优先级目标”收敛：防首都 > 保矿/保城 > 抢矿/夺城/打首都。
        before_alignment = self.get_priority_alignment(
            player,
            from_pos,
            board_state,
            analysis=current_analysis,
            turn_steps=turn_steps,
        )
        after_alignment = self.get_priority_alignment(
            player,
            to_pos,
            simulated['board'],
            analysis=simulated_analysis,
            turn_steps=turn_steps,
        )
        score += (after_alignment - before_alignment) * SCORE_PRIORITY_ALIGNMENT

        # 连击潜力：若移动后还能继续威胁战略点，则鼓励推进。
        if attacker_survived and simulated['steps_left'] > 0:
            chain_targets = self.count_strategic_targets_in_reach(
                player,
                to_pos,
                simulated['board'],
                simulated['steps_left'],
            )
            if chain_targets > 0:
                score += min(SCORE_CHAIN_MAX, SCORE_CHAIN_BASE + chain_targets * SCORE_CHAIN_PER_TARGET)

        # 保护己方首都：避免首都驻军轻易外出
        if self.capitals.get(player) == from_pos:
            score += SCORE_LEAVE_CAPITAL_PENALTY

        # 若己方首都受威胁，鼓励回防
        own_capital = self.capitals.get(player)
        if own_capital is not None:
            cap_hp_before = int(board_state[own_capital[0], own_capital[1], 1])
            cap_hp_after = int(simulated['board'][own_capital[0], own_capital[1], 1])
            cap_support_before = self.get_local_friendly_hp(player, own_capital, board_state, radius=2)
            cap_support_after = self.get_local_friendly_hp(player, own_capital, simulated['board'], radius=2)
            cap_threat_before = self.get_max_enemy_threat_against(
                player,
                own_capital,
                board_state,
                turn_steps,
                analysis=current_analysis,
            )
            cap_threat = self.get_max_enemy_threat_against(
                player,
                own_capital,
                simulated['board'],
                turn_steps,
                analysis=simulated_analysis,
            )
            if cap_threat_before > cap_threat:
                score += (cap_threat_before - cap_threat) * SCORE_CAPITAL_THREAT_REDUCED
            if cap_threat > 0:
                before_own_dist = abs(from_pos[0] - own_capital[0]) + abs(from_pos[1] - own_capital[1])
                after_own_dist = abs(to_pos[0] - own_capital[0]) + abs(to_pos[1] - own_capital[1])
                score += (cap_support_after - cap_support_before) * SCORE_CAPITAL_SUPPORT_PER_HP
                if after_own_dist < before_own_dist:
                    score += SCORE_DEFEND_CAPITAL_APPROACH
                elif after_own_dist > before_own_dist:
                    score += SCORE_DEFEND_CAPITAL_AWAY
                if before_own_dist <= 2 and after_own_dist > before_own_dist:
                    score -= SCORE_CAPITAL_SUPPORT_STEP
                elif after_own_dist <= 1 and attacker_survived:
                    score += SCORE_CAPITAL_SUPPORT_STEP
            if cap_threat_before >= max(1, cap_hp_before) and cap_threat >= max(1, cap_hp_after):
                score += SCORE_CAPITAL_FATAL_THREAT_PENALTY
                if from_pos == own_capital:
                    score += SCORE_CAPITAL_FATAL_THREAT_PENALTY * 0.5

        # 若己方金矿受威胁，鼓励回防（金矿是重要资源）
        for mine_pos in current_analysis['own_mines']:
            mine_threat = self.get_max_enemy_threat_against(
                player,
                mine_pos,
                board_state,
                turn_steps,
                analysis=current_analysis,
            )
            if mine_threat > 0:
                mine_support_before = self.get_local_friendly_hp(player, mine_pos, board_state, radius=1)
                mine_support_after = self.get_local_friendly_hp(player, mine_pos, simulated['board'], radius=1)
                before_mine_dist = abs(from_pos[0] - mine_pos[0]) + abs(from_pos[1] - mine_pos[1])
                after_mine_dist = abs(to_pos[0] - mine_pos[0]) + abs(to_pos[1] - mine_pos[1])
                score += (mine_support_after - mine_support_before) * SCORE_ASSET_SUPPORT_PER_HP
                if after_mine_dist < before_mine_dist:
                    score += SCORE_ASSET_SUPPORT_STEP
                elif after_mine_dist > before_mine_dist:
                    score -= 8

        # 受威胁城市也要有守军，避免只会抢点不会保点。
        for i in range(BOARD_SIZE):
            for j in range(BOARD_SIZE):
                owner, hp, city_type, _ = board_state[i, j]
                if owner != player or city_type not in (CITY_SMALL, CITY_MAJOR):
                    continue
                city_threat = self.get_max_enemy_threat_against(
                    player,
                    (i, j),
                    board_state,
                    turn_steps,
                    analysis=current_analysis,
                )
                if city_threat <= 0:
                    continue
                city_support_before = self.get_local_friendly_hp(player, (i, j), board_state, radius=1)
                city_support_after = self.get_local_friendly_hp(player, (i, j), simulated['board'], radius=1)
                before_city_dist = abs(from_pos[0] - i) + abs(from_pos[1] - j)
                after_city_dist = abs(to_pos[0] - i) + abs(to_pos[1] - j)
                score += (city_support_after - city_support_before) * SCORE_ASSET_SUPPORT_PER_HP
                if after_city_dist < before_city_dist:
                    score += SCORE_ASSET_SUPPORT_STEP * (1.15 if city_type == CITY_MAJOR else 0.85)
                elif after_city_dist > before_city_dist and before_city_dist <= 2:
                    score -= 6
                if after_city_dist == 0 and attacker_survived:
                    score += 10

        # 威胁评估：避免走到下一手可被轻易反杀的位置
        if attacker_survived:
            threat_hp = self.get_max_enemy_threat_against(
                player,
                to_pos,
                simulated['board'],
                turn_steps,
                analysis=simulated_analysis,
            )
            survivor_hp = simulated['survivor_hp']
            if target_is_enemy_capital:
                risk_factor = RISK_FACTOR_ENEMY_CAPITAL
            elif target_is_enemy_city or target_is_enemy_mine:
                risk_factor = RISK_FACTOR_ENEMY_CITY_OR_MINE
            elif target_is_neutral_city or target_is_neutral_mine:
                risk_factor = RISK_FACTOR_NEUTRAL_CITY_OR_MINE
            elif target_is_strategic:
                risk_factor = RISK_FACTOR_STRATEGIC
            else:
                risk_factor = RISK_FACTOR_DEFAULT

            if threat_hp >= survivor_hp and threat_hp > 0:
                score -= (SCORE_THREAT_BASE + (threat_hp - survivor_hp) * SCORE_THREAT_PER_HP_DIFF) * risk_factor
            elif threat_hp > 0:
                score -= max(0, (threat_hp - survivor_hp * SCORE_THREAT_SURVIVOR_FACTOR) * SCORE_THREAT_LOW_PER_DIFF) * risk_factor

        # 行动点效率
        score -= (simulated['terrain_cost'] - 1) * SCORE_ACTION_POINT_EFFICIENCY

        # 减少“来回横跳”的重复步骤，优先持续推进。
        if board_state is self.board and getattr(self, 'last_move', None) == (to_pos, from_pos):
            score += SCORE_REVERSE_MOVE_PENALTY

        # 空地扩张如果既不接近目标，也不形成前压，就视为低质量漂移。
        if target_player == 0 and target_city_type == 0 and not target_has_mine:
            pressure_before = self.count_forward_pressure(player, from_pos, board_state)
            pressure_after = self.count_forward_pressure(player, to_pos, simulated['board'])
            if pressure_after > pressure_before:
                score += SCORE_FORWARD_PRESSURE * (pressure_after - pressure_before)
            elif after_alignment <= before_alignment:
                score += SCORE_IDLE_NEUTRAL_DRIFT

        # 普通/简单难度允许轻微随机打破同分；困难模式会关闭噪声。
        if add_noise:
            score += random.random() * NOISE_SCALE
        return score, simulated

    def enumerate_ai_actions(self, player, board_state, move_count_state, steps_left):
        actions = []
        for from_pos in self.get_player_soldiers_from_state(player, board_state, move_count_state):
            moves = self.get_possible_moves_for_state(player, from_pos, board_state, move_count_state, steps_left)
            for to_pos in moves:
                actions.append((from_pos, to_pos))
        return actions

    def estimate_best_followup_score(self, player, board_state, move_count_state, steps_left, limit=24):
        if steps_left <= 0:
            return 0.0

        current_analysis = self.analyze_board_state(player, board_state)
        turn_steps = self.calculate_steps_per_turn()
        scored = []
        for from_pos, to_pos in self.enumerate_ai_actions(player, board_state, move_count_state, steps_left):
            score, _ = self.score_ai_move(
                player,
                from_pos,
                to_pos,
                board_state,
                move_count_state,
                steps_left,
                current_analysis=current_analysis,
                turn_steps=turn_steps,
            )
            scored.append(score)

        if not scored:
            return 0.0

        scored.sort(reverse=True)
        return scored[0] if len(scored) <= limit else scored[:limit][0]

    def evaluate_board_state(self, player, board_state):
        own_capital = self.capitals.get(player)
        if own_capital is not None and board_state[own_capital[0], own_capital[1], 0] != player:
            return -10**8

        score = 0.0
        for i in range(BOARD_SIZE):
            for j in range(BOARD_SIZE):
                owner, hp, city_type, _ = board_state[i, j]
                has_mine = self.resource_map[i, j] == RESOURCE_GOLD_MINE
                hp = int(hp)

                if owner == player:
                    score += 6 + hp * 1.35
                    if city_type == CITY_CAPITAL:
                        score += 260
                    elif city_type == CITY_MAJOR:
                        score += 92
                    elif city_type == CITY_SMALL:
                        score += 40
                    if has_mine:
                        score += 98
                elif owner > 0:
                    score -= 4 + hp * 1.1
                    if city_type == CITY_CAPITAL:
                        score -= 200
                    elif city_type == CITY_MAJOR:
                        score -= 68
                    elif city_type == CITY_SMALL:
                        score -= 28
                    if has_mine:
                        score -= 72

        enemy_caps_alive = 0
        for enemy, cap_pos in self.capitals.items():
            if enemy == player:
                continue
            if board_state[cap_pos[0], cap_pos[1], 0] == enemy:
                enemy_caps_alive += 1
        score += (3 - enemy_caps_alive) * 180
        return score

    def _rank_actions_for_player(
        self,
        player,
        board_state,
        move_count_state,
        steps_left,
        limit=16,
        add_noise=True,
    ):
        current_analysis = self.analyze_board_state(player, board_state)
        turn_steps = self.calculate_steps_per_turn()
        ranked = []
        for from_pos, to_pos in self.enumerate_ai_actions(player, board_state, move_count_state, steps_left):
            action_score, simulated = self.score_ai_move(
                player,
                from_pos,
                to_pos,
                board_state,
                move_count_state,
                steps_left,
                add_noise=add_noise,
                current_analysis=current_analysis,
                turn_steps=turn_steps,
            )
            if simulated is None:
                continue
            ranked.append((action_score, from_pos, to_pos, simulated))

        ranked.sort(key=lambda item: item[0], reverse=True)
        return ranked[:limit]

    def _rank_enemy_counter_actions(self, player, board_state, per_enemy_limit=3):
        enemy_steps = self.calculate_steps_per_turn()
        enemy_move_count = np.zeros((BOARD_SIZE, BOARD_SIZE), dtype=int)
        counters = []

        for enemy in self.players:
            if enemy == player:
                continue
            ranked = self._rank_actions_for_player(
                enemy,
                board_state,
                enemy_move_count,
                enemy_steps,
                limit=per_enemy_limit,
                add_noise=False,
            )
            for action_score, from_pos, to_pos, simulated in ranked:
                counters.append((action_score, enemy, from_pos, to_pos, simulated))

        counters.sort(key=lambda item: item[0], reverse=True)
        return counters

    def _alphabeta_value(self, player, board_state, move_count_state, steps_left, depth, alpha, beta, maximizing):
        if depth <= 0:
            return self.evaluate_board_state(player, board_state)

        if maximizing:
            ranked = self._rank_actions_for_player(
                player,
                board_state,
                move_count_state,
                steps_left,
                limit=8,
                add_noise=False,
            )
            if not ranked:
                return self.evaluate_board_state(player, board_state)

            value = -10**9
            for _, _, _, simulated in ranked:
                child_value = self._alphabeta_value(
                    player,
                    simulated['board'],
                    simulated['move_count'],
                    simulated['steps_left'],
                    depth - 1,
                    alpha,
                    beta,
                    maximizing=False,
                )
                if child_value > value:
                    value = child_value
                if value > alpha:
                    alpha = value
                if beta <= alpha:
                    break
            return value

        counters = self._rank_enemy_counter_actions(player, board_state, per_enemy_limit=3)
        if not counters:
            return self.evaluate_board_state(player, board_state)

        value = 10**9
        for _, _, _, _, simulated in counters:
            child_value = self._alphabeta_value(
                player,
                simulated['board'],
                simulated['move_count'],
                steps_left,
                depth - 1,
                alpha,
                beta,
                maximizing=True,
            )
            if child_value < value:
                value = child_value
            if value < beta:
                beta = value
            if beta <= alpha:
                break
        return value

    def choose_ai_action_easy(self, player):
        ranked = self._rank_actions_for_player(
            player,
            self.board,
            self.move_count_grid,
            self.steps_left,
            limit=12,
            add_noise=True,
        )
        if not ranked:
            return None, None

        # 从 Top 6 动作中按排名加权随机选择（排名越前权重越高）
        top_pool_size = min(6, len(ranked))
        pool = ranked[:top_pool_size]
        # 权重：第 1 名权重最高，依次递减
        weights = [top_pool_size - idx for idx in range(top_pool_size)]
        picked = random.choices(pool, weights=weights, k=1)[0]
        return (picked[1], picked[2]), picked[0]

    def choose_ai_action_normal(self, player):
        first_actions = self.enumerate_ai_actions(player, self.board, self.move_count_grid, self.steps_left)
        if not first_actions:
            return None, None

        beam_width = 16
        candidates = []
        current_analysis = self.analyze_board_state(player, self.board)
        turn_steps = self.calculate_steps_per_turn()

        for from_pos, to_pos in first_actions:
            immediate_score, simulated = self.score_ai_move(
                player,
                from_pos,
                to_pos,
                self.board,
                self.move_count_grid,
                self.steps_left,
                current_analysis=current_analysis,
                turn_steps=turn_steps,
            )
            if simulated is None:
                continue
            candidates.append((immediate_score, from_pos, to_pos, simulated))

        if not candidates:
            return None, None

        candidates.sort(key=lambda item: item[0], reverse=True)
        candidates = candidates[:beam_width]

        best_action = None
        best_total_score = -10**9

        for immediate_score, from_pos, to_pos, simulated in candidates:
            followup_score = self.estimate_best_followup_score(
                player,
                simulated['board'],
                simulated['move_count'],
                simulated['steps_left'],
            )
            total_score = immediate_score + 0.82 * followup_score
            if total_score > best_total_score:
                best_total_score = total_score
                best_action = (from_pos, to_pos)

        return best_action, best_total_score

    def choose_ai_action_hard(self, player):
        ranked = self._rank_actions_for_player(
            player,
            self.board,
            self.move_count_grid,
            self.steps_left,
            limit=10,
            add_noise=False,
        )
        if not ranked:
            return None, None

        best_action = None
        best_value = -10**9
        alpha = -10**9
        beta = 10**9

        for immediate_score, from_pos, to_pos, simulated in ranked:
            reply_value = self._alphabeta_value(
                player,
                simulated['board'],
                simulated['move_count'],
                simulated['steps_left'],
                depth=1,
                alpha=alpha,
                beta=beta,
                maximizing=False,
            )
            combined = reply_value + immediate_score * 0.2
            if combined > best_value:
                best_value = combined
                best_action = (from_pos, to_pos)
            if best_value > alpha:
                alpha = best_value

        return best_action, best_value

    def choose_ai_action_learned(self, player):
        policy = self._load_learned_policy()
        if policy is None:
            if hasattr(self, 'log') and self.learned_policy_error:
                self.log.append(f'{self.learned_policy_error}，回退到普通AI')
                self.learned_policy_error = None
            return self.choose_ai_action_normal(player)

        actions = self.enumerate_ai_actions(player, self.board, self.move_count_grid, self.steps_left)
        if not actions:
            return None, None

        current_analysis = self.analyze_board_state(player, self.board)
        turn_steps = self.calculate_steps_per_turn()
        feature_rows = []
        for from_pos, to_pos in actions:
            feature_rows.append(
                (
                    from_pos,
                    to_pos,
                    self._extract_learned_features(from_pos, to_pos, current_analysis, turn_steps),
                )
            )

        if not feature_rows:
            return None, None

        feature_matrix = np.stack([row[2] for row in feature_rows], axis=0)
        policy_scores = policy.score_candidates(feature_matrix)
        if policy_scores.size == 0:
            return None, None

        heuristic_ranked = self._rank_actions_for_player(
            player,
            self.board,
            self.move_count_grid,
            self.steps_left,
            limit=2,
            add_noise=False,
        )
        action_index_map = {
            (from_pos, to_pos): index for index, (from_pos, to_pos, _) in enumerate(feature_rows)
        }
        candidate_indices = set()

        top_k = min(
            len(feature_rows),
            max(LEARNED_POLICY_MIN_K, min(LEARNED_POLICY_TOP_K, len(feature_rows))),
        )
        policy_order = np.argsort(policy_scores)[::-1]
        candidate_indices.update(int(index) for index in policy_order[:top_k])

        for _, from_pos, to_pos, _ in heuristic_ranked:
            mapped_index = action_index_map.get((from_pos, to_pos))
            if mapped_index is not None:
                candidate_indices.add(mapped_index)

        score_std = float(np.std(policy_scores))
        score_mean = float(np.mean(policy_scores))
        score_scale = score_std if score_std > 1e-6 else 1.0

        best_action = None
        best_score = -10**9
        for candidate_index in candidate_indices:
            from_pos, to_pos, _ = feature_rows[candidate_index]
            immediate_score, simulated = self.score_ai_move(
                player,
                from_pos,
                to_pos,
                self.board,
                self.move_count_grid,
                self.steps_left,
                add_noise=False,
                current_analysis=current_analysis,
                turn_steps=turn_steps,
            )
            if simulated is None:
                continue

            followup_score = self.estimate_best_followup_score(
                player,
                simulated['board'],
                simulated['move_count'],
                simulated['steps_left'],
                limit=12,
            )
            policy_prior = ((float(policy_scores[candidate_index]) - score_mean) / score_scale) * LEARNED_POLICY_PRIOR_WEIGHT
            combined_score = immediate_score + followup_score * LEARNED_POLICY_FOLLOWUP_WEIGHT + policy_prior
            if combined_score > best_score:
                best_score = combined_score
                best_action = (from_pos, to_pos)

        if best_action is None:
            return self.choose_ai_action_normal(player)
        return best_action, best_score

    def _extract_learned_features(self, from_pos, to_pos, current_analysis, turn_steps):
        action = EncodedAction(from_pos=from_pos, to_pos=to_pos, action_id=-1)
        return extract_action_features(
            self,
            action,
            current_analysis=current_analysis,
            turn_steps=turn_steps,
        )

    def choose_ai_action(self, player):
        difficulty = getattr(self, 'ai_difficulty', AI_DIFFICULTY_NORMAL)
        if difficulty == AI_DIFFICULTY_EASY:
            return self.choose_ai_action_easy(player)
        if difficulty == AI_DIFFICULTY_HARD:
            return self.choose_ai_action_hard(player)
        if difficulty == AI_DIFFICULTY_LEARNED:
            return self.choose_ai_action_learned(player)
        return self.choose_ai_action_normal(player)

    def perform_ai_action(self):
        if self.current_player not in self.ai_players:
            return False

        best_action, plan_score = self.choose_ai_action(self.current_player)
        if best_action is None:
            self.steps_left = 0
            self.log.append(f'玩家{self.current_player}(AI)无可执行动作，结束回合')
            return False

        success, message = self.move_soldier(best_action[0], best_action[1])
        if success:
            difficulty = AI_DIFFICULTY_LABELS.get(getattr(self, 'ai_difficulty', AI_DIFFICULTY_NORMAL), '普通')
            self.log.append(f'玩家{self.current_player}(AI-{difficulty})行动: {message} (评估{plan_score:.1f})')
            return True

        self.steps_left = 0
        self.log.append(f'玩家{self.current_player}(AI)行动失败: {message}')
        return False

    def maybe_run_ai_turn(self):
        if self.game_over or self.current_player not in self.ai_players:
            return

        now = pygame.time.get_ticks()
        if now - self.last_ai_action_ms < self.ai_action_delay_ms:
            return
        self.last_ai_action_ms = now

        moved = self.perform_ai_action()
        if self.game_over:
            return
        if self.steps_left <= 0 or not moved:
            self.next_player()
