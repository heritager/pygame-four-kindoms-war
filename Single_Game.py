import pygame
import numpy as np
import random
import sys
import time
import os
import math

pygame.init()

def get_font(size):
    return pygame.font.SysFont('simhei,microsoft yahei,wqy-zenhei', size)

CHINESE_FONT_TINY = get_font(14)
CHINESE_FONT_SMALL = get_font(18)
CHINESE_FONT_MEDIUM = get_font(22)
CHINESE_FONT_LARGE = get_font(28)

if CHINESE_FONT_SMALL is None:
    CHINESE_FONT_TINY = pygame.font.Font(None, 14)
    CHINESE_FONT_SMALL = pygame.font.Font(None, 18)
    CHINESE_FONT_MEDIUM = pygame.font.Font(None, 22)
    CHINESE_FONT_LARGE = pygame.font.Font(None, 28)

BOARD_SIZE = 20
TILE_SIZE = 40
WIDTH = BOARD_SIZE * TILE_SIZE
HEIGHT = BOARD_SIZE * TILE_SIZE + 150
FPS = 60

COLORS = {
    'BACKGROUND': (30, 35, 40),
    'GRID': (46, 52, 64),
    'NEUTRAL': (100, 100, 120),
    'PLAIN': (76, 86, 106),
    'FOREST': (59, 99, 76),
    'MOUNTAIN': (94, 92, 100),
    'WATER': (80, 120, 160),
    'GOLD_MINE': (255, 215, 0),
    'BUTTON': (70, 130, 180),
    'BUTTON_HOVER': (90, 150, 200),
    0: (70, 70, 90),
    1: (220, 60, 60),
    2: (60, 150, 220),
    3: (220, 180, 60),
    4: (100, 200, 100),
    'CITY': (180, 160, 140),
    'MAJOR_CITY': (200, 170, 100),
    'CAPITAL': (200, 100, 100),
    'TEXT': (220, 220, 220),
    'AI_THINKING': (100, 200, 255),
    'SELECTED': (255, 255, 200),
    'MOVE_RANGE': (100, 255, 100)
}

TERRITORY_COLORS = {
    1: (220, 60, 60, 100),
    2: (60, 150, 220, 100),
    3: (220, 180, 60, 100),
    4: (100, 200, 100, 100)
}

TERRAIN_PLAIN = 0
TERRAIN_FOREST = 1
TERRAIN_MOUNTAIN = 2
TERRAIN_WATER = 3

TERRAIN_NAMES = {
    TERRAIN_PLAIN: "平原",
    TERRAIN_FOREST: "森林",
    TERRAIN_MOUNTAIN: "山脉",
    TERRAIN_WATER: "水域"
}

CITY_NONE = 0
CITY_SMALL = 1
CITY_MAJOR = 2
CITY_CAPITAL = 3

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("四国争霸 - 单人模式")
clock = pygame.time.Clock()

def generate_perlin_noise(width, height, scale=10.0, octaves=6, persistence=0.5, lacunarity=2.0):
    noise = np.zeros((width, height))
    
    for i in range(width):
        for j in range(height):
            noise[i][j] = perlin(i/scale, j/scale, octaves, persistence, lacunarity)
    noise = (noise - np.min(noise)) / (np.max(noise) - np.min(noise))
    return noise

def perlin(x, y, octaves=6, persistence=0.5, lacunarity=2.0):
    total = 0
    frequency = 1.0
    amplitude = 1.0
    max_value = 0
    
    for _ in range(octaves):
        total += interpolated_noise(x * frequency, y * frequency) * amplitude
        
        max_value += amplitude
        amplitude *= persistence
        frequency *= lacunarity
    
    return total / max_value

def interpolated_noise(x, y):
    x_int = int(x)
    y_int = int(y)
    x_frac = x - x_int
    y_frac = y - y_int
    
    v1 = smooth_noise(x_int, y_int)
    v2 = smooth_noise(x_int + 1, y_int)
    v3 = smooth_noise(x_int, y_int + 1)
    v4 = smooth_noise(x_int + 1, y_int + 1)
    
    i1 = interpolate(v1, v2, x_frac)
    i2 = interpolate(v3, v4, x_frac)
    
    return interpolate(i1, i2, y_frac)

def interpolate(a, b, x):
    ft = x * 3.1415927
    f = (1 - math.cos(ft)) * 0.5
    return a * (1 - f) + b * f

