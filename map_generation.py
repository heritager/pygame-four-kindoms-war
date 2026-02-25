import math
import random

import numpy as np

from constants import (
    BOARD_SIZE,
    CITY_MAJOR,
    CITY_SMALL,
    RESOURCE_GOLD_MINE,
    TERRAIN_FOREST,
    TERRAIN_MOUNTAIN,
    TERRAIN_PLAIN,
    TERRAIN_WATER,
)


def generate_perlin_noise(width, height, scale=10.0, octaves=6, persistence=0.5, lacunarity=2.0):
    noise = np.zeros((width, height))

    for i in range(width):
        for j in range(height):
            noise[i][j] = perlin(i / scale, j / scale, octaves, persistence, lacunarity)
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
    corners = (noise(x - 1, y - 1) + noise(x + 1, y - 1) + noise(x - 1, y + 1) + noise(x + 1, y + 1)) / 16.0
    sides = (noise(x - 1, y) + noise(x + 1, y) + noise(x, y - 1) + noise(x, y + 1)) / 8.0
    center = noise(x, y) / 4.0
    return corners + sides + center


def noise(x, y):
    n = int(x + y * 57)
    n = (n << 13) ^ n
    return 1.0 - ((n * (n * n * 15731 + 789221) + 1376312589) & 0x7FFFFFFF) / 1073741824.0


