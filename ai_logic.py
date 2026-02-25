import random

import pygame

from constants import (
    BOARD_SIZE,
    CITY_CAPITAL,
    CITY_MAJOR,
    CITY_SMALL,
    RESOURCE_GOLD_MINE,
    TERRAIN_WATER,
)


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

    def simulate_ai_move(self, player, from_pos, to_pos, board_state, move_count_state, steps_left):
        x1, y1 = from_pos
        x2, y2 = to_pos
        source_player, source_hp, source_city_type, _ = board_state[x1, y1]

        if source_player != player or source_hp <= 0:
            return None
        if move_count_state[x1, y1] >= 3:
            return None

        terrain_cost, terrain_error = self.get_terrain_cost(from_pos, to_pos)
        if terrain_error or terrain_cost > steps_left:
            return None

        target_player, target_hp, target_city_type, _ = board_state[x2, y2]
        if target_player == player and target_hp > 0:
            return None

        board_copy = board_state.copy()
        move_count_copy = move_count_state.copy()
        move_count = move_count_copy[x1, y1]

        attacker_survived = False
        survivor_hp = 0
        defender_survived = False

        if target_player != 0 and target_hp > 0:
            if source_hp > target_hp:
                survivor_hp = source_hp - target_hp
                board_copy[x2, y2] = [player, survivor_hp, target_city_type, 0]
                attacker_survived = True
            elif source_hp < target_hp:
                survivor_hp = target_hp - source_hp
                board_copy[x2, y2] = [target_player, survivor_hp, target_city_type, 0]
                defender_survived = True
            else:
                board_copy[x2, y2] = [0, 0, target_city_type, 0]
        else:
            survivor_hp = source_hp
            board_copy[x2, y2] = [player, survivor_hp, target_city_type, 0]
            attacker_survived = True

        board_copy[x1, y1] = [source_player, 0, source_city_type, 0]

        move_count_copy[x1, y1] = 0
        if attacker_survived:
            move_count_copy[x2, y2] = move_count + 1
        else:
            move_count_copy[x2, y2] = move_count_state[x2, y2]

        if attacker_survived and self.terrain[x2][y2] != TERRAIN_WATER:
            board_copy[x2, y2, 0] = player

        captured_city = attacker_survived and target_city_type > 0 and target_player != player
        captured_capital = captured_city and target_city_type == CITY_CAPITAL

        return {
            'board': board_copy,
            'move_count': move_count_copy,
            'steps_left': steps_left - terrain_cost,
            'terrain_cost': terrain_cost,
            'attacker_survived': attacker_survived,
            'defender_survived': defender_survived,
            'survivor_hp': survivor_hp,
            'source_hp': int(source_hp),
            'target_player': int(target_player),
            'target_hp': int(target_hp),
            'target_city_type': int(target_city_type),
            'captured_city': captured_city,
            'captured_capital': captured_capital,
            'from_pos': from_pos,
            'to_pos': to_pos,
        }

    def score_ai_move(self, player, from_pos, to_pos, board_state, move_count_state, steps_left):
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
            score += 34
        elif target_player != player and target_hp > 0:
            if attacker_survived:
                score += 98 + min(44, target_hp * 2)
            elif defender_survived:
                score -= 52
            else:
                score += 24

        # 金矿价值：优先抢占中立/敌方矿点。
        if target_has_mine:
            if target_is_neutral_mine:
                score += 96
            elif target_is_enemy_mine:
                score += 152

        # 城市/首都价值
        if simulated['captured_capital']:
            score += 520
        elif simulated['captured_city']:
            if target_city_type == CITY_MAJOR:
                score += 148
            elif target_city_type == CITY_SMALL:
                score += 98

        # 接近敌方首都的长期价值
        before_dist = self.distance_to_nearest_enemy_capital(player, from_pos)
        after_dist = self.distance_to_nearest_enemy_capital(player, to_pos)
        if after_dist < before_dist:
            score += (before_dist - after_dist) * 8
        elif after_dist > before_dist:
            score -= 3

        # 接近战略目标（城市/首都/金矿）的价值
        before_obj_dist = self.distance_to_nearest_strategic_target(player, from_pos, board_state)
        after_obj_dist = self.distance_to_nearest_strategic_target(player, to_pos, simulated['board'])
        if after_obj_dist < before_obj_dist:
            score += (before_obj_dist - after_obj_dist) * 7
        elif after_obj_dist > before_obj_dist:
            score -= 4

        # 连击潜力：若移动后还能继续威胁战略点，则鼓励推进。
        if attacker_survived and simulated['steps_left'] > 0:
            chain_targets = self.count_strategic_targets_in_reach(
                player,
                to_pos,
                simulated['board'],
                simulated['steps_left'],
            )
            if chain_targets > 0:
                score += min(96, 36 + chain_targets * 24)

        # 保护己方首都：避免首都驻军轻易外出
        if self.capitals.get(player) == from_pos:
            score -= 70

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
                    score += 16
                elif after_own_dist > before_own_dist:
                    score -= 10

        # 威胁评估：避免走到下一手可被轻易反杀的位置
        if attacker_survived:
            enemy_steps = self.calculate_steps_per_turn()
            threat_hp = self.get_max_enemy_threat_against(player, to_pos, simulated['board'], enemy_steps)
            survivor_hp = simulated['survivor_hp']
            if target_is_enemy_capital:
                risk_factor = 0.18
            elif target_is_enemy_city or target_is_enemy_mine:
                risk_factor = 0.42
            elif target_is_neutral_city or target_is_neutral_mine:
                risk_factor = 0.62
            elif target_is_strategic:
                risk_factor = 0.7
            else:
                risk_factor = 1.0

            if threat_hp >= survivor_hp and threat_hp > 0:
                score -= (130 + (threat_hp - survivor_hp) * 8) * risk_factor
            elif threat_hp > 0:
                score -= max(0, (threat_hp - survivor_hp * 0.6) * 4) * risk_factor

        # 行动点效率
        score -= (simulated['terrain_cost'] - 1) * 9

        # 轻微随机打破同分
        score += random.random() * 0.2
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

    def choose_ai_action(self, player):
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
            self.log.append(f'玩家{self.current_player}(AI)行动: {message} (评估{plan_score:.1f})')
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
