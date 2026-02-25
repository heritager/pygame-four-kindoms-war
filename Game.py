import pygame
import numpy as np
import random
import sys
import time
import os
import math

# 初始化pygame
pygame.init()

def get_font(size):
    # 优先尝试常见的中文字体名称，pygame 会自动处理回退
    return pygame.font.SysFont('simhei,microsoft yahei,wqy-zenhei', size)

# 初始化各字号字体
CHINESE_FONT_TINY = get_font(14)
CHINESE_FONT_SMALL = get_font(18)
CHINESE_FONT_MEDIUM = get_font(22)
CHINESE_FONT_LARGE = get_font(28)

# 如果所有字体都加载失败（少见），强制使用默认字体防止崩溃
if CHINESE_FONT_SMALL is None:
    CHINESE_FONT_TINY = pygame.font.Font(None, 14)
    CHINESE_FONT_SMALL = pygame.font.Font(None, 18)
    CHINESE_FONT_MEDIUM = pygame.font.Font(None, 22)
    CHINESE_FONT_LARGE = pygame.font.Font(None, 28)

# 游戏常量
BOARD_SIZE = 20
TILE_SIZE = 40
WIDTH = BOARD_SIZE * TILE_SIZE
HEIGHT = BOARD_SIZE * TILE_SIZE + 150
FPS = 60

# 颜色定义
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
    'MOVE_RANGE': (100, 255, 100)  # 可移动范围边框颜色
}

# 创建半透明领土颜色
TERRITORY_COLORS = {
    1: (220, 60, 60, 100),
    2: (60, 150, 220, 100),
    3: (220, 180, 60, 100),
    4: (100, 200, 100, 100)
}

# 地形类型
TERRAIN_PLAIN = 0
TERRAIN_FOREST = 1
TERRAIN_MOUNTAIN = 2
TERRAIN_WATER = 3

# 地形名称
TERRAIN_NAMES = {
    TERRAIN_PLAIN: "平原",
    TERRAIN_FOREST: "森林",
    TERRAIN_MOUNTAIN: "山脉",
    TERRAIN_WATER: "水域"
}

# 城市类型
CITY_NONE = 0
CITY_SMALL = 1
CITY_MAJOR = 2
CITY_CAPITAL = 3

# 创建游戏窗口
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("四国争霸")
clock = pygame.time.Clock()

# 简化地形生成
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