def smooth_noise(x, y):
    corners = (noise(x-1, y-1) + noise(x+1, y-1) + noise(x-1, y+1) + noise(x+1, y+1)) / 16.0
    sides = (noise(x-1, y) + noise(x+1, y) + noise(x, y-1) + noise(x, y+1)) / 8.0
    center = noise(x, y) / 4.0
    return corners + sides + center

def noise(x, y):
    n = int(x + y * 57)
    n = (n << 13) ^ n
    return (1.0 - ((n * (n * n * 15731 + 789221) + 1376312589) & 0x7fffffff) / 1073741824.0)

class AIPlayer:
    def __init__(self, player_id, game):
        self.player_id = player_id
        self.game = game
        
    def get_all_possible_moves(self):
        moves = []
        for i in range(BOARD_SIZE):
            for j in range(BOARD_SIZE):
                player, hp, city_type, unit_type = self.game.board[i, j]
                if player == self.player_id and hp > 0:
                    from_pos = (i, j)
                    possible_destinations = self.game.calculate_possible_moves(from_pos)
                    for to_pos in possible_destinations:
                        moves.append((from_pos, to_pos))
        return moves
    
    def evaluate_move(self, from_pos, to_pos):
        x1, y1 = from_pos
        x2, y2 = to_pos
        score = 0
        
        player, hp, city_type, unit_type = self.game.board[x1, y1]
        target_player, target_hp, target_city_type, target_unit_type = self.game.board[x2, y2]
        target_terrain = self.game.terrain[x2][y2]
        
        base_score = hp
        
        if target_player == 0:
            if target_city_type == CITY_CAPITAL:
                score += base_score * 15
            elif target_city_type == CITY_MAJOR:
                score += base_score * 10
            elif target_city_type == CITY_SMALL:
                score += base_score * 6
            else:
                score += base_score * 2
                
            if target_terrain == TERRAIN_FOREST:
                score += base_score * 1.5
            elif target_terrain == TERRAIN_PLAIN:
                score += base_score * 1
                
            adjacent_enemies = self.count_adjacent_enemies(to_pos)
            if adjacent_enemies > 0:
                score -= base_score * adjacent_enemies * 0.5
                
            distance_to_enemy_capital = self.get_distance_to_nearest_enemy_capital(to_pos)
            if distance_to_enemy_capital < 5:
                score += base_score * (5 - distance_to_enemy_capital) * 0.3
                
        elif target_player != self.player_id:
            if hp > target_hp:
                remaining_hp = hp - target_hp
                if target_city_type == CITY_CAPITAL:
                    score += base_score * 20 + remaining_hp * 3
                elif target_city_type == CITY_MAJOR:
                    score += base_score * 12 + remaining_hp * 2
                elif target_city_type == CITY_SMALL:
                    score += base_score * 8 + remaining_hp * 1.5
                else:
                    score += base_score * 5 + remaining_hp * 1
                    
                if target_terrain == TERRAIN_FOREST:
                    score += base_score * 2
                elif target_terrain == TERRAIN_PLAIN:
                    score += base_score * 1
                    
                score += self.count_adjacent_enemies(to_pos) * base_score * 0.5
            elif hp < target_hp:
                score -= base_score * 3
            else:
                if target_city_type == CITY_CAPITAL:
                    score += base_score * 8
                elif target_city_type == CITY_MAJOR:
                    score += base_score * 5
                elif target_city_type == CITY_SMALL:
                    score += base_score * 3
                else:
                    score += base_score * 1
                    
                score -= self.count_adjacent_enemies(to_pos) * base_score * 1
        
        current_pos_danger = self.count_adjacent_enemies(from_pos)
        if current_pos_danger > 0:
            score += base_score * current_pos_danger * 0.8
            
        capital_pos = self.game.capitals.get(self.player_id)
        if capital_pos:
            dist_from_capital = abs(x1 - capital_pos[0]) + abs(y1 - capital_pos[1])
            if dist_from_capital <= 3:
                score -= base_score * 0.5
                
            dist_to_capital = abs(x2 - capital_pos[0]) + abs(y2 - capital_pos[1])
            if dist_to_capital <= 2:
                score -= base_score * 0.3
        
        territory_expansion = self.calculate_territory_expansion(to_pos)
        score += territory_expansion * base_score * 0.2
        
        return score
    
    def count_adjacent_enemies(self, pos):
        count = 0
        x, y = pos
        for dx, dy in [(0, 1), (1, 0), (0, -1), (-1, 0), (1, 1), (-1, -1), (1, -1), (-1, 1)]:
            nx, ny = x + dx, y + dy
            if 0 <= nx < BOARD_SIZE and 0 <= ny < BOARD_SIZE:
                enemy_player, enemy_hp, _, _ = self.game.board[nx, ny]
                if enemy_player != 0 and enemy_player != self.player_id and enemy_hp > 0:
                    count += 1
        return count
    
    def get_distance_to_nearest_enemy_capital(self, pos):
        x, y = pos
        min_dist = float('inf')
        for player_id, capital_pos in self.game.capitals.items():
            if player_id != self.player_id and player_id in self.game.players:
                dist = abs(x - capital_pos[0]) + abs(y - capital_pos[1])
                min_dist = min(min_dist, dist)
        return min_dist
    
    def calculate_territory_expansion(self, pos):
        x, y = pos
        expansion = 0
        for dx, dy in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
            nx, ny = x + dx, y + dy
            if 0 <= nx < BOARD_SIZE and 0 <= ny < BOARD_SIZE:
                owner = self.game.board[nx, ny, 0]
                if owner == 0:
                    expansion += 1
                elif owner != self.player_id:
                    expansion += 2
        return expansion
    
    def select_best_move(self):
        all_moves = self.get_all_possible_moves()
        if not all_moves:
            return None
        
        best_move = None
        best_score = float('-inf')
        
        for from_pos, to_pos in all_moves:
            score = self.evaluate_move(from_pos, to_pos)
            if score > best_score:
                best_score = score
                best_move = (from_pos, to_pos)
        
        if best_score < 0:
            safe_moves = []
            for from_pos, to_pos in all_moves:
                x2, y2 = to_pos
                if self.count_adjacent_enemies(to_pos) == 0:
                    safe_moves.append((from_pos, to_pos))
            if safe_moves:
                return random.choice(safe_moves)
        
        return best_move

