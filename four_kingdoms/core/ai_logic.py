import random

import numpy as np
import pygame

from ..config.constants import (
    AI_DIFFICULTY_EASY,
    AI_DIFFICULTY_HARD,
    AI_DIFFICULTY_LABELS,
    AI_DIFFICULTY_NORMAL,
    BOARD_SIZE,
    CITY_CAPITAL,
    CITY_MAJOR,
    CITY_SMALL,
    RESOURCE_GOLD_MINE,
)


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
SCORE_CAPTURE_MAJOR_CITY = 148  # 占领大城市
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


class AIMixin:
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

    def distance_to_nearest_strategic_target(self, player, pos, board_state):
        x, y = pos
        best_distance = 10**9

        for i in range(BOARD_SIZE):
            for j in range(BOARD_SIZE):
                owner, _, city_type, _ = board_state[i, j]
                has_mine = self.resource_map[i, j] == RESOURCE_GOLD_MINE

                is_target = False
                if city_type == CITY_CAPITAL and owner > 0 and owner != player:
                    is_target = True
                elif city_type in (CITY_MAJOR, CITY_SMALL) and owner != player:
                    is_target = True
                elif has_mine and owner != player:
                    is_target = True

                if is_target:
                    distance = abs(x - i) + abs(y - j)
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

    def get_max_enemy_threat_against(self, player, target_pos, board_state, enemy_steps):
        target_x, target_y = target_pos
        max_threat_hp = 0

        for i in range(BOARD_SIZE):
            for j in range(BOARD_SIZE):
                enemy_player, enemy_hp, _, _ = board_state[i, j]
                if enemy_player <= 0 or enemy_player == player or enemy_hp <= 0:
                    continue

                target_owner, target_hp, _, _ = board_state[target_x, target_y]
                if target_owner == enemy_player and target_hp > 0:
                    continue

                terrain_cost, error = self.get_terrain_cost((i, j), target_pos)
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

    def score_ai_move(self, player, from_pos, to_pos, board_state, move_count_state, steps_left, add_noise=True):
        simulated = self.simulate_ai_move(player, from_pos, to_pos, board_state, move_count_state, steps_left)
        if simulated is None:
            return -10**9, None

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
        before_obj_dist = self.distance_to_nearest_strategic_target(player, from_pos, board_state)
        after_obj_dist = self.distance_to_nearest_strategic_target(player, to_pos, simulated['board'])
        if after_obj_dist < before_obj_dist:
            score += (before_obj_dist - after_obj_dist) * SCORE_APPROACH_STRATEGIC_PER_STEP
        elif after_obj_dist > before_obj_dist:
            score += SCORE_AWAY_FROM_STRATEGIC

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
            cap_threat = self.get_max_enemy_threat_against(
                player,
                own_capital,
                simulated['board'],
                self.calculate_steps_per_turn(),
            )
            if cap_threat > 0:
                before_own_dist = abs(from_pos[0] - own_capital[0]) + abs(from_pos[1] - own_capital[1])
                after_own_dist = abs(to_pos[0] - own_capital[0]) + abs(to_pos[1] - own_capital[1])
                if after_own_dist < before_own_dist:
                    score += SCORE_DEFEND_CAPITAL_APPROACH
                elif after_own_dist > before_own_dist:
                    score += SCORE_DEFEND_CAPITAL_AWAY

        # 若己方金矿受威胁，鼓励回防（金矿是重要资源）
        own_mines = []
        for i in range(BOARD_SIZE):
            for j in range(BOARD_SIZE):
                if self.resource_map[i, j] == RESOURCE_GOLD_MINE:
                    mine_owner = simulated['board'][i, j, 0]
                    mine_hp = simulated['board'][i, j, 1]
                    if mine_owner == player and mine_hp > 0:
                        own_mines.append((i, j))

        for mine_pos in own_mines:
            mine_threat = self.get_max_enemy_threat_against(
                player,
                mine_pos,
                simulated['board'],
                self.calculate_steps_per_turn(),
            )
            if mine_threat > 0:
                before_mine_dist = abs(from_pos[0] - mine_pos[0]) + abs(from_pos[1] - mine_pos[1])
                after_mine_dist = abs(to_pos[0] - mine_pos[0]) + abs(to_pos[1] - mine_pos[1])
                if after_mine_dist < before_mine_dist:
                    score += 12  # 回防金矿加分
                elif after_mine_dist > before_mine_dist:
                    score -= 8  # 离开金矿减分

        # 威胁评估：避免走到下一手可被轻易反杀的位置
        if attacker_survived:
            enemy_steps = self.calculate_steps_per_turn()
            threat_hp = self.get_max_enemy_threat_against(player, to_pos, simulated['board'], enemy_steps)
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

        scored = []
        for from_pos, to_pos in self.enumerate_ai_actions(player, board_state, move_count_state, steps_left):
            score, _ = self.score_ai_move(player, from_pos, to_pos, board_state, move_count_state, steps_left)
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
                        score += 72
                    elif city_type == CITY_SMALL:
                        score += 40
                    if has_mine:
                        score += 98
                elif owner > 0:
                    score -= 4 + hp * 1.1
                    if city_type == CITY_CAPITAL:
                        score -= 200
                    elif city_type == CITY_MAJOR:
                        score -= 52
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

        for from_pos, to_pos in first_actions:
            immediate_score, simulated = self.score_ai_move(
                player, from_pos, to_pos, self.board, self.move_count_grid, self.steps_left
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

    def choose_ai_action(self, player):
        difficulty = getattr(self, 'ai_difficulty', AI_DIFFICULTY_NORMAL)
        if difficulty == AI_DIFFICULTY_EASY:
            return self.choose_ai_action_easy(player)
        if difficulty == AI_DIFFICULTY_HARD:
            return self.choose_ai_action_hard(player)
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
