import math

import pygame

from constants import (
    BOARD_PIXEL_SIZE,
    BOARD_SIZE,
    CHINESE_FONT_MEDIUM,
    CHINESE_FONT_SMALL,
    CHINESE_FONT_TINY,
    CITY_CAPITAL,
    CITY_MAJOR,
    COLORS,
    HEIGHT,
    MODE_LABELS,
    MODE_SINGLE_AI,
    RESOURCE_GOLD_MINE,
    SIDE_PANEL_WIDTH,
    TERRAIN_FOREST,
    TERRAIN_MOUNTAIN,
    TERRAIN_PLAIN,
    TERRAIN_WATER,
    TERRITORY_COLORS,
    TILE_SIZE,
    WIDTH,
)


class RenderMixin:
    def draw_text_with_shadow(self, screen, font, text, pos, color, center=False):
        if not font:
            return

        shadow_surf = font.render(text, True, COLORS['SHADOW'])
        text_surf = font.render(text, True, color)
        if center:
            text_rect = text_surf.get_rect(center=pos)
            shadow_rect = shadow_surf.get_rect(center=(pos[0] + 1, pos[1] + 1))
        else:
            text_rect = text_surf.get_rect(topleft=pos)
            shadow_rect = shadow_surf.get_rect(topleft=(pos[0] + 1, pos[1] + 1))

        screen.blit(shadow_surf, shadow_rect)
        screen.blit(text_surf, text_rect)

    def draw_soldier_icon(self, screen, player, hp, center_pos):
        center_x, center_y = center_pos
        base_color = COLORS[player]

        # 主体阴影
        pygame.draw.circle(screen, (24, 24, 28), (center_x + 1, center_y + 2), TILE_SIZE // 3)
        # 主体
        pygame.draw.circle(screen, base_color, (center_x, center_y), TILE_SIZE // 3)
        # 头盔顶
        pygame.draw.arc(
            screen,
            (235, 235, 235),
            (center_x - TILE_SIZE // 4, center_y - TILE_SIZE // 4, TILE_SIZE // 2, TILE_SIZE // 3),
            3.2,
            6.2,
            2,
        )
        # 剑形符号
        pygame.draw.line(screen, (245, 245, 245), (center_x, center_y - 8), (center_x, center_y + 8), 2)
        pygame.draw.line(screen, (245, 245, 245), (center_x - 4, center_y + 3), (center_x + 4, center_y + 3), 2)

        self.draw_text_with_shadow(screen, CHINESE_FONT_MEDIUM, str(hp), (center_x, center_y + 1), (255, 255, 255), center=True)

    def draw_hud_legend_icon(self, screen, legend_type, x, y, size=14):
        if legend_type == 'small_city':
            pygame.draw.rect(screen, (76, 70, 62), (x + size // 4 + 1, y + size // 2 + 1, size // 2, size // 2))
            pygame.draw.rect(screen, COLORS['CITY'], (x + size // 4, y + size // 2, size // 2, size // 2))
            pygame.draw.rect(screen, (156, 140, 124), (x + size // 5, y + size // 2, size * 3 // 5, max(2, size // 6)))
        elif legend_type == 'major_city':
            pygame.draw.rect(screen, (78, 68, 52), (x + size // 4 + 1, y + size // 2 + 1, size // 2, size // 2))
            pygame.draw.rect(screen, COLORS['MAJOR_CITY'], (x + size // 4, y + size // 2, size // 2, size // 2))
            pygame.draw.polygon(screen, (170, 132, 92), [
                (x + size // 4, y + size // 2),
                (x + size * 3 // 4, y + size // 2),
                (x + size // 2, y + size // 3),
            ])
        elif legend_type == 'capital':
            pygame.draw.rect(screen, (68, 58, 58), (x + size // 4 + 1, y + size // 4 + 1, size // 2, size // 2))
            pygame.draw.rect(screen, COLORS['CAPITAL'], (x + size // 4, y + size // 4, size // 2, size // 2))
            pygame.draw.polygon(screen, (230, 190, 70), [
                (x + size // 4, y + size // 4),
                (x + size * 3 // 4, y + size // 4),
                (x + size // 2, y + 1),
            ])
        elif legend_type == 'gold_mine':
            pygame.draw.rect(screen, (92, 78, 46), (x + 1, y + size - 4, size - 2, 3), border_radius=1)
            pygame.draw.polygon(screen, COLORS['GOLD_MINE'], [
                (x + size // 2, y + 1),
                (x + size - 1, y + size // 2),
                (x + size // 2, y + size - 2),
                (x + 1, y + size // 2),
            ])
            pygame.draw.circle(screen, (255, 240, 172), (x + size // 2 - 1, y + size // 2 - 1), max(1, size // 6))

    def draw_territory_borders(self, screen):
        for i in range(BOARD_SIZE):
            for j in range(BOARD_SIZE):
                owner = self.board[i, j, 0]
                if owner <= 0 or self.terrain[i][j] == TERRAIN_WATER:
                    continue

                color = TERRITORY_COLORS[owner]
                x = j * TILE_SIZE
                y = i * TILE_SIZE
                width = 3
                shadow_width = width + 2

                # 内部标记，让占领区在大块连片时也能看见“颜色变化”
                pygame.draw.circle(screen, color, (x + 6, y + 6), 2)

                # 上边
                if i == 0 or self.board[i - 1, j, 0] != owner or self.terrain[i - 1][j] == TERRAIN_WATER:
                    pygame.draw.line(screen, (20, 20, 24), (x, y), (x + TILE_SIZE, y), shadow_width)
                    pygame.draw.line(screen, color, (x, y), (x + TILE_SIZE, y), width)
                # 下边
                if i == BOARD_SIZE - 1 or self.board[i + 1, j, 0] != owner or self.terrain[i + 1][j] == TERRAIN_WATER:
                    pygame.draw.line(screen, (20, 20, 24), (x, y + TILE_SIZE - 1), (x + TILE_SIZE, y + TILE_SIZE - 1), shadow_width)
                    pygame.draw.line(screen, color, (x, y + TILE_SIZE - 1), (x + TILE_SIZE, y + TILE_SIZE - 1), width)
                # 左边
                if j == 0 or self.board[i, j - 1, 0] != owner or self.terrain[i][j - 1] == TERRAIN_WATER:
                    pygame.draw.line(screen, (20, 20, 24), (x, y), (x, y + TILE_SIZE), shadow_width)
                    pygame.draw.line(screen, color, (x, y), (x, y + TILE_SIZE), width)
                # 右边
                if j == BOARD_SIZE - 1 or self.board[i, j + 1, 0] != owner or self.terrain[i][j + 1] == TERRAIN_WATER:
                    pygame.draw.line(screen, (20, 20, 24), (x + TILE_SIZE - 1, y), (x + TILE_SIZE - 1, y + TILE_SIZE), shadow_width)
                    pygame.draw.line(screen, color, (x + TILE_SIZE - 1, y), (x + TILE_SIZE - 1, y + TILE_SIZE), width)

    def draw_stylish_button(self, screen, rect, text, is_hovered, is_pressed, disabled=False):
        if disabled:
            base_color = (86, 92, 102)
            hover_color = (86, 92, 102)
            shadow_color = (58, 62, 70)
            text_color = (208, 208, 216)
        else:
            base_color = COLORS['BUTTON']
            hover_color = COLORS['BUTTON_HOVER']
            shadow_color = COLORS['BUTTON_SHADOW']
            text_color = (255, 255, 255)

        current_color = hover_color if is_hovered and not disabled else base_color
        offset_y = 4 if not is_pressed else 1

        shadow_rect = pygame.Rect(rect.x, rect.y + offset_y, rect.width, rect.height)
        pygame.draw.rect(screen, shadow_color, shadow_rect, border_radius=9)

        main_rect_y = rect.y if is_pressed else rect.y - 3
        main_rect = pygame.Rect(rect.x, main_rect_y, rect.width, rect.height)
        pygame.draw.rect(screen, current_color, main_rect, border_radius=9)
        pygame.draw.rect(screen, (218, 226, 236), main_rect, 1, border_radius=9)

        highlight_height = max(4, rect.height // 2 - 4)
        highlight = pygame.Surface((rect.width - 12, highlight_height), pygame.SRCALPHA)
        highlight.fill((255, 255, 255, 48 if not disabled else 22))
        screen.blit(highlight, (rect.x + 6, main_rect_y + 5))

        self.draw_text_with_shadow(screen, CHINESE_FONT_SMALL, text, main_rect.center, text_color, center=True)

    def add_move_animation(self, from_pos, to_pos, player, hp):
        self.move_animations.append({
            'from': from_pos,
            'to': to_pos,
            'player': player,
            'hp': hp,
            'start': pygame.time.get_ticks(),
            'duration': 140,
        })

    def add_combat_effect(self, pos, text):
        self.combat_effects.append({
            'pos': pos,
            'text': text,
            'start': pygame.time.get_ticks(),
            'duration': 700,
        })

    def collect_active_move_animations(self, now):
        active = []
        remaining = []

        for anim in self.move_animations:
            elapsed = now - anim['start']
            if elapsed < anim['duration']:
                active.append(anim)
                remaining.append(anim)

        self.move_animations = remaining
        return active

    def draw_combat_effects(self, screen, now):
        remaining = []

        for effect in self.combat_effects:
            elapsed = now - effect['start']
            duration = effect['duration']
            if elapsed >= duration:
                continue

            progress = elapsed / duration
            x, y = effect['pos']
            px = y * TILE_SIZE
            py = x * TILE_SIZE

            flash = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
            alpha = int(COLORS['ATTACK_FLASH'][3] * (1.0 - progress))
            flash.fill((COLORS['ATTACK_FLASH'][0], COLORS['ATTACK_FLASH'][1], COLORS['ATTACK_FLASH'][2], alpha))
            screen.blit(flash, (px, py))

            float_y = py - int(18 * progress)
            text_color = (255, max(90, 220 - int(120 * progress)), max(90, 220 - int(120 * progress)))
            self.draw_text_with_shadow(
                screen,
                CHINESE_FONT_SMALL,
                effect['text'],
                (px + TILE_SIZE // 2, float_y + TILE_SIZE // 2),
                text_color,
                center=True,
            )

            remaining.append(effect)

        self.combat_effects = remaining

    def draw(self, screen):
        now = pygame.time.get_ticks()
        screen.fill(COLORS['BACKGROUND'])

        # 绘制地形底图（低饱和背景 + 简单纹理）
        for i in range(BOARD_SIZE):
            for j in range(BOARD_SIZE):
                tile_x = j * TILE_SIZE
                tile_y = i * TILE_SIZE
                terrain_type = self.terrain[i][j]

                if terrain_type == TERRAIN_PLAIN:
                    color = COLORS['PLAIN']
                elif terrain_type == TERRAIN_FOREST:
                    color = COLORS['FOREST']
                elif terrain_type == TERRAIN_MOUNTAIN:
                    color = COLORS['MOUNTAIN']
                else:
                    color = COLORS['WATER']

                pygame.draw.rect(screen, color, (tile_x, tile_y, TILE_SIZE, TILE_SIZE))

                if terrain_type == TERRAIN_FOREST:
                    trunk_color = (88, 78, 66)
                    for seed in range(3):
                        ox = ((i * 13 + j * 17 + seed * 11) % 18) - 9
                        oy = ((i * 7 + j * 19 + seed * 5) % 14) - 7
                        radius = 4 + ((i + j + seed) % 3)
                        cx = tile_x + TILE_SIZE // 2 + ox
                        cy = tile_y + TILE_SIZE // 2 + oy
                        pygame.draw.circle(screen, (88, 128, 86), (cx, cy), radius)
                        pygame.draw.rect(screen, trunk_color, (cx - 1, cy + 2, 2, 4))
                elif terrain_type == TERRAIN_MOUNTAIN:
                    pygame.draw.polygon(screen, (168, 170, 176), [
                        (tile_x + 4, tile_y + TILE_SIZE - 3),
                        (tile_x + TILE_SIZE // 2 - 4, tile_y + 10),
                        (tile_x + TILE_SIZE - 10, tile_y + TILE_SIZE - 3),
                    ])
                    pygame.draw.polygon(screen, (148, 150, 158), [
                        (tile_x + 10, tile_y + TILE_SIZE - 4),
                        (tile_x + TILE_SIZE // 2 + 2, tile_y + 6),
                        (tile_x + TILE_SIZE - 4, tile_y + TILE_SIZE - 4),
                    ])
                    pygame.draw.polygon(screen, (210, 212, 218), [
                        (tile_x + TILE_SIZE // 2 - 2, tile_y + 11),
                        (tile_x + TILE_SIZE // 2 + 3, tile_y + 17),
                        (tile_x + TILE_SIZE // 2 - 7, tile_y + 18),
                    ])
                elif terrain_type == TERRAIN_WATER:
                    wave_shift = (now // 180 + i + j) % 8
                    for k in range(2):
                        y = tile_y + 11 + k * 12 + (wave_shift % 3)
                        pygame.draw.arc(screen, (132, 168, 194), (tile_x + 4, y, TILE_SIZE - 8, 10), 0, math.pi, 1)

        # 领土改为边线显示，保留地形中心纹理
        self.draw_territory_borders(screen)

        # 鼠标悬停高亮
        if self.hover_pos and not self.show_help:
            hx, hy = self.hover_pos
            if 0 <= hx < BOARD_SIZE and 0 <= hy < BOARD_SIZE:
                hover_surf = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
                hover_surf.fill(COLORS['HOVER'])
                screen.blit(hover_surf, (hy * TILE_SIZE, hx * TILE_SIZE))
                pygame.draw.rect(screen, (236, 236, 236), (hy * TILE_SIZE, hx * TILE_SIZE, TILE_SIZE, TILE_SIZE), 1)

        # 可移动范围
        for pos in self.possible_moves:
            x, y = pos
            pygame.draw.rect(screen, COLORS['MOVE_RANGE'], (y * TILE_SIZE, x * TILE_SIZE, TILE_SIZE, TILE_SIZE), 2)

        # 网格线
        for i in range(BOARD_SIZE):
            for j in range(BOARD_SIZE):
                pygame.draw.rect(screen, COLORS['GRID'], (j * TILE_SIZE, i * TILE_SIZE, TILE_SIZE, TILE_SIZE), 1)

        # 城市
        for i in range(BOARD_SIZE):
            for j in range(BOARD_SIZE):
                _, _, city_type, _ = self.board[i, j]
                if city_type <= 0:
                    continue

                x = j * TILE_SIZE
                y = i * TILE_SIZE
                shadow = (x + 1, y + 2)
                if city_type == CITY_CAPITAL:
                    pygame.draw.rect(screen, (68, 58, 58), (shadow[0] + TILE_SIZE // 4, shadow[1] + TILE_SIZE // 4, TILE_SIZE // 2, TILE_SIZE // 2))
                    pygame.draw.rect(screen, COLORS['CAPITAL'], (x + TILE_SIZE // 4, y + TILE_SIZE // 4, TILE_SIZE // 2, TILE_SIZE // 2))
                    pygame.draw.polygon(screen, (230, 190, 70), [
                        (x + TILE_SIZE // 4, y + TILE_SIZE // 4),
                        (x + TILE_SIZE * 3 // 4, y + TILE_SIZE // 4),
                        (x + TILE_SIZE // 2, y + 2),
                    ])
                elif city_type == CITY_MAJOR:
                    pygame.draw.rect(screen, (78, 68, 52), (shadow[0] + TILE_SIZE // 4, shadow[1] + TILE_SIZE // 2, TILE_SIZE // 2, TILE_SIZE // 2))
                    pygame.draw.rect(screen, COLORS['MAJOR_CITY'], (x + TILE_SIZE // 4, y + TILE_SIZE // 2, TILE_SIZE // 2, TILE_SIZE // 2))
                    pygame.draw.polygon(screen, (170, 132, 92), [
                        (x + TILE_SIZE // 4, y + TILE_SIZE // 2),
                        (x + TILE_SIZE * 3 // 4, y + TILE_SIZE // 2),
                        (x + TILE_SIZE // 2, y + TILE_SIZE // 3),
                    ])
                else:
                    pygame.draw.rect(screen, (76, 70, 62), (shadow[0] + TILE_SIZE // 3, shadow[1] + TILE_SIZE // 2, TILE_SIZE // 3, TILE_SIZE // 2))
                    pygame.draw.rect(screen, COLORS['CITY'], (x + TILE_SIZE // 3, y + TILE_SIZE // 2, TILE_SIZE // 3, TILE_SIZE // 2))
                    pygame.draw.rect(screen, (156, 140, 124), (x + TILE_SIZE // 4, y + TILE_SIZE // 2, TILE_SIZE // 2, TILE_SIZE // 8))

        # 金矿标记
        for i in range(BOARD_SIZE):
            for j in range(BOARD_SIZE):
                if self.resource_map[i, j] != RESOURCE_GOLD_MINE:
                    continue

                x = j * TILE_SIZE
                y = i * TILE_SIZE
                icon_x = x + TILE_SIZE // 2 - 8
                icon_y = y + TILE_SIZE // 2 - 8
                glow = pygame.Surface((18, 18), pygame.SRCALPHA)
                glow.fill((255, 220, 80, 56))
                screen.blit(glow, (icon_x - 1, icon_y - 1))
                self.draw_hud_legend_icon(screen, 'gold_mine', icon_x, icon_y, size=16)

                mine_owner = self.board[i, j, 0]
                if mine_owner > 0:
                    pygame.draw.rect(
                        screen,
                        COLORS[mine_owner],
                        (x + 4, y + 4, TILE_SIZE - 8, TILE_SIZE - 8),
                        1,
                        border_radius=4,
                    )

        # 单位移动动画
        active_animations = self.collect_active_move_animations(now)
        animation_targets = {anim['to'] for anim in active_animations}

        # 静态单位
        for i in range(BOARD_SIZE):
            for j in range(BOARD_SIZE):
                player, hp, _, _ = self.board[i, j]
                if hp <= 0:
                    continue
                if (i, j) in animation_targets:
                    continue

                center_x = j * TILE_SIZE + TILE_SIZE // 2
                center_y = i * TILE_SIZE + TILE_SIZE // 2
                self.draw_soldier_icon(screen, player, hp, (center_x, center_y))

                move_count = self.move_count_grid[i, j]
                if move_count > 0:
                    self.draw_text_with_shadow(screen, CHINESE_FONT_TINY, f'{move_count}/3', (j * TILE_SIZE + 2, i * TILE_SIZE + 2), (255, 250, 210))

        # 动态单位
        for anim in active_animations:
            elapsed = now - anim['start']
            progress = max(0.0, min(1.0, elapsed / anim['duration']))
            eased = 1.0 - (1.0 - progress) * (1.0 - progress)

            from_x, from_y = anim['from']
            to_x, to_y = anim['to']
            start_px = from_y * TILE_SIZE + TILE_SIZE // 2
            start_py = from_x * TILE_SIZE + TILE_SIZE // 2
            end_px = to_y * TILE_SIZE + TILE_SIZE // 2
            end_py = to_x * TILE_SIZE + TILE_SIZE // 2
            current_px = int(start_px + (end_px - start_px) * eased)
            current_py = int(start_py + (end_py - start_py) * eased)

            self.draw_soldier_icon(screen, anim['player'], anim['hp'], (current_px, current_py))

        # 首都标记（脉冲效果）
        pulse = int(2 * math.sin(now / 220))
        for player, (x, y) in self.capitals.items():
            if player in self.players:
                pygame.draw.circle(
                    screen,
                    (250, 218, 96),
                    (y * TILE_SIZE + TILE_SIZE // 2, x * TILE_SIZE + TILE_SIZE // 2),
                    TILE_SIZE // 4 + pulse,
                    2,
                )

        # 战斗闪烁和飘字
        self.draw_combat_effects(screen, now)

        # HUD 右侧栏
        panel_x = BOARD_PIXEL_SIZE
        pygame.draw.rect(screen, COLORS['PANEL'], (panel_x, 0, SIDE_PANEL_WIDTH, HEIGHT))

        status_box = pygame.Rect(panel_x + 10, 10, SIDE_PANEL_WIDTH - 20, 250)
        log_box = pygame.Rect(panel_x + 10, 270, SIDE_PANEL_WIDTH - 20, 300)
        ops_box = pygame.Rect(panel_x + 10, 580, SIDE_PANEL_WIDTH - 20, 210)
        for box in (status_box, log_box, ops_box):
            pygame.draw.rect(screen, COLORS['PANEL_BOX'], box, border_radius=10)
            pygame.draw.rect(screen, COLORS['PANEL_STROKE'], box, 1, border_radius=10)

        # 左侧状态区
        if not self.game_over:
            if self.current_player in self.ai_players:
                status_text = f'玩家{self.current_player} (AI)'
                status_color = COLORS['AI_THINKING']
            else:
                status_text = f'玩家{self.current_player}'
                status_color = COLORS[self.current_player]
                if self.player_defeated and self.game_mode == MODE_SINGLE_AI:
                    status_text += ' 观战中'
            self.draw_text_with_shadow(screen, CHINESE_FONT_MEDIUM, status_text, (status_box.x + 12, status_box.y + 10), status_color)
            self.draw_text_with_shadow(screen, CHINESE_FONT_SMALL, f'第 {self.round_count} 轮', (status_box.x + 12, status_box.y + 40), (224, 228, 236))
            self.draw_text_with_shadow(screen, CHINESE_FONT_SMALL, f'行动点: {self.steps_left}', (status_box.x + 12, status_box.y + 66), (214, 220, 230))
            self.draw_text_with_shadow(screen, CHINESE_FONT_TINY, f'模式: {MODE_LABELS.get(self.game_mode, self.game_mode)}', (status_box.x + 12, status_box.y + 88), (180, 190, 206))
        elif self.winner:
            self.draw_text_with_shadow(screen, CHINESE_FONT_MEDIUM, f'胜利者: 玩家{self.winner}', (status_box.x + 12, status_box.y + 10), COLORS[self.winner])
        else:
            self.draw_text_with_shadow(screen, CHINESE_FONT_MEDIUM, '游戏结束: 平局', (status_box.x + 12, status_box.y + 10), (228, 228, 228))

        territory_x = status_box.x + 12
        territory_y = status_box.y + 128
        for player in [1, 2, 3, 4]:
            active = player in self.players
            block_color = COLORS[player] if active else (100, 104, 110)
            pygame.draw.rect(screen, block_color, (territory_x, territory_y, 12, 12), border_radius=2)
            suffix = '' if active else 'x'
            self.draw_text_with_shadow(
                screen,
                CHINESE_FONT_TINY,
                f'{self.territory_count[player]}{suffix}',
                (territory_x + 16, territory_y - 1),
                (236, 236, 240),
            )
            territory_x += 58

        # 图例
        legend_title_y = territory_y + 20
        self.draw_text_with_shadow(screen, CHINESE_FONT_TINY, '图例', (status_box.x + 12, legend_title_y), (214, 220, 232))
        legend_items = [
            ('small_city', '小城市'),
            ('major_city', '大城市'),
            ('capital', '首都'),
            ('gold_mine', '金矿'),
        ]
        for idx, (legend_type, label) in enumerate(legend_items):
            row_y = legend_title_y + 18 + idx * 18
            self.draw_hud_legend_icon(screen, legend_type, status_box.x + 12, row_y, size=14)
            self.draw_text_with_shadow(screen, CHINESE_FONT_TINY, label, (status_box.x + 34, row_y - 1), (224, 230, 240))

        # 中间日志区
        self.draw_text_with_shadow(screen, CHINESE_FONT_SMALL, '战报', (log_box.x + 10, log_box.y + 8), (220, 226, 236))
        visible_logs, max_scroll = self.get_visible_logs()
        for idx, entry in enumerate(visible_logs):
            brightness = 150 + idx * 35
            color = (brightness, brightness, min(255, brightness + 10))
            short_entry = entry if len(entry) <= 24 else entry[:23] + '…'
            self.draw_text_with_shadow(screen, CHINESE_FONT_TINY, short_entry, (log_box.x + 12, log_box.y + 34 + idx * 24), color)

        if max_scroll > 0:
            self.draw_text_with_shadow(
                screen,
                CHINESE_FONT_TINY,
                f'滚动 {self.log_scroll_offset}/{max_scroll}',
                (log_box.right - 120, log_box.bottom - 20),
                (172, 180, 196),
            )

        # 操作区
        self.draw_text_with_shadow(screen, CHINESE_FONT_SMALL, '操作', (ops_box.x + 12, ops_box.y + 8), (224, 228, 236))
        human_turn = self.is_human_turn()
        if self.game_over:
            button_label = '已结束'
        elif self.current_player in self.ai_players:
            button_label = 'AI回合'
        elif human_turn:
            button_label = '结束回合'
        else:
            button_label = '等待中'
        is_pressed = now < self.button_press_until_ms
        button_w = 148
        button_h = 42
        button_x = ops_box.x + (ops_box.width - button_w) // 2
        button_y = ops_box.y + 88
        self.end_turn_button = pygame.Rect(button_x, button_y, button_w, button_h)
        self.draw_stylish_button(
            screen,
            self.end_turn_button,
            button_label,
            self.button_hovered,
            is_pressed,
            disabled=not human_turn,
        )
        help_button_w = 148
        help_button_h = 34
        help_button_x = ops_box.x + (ops_box.width - help_button_w) // 2
        help_button_y = button_y + button_h + 10
        self.help_button = pygame.Rect(help_button_x, help_button_y, help_button_w, help_button_h)
        help_hovered = (not self.show_help) and self.help_button.collidepoint(pygame.mouse.get_pos())
        help_pressed = now < self.help_button_press_until_ms
        self.draw_stylish_button(
            screen,
            self.help_button,
            '规则说明',
            help_hovered,
            help_pressed,
            disabled=False,
        )

        self.draw_text_with_shadow(screen, CHINESE_FONT_TINY, 'H:帮助  R:重开  M:模式', (ops_box.x + 14, ops_box.y + 178), (184, 192, 208))

        tips = '左键选择 右键取消 滚轮日志 ESC退出'
        self.draw_text_with_shadow(screen, CHINESE_FONT_TINY, tips, (ops_box.x + 14, ops_box.y + 194), (188, 194, 204))

        # 帮助弹窗
        if self.show_help:
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 166))
            screen.blit(overlay, (0, 0))

            panel = pygame.Rect(68, 70, WIDTH - 136, HEIGHT - 210)
            pygame.draw.rect(screen, (34, 40, 48), panel, border_radius=12)
            pygame.draw.rect(screen, (134, 150, 172), panel, 2, border_radius=12)

            close_size = 30
            self.help_close_button = pygame.Rect(panel.right - close_size - 12, panel.y + 12, close_size, close_size)
            close_hover = self.help_close_button.collidepoint(pygame.mouse.get_pos())
            close_bg = (122, 74, 74) if close_hover else (82, 56, 56)
            pygame.draw.rect(screen, close_bg, self.help_close_button, border_radius=7)
            pygame.draw.rect(screen, (204, 164, 164), self.help_close_button, 1, border_radius=7)
            cx, cy = self.help_close_button.center
            pygame.draw.line(screen, (242, 232, 232), (cx - 6, cy - 6), (cx + 6, cy + 6), 2)
            pygame.draw.line(screen, (242, 232, 232), (cx + 6, cy - 6), (cx - 6, cy + 6), 2)

            help_lines = [
                '游戏说明',
                '1. 平原/山脉: 仅上下左右移动; 涉及山脉移动消耗2步。',
                '2. 森林: 8方向移动1格; 水域: 曼哈顿距离不超过2格。',
                '3. 每个士兵每回合最多移动3次。',
                '4. 回合制生产: 每轮结束后进行城市生产与包围占领。',
                '5. 金矿每轮为占领方提供+5兵力，有兵则额外+5血量。',
                '6. 模式支持: 4人本地对战 / 1人对3个AI (M返回模式选择)。',
                '7. 单人模式下玩家1被淘汰后可观战。',
                '按 H 或点击右上角 X 关闭帮助。',
            ]

            for idx, line in enumerate(help_lines):
                font = CHINESE_FONT_SMALL if idx == 0 else CHINESE_FONT_TINY
                color = (232, 236, 244) if idx == 0 else (204, 212, 226)
                self.draw_text_with_shadow(screen, font, line, (panel.x + 24, panel.y + 22 + idx * 30), color)
        else:
            self.help_close_button = pygame.Rect(0, 0, 0, 0)