class Game:
    def __init__(self):
        self.reset_game()
        
    def reset_game(self):
        self.generate_terrain()
        
        self.player_defeated = False

        self.board = np.zeros((BOARD_SIZE, BOARD_SIZE, 4), dtype=int)
        
        self.move_count_grid = np.zeros((BOARD_SIZE, BOARD_SIZE), dtype=int)
        
        capital_positions = [
            (3, 3),
            (3, BOARD_SIZE-4),
            (BOARD_SIZE-4, 3),
            (BOARD_SIZE-4, BOARD_SIZE-4)
        ]
        
        for idx, pos in enumerate(capital_positions):
            i, j = pos
            player_id = idx + 1
            self.board[i, j] = [player_id, 1, CITY_CAPITAL, 0]
            for dx in range(-1, 2):
                for dy in range(-1, 2):
                    ni, nj = i + dx, j + dy
                    if 0 <= ni < BOARD_SIZE and 0 <= nj < BOARD_SIZE:
                        self.board[ni, nj, 0] = player_id
                        self.board[ni, nj, 1] = 1 if (dx, dy) == (0, 0) else 0

        max_cities = int(BOARD_SIZE * BOARD_SIZE / 10)
        num_cities = random.randint(max_cities // 2, max_cities)
        city_positions = []
        
        while len(city_positions) < num_cities:
            i = random.randint(0, BOARD_SIZE-1)
            j = random.randint(0, BOARD_SIZE-1)
            
            if (i, j) in capital_positions or self.terrain[i][j] == TERRAIN_WATER:
                continue
                
            if (i, j) not in city_positions:
                city_positions.append((i, j))
                city_type = CITY_MAJOR if random.random() < 0.33 else CITY_SMALL
                self.board[i, j, 2] = city_type
                self.board[i, j, 0] = 0
        
        self.players = [1, 2, 3, 4]
        self.current_player = 1
        self.game_over = False
        self.winner = None
        self.capitals = {
            1: (3, 3),
            2: (3, BOARD_SIZE-4),
            3: (BOARD_SIZE-4, 3),
            4: (BOARD_SIZE-4, BOARD_SIZE-4)
        }
        
        self.round_count = 1
        self.steps_per_turn = self.calculate_steps_per_turn()
        self.steps_left = self.steps_per_turn
        self.selected_pos = None
        self.move_history = []
        
        self.log = ["游戏开始! 单人模式", "玩家1(红色)对战3个AI", 
                   f"第{self.round_count}轮开始, 每位玩家每回合{self.steps_per_turn}步"]
        
        self.update_territory_count()
        
        self.end_turn_button = pygame.Rect(WIDTH - 120, HEIGHT - 40, 100, 30)
        self.button_hovered = False
        
        self.possible_moves = []
        
        self.ai_players = {
            2: AIPlayer(2, self),
            3: AIPlayer(3, self),
            4: AIPlayer(4, self)
        }
        
        self.ai_thinking = False
        self.ai_move_delay = 0
    
    def generate_terrain(self):
        self.terrain = np.zeros((BOARD_SIZE, BOARD_SIZE), dtype=int)
        noise_map = generate_perlin_noise(BOARD_SIZE, BOARD_SIZE, scale=6.0)
        
        for i in range(BOARD_SIZE):
            for j in range(BOARD_SIZE):
                if noise_map[i][j] < 0.25:
                    self.terrain[i][j] = TERRAIN_WATER
                elif noise_map[i][j] < 0.35:
                    self.terrain[i][j] = TERRAIN_MOUNTAIN
                elif noise_map[i][j] < 0.6:
                    self.terrain[i][j] = TERRAIN_FOREST
                else:
                    self.terrain[i][j] = TERRAIN_PLAIN
    
    def calculate_territories(self):
        visited = np.zeros((BOARD_SIZE, BOARD_SIZE), dtype=bool)
        
        for i in range(BOARD_SIZE):
            for j in range(BOARD_SIZE):
                if (visited[i, j] or 
                    self.terrain[i][j] == TERRAIN_WATER or 
                    self.board[i, j, 2] > 0):
                    continue
                    
                region = []
                queue = [(i, j)]
                region_owner = self.board[i, j, 0]
                border_owners = set()
                border_has_unowned = False
                has_soldiers = False
                
                while queue:
                    x, y = queue.pop(0)
                    if visited[x, y]:
                        continue
                    visited[x, y] = True
                    
                    if self.board[x, y, 0] != region_owner:
                        continue
                        
                    region.append((x, y))
                    
                    if self.board[x, y, 1] > 0:
                        has_soldiers = True
                    
                    for dx, dy in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
                        nx, ny = x + dx, y + dy
                        
                        if nx < 0 or nx >= BOARD_SIZE or ny < 0 or ny >= BOARD_SIZE:
                            continue
                        if self.terrain[nx][ny] == TERRAIN_WATER:
                            continue
                        if self.board[nx, ny, 2] > 0:
                            continue
                        
                        n_owner = self.board[nx, ny, 0]
                        
                        if n_owner == region_owner:
                            if not visited[nx, ny]:
                                queue.append((nx, ny))
                        else:
                            if n_owner != 0:
                                border_owners.add(n_owner)
                            else:
                                border_has_unowned = True
                
                if not has_soldiers and len(border_owners) == 1 and not border_has_unowned:
                    new_owner = border_owners.pop()
                    for x, y in region:
                        self.board[x, y, 0] = new_owner
                        self.log.append(f"玩家{new_owner}通过包围获得领土({y},{x})")
    
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
    
    def move_soldier(self, from_pos, to_pos):
        x1, y1 = from_pos
        x2, y2 = to_pos
        
        if not (0 <= x2 < BOARD_SIZE and 0 <= y2 < BOARD_SIZE):
            return False, "目标位置超出边界"
        
        player, hp, city_type, unit_type = self.board[x1, y1]
        
        if player != self.current_player:
            return False, "只能移动自己士兵"
            
        move_count = self.move_count_grid[x1, y1]
        if move_count >= 3:
            return False, "该士兵本回合已移动3次"
        
        target_player, target_hp, target_city_type, target_unit_type = self.board[x2, y2]
        
        if target_player == player and target_hp > 0:
            return False, "不能移动到己方士兵位置"
        
        start_terrain = self.terrain[x1][y1]
        target_terrain = self.terrain[x2][y2]
        
        dx = abs(x1 - x2)
        dy = abs(y1 - y2)
        
        if start_terrain == TERRAIN_MOUNTAIN or target_terrain == TERRAIN_MOUNTAIN:
            terrain_cost = 2
            if start_terrain == TERRAIN_MOUNTAIN:
                if not ((dx == 1 and dy == 0) or (dx == 0 and dy == 1)):
                    return False, "只能上下左右移动"
        elif start_terrain == TERRAIN_WATER:
            if target_terrain != TERRAIN_WATER:
                if dx > 1 or dy > 1:
                    return False, "水域登陆只能移动1格以内"
                terrain_cost = 1
            else:
                if dx > 2 or dy > 2:
                    return False, "水域中只能移动2格以内"
                terrain_cost = 1
        elif start_terrain == TERRAIN_FOREST:
            if target_terrain == TERRAIN_WATER:
                if dx > 1 or dy > 1:
                    return False, "进入水域只能移动1格以内"
                terrain_cost = 1
            elif dx > 1 or dy > 1:
                return False, "森林中只能移动1格（包括斜向）"
            else:
                terrain_cost = 1
        else:
            if target_terrain == TERRAIN_WATER:
                if dx > 1 or dy > 1:
                    return False, "进入水域只能移动1格以内"
                terrain_cost = 1
            elif not ((dx == 1 and dy == 0) or (dx == 0 and dy == 1)):
                return False, "只能上下左右移动"
            else:
                terrain_cost = 1
        
        if self.steps_left < terrain_cost:
            return False, f"行动点不足! 需要{terrain_cost}点"
        
        battle_outcome = None
        if target_player != 0 and target_hp > 0:
            if hp > target_hp:
                new_hp = hp - target_hp
                self.board[x2, y2] = [player, new_hp, target_city_type, 0]
                self.log.append(f"玩家{player}在({y2},{x2})击败玩家{target_player}, 剩余血量{new_hp}")
                battle_outcome = True
            elif hp < target_hp:
                new_hp = target_hp - hp
                self.board[x2, y2] = [target_player, new_hp, target_city_type, 0]
                self.log.append(f"玩家{target_player}在({y2},{x2})防守成功, 剩余血量{new_hp}")
                battle_outcome = False
            else:
                self.board[x2, y2] = [0, 0, target_city_type, 0]
                self.log.append(f"玩家{player}和玩家{target_player}在({y2},{x2})同归于尽")
                battle_outcome = None
        else:
            self.board[x2, y2] = [player, hp, target_city_type, 0]
            self.log.append(f"玩家{player}移动士兵到({y2},{x2})")
        
        current_player, _, city_type, _ = self.board[x1, y1]
        self.board[x1, y1] = [current_player, 0, city_type, 0]
        
        self.move_history.append((from_pos, to_pos))
        
        self.move_count_grid[x2, y2] = move_count + 1
        self.move_count_grid[x1, y1] = 0
        
        self.steps_left -= terrain_cost
        
        if battle_outcome is not False and self.terrain[x2][y2] != TERRAIN_WATER:
            self.board[x2, y2, 0] = player
        
        self.update_territory_count()
        
        eliminated = []
        for p, pos in self.capitals.items():
            cap_x, cap_y = pos
            if self.board[cap_x, cap_y, 0] != p and p in self.players:
                eliminated.append(p)
                self.players.remove(p)
                self.log.append(f"玩家{player}占领了玩家{p}的首都! 玩家{p}被消灭!")
                
                if p == 1:
                    self.game_over = True
                    self.player_defeated = True
                    self.log.append("游戏结束! 玩家失败!")
                
                for i in range(BOARD_SIZE):
                    for j in range(BOARD_SIZE):
                        if self.board[i, j, 0] == p:
                            self.board[i, j, 0] = 0
                            self.board[i, j, 1] = 0
                            
        if self.steps_left <= 0 and not self.game_over:
            self.next_player()
                            
        return True, "移动成功"
    
    def next_player(self):
        if len(self.players) <= 1:
            self.game_over = True
            self.winner = self.players[0] if self.players else None
            if self.winner:
                self.log.append(f"游戏结束! 玩家{self.winner}获胜!")
            else:
                self.log.append("游戏结束! 所有玩家均被消灭!")
            return

        current_index = self.players.index(self.current_player)
        next_index = (current_index + 1) % len(self.players)
        self.current_player = self.players[next_index]
        
        self.steps_per_turn = self.calculate_steps_per_turn()
        self.steps_left = self.steps_per_turn
        
        self.move_count_grid = np.zeros((BOARD_SIZE, BOARD_SIZE), dtype=int)
        
        self.selected_pos = None
        self.possible_moves = []

        if self.current_player == 1:
            self.round_count += 1
            self.log.append(f"第{self.round_count}轮开始! 每位玩家每回合{self.steps_per_turn}步")
            self.production_phase()
            self.ai_thinking = False
        else:
            self.log.append(f"玩家{self.current_player}(AI)的回合开始")
            self.ai_thinking = True
            self.ai_move_delay = 30
    
    def production_phase(self):
        self.calculate_territories()
        self.log.append(f"第{self.round_count-1}轮结束，生产阶段开始")
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
                    else:
                        hp = 1
                        self.board[i, j, 1] = hp
    
    def calculate_possible_moves(self, pos):
        moves = []
        x, y = pos
        start_terrain = self.terrain[x][y]
        
        if start_terrain == TERRAIN_WATER:
            for dx in range(-2, 3):
                for dy in range(-2, 3):
                    if dx == 0 and dy == 0:
                        continue
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < BOARD_SIZE and 0 <= ny < BOARD_SIZE:
                        if self.terrain[nx][ny] != TERRAIN_WATER:
                            if abs(dx) > 1 or abs(dy) > 1:
                                continue
                        terrain_cost = 2 if self.terrain[nx][ny] == TERRAIN_MOUNTAIN else 1
                        if self.steps_left >= terrain_cost:
                            moves.append((nx, ny))
        elif start_terrain == TERRAIN_MOUNTAIN:
            for dx, dy in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
                nx, ny = x + dx, y + dy
                if 0 <= nx < BOARD_SIZE and 0 <= ny < BOARD_SIZE:
                    if self.terrain[nx][ny] != TERRAIN_WATER:
                        terrain_cost = 2 if self.terrain[nx][ny] == TERRAIN_MOUNTAIN else 1
                        if self.steps_left >= terrain_cost:
                            moves.append((nx, ny))
        elif start_terrain == TERRAIN_FOREST:
            for dx in range(-1, 2):
                for dy in range(-1, 2):
                    if dx == 0 and dy == 0:
                        continue
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < BOARD_SIZE and 0 <= ny < BOARD_SIZE:
                        if self.terrain[nx][ny] != TERRAIN_WATER:
                            terrain_cost = 2 if self.terrain[nx][ny] == TERRAIN_MOUNTAIN else 1
                            if self.steps_left >= terrain_cost:
                                moves.append((nx, ny))
        else:
            for dx, dy in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
                nx, ny = x + dx, y + dy
                if 0 <= nx < BOARD_SIZE and 0 <= ny < BOARD_SIZE:
                    if self.terrain[nx][ny] != TERRAIN_WATER:
                        terrain_cost = 2 if self.terrain[nx][ny] == TERRAIN_MOUNTAIN else 1
                        if self.steps_left >= terrain_cost:
                            moves.append((nx, ny))
        
        return moves
    
    def execute_ai_turn(self):
        if not self.ai_thinking:
            return
            
        ai_player = self.ai_players.get(self.current_player)
        if not ai_player:
            self.ai_thinking = False
            self.next_player()
            return
        
        if self.ai_move_delay > 0:
            self.ai_move_delay -= 1
            return
        
        if self.steps_left > 0:
            best_move = ai_player.select_best_move()
            
            if best_move:
                from_pos, to_pos = best_move
                success, message = self.move_soldier(from_pos, to_pos)
                if success:
                    self.ai_move_delay = 15
                else:
                    self.steps_left = 0
            else:
                self.steps_left = 0
        else:
            self.ai_thinking = False
            self.next_player()
    
    def draw_board(self):
        screen.fill(COLORS['BACKGROUND'])
        
        for i in range(BOARD_SIZE):
            for j in range(BOARD_SIZE):
                x = j * TILE_SIZE
                y = i * TILE_SIZE
                
                terrain_type = self.terrain[i][j]
                if terrain_type == TERRAIN_PLAIN:
                    color = COLORS['PLAIN']
                elif terrain_type == TERRAIN_FOREST:
                    color = COLORS['FOREST']
                elif terrain_type == TERRAIN_MOUNTAIN:
                    color = COLORS['MOUNTAIN']
                else:
                    color = COLORS['WATER']
                
                pygame.draw.rect(screen, color, (x, y, TILE_SIZE, TILE_SIZE))
                
                if terrain_type == TERRAIN_FOREST:
                    pygame.draw.rect(screen, (40, 30, 20),
                                    (j * TILE_SIZE + TILE_SIZE//3, 
                                     i * TILE_SIZE + TILE_SIZE*2//3,
                                     TILE_SIZE//8, TILE_SIZE//3))
                    pygame.draw.circle(screen, (40, 80, 40),
                                     (j * TILE_SIZE + TILE_SIZE//2, 
                                      i * TILE_SIZE + TILE_SIZE//2),
                                     TILE_SIZE//4)
                elif terrain_type == TERRAIN_MOUNTAIN:
                    pygame.draw.polygon(screen, (120, 110, 100), [
                        (j * TILE_SIZE, i * TILE_SIZE + TILE_SIZE),
                        (j * TILE_SIZE + TILE_SIZE//2, i * TILE_SIZE),
                        (j * TILE_SIZE + TILE_SIZE, i * TILE_SIZE + TILE_SIZE)
                    ])
                elif terrain_type == TERRAIN_WATER:
                    for k in range(3):
                        offset = (i + j + self.round_count) % 3
                        pygame.draw.arc(screen, (100, 150, 200),
                                       (j * TILE_SIZE + offset*3, i * TILE_SIZE + offset*3,
                                        TILE_SIZE - offset*6, TILE_SIZE - offset*6),
                                       0, 3.14, 1)
                
                pygame.draw.rect(screen, COLORS['GRID'], (x, y, TILE_SIZE, TILE_SIZE), 1)
                
                player, hp, city_type, unit_type = self.board[i, j]
                
                if player > 0 and terrain_type != TERRAIN_WATER:
                    s = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
                    s.fill(TERRITORY_COLORS[player])
                    screen.blit(s, (x, y))
                
                if city_type > 0:
                    if city_type == CITY_CAPITAL:
                        pygame.draw.rect(screen, COLORS['CAPITAL'],
                                       (j * TILE_SIZE + TILE_SIZE//4, 
                                        i * TILE_SIZE + TILE_SIZE//4,
                                        TILE_SIZE//2, TILE_SIZE//2))
                        roof_points = [
                            (j * TILE_SIZE + TILE_SIZE//4, i * TILE_SIZE + TILE_SIZE//4),
                            (j * TILE_SIZE + TILE_SIZE*3//4, i * TILE_SIZE + TILE_SIZE//4),
                            (j * TILE_SIZE + TILE_SIZE//2, i * TILE_SIZE)
                        ]
                        pygame.draw.polygon(screen, (220, 180, 40), roof_points)
                    elif city_type == CITY_MAJOR:
                        pygame.draw.rect(screen, COLORS['MAJOR_CITY'],
                                       (j * TILE_SIZE + TILE_SIZE//4, 
                                        i * TILE_SIZE + TILE_SIZE//2,
                                        TILE_SIZE//2, TILE_SIZE//2))
                        roof_points = [
                            (j * TILE_SIZE + TILE_SIZE//4, i * TILE_SIZE + TILE_SIZE//2),
                            (j * TILE_SIZE + TILE_SIZE*3//4, i * TILE_SIZE + TILE_SIZE//2),
                            (j * TILE_SIZE + TILE_SIZE//2, i * TILE_SIZE + TILE_SIZE//3)
                        ]
                        pygame.draw.polygon(screen, (160, 120, 80), roof_points)
                    elif city_type == CITY_SMALL:
                        pygame.draw.rect(screen, COLORS['CITY'],
                                       (j * TILE_SIZE + TILE_SIZE//3, 
                                        i * TILE_SIZE + TILE_SIZE//2,
                                        TILE_SIZE//3, TILE_SIZE//2))
                        pygame.draw.rect(screen, (150, 130, 110),
                                       (j * TILE_SIZE + TILE_SIZE//4, 
                                        i * TILE_SIZE + TILE_SIZE//2,
                                        TILE_SIZE//2, TILE_SIZE//8))
                
                if hp > 0:
                    soldier_color = COLORS[player]
                    center_x = j * TILE_SIZE + TILE_SIZE // 2
                    center_y = i * TILE_SIZE + TILE_SIZE // 2
                    
                    pygame.draw.circle(screen, soldier_color, 
                                     (center_x, center_y), 
                                     TILE_SIZE // 3)
                    
                    hp_text = CHINESE_FONT_MEDIUM.render(str(hp), True, (255, 255, 255))
                    hp_rect = hp_text.get_rect(center=(center_x, center_y))
                    screen.blit(hp_text, hp_rect)
                    
                    move_count = self.move_count_grid[i, j]
                    if move_count > 0:
                        move_text = f"{move_count}/3"
                        text = CHINESE_FONT_TINY.render(move_text, True, (255, 255, 200))
                        screen.blit(text, (j * TILE_SIZE + 2, i * TILE_SIZE + 2))
        
        for player, (x, y) in self.capitals.items():
            if player in self.players:
                pygame.draw.circle(screen, (255, 215, 0),
                                  (y * TILE_SIZE + TILE_SIZE // 2, 
                                   x * TILE_SIZE + TILE_SIZE // 2), 
                                  TILE_SIZE // 4, 3)
        
        if self.selected_pos:
            sx, sy = self.selected_pos
            pygame.draw.rect(screen, COLORS['SELECTED'], 
                           (sy * TILE_SIZE, sx * TILE_SIZE, TILE_SIZE, TILE_SIZE), 3)
        
        for px, py in self.possible_moves:
            pygame.draw.rect(screen, COLORS['MOVE_RANGE'], 
                           (py * TILE_SIZE, px * TILE_SIZE, TILE_SIZE, TILE_SIZE), 3)
    
    def draw_ui(self):
        ui_y = BOARD_SIZE * TILE_SIZE
        
        pygame.draw.rect(screen, (40, 45, 50), (0, ui_y, WIDTH, HEIGHT - ui_y))
        
        current_player_text = f"当前玩家: {self.current_player} {'(AI)' if self.current_player != 1 else '(你)'}"
        player_text = CHINESE_FONT_MEDIUM.render(current_player_text, True, COLORS[self.current_player])
        screen.blit(player_text, (20, ui_y + 10))
        
        steps_text = f"剩余步数: {self.steps_left}"
        steps_surface = CHINESE_FONT_SMALL.render(steps_text, True, COLORS['TEXT'])
        screen.blit(steps_surface, (20, ui_y + 40))
        
        round_text = f"第 {self.round_count} 轮"
        round_surface = CHINESE_FONT_SMALL.render(round_text, True, COLORS['TEXT'])
        screen.blit(round_surface, (20, ui_y + 70))
        
        territory_text = "领地: "
        x_offset = 200
        for player_id in [1, 2, 3, 4]:
            count = self.territory_count.get(player_id, 0)
            t_text = f"P{player_id}:{count} "
            t_surface = CHINESE_FONT_SMALL.render(t_text, True, COLORS[player_id])
            screen.blit(t_surface, (x_offset, ui_y + 70))
            x_offset += 80
        
        if self.current_player == 1 and not self.game_over:
            mouse_pos = pygame.mouse.get_pos()
            self.button_hovered = self.end_turn_button.collidepoint(mouse_pos)
            button_color = COLORS['BUTTON_HOVER'] if self.button_hovered else COLORS['BUTTON']
            pygame.draw.rect(screen, button_color, self.end_turn_button, border_radius=5)
            
            end_text = CHINESE_FONT_SMALL.render("结束回合", True, (255, 255, 255))
            end_rect = end_text.get_rect(center=self.end_turn_button.center)
            screen.blit(end_text, end_rect)
        
        log_y = ui_y + 100
        for i, log_entry in enumerate(self.log[-5:]):
            log_text = CHINESE_FONT_TINY.render(log_entry, True, COLORS['TEXT'])
            screen.blit(log_text, (20, log_y + i * 18))
        
        if self.ai_thinking:
            thinking_text = CHINESE_FONT_MEDIUM.render("AI思考中...", True, COLORS['AI_THINKING'])
            thinking_rect = thinking_text.get_rect(center=(WIDTH//2, ui_y + 50))
            screen.blit(thinking_text, thinking_rect)
        
        if self.game_over:
            if self.player_defeated:
                result_text = "游戏结束! 你失败了!"
                result_color = (255, 100, 100)
            elif self.winner == 1:
                result_text = "恭喜! 你获得了胜利!"
                result_color = (100, 255, 100)
            else:
                result_text = f"游戏结束! 玩家{self.winner}获胜!"
                result_color = COLORS.get(self.winner, (200, 200, 200))
            
            result_surface = CHINESE_FONT_LARGE.render(result_text, True, result_color)
            result_rect = result_surface.get_rect(center=(WIDTH//2, HEIGHT//2))
            
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 180))
            screen.blit(overlay, (0, 0))
            screen.blit(result_surface, result_rect)
    
    def handle_click(self, pos):
        if self.game_over or self.current_player != 1:
            return
        
        x, y = pos
        
        if self.end_turn_button.collidepoint(pos):
            self.next_player()
            return
        
        if y >= BOARD_SIZE * TILE_SIZE:
            return
        
        grid_x = y // TILE_SIZE
        grid_y = x // TILE_SIZE
        
        if 0 <= grid_x < BOARD_SIZE and 0 <= grid_y < BOARD_SIZE:
            player, hp, city_type, unit_type = self.board[grid_x, grid_y]
            
            if self.selected_pos:
                if (grid_x, grid_y) in self.possible_moves:
                    success, message = self.move_soldier(self.selected_pos, (grid_x, grid_y))
                    if success:
                        self.selected_pos = None
                        self.possible_moves = []
                    return
            
            if player == self.current_player and hp > 0:
                self.selected_pos = (grid_x, grid_y)
                self.possible_moves = self.calculate_possible_moves((grid_x, grid_y))
            else:
                self.selected_pos = None
                self.possible_moves = []
    
    def run(self):
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:
                        self.handle_click(event.pos)
            
            self.execute_ai_turn()
            
            self.draw_board()
            self.draw_ui()
            
            pygame.display.flip()
            clock.tick(FPS)
        
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    game = Game()
    game.run()