class Game:
    def __init__(self):
        self.reset_game()
        
    def reset_game(self):
        # 初始化地形
        self.generate_terrain()
        
        self.player_defeated = False  # 新增：玩家失败标志

        # 初始化棋盘
        self.board = np.zeros((BOARD_SIZE, BOARD_SIZE, 4), dtype=int)
        
        # 士兵移动计数网格（替代ID系统）
        self.move_count_grid = np.zeros((BOARD_SIZE, BOARD_SIZE), dtype=int)
        
        # 设置四个首都
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
            # 在首都周围生成一些初始领土
            for dx in range(-1, 2):
                for dy in range(-1, 2):
                    ni, nj = i + dx, j + dy
                    if 0 <= ni < BOARD_SIZE and 0 <= nj < BOARD_SIZE:
                        self.board[ni, nj, 0] = player_id
                        self.board[ni, nj, 1] = 1 if (dx, dy) == (0, 0) else 0

        # 随机生成中立城市
        max_cities = int(BOARD_SIZE * BOARD_SIZE / 10)
        num_cities = random.randint(max_cities // 2, max_cities)
        city_positions = []
        
        # 生成城市位置
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
        
        # 游戏状态
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
        
        # 回合和移动管理
        self.round_count = 1
        self.steps_per_turn = self.calculate_steps_per_turn()
        self.steps_left = self.steps_per_turn
        self.selected_pos = None
        self.move_history = []
        
        # 游戏日志
        self.log = ["游戏开始!", "四位玩家轮流进行游戏", 
                   f"第{self.round_count}轮开始, 每位玩家每回合{self.steps_per_turn}步"]
        
        # 玩家领地计数
        self.update_territory_count()
        
        # 结束回合按钮
        self.end_turn_button = pygame.Rect(WIDTH - 120, HEIGHT - 40, 100, 30)
        self.button_hovered = False
        
        # 可移动位置列表
        self.possible_moves = []
    
    def generate_terrain(self):
        """简化的地形生成"""
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
        """计算包围领土 - 支持占领敌方无士兵领土"""
        visited = np.zeros((BOARD_SIZE, BOARD_SIZE), dtype=bool)
        
        for i in range(BOARD_SIZE):
            for j in range(BOARD_SIZE):
                # 跳过已访问、水域、中立城市（中立城市本身不可归属）
                if (visited[i, j] or 
                    self.terrain[i][j] == TERRAIN_WATER or 
                    self.board[i, j, 2] > 0):  # 中立城市（city>0 且 owner=0）
                    continue
                    
                region = []
                queue = [(i, j)]
                region_owner = self.board[i, j, 0]   # 区域当前所有者（0 表示无主）
                border_owners = set()                 # 相邻的其他玩家
                border_has_unowned = False            # 相邻是否有无主普通格子
                has_soldiers = False                   # 区域内是否有士兵
                
                while queue:
                    x, y = queue.pop(0)
                    if visited[x, y]:
                        continue
                    visited[x, y] = True
                    
                    # 确保当前格子所有者与 region_owner 一致（防止 BFS 错误）
                    if self.board[x, y, 0] != region_owner:
                        continue
                        
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
        
        # 检查移动是否合法
        if not (0 <= x2 < BOARD_SIZE and 0 <= y2 < BOARD_SIZE):
            return False, "目标位置超出边界"
        
        # 获取棋子信息
        player, hp, city_type, unit_type = self.board[x1, y1]
        
        # 只能移动当前玩家的棋子
        if player != self.current_player:
            return False, "只能移动自己士兵"
            
        # 检查士兵移动次数
        move_count = self.move_count_grid[x1, y1]
        if move_count >= 3:
            return False, "该士兵本回合已移动3次"
        
        # 获取目标位置信息
        target_player, target_hp, target_city_type, target_unit_type = self.board[x2, y2]
        
        # 检查是否移动到自己领土（非战斗）
        if target_player == player and target_hp > 0:
            return False, "不能移动到己方士兵位置"
        
        # 计算地形消耗
        start_terrain = self.terrain[x1][y1]
        target_terrain = self.terrain[x2][y2]
        
        # 计算移动距离
        dx = abs(x1 - x2)
        dy = abs(y1 - y2)
        
        # 计算移动消耗
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
            if dx > 1 or dy > 1:
                return False, "森林中只能移动1格（包括斜向）"
            terrain_cost = 1
        else:
            if not ((dx == 1 and dy == 0) or (dx == 0 and dy == 1)):
                return False, "只能上下左右移动"
            terrain_cost = 1
        
        # 检查是否有足够行动点
        if self.steps_left < terrain_cost:
            return False, f"行动点不足! 需要{terrain_cost}点"
        
        # 移动棋子
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
        
        # 清除原位置士兵
        current_player, _, city_type, _ = self.board[x1, y1]
        self.board[x1, y1] = [current_player, 0, city_type, 0]
        
        # 记录移动历史
        self.move_history.append((from_pos, to_pos))
        
        # 更新移动计数
        self.move_count_grid[x2, y2] = move_count + 1
        self.move_count_grid[x1, y1] = 0
        
        # 消耗行动点
        self.steps_left -= terrain_cost
        
        # 更新领土
        if battle_outcome is not False and self.terrain[x2][y2] != TERRAIN_WATER:
            self.board[x2, y2, 0] = player
        
        self.update_territory_count()
        
        # 检查首都是否被占领
        eliminated = []
        for p, pos in self.capitals.items():
            cap_x, cap_y = pos
            if self.board[cap_x, cap_y, 0] != p and p in self.players:
                eliminated.append(p)
                self.players.remove(p)
                self.log.append(f"玩家{player}占领了玩家{p}的首都! 玩家{p}被消灭!")
                
                # 新增：检查是否是人类玩家的首都被占领
                if p == 1:  # 人类玩家
                    self.game_over = True
                    self.player_defeated = True
                    self.log.append("游戏结束! 玩家失败!")
                
                for i in range(BOARD_SIZE):
                    for j in range(BOARD_SIZE):
                        if self.board[i, j, 0] == p:
                            self.board[i, j, 0] = 0
                            self.board[i, j, 1] = 0
                            
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
        
        # 计算当前玩家剩余步数
        self.steps_per_turn = self.calculate_steps_per_turn()
        self.steps_left = self.steps_per_turn
        
        # 重置所有士兵移动计数
        self.move_count_grid = np.zeros((BOARD_SIZE, BOARD_SIZE), dtype=int)
        
        # 重置选中位置和可移动范围
        self.selected_pos = None
        self.possible_moves = []

        # 检查是否完成一轮（当回到玩家1时表示一轮结束）
        if self.current_player == 1:
            self.round_count += 1
            self.log.append(f"第{self.round_count}轮开始! 每位玩家每回合{self.steps_per_turn}步")
            # 只在完成一轮后触发生产阶段
            self.production_phase()
        else:
            self.log.append(f"玩家{self.current_player}的回合开始")
    
    def production_phase(self):
        """生产阶段（只在每轮结束后触发）"""
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
        """计算并存储可能的移动位置"""
        self.possible_moves = []
        x, y = pos
        start_terrain = self.terrain[x][y]
        
        if start_terrain == TERRAIN_WATER:
            for dx in range(-2, 3):
                for dy in range(-2, 3):
                    if dx == 0 and dy == 0:
                        continue
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < BOARD_SIZE and 0 <= ny < BOARD_SIZE:
                        # 水域移动
                        if self.terrain[nx][ny] != TERRAIN_WATER:
                            # 登陆陆地限制为1格
                            if abs(dx) > 1 or abs(dy) > 1:
                                continue
                        terrain_cost = 2 if self.terrain[nx][ny] == TERRAIN_MOUNTAIN else 1
                        if self.steps_left >= terrain_cost:
                            self.possible_moves.append((nx, ny))
        elif start_terrain == TERRAIN_MOUNTAIN:
            for dx, dy in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
                nx, ny = x + dx, y + dy
                if 0 <= nx < BOARD_SIZE and 0 <= ny < BOARD_SIZE:
                    terrain_cost = 2
                    if self.steps_left >= terrain_cost:
                        self.possible_moves.append((nx, ny))
        elif start_terrain == TERRAIN_FOREST:
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    if dx == 0 and dy == 0:
                        continue
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < BOARD_SIZE and 0 <= ny < BOARD_SIZE:
                        terrain_cost = 2 if self.terrain[nx][ny] == TERRAIN_MOUNTAIN else 1
                        if self.steps_left >= terrain_cost:
                            self.possible_moves.append((nx, ny))
        else:
            for dx, dy in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
                nx, ny = x + dx, y + dy
                if 0 <= nx < BOARD_SIZE and 0 <= ny < BOARD_SIZE:
                    terrain_cost = 2 if self.terrain[nx][ny] == TERRAIN_MOUNTAIN else 1
                    if self.steps_left >= terrain_cost:
                        self.possible_moves.append((nx, ny))

    def draw(self, screen):
        # 绘制地形背景
        for i in range(BOARD_SIZE):
            for j in range(BOARD_SIZE):
                terrain_type = self.terrain[i][j]
                
                if terrain_type == TERRAIN_PLAIN:
                    color = COLORS['PLAIN']
                elif terrain_type == TERRAIN_FOREST:
                    color = COLORS['FOREST']
                elif terrain_type == TERRAIN_MOUNTAIN:
                    color = COLORS['MOUNTAIN']
                elif terrain_type == TERRAIN_WATER:
                    color = COLORS['WATER']
                
                pygame.draw.rect(screen, color, 
                                (j * TILE_SIZE, i * TILE_SIZE, 
                                 TILE_SIZE, TILE_SIZE))
                
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
        
        # 绘制领土半透明覆盖
        for i in range(BOARD_SIZE):
            for j in range(BOARD_SIZE):
                player = self.board[i, j, 0]
                terrain_type = self.terrain[i][j]
                if player > 0 and terrain_type != TERRAIN_WATER:
                    territory_surface = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
                    territory_color = TERRITORY_COLORS[player]
                    territory_surface.fill(territory_color)
                    screen.blit(territory_surface, (j * TILE_SIZE, i * TILE_SIZE))
        
        # 绘制可移动范围（边框高亮）
        for pos in self.possible_moves:
            x, y = pos
            pygame.draw.rect(screen, COLORS['MOVE_RANGE'], 
                            (y * TILE_SIZE, x * TILE_SIZE, 
                             TILE_SIZE, TILE_SIZE), 3)
        
        # 绘制棋盘格子边框
        for i in range(BOARD_SIZE):
            for j in range(BOARD_SIZE):
                border_color = COLORS['GRID']
                pygame.draw.rect(screen, border_color, 
                                (j * TILE_SIZE, i * TILE_SIZE, 
                                 TILE_SIZE, TILE_SIZE), 1)
        
        # 绘制城市
        for i in range(BOARD_SIZE):
            for j in range(BOARD_SIZE):
                player, hp, city_type, unit_type = self.board[i, j]
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
        
        # 绘制士兵
        for i in range(BOARD_SIZE):
            for j in range(BOARD_SIZE):
                player, hp, city_type, unit_type = self.board[i, j]
                if hp > 0:
                    soldier_color = COLORS[player]
                    center_x = j * TILE_SIZE + TILE_SIZE // 2
                    center_y = i * TILE_SIZE + TILE_SIZE // 2
                    
                    pygame.draw.circle(screen, soldier_color, 
                                     (center_x, center_y), 
                                     TILE_SIZE // 3)
                    
                    if CHINESE_FONT_MEDIUM:
                        text = CHINESE_FONT_MEDIUM.render(str(hp), True, (255, 255, 255))
                        text_rect = text.get_rect(center=(center_x, center_y))
                        screen.blit(text, text_rect)
                    
                    # 显示移动次数
                    move_count = self.move_count_grid[i, j]
                    if move_count > 0:
                        move_text = f"{move_count}/3"
                        if CHINESE_FONT_TINY:
                            text = CHINESE_FONT_TINY.render(move_text, True, (255, 255, 200))
                            screen.blit(text, (j * TILE_SIZE + 2, i * TILE_SIZE + 2))
        
        # 绘制首都标记
        for player, (x, y) in self.capitals.items():
            if player in self.players:
                pygame.draw.circle(screen, (255, 215, 0),
                                  (y * TILE_SIZE + TILE_SIZE // 2, 
                                   x * TILE_SIZE + TILE_SIZE // 2), 
                                  TILE_SIZE // 4, 3)
        
        # 绘制信息面板
        pygame.draw.rect(screen, (25, 30, 35), (0, HEIGHT-150, WIDTH, 150))
        
        # 显示当前玩家和回合信息
        if not self.game_over:
            status_text = f"玩家 {self.current_player} 的回合 - 第{self.round_count}轮 - 剩余步数: {self.steps_left}"
            
            if CHINESE_FONT_MEDIUM:
                text = CHINESE_FONT_MEDIUM.render(status_text, True, COLORS[self.current_player])
                screen.blit(text, (10, HEIGHT - 140))
        
        elif self.player_defeated:  # 新增：显示玩家失败
            if CHINESE_FONT_MEDIUM:
                text = CHINESE_FONT_MEDIUM.render("游戏结束! 玩家失败!", True, (255, 0, 0))
                screen.blit(text, (10, HEIGHT - 140))
        elif self.winner:
            result = f"玩家{self.winner}获胜!"
            if CHINESE_FONT_MEDIUM:
                text = CHINESE_FONT_MEDIUM.render(result, True, COLORS[self.winner])
                screen.blit(text, (10, HEIGHT - 140))
        else:
            if CHINESE_FONT_MEDIUM:
                text = CHINESE_FONT_MEDIUM.render("游戏结束! 平局!", True, (255, 255, 255))
                screen.blit(text, (10, HEIGHT - 140))
        
        # 显示领地信息
        territory_y = HEIGHT - 115
        if CHINESE_FONT_SMALL:
            text = CHINESE_FONT_SMALL.render("领地:", True, COLORS['TEXT'])
            screen.blit(text, (10, territory_y))
        
        territory_x = 60
        for player in [1, 2, 3, 4]:
            if player not in self.players:
                continue
                
            territory_count = self.territory_count[player]
            pygame.draw.rect(screen, COLORS[player], (territory_x, territory_y, 16, 16))
            if CHINESE_FONT_TINY:
                text = CHINESE_FONT_TINY.render(f"{territory_count}", True, (255, 255, 255))
                screen.blit(text, (territory_x + 20, territory_y))
            
            territory_x += 80
        
        # 显示游戏日志
        log_y = HEIGHT - 95
        for i, log_entry in enumerate(self.log[-4:]):
            if CHINESE_FONT_TINY:
                text = CHINESE_FONT_TINY.render(log_entry, True, COLORS['TEXT'])
                screen.blit(text, (10, log_y + i * 18))
        
        # 绘制结束回合按钮
        button_color = COLORS['BUTTON_HOVER'] if self.button_hovered else COLORS['BUTTON']
        pygame.draw.rect(screen, button_color, self.end_turn_button, border_radius=5)
        pygame.draw.rect(screen, (200, 200, 220), self.end_turn_button, 2, border_radius=5)
        
        if CHINESE_FONT_SMALL:
            text = CHINESE_FONT_SMALL.render("结束回合", True, (255, 255, 255))
            text_rect = text.get_rect(center=self.end_turn_button.center)
            screen.blit(text, text_rect)
        
        # 显示操作提示
        tips = "操作: 点击选择士兵 → 点击目标位置移动 | R: 重新开始 | ESC: 退出"
        if CHINESE_FONT_TINY:
            text = CHINESE_FONT_TINY.render(tips, True, (180, 180, 200))
            screen.blit(text, (10, HEIGHT - 20))

# 创建游戏实例
game = Game()

# 游戏主循环
running = True

while running:
    # 检查鼠标是否悬停在按钮上
    mouse_pos = pygame.mouse.get_pos()
    game.button_hovered = game.end_turn_button.collidepoint(mouse_pos)
    
    # 处理事件
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_r:  # 按R键重置游戏
                game = Game()
            elif event.key == pygame.K_ESCAPE:  # ESC退出
                running = False
        
        if not game.game_over and event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # 左键点击
                x, y = pygame.mouse.get_pos()
                
                # 检查是否点击了结束回合按钮
                if game.end_turn_button.collidepoint(x, y):
                    game.steps_left = 0
                    game.log.append(f"玩家{game.current_player}主动结束回合")
                    game.next_player()
                    continue
                
                # 只处理棋盘区域点击
                if y < BOARD_SIZE * TILE_SIZE:
                    board_x, board_y = y // TILE_SIZE, x // TILE_SIZE
                    
                    if game.selected_pos is None:
                        # 选择棋子
                        player, hp, _, _ = game.board[board_x, board_y]
                        if player == game.current_player and hp > 0:
                            game.selected_pos = (board_x, board_y)
                            # 计算并存储可能的移动位置
                            game.calculate_possible_moves((board_x, board_y))
                    else:
                        # 移动棋子
                        if (board_x, board_y) in game.possible_moves:
                            success, message = game.move_soldier(game.selected_pos, (board_x, board_y))
                            if success:
                                game.log.append(message)
                                
                                # 检查是否结束当前回合
                                if game.steps_left <= 0:
                                    game.next_player()
                            else:
                                game.log.append(f"移动失败: {message}")
                            
                            game.selected_pos = None
                            game.possible_moves = []
                        else:
                            # 如果点击了其他位置，取消选择或选择新棋子
                            player, hp, _, _ = game.board[board_x, board_y]
                            if player == game.current_player and hp > 0:
                                game.selected_pos = (board_x, board_y)
                                game.calculate_possible_moves((board_x, board_y))
                            else:
                                game.selected_pos = None
                                game.possible_moves = []
    
    # 绘制游戏
    game.draw(screen)
    
    # 绘制选中的棋子
    if game.selected_pos:
        x, y = game.selected_pos
        pygame.draw.rect(screen, COLORS['SELECTED'], 
                        (y * TILE_SIZE, x * TILE_SIZE, 
                         TILE_SIZE, TILE_SIZE), 3)
    
    pygame.display.flip()
    clock.tick(FPS)

pygame.quit()
sys.exit()