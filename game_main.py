import sys
from collections import deque

import numpy as np
import pygame

from ai_logic import AIMixin
from constants import (
    BOARD_PIXEL_SIZE,
    BOARD_SIZE,
    CITY_CAPITAL,
    CITY_MAJOR,
    CITY_SMALL,
    HEIGHT,
    MODE_HOTSEAT,
    MODE_LABELS,
    MODE_SINGLE_AI,
    RESOURCE_GOLD_MINE,
    TERRAIN_PLAIN,
    TERRAIN_FOREST,
    TERRAIN_MOUNTAIN,
    TERRAIN_WATER,
)
from map_presets import DEFAULT_MAP_PRESET, get_map_preset
from map_generation import MapGenerationMixin
from render_mixin import RenderMixin


class Game(MapGenerationMixin, AIMixin, RenderMixin):
    def __init__(self, game_mode=MODE_SINGLE_AI, map_preset_id=DEFAULT_MAP_PRESET):
        self.game_mode = game_mode
        self.primary_human = 1
        self.map_preset = get_map_preset(map_preset_id)
        self.map_preset_id = self.map_preset['id']
        self.map_name = self.map_preset['name']
        self.reset_game()
        
    def reset_game(self):
        # 初始化地形
        self.generate_terrain()
        
        self.capitals = {
            1: (3, 3),
            2: (3, BOARD_SIZE - 4),
            3: (BOARD_SIZE - 4, 3),
            4: (BOARD_SIZE - 4, BOARD_SIZE - 4)
        }
        # 地形均衡，避免单侧大面积水域导致资源失衡
        self.rebalance_terrain_for_fairness(self.capitals)
        
        self.player_defeated = False  # 单人模式下玩家1被淘汰时用于观战提示

        # 初始化棋盘
        self.board = np.zeros((BOARD_SIZE, BOARD_SIZE, 4), dtype=int)
        
        # 士兵移动计数网格（替代ID系统）
        self.move_count_grid = np.zeros((BOARD_SIZE, BOARD_SIZE), dtype=int)
        self.resource_map = np.zeros((BOARD_SIZE, BOARD_SIZE), dtype=int)
        
        # 设置四个首都
        capital_positions = list(self.capitals.values())
        
        for idx, pos in enumerate(capital_positions):
            i, j = pos
            player_id = idx + 1
            self.board[i, j] = [player_id, 1, CITY_CAPITAL, 0]
            # 在首都周围生成一些初始领土
            for dx in range(-1, 2):
                for dy in range(-1, 2):
                    ni, nj = i + dx, j + dy
                    if 0 <= ni < BOARD_SIZE and 0 <= nj < BOARD_SIZE:
                        self.board[ni, nj, 0] = player_id
                        self.board[ni, nj, 1] = 1 if (dx, dy) == (0, 0) else 0

        capital_set = set(capital_positions)
        self.city_distribution_summary, self.city_distribution_by_zone = self.place_balanced_neutral_cities(
            capital_set,
            self.capitals
        )
        self.gold_mine_positions, self.gold_mine_by_zone = self.place_balanced_gold_mines(
            capital_set,
            self.capitals
        )
        
        # 游戏状态
        self.players = [1, 2, 3, 4]
        if self.game_mode == MODE_HOTSEAT:
            self.human_players = {1, 2, 3, 4}
            self.ai_players = set()
        else:
            self.human_players = {1}
            self.ai_players = {2, 3, 4}
        self.current_player = 1
        self.game_over = False
        self.winner = None
        
        # 回合和移动管理
        self.round_count = 1
        self.players_who_played_this_round = set()
        self.steps_per_turn = self.calculate_steps_per_turn()
        self.steps_left = self.steps_per_turn
        self.selected_pos = None
        self.move_history = []
        self.last_ai_action_ms = 0
        self.ai_action_delay_ms = 180
        self.move_animations = []
        self.combat_effects = []
        
        # 游戏日志
        self.log = [
            f"游戏开始! 模式: {MODE_LABELS.get(self.game_mode, self.game_mode)}",
            f"地图关卡: {self.map_name}",
            "四位玩家轮流进行游戏",
            f"第{self.round_count}轮开始, 每位玩家每回合{self.steps_per_turn}步",
        ]
        self.log.append(
            "城市分布: 保底小城{} 平原大城{} 平原小城{} 森林小城{} 山地小城{}".format(
                self.city_distribution_summary["home_small"],
                self.city_distribution_summary["plain_major"],
                self.city_distribution_summary["plain_small"],
                self.city_distribution_summary["forest_small"],
                self.city_distribution_summary["mountain_small"]
            )
        )
        self.log.append(
            "分区地形: " + " ".join(
                [
                    "P{} 水{:.0f}% 平{:.0f}% 山{:.0f}%".format(
                        player,
                        self.zone_terrain_ratio[player]["water"] * 100,
                        self.zone_terrain_ratio[player]["plain"] * 100,
                        self.zone_terrain_ratio[player]["mountain"] * 100
                    )
                    for player in [1, 2, 3, 4]
                ]
            )
        )
        self.log.append(
            "分区水域: " + " ".join(
                [f"P{player}:{self.zone_water_ratio[player]*100:.0f}%" for player in [1, 2, 3, 4]]
            )
        )
        self.log.append(
            "分区城市: " + " ".join(
                [
                    "P{}:{}".format(
                        player,
                        self.city_distribution_by_zone[player]["home_small"]
                        + self.city_distribution_by_zone[player]["major"]
                        + self.city_distribution_by_zone[player]["plain_small"]
                        + self.city_distribution_by_zone[player]["forest_small"]
                        + self.city_distribution_by_zone[player]["mountain_small"]
                    )
                    for player in [1, 2, 3, 4]
                ]
            )
        )
        self.log.append(
            "分区大城: " + " ".join(
                [
                    "P{}:{}".format(
                        player,
                        self.city_distribution_by_zone[player]["major"]
                    )
                    for player in [1, 2, 3, 4]
                ]
            )
        )
        self.log.append(
            "金矿分布: " + " ".join([f"P{player}:{self.gold_mine_by_zone[player]}" for player in [1, 2, 3, 4]])
        )
        self.log_scroll_offset = 0
        self.max_visible_logs = 3
        
        # 玩家领地计数
        self.update_territory_count()
        
        # 结束回合按钮
        self.end_turn_button = pygame.Rect(BOARD_PIXEL_SIZE + 96, HEIGHT - 132, 128, 38)
        self.button_hovered = False
        self.button_press_until_ms = 0
        self.help_button = pygame.Rect(BOARD_PIXEL_SIZE + 96, HEIGHT - 86, 128, 34)
        self.help_button_press_until_ms = 0
        
        # 可移动位置列表
        self.possible_moves = []
        self.hover_pos = None
        
        # UI 状态
        self.show_help = False
        self.help_close_button = pygame.Rect(0, 0, 0, 0)
    
    def calculate_territories(self):
        """计算包围领土 - 支持占领敌方无士兵领土"""
        visited = np.zeros((BOARD_SIZE, BOARD_SIZE), dtype=bool)
        captured_count = {1: 0, 2: 0, 3: 0, 4: 0}
        
        for i in range(BOARD_SIZE):
            for j in range(BOARD_SIZE):
                # 跳过已访问、水域、中立城市（中立城市本身不可归属）
                if (visited[i, j] or 
                    self.terrain[i][j] == TERRAIN_WATER or 
                    self.board[i, j, 2] > 0):  # 中立城市（city>0 且 owner=0）
                    continue
                    
                region = []
                queue = deque([(i, j)])
                region_owner = self.board[i, j, 0]   # 区域当前所有者（0 表示无主）
                border_owners = set()                 # 相邻的其他玩家
                border_has_unowned = False            # 相邻是否有无主普通格子
                has_soldiers = False                   # 区域内是否有士兵
                
                while queue:
                    x, y = queue.popleft()
                    if visited[x, y]:
                        continue
                    
                    # 确保当前格子所有者与 region_owner 一致（防止 BFS 错误）
                    if self.board[x, y, 0] != region_owner:
                        continue
                    visited[x, y] = True
                        
                    region.append((x, y))
                    
                    # 检查区域内士兵
                    if self.board[x, y, 1] > 0:
                        has_soldiers = True
                    
                    # 四方向探索
                    for dx, dy in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
                        nx, ny = x + dx, y + dy
                        
                        # 边界视为封闭
                        if nx < 0 or nx >= BOARD_SIZE or ny < 0 or ny >= BOARD_SIZE:
                            continue
                        # 水域视为封闭
                        if self.terrain[nx][ny] == TERRAIN_WATER:
                            continue
                        # 中立城市视为封闭
                        if self.board[nx, ny, 2] > 0:
                            continue
                        
                        n_owner = self.board[nx, ny, 0]
                        
                        if n_owner == region_owner:
                            # 相同所有者：加入队列继续探索
                            if not visited[nx, ny]:
                                queue.append((nx, ny))
                        else:
                            # 不同所有者或无主
                            if n_owner != 0:
                                border_owners.add(n_owner)      # 其他玩家领土
                            else:
                                border_has_unowned = True       # 无主普通格子
                
                # 归属条件：
                # 1. 区域内无士兵
                # 2. 边界上只有一个其他玩家
                # 3. 边界上没有无主普通格子（即被完全包围）
                if not has_soldiers and len(border_owners) == 1 and not border_has_unowned:
                    new_owner = next(iter(border_owners))
                    for x, y in region:
                        if self.board[x, y, 0] != new_owner:
                            self.board[x, y, 0] = new_owner
                            captured_count[new_owner] += 1
        
        summary = [f"玩家{player}+{count}格" for player, count in captured_count.items() if count > 0]
        if summary:
            self.log.append("包围占领: " + "，".join(summary))
    
    def calculate_steps_per_turn(self):
        if self.round_count <= 5:
            return 3
        elif self.round_count <= 10:
            return 6
        else:
            return 10
    
    def update_territory_count(self):
        self.territory_count = {1: 0, 2: 0, 3: 0, 4: 0}
        for i in range(BOARD_SIZE):
            for j in range(BOARD_SIZE):
                player = self.board[i, j, 0]
                terrain_type = self.terrain[i][j]
                if player > 0 and terrain_type != TERRAIN_WATER:
                    self.territory_count[player] += 1
    
    def get_terrain_cost(self, from_pos, to_pos):
        """返回移动消耗，非法移动返回 (None, 原因)"""
        x1, y1 = from_pos
        x2, y2 = to_pos
        
        if not (0 <= x2 < BOARD_SIZE and 0 <= y2 < BOARD_SIZE):
            return None, "目标位置超出边界"
        if from_pos == to_pos:
            return None, "不能原地移动"
        
        dx = abs(x1 - x2)
        dy = abs(y1 - y2)
        start_terrain = self.terrain[x1][y1]
        target_terrain = self.terrain[x2][y2]
        
        if start_terrain == TERRAIN_MOUNTAIN:
            if not ((dx == 1 and dy == 0) or (dx == 0 and dy == 1)):
                return None, "山脉中只能上下左右移动"
        elif start_terrain == TERRAIN_WATER:
            if target_terrain != TERRAIN_WATER:
                if dx > 1 or dy > 1:
                    return None, "水域登陆只能移动1格以内"
            else:
                # 使用曼哈顿距离，避免 (2,2) 这种超预期的远距离对角点。
                if dx + dy > 2:
                    return None, "水域中只能移动2格以内"
        elif start_terrain == TERRAIN_FOREST:
            if dx > 1 or dy > 1:
                return None, "森林中只能移动1格（包括斜向）"
        else:
            if not ((dx == 1 and dy == 0) or (dx == 0 and dy == 1)):
                return None, "平原中只能上下左右移动"
        
        terrain_cost = 2 if (start_terrain == TERRAIN_MOUNTAIN or target_terrain == TERRAIN_MOUNTAIN) else 1
        return terrain_cost, None
    
    def get_move_candidates(self, pos):
        x, y = pos
        start_terrain = self.terrain[x][y]
        candidates = []
        
        if start_terrain == TERRAIN_WATER:
            for dx in range(-2, 3):
                for dy in range(-2, 3):
                    if dx == 0 and dy == 0:
                        continue
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < BOARD_SIZE and 0 <= ny < BOARD_SIZE:
                        candidates.append((nx, ny))
        elif start_terrain == TERRAIN_FOREST:
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    if dx == 0 and dy == 0:
                        continue
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < BOARD_SIZE and 0 <= ny < BOARD_SIZE:
                        candidates.append((nx, ny))
        else:
            for dx, dy in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
                nx, ny = x + dx, y + dy
                if 0 <= nx < BOARD_SIZE and 0 <= ny < BOARD_SIZE:
                    candidates.append((nx, ny))
        
        return candidates
    
    def get_possible_moves_for(self, pos):
        x, y = pos
        player, hp, _, _ = self.board[x, y]
        if player != self.current_player or hp <= 0:
            return []
        if self.move_count_grid[x, y] >= 3:
            return []
        
        possible_moves = []
        for target in self.get_move_candidates(pos):
            tx, ty = target
            target_player, target_hp, _, _ = self.board[tx, ty]
            
            # 不显示己方士兵格，避免“可点但会失败”的体验问题
            if target_player == player and target_hp > 0:
                continue
            
            terrain_cost, error = self.get_terrain_cost(pos, target)
            if error:
                continue
            if self.steps_left < terrain_cost:
                continue
            possible_moves.append(target)
        
        return possible_moves
    
    def calculate_possible_moves(self, pos):
        """计算并存储可能的移动位置"""
        self.possible_moves = self.get_possible_moves_for(pos)
    
    def is_human_turn(self):
        return (not self.game_over) and (self.current_player in self.human_players)
    
    def check_game_over(self):
        if self.game_over:
            return True
        if len(self.players) <= 1:
            self.game_over = True
            self.winner = self.players[0] if self.players else None
            if self.winner:
                self.log.append(f"游戏结束! 玩家{self.winner}获胜!")
            else:
                self.log.append("游戏结束! 所有玩家均被消灭!")
            self.selected_pos = None
            self.possible_moves = []
            return True
        return False
    
    def remove_player(self, player, conqueror):
        if player not in self.players:
            return
        
        self.players.remove(player)
        self.players_who_played_this_round.discard(player)
        self.ai_players.discard(player)
        self.human_players.discard(player)
        self.log.append(f"玩家{conqueror}占领了玩家{player}的首都! 玩家{player}被消灭!")
        
        if self.game_mode == MODE_SINGLE_AI and player == self.primary_human:
            self.player_defeated = True
            self.log.append("玩家1已被消灭，进入观战模式。")
        
        for i in range(BOARD_SIZE):
            for j in range(BOARD_SIZE):
                if self.board[i, j, 0] == player:
                    self.board[i, j, 0] = 0
                    self.board[i, j, 1] = 0
    
    def move_soldier(self, from_pos, to_pos):
        x1, y1 = from_pos
        x2, y2 = to_pos
        
        if not (0 <= x1 < BOARD_SIZE and 0 <= y1 < BOARD_SIZE):
            return False, "起始位置超出边界"
        
        terrain_cost, terrain_error = self.get_terrain_cost(from_pos, to_pos)
        if terrain_error:
            return False, terrain_error
        
        # 获取棋子信息
        player, hp, city_type, unit_type = self.board[x1, y1]
        
        # 只能移动当前玩家的棋子
        if player != self.current_player:
            return False, "只能移动自己士兵"
        if hp <= 0:
            return False, "该位置没有可移动士兵"
            
        # 检查士兵移动次数
        move_count = self.move_count_grid[x1, y1]
        if move_count >= 3:
            return False, "该士兵本回合已移动3次"
        
        # 获取目标位置信息
        target_player, target_hp, target_city_type, target_unit_type = self.board[x2, y2]
        target_move_count = self.move_count_grid[x2, y2]
        
        # 检查是否移动到自己领土（非战斗）
        if target_player == player and target_hp > 0:
            return False, "不能移动到己方士兵位置"
        
        # 检查是否有足够行动点
        if self.steps_left < terrain_cost:
            return False, f"行动点不足! 需要{terrain_cost}点"
        
        # 移动棋子
        attacker_survived = False
        attack_damage_text = None
        if target_player != 0 and target_hp > 0:
            attack_damage_text = f"-{min(hp, target_hp)}"
            if hp > target_hp:
                new_hp = hp - target_hp
                self.board[x2, y2] = [player, new_hp, target_city_type, 0]
                self.log.append(f"玩家{player}在({y2},{x2})击败玩家{target_player}, 剩余血量{new_hp}")
                attacker_survived = True
            elif hp < target_hp:
                new_hp = target_hp - hp
                self.board[x2, y2] = [target_player, new_hp, target_city_type, 0]
                self.log.append(f"玩家{target_player}在({y2},{x2})防守成功, 剩余血量{new_hp}")
            else:
                self.board[x2, y2] = [0, 0, target_city_type, 0]
                self.log.append(f"玩家{player}和玩家{target_player}在({y2},{x2})同归于尽")
        else:
            self.board[x2, y2] = [player, hp, target_city_type, 0]
            self.log.append(f"玩家{player}移动士兵到({y2},{x2})")
            attacker_survived = True
        
        # 清除原位置士兵
        current_player, _, city_type, _ = self.board[x1, y1]
        self.board[x1, y1] = [current_player, 0, city_type, 0]
        
        # 记录移动历史
        self.move_history.append((from_pos, to_pos))
        
        # 更新移动计数
        self.move_count_grid[x1, y1] = 0
        if attacker_survived:
            self.move_count_grid[x2, y2] = move_count + 1
        else:
            self.move_count_grid[x2, y2] = target_move_count
        
        # 消耗行动点
        self.steps_left -= terrain_cost
        
        # 更新领土
        if attacker_survived and self.terrain[x2][y2] != TERRAIN_WATER:
            self.board[x2, y2, 0] = player
        
        if attack_damage_text:
            self.add_combat_effect((x2, y2), attack_damage_text)
        
        if attacker_survived:
            animated_hp = int(self.board[x2, y2, 1])
            self.add_move_animation(from_pos, to_pos, player, animated_hp)
        
        # 检查首都是否被占领
        eliminated = []
        for p, pos in self.capitals.items():
            cap_x, cap_y = pos
            if self.board[cap_x, cap_y, 0] != p and p in self.players:
                eliminated.append(p)
        
        for defeated_player in eliminated:
            self.remove_player(defeated_player, player)
        
        self.update_territory_count()
        self.check_game_over()
        
        return True, "移动成功"
    
    def next_player(self):
        if self.check_game_over():
            return
        
        if self.current_player not in self.players:
            if not self.players:
                self.check_game_over()
                return
            self.current_player = self.players[0]
        
        self.players_who_played_this_round.add(self.current_player)
        
        current_index = self.players.index(self.current_player)
        next_index = (current_index + 1) % len(self.players)
        self.current_player = self.players[next_index]
        
        if all(player in self.players_who_played_this_round for player in self.players):
            self.production_phase()
            self.round_count += 1
            self.players_who_played_this_round.clear()
            next_steps = self.calculate_steps_per_turn()
            self.log.append(f"第{self.round_count}轮开始, 每位玩家每回合{next_steps}步")
        
        # 计算当前玩家剩余步数
        self.steps_per_turn = self.calculate_steps_per_turn()
        self.steps_left = self.steps_per_turn
        
        # 重置所有士兵移动计数
        self.move_count_grid = np.zeros((BOARD_SIZE, BOARD_SIZE), dtype=int)
        
        # 重置选中位置和可移动范围
        self.selected_pos = None
        self.possible_moves = []
        
        if self.current_player in self.ai_players:
            self.log.append(f"玩家{self.current_player}(AI)的回合开始")
        else:
            self.log.append(f"玩家{self.current_player}的回合开始")
    
    def production_phase(self):
        """生产阶段（只在每轮结束后触发）"""
        self.log.append(f"第{self.round_count}轮结束，生产阶段开始")
        self.calculate_territories()
        production = {1: 0, 2: 0, 3: 0, 4: 0}
        mine_production = {1: 0, 2: 0, 3: 0, 4: 0}
        
        for i in range(BOARD_SIZE):
            for j in range(BOARD_SIZE):
                player, hp, city_type, unit_type = self.board[i, j]
                
                if city_type > 0 and player > 0:
                    if hp > 0:
                        if city_type == CITY_SMALL:
                            hp += 1
                        elif city_type == CITY_MAJOR:
                            hp += 2
                        elif city_type == CITY_CAPITAL:
                            hp += 2
                        hp = min(hp, 99)
                        self.board[i, j, 1] = hp
                        production[player] += 1
                    else:
                        hp = 1
                        self.board[i, j, 1] = hp
                        production[player] += 1

        for i in range(BOARD_SIZE):
            for j in range(BOARD_SIZE):
                if self.resource_map[i, j] != RESOURCE_GOLD_MINE:
                    continue

                player = self.board[i, j, 0]
                if player <= 0:
                    continue

                hp = self.board[i, j, 1]
                if hp > 0:
                    new_hp = min(99, hp + 5)
                    self.board[i, j, 1] = new_hp
                    mine_production[player] += (new_hp - hp)
                else:
                    self.board[i, j, 1] = 5
                    mine_production[player] += 5
        
        produced_summary = [f"玩家{p}+{v}" for p, v in production.items() if v > 0]
        if produced_summary:
            self.log.append("城市生产: " + "，".join(produced_summary))
        mine_summary = [f"玩家{p}+{v}血" for p, v in mine_production.items() if v > 0]
        if mine_summary:
            self.log.append("金矿产兵: " + "，".join(mine_summary))
        self.update_territory_count()
    
    def get_player_soldiers(self, player):
        return self.get_player_soldiers_from_state(player, self.board, self.move_count_grid)
    
    def scroll_log(self, delta):
        max_scroll = max(0, len(self.log) - self.max_visible_logs)
        self.log_scroll_offset = max(0, min(max_scroll, self.log_scroll_offset + delta))
    
    def get_visible_logs(self):
        max_scroll = max(0, len(self.log) - self.max_visible_logs)
        self.log_scroll_offset = max(0, min(max_scroll, self.log_scroll_offset))
        
        if not self.log:
            return [], max_scroll
        
        end = len(self.log) - self.log_scroll_offset
        start = max(0, end - self.max_visible_logs)
        return self.log[start:end], max_scroll

def main():
    from app_controller import App

    app = App(Game)
    app.run()
    pygame.quit()
    sys.exit()


if __name__ == '__main__':
    main()