class MapGenerationMixin:
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

    def get_zone_owner(self, x, y, capital_map):
        nearest_player = None
        nearest_distance = 10**9
        for player, (cx, cy) in capital_map.items():
            distance = abs(x - cx) + abs(y - cy)
            if distance < nearest_distance:
                nearest_distance = distance
                nearest_player = player
        return nearest_player

    def rebalance_terrain_for_fairness(self, capital_map):
        # 先按首都构建分区，后续按分区做均衡约束。
        zone_cells = {player: [] for player in capital_map}
        for i in range(BOARD_SIZE):
            for j in range(BOARD_SIZE):
                zone_owner = self.get_zone_owner(i, j, capital_map)
                zone_cells[zone_owner].append((i, j))

        # 首都周边优先陆地化，避免开局被水域锁死。
        for player, (cx, cy) in capital_map.items():
            for i in range(max(0, cx - 3), min(BOARD_SIZE, cx + 4)):
                for j in range(max(0, cy - 3), min(BOARD_SIZE, cy + 4)):
                    if abs(i - cx) + abs(j - cy) <= 3 and self.terrain[i][j] == TERRAIN_WATER:
                        self.terrain[i][j] = TERRAIN_PLAIN if random.random() < 0.8 else TERRAIN_FOREST

        # 硬约束：控制每个国家分区水域上限、山地上限和平原下限。
        max_zone_water_ratio = 0.28
        max_zone_mountain_ratio = 0.20
        min_zone_plain_ratio = 0.32
        for player, cells in zone_cells.items():
            cap_x, cap_y = capital_map[player]

            water_cells = [(x, y) for x, y in cells if self.terrain[x][y] == TERRAIN_WATER]
            allowed_water = int(len(cells) * max_zone_water_ratio)
            if len(water_cells) > allowed_water:
                convert_count = len(water_cells) - allowed_water
                water_cells.sort(key=lambda pos: abs(pos[0] - cap_x) + abs(pos[1] - cap_y))
                for x, y in water_cells[:convert_count]:
                    self.terrain[x][y] = TERRAIN_PLAIN if random.random() < 0.78 else TERRAIN_FOREST

            mountain_cells = [(x, y) for x, y in cells if self.terrain[x][y] == TERRAIN_MOUNTAIN]
            allowed_mountain = int(len(cells) * max_zone_mountain_ratio)
            if len(mountain_cells) > allowed_mountain:
                convert_count = len(mountain_cells) - allowed_mountain
                mountain_cells.sort(key=lambda pos: abs(pos[0] - cap_x) + abs(pos[1] - cap_y))
                for x, y in mountain_cells[:convert_count]:
                    self.terrain[x][y] = TERRAIN_PLAIN if random.random() < 0.62 else TERRAIN_FOREST

            plain_cells = [(x, y) for x, y in cells if self.terrain[x][y] == TERRAIN_PLAIN]
            required_plain = int(len(cells) * min_zone_plain_ratio)
            if len(plain_cells) < required_plain:
                need = required_plain - len(plain_cells)
                convert_candidates = []
                for terrain_type in (TERRAIN_WATER, TERRAIN_MOUNTAIN, TERRAIN_FOREST):
                    terrain_cells = [(x, y) for x, y in cells if self.terrain[x][y] == terrain_type]
                    terrain_cells.sort(key=lambda pos: abs(pos[0] - cap_x) + abs(pos[1] - cap_y))
                    convert_candidates.extend(terrain_cells)
                for x, y in convert_candidates[:need]:
                    self.terrain[x][y] = TERRAIN_PLAIN

        self.zone_water_ratio = {}
        self.zone_terrain_ratio = {}
        for player, cells in zone_cells.items():
            cell_count = max(1, len(cells))
            water_count = sum(1 for x, y in cells if self.terrain[x][y] == TERRAIN_WATER)
            plain_count = sum(1 for x, y in cells if self.terrain[x][y] == TERRAIN_PLAIN)
            forest_count = sum(1 for x, y in cells if self.terrain[x][y] == TERRAIN_FOREST)
            mountain_count = sum(1 for x, y in cells if self.terrain[x][y] == TERRAIN_MOUNTAIN)

            self.zone_water_ratio[player] = water_count / cell_count
            self.zone_terrain_ratio[player] = {
                'water': water_count / cell_count,
                'plain': plain_count / cell_count,
                'forest': forest_count / cell_count,
                'mountain': mountain_count / cell_count,
            }

    def place_balanced_neutral_cities(self, capital_set, capital_map):
        zone_plain = {player: [] for player in capital_map}
        zone_forest = {player: [] for player in capital_map}
        zone_mountain = {player: [] for player in capital_map}

        for i in range(BOARD_SIZE):
            for j in range(BOARD_SIZE):
                if (i, j) in capital_set:
                    continue
                # 避免把中立城市刷在初始领土上
                if self.board[i, j, 0] != 0:
                    continue

                terrain = self.terrain[i][j]
                if terrain == TERRAIN_WATER:
                    continue

                zone_owner = self.get_zone_owner(i, j, capital_map)
                if terrain == TERRAIN_PLAIN:
                    zone_plain[zone_owner].append((i, j))
                elif terrain == TERRAIN_FOREST:
                    zone_forest[zone_owner].append((i, j))
                else:
                    zone_mountain[zone_owner].append((i, j))

        for player in capital_map:
            random.shuffle(zone_plain[player])
            random.shuffle(zone_forest[player])
            random.shuffle(zone_mountain[player])

        players = sorted(capital_map.keys())

        # 每个国家保底一个“家门口小城”，确保开局补给不会断档。
        home_small_guaranteed = {player: 0 for player in players}
        for player in players:
            cx, cy = capital_map[player]
            picked = None
            picked_pool = None

            for pool in (zone_plain[player], zone_forest[player], zone_mountain[player]):
                for idx, (x, y) in enumerate(pool):
                    dist = abs(x - cx) + abs(y - cy)
                    if 3 <= dist <= 6:
                        picked = (x, y)
                        picked_pool = pool
                        del picked_pool[idx]
                        break
                if picked is not None:
                    break

            if picked is None:
                for pool in (zone_plain[player], zone_forest[player], zone_mountain[player]):
                    if pool:
                        picked = pool.pop()
                        break

            if picked is not None:
                x, y = picked
                self.board[x, y, 2] = CITY_SMALL
                self.board[x, y, 0] = 0
                home_small_guaranteed[player] = 1

        max_cities = int(BOARD_SIZE * BOARD_SIZE / 10)
        target_total_cities = random.randint(max_cities // 2, max_cities)
        guaranteed_total = sum(home_small_guaranteed.values())
        num_cities = max(0, target_total_cities - guaranteed_total)
        zone_available = {
            player: len(zone_plain[player]) + len(zone_forest[player]) + len(zone_mountain[player])
            for player in capital_map
        }
        available_cells = sum(zone_available.values())
        num_cities = min(num_cities, available_cells)

        zone_quota = {player: num_cities // len(players) for player in players}
        remaining = num_cities - sum(zone_quota.values())

        ranked_players = sorted(players, key=lambda p: zone_available[p], reverse=True)
        for player in ranked_players:
            if remaining <= 0:
                break
            zone_quota[player] += 1
            remaining -= 1

        overflow = 0
        for player in players:
            if zone_quota[player] > zone_available[player]:
                overflow += zone_quota[player] - zone_available[player]
                zone_quota[player] = zone_available[player]

        while overflow > 0:
            candidates = sorted(players, key=lambda p: zone_available[p] - zone_quota[p], reverse=True)
            if not candidates or (zone_available[candidates[0]] - zone_quota[candidates[0]] <= 0):
                break
            zone_quota[candidates[0]] += 1
            overflow -= 1

        total_summary = {
            'home_small': sum(home_small_guaranteed.values()),
            'plain_major': 0,
            'plain_small': 0,
            'forest_small': 0,
            'mountain_small': 0,
        }
        zone_summary = {
            player: {
                'home_small': home_small_guaranteed[player],
                'major': 0,
                'plain_small': 0,
                'forest_small': 0,
                'mountain_small': 0,
            }
            for player in players
        }

        for player in players:
            quota = zone_quota[player]
            if quota <= 0:
                continue

            plain_cells = zone_plain[player]
            forest_cells = zone_forest[player]
            mountain_cells = zone_mountain[player]

            min_major = 1 if quota >= 3 else 0
            major_count = min(max(int(quota * 0.35), min_major), len(plain_cells))
            small_needed = quota - major_count

            forest_small = min(int(small_needed * 0.30), len(forest_cells))
            plain_small = min(small_needed - forest_small, max(0, len(plain_cells) - major_count))

            remaining_small = small_needed - forest_small - plain_small
            if remaining_small > 0:
                extra_forest = min(remaining_small, max(0, len(forest_cells) - forest_small))
                forest_small += extra_forest
                remaining_small -= extra_forest

            mountain_small = min(remaining_small, len(mountain_cells)) if remaining_small > 0 else 0

            for i, j in plain_cells[:major_count]:
                self.board[i, j, 2] = CITY_MAJOR
                self.board[i, j, 0] = 0

            plain_small_start = major_count
            plain_small_end = major_count + plain_small
            for i, j in plain_cells[plain_small_start:plain_small_end]:
                self.board[i, j, 2] = CITY_SMALL
                self.board[i, j, 0] = 0

            for i, j in forest_cells[:forest_small]:
                self.board[i, j, 2] = CITY_SMALL
                self.board[i, j, 0] = 0

            for i, j in mountain_cells[:mountain_small]:
                self.board[i, j, 2] = CITY_SMALL
                self.board[i, j, 0] = 0

            zone_summary[player]['major'] = major_count
            zone_summary[player]['plain_small'] = plain_small
            zone_summary[player]['forest_small'] = forest_small
            zone_summary[player]['mountain_small'] = mountain_small

            total_summary['plain_major'] += major_count
            total_summary['plain_small'] += plain_small
            total_summary['forest_small'] += forest_small
            total_summary['mountain_small'] += mountain_small

        return total_summary, zone_summary

    def place_balanced_gold_mines(self, capital_set, capital_map):
        players = sorted(capital_map.keys())
        zone_candidates = {player: [] for player in players}

        for i in range(BOARD_SIZE):
            for j in range(BOARD_SIZE):
                if (i, j) in capital_set:
                    continue
                if self.terrain[i][j] == TERRAIN_WATER:
                    continue
                if self.board[i, j, 2] > 0:
                    continue
                # 避免刷在首都初始领土上，防止开局即被单方吃掉。
                if self.board[i, j, 0] != 0:
                    continue

                zone_owner = self.get_zone_owner(i, j, capital_map)
                zone_candidates[zone_owner].append((i, j))

        for player in players:
            random.shuffle(zone_candidates[player])

        mine_count = random.randint(2, 3)
        selected = []
        zone_mine_count = {player: 0 for player in players}
        selected_set = set()

        # 第一阶段：尽量每个分区最多1个，且彼此保持一定距离。
        available_zones = [player for player in players if zone_candidates[player]]
        random.shuffle(available_zones)
        for min_distance in (7, 5, 3):
            for player in available_zones:
                if len(selected) >= mine_count:
                    break
                if zone_mine_count[player] > 0:
                    continue

                for pos in zone_candidates[player]:
                    if pos in selected_set:
                        continue
                    if all(abs(pos[0] - s[0]) + abs(pos[1] - s[1]) >= min_distance for s in selected):
                        selected.append(pos)
                        selected_set.add(pos)
                        zone_mine_count[player] += 1
                        break
            if len(selected) >= mine_count:
                break

        # 第二阶段：若候选分区不足，再放宽条件补齐。
        if len(selected) < mine_count:
            fallback = []
            for player in players:
                for pos in zone_candidates[player]:
                    if pos not in selected_set:
                        fallback.append((player, pos))
            random.shuffle(fallback)

            for min_distance in (3, 1, 0):
                for player, pos in fallback:
                    if len(selected) >= mine_count:
                        break
                    if pos in selected_set:
                        continue
                    # 优先保持每个分区至多1个，实在不够再突破。
                    if zone_mine_count[player] > 0 and len(available_zones) >= mine_count:
                        continue
                    if all(abs(pos[0] - s[0]) + abs(pos[1] - s[1]) >= min_distance for s in selected):
                        selected.append(pos)
                        selected_set.add(pos)
                        zone_mine_count[player] += 1
                if len(selected) >= mine_count:
                    break

        for x, y in selected:
            self.resource_map[x, y] = RESOURCE_GOLD_MINE

        return selected, zone_mine_count
