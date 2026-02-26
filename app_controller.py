import pygame

from constants import (
    BOARD_PIXEL_SIZE,
    CHINESE_FONT_LARGE,
    CHINESE_FONT_SMALL,
    CHINESE_FONT_TINY,
    COLORS,
    FPS,
    HEIGHT,
    MODE_HOTSEAT,
    MODE_LABELS,
    MODE_SINGLE_AI,
    TILE_SIZE,
    WIDTH,
)
from map_presets import DEFAULT_MAP_PRESET, MAP_PRESET_ORDER, MAP_PRESETS
from ui_text import draw_text_with_shadow as draw_text_with_shadow_shared


class App:
    def __init__(self, game_class):
        if not pygame.get_init():
            pygame.init()
        self.game_class = game_class
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption('四国争霸')
        self.clock = pygame.time.Clock()
        self.game = None
        self.running = True
        self.pending_mode = None
        self.mode_button_hotseat = pygame.Rect(WIDTH // 2 - 180, HEIGHT // 2 - 30, 360, 58)
        self.mode_button_ai = pygame.Rect(WIDTH // 2 - 180, HEIGHT // 2 + 46, 360, 58)
        self.map_buttons = [
            pygame.Rect(WIDTH // 2 - 180, HEIGHT // 2 - 40 + idx * 74, 360, 58)
            for idx in range(len(MAP_PRESET_ORDER))
        ]
        self.map_back_button = pygame.Rect(WIDTH // 2 - 180, HEIGHT // 2 + 200, 360, 42)

    def start_game(self, mode, map_preset_id=DEFAULT_MAP_PRESET):
        self.game = self.game_class(mode, map_preset_id=map_preset_id)
        self.pending_mode = None

    def draw_text_with_shadow(self, font, text, pos, color, center=False):
        draw_text_with_shadow_shared(self.screen, font, text, pos, color, center=center)

    def draw_mode_button(self, rect, title, subtitle, hovered):
        base = (64, 104, 146)
        hover = (90, 138, 186)
        shadow = (42, 72, 102)
        color = hover if hovered else base

        shadow_rect = pygame.Rect(rect.x, rect.y + 4, rect.width, rect.height)
        pygame.draw.rect(self.screen, shadow, shadow_rect, border_radius=10)
        pygame.draw.rect(self.screen, color, rect, border_radius=10)
        pygame.draw.rect(self.screen, (218, 226, 236), rect, 1, border_radius=10)

        highlight = pygame.Surface((rect.width - 16, rect.height // 2 - 6), pygame.SRCALPHA)
        highlight.fill((255, 255, 255, 42))
        self.screen.blit(highlight, (rect.x + 8, rect.y + 6))

        self.draw_text_with_shadow(CHINESE_FONT_SMALL, title, (rect.x + 16, rect.y + 10), (248, 248, 252))
        self.draw_text_with_shadow(CHINESE_FONT_TINY, subtitle, (rect.x + 16, rect.y + 34), (224, 230, 240))

    def draw_mode_menu(self, hover_hotseat, hover_ai):
        self.screen.fill(COLORS['BACKGROUND'])

        panel = pygame.Rect(120, 120, WIDTH - 240, HEIGHT - 260)
        pygame.draw.rect(self.screen, COLORS['PANEL_BOX'], panel, border_radius=14)
        pygame.draw.rect(self.screen, COLORS['PANEL_STROKE'], panel, 2, border_radius=14)

        self.draw_text_with_shadow(CHINESE_FONT_LARGE, '选择游戏模式', (WIDTH // 2, panel.y + 42), (236, 240, 248), center=True)
        self.draw_text_with_shadow(CHINESE_FONT_TINY, '按键 1/2 选择模式，下一步选择地图关卡', (WIDTH // 2, panel.y + 78), (176, 188, 206), center=True)

        self.draw_mode_button(self.mode_button_hotseat, '1. 4人本地对战', '4个玩家轮流手动操作', hover_hotseat)
        self.draw_mode_button(self.mode_button_ai, '2. 1人对战3个AI', '玩家1手动操作，玩家2/3/4由AI控制', hover_ai)

        intro_box = pygame.Rect(panel.x + 40, panel.bottom - 132, panel.width - 80, 84)
        pygame.draw.rect(self.screen, (30, 36, 44), intro_box, border_radius=10)
        pygame.draw.rect(self.screen, (108, 122, 142), intro_box, 1, border_radius=10)
        self.draw_text_with_shadow(CHINESE_FONT_TINY, '开页说明', (intro_box.x + 12, intro_box.y + 8), (218, 224, 236))
        intro_lines = [
            '目标: 夺取敌方首都并存活到最后。城市每轮会产兵，控制城市就是控制资源。',
            '地形: 平原/山脉四向，森林八向，水域可2格机动但上岸仅1格。',
            '操作: 左键选中并移动，右键取消，滚轮看战报，H帮助，M回模式。',
        ]
        for idx, line in enumerate(intro_lines):
            self.draw_text_with_shadow(
                CHINESE_FONT_TINY,
                line,
                (intro_box.x + 12, intro_box.y + 28 + idx * 18),
                (188, 198, 214),
            )

        self.draw_text_with_shadow(CHINESE_FONT_TINY, 'ESC 退出', (WIDTH // 2, panel.bottom - 34), (176, 188, 206), center=True)

    def draw_map_menu(self, hover_map_idx, hover_back):
        self.screen.fill(COLORS['BACKGROUND'])

        panel = pygame.Rect(120, 80, WIDTH - 240, HEIGHT - 160)
        pygame.draw.rect(self.screen, COLORS['PANEL_BOX'], panel, border_radius=14)
        pygame.draw.rect(self.screen, COLORS['PANEL_STROKE'], panel, 2, border_radius=14)

        mode_name = MODE_LABELS.get(self.pending_mode, self.pending_mode)
        self.draw_text_with_shadow(CHINESE_FONT_LARGE, '选择地图关卡', (WIDTH // 2, panel.y + 40), (236, 240, 248), center=True)
        self.draw_text_with_shadow(CHINESE_FONT_TINY, f'当前模式: {mode_name}', (WIDTH // 2, panel.y + 74), (176, 188, 206), center=True)
        self.draw_text_with_shadow(CHINESE_FONT_TINY, '按键 1/2/3 选择关卡，Backspace 返回模式选择', (WIDTH // 2, panel.y + 96), (176, 188, 206), center=True)

        for idx, map_id in enumerate(MAP_PRESET_ORDER):
            preset = MAP_PRESETS[map_id]
            title = f'{idx + 1}. {preset["name"]}'
            subtitle = preset['subtitle']
            self.draw_mode_button(self.map_buttons[idx], title, subtitle, hover_map_idx == idx)

        back_base = (80, 88, 102)
        back_hover = (102, 112, 130)
        back_color = back_hover if hover_back else back_base
        pygame.draw.rect(self.screen, back_color, self.map_back_button, border_radius=10)
        pygame.draw.rect(self.screen, (198, 208, 220), self.map_back_button, 1, border_radius=10)
        self.draw_text_with_shadow(CHINESE_FONT_SMALL, '返回模式选择', self.map_back_button.center, (236, 240, 246), center=True)

        self.draw_text_with_shadow(CHINESE_FONT_TINY, 'ESC 退出', (WIDTH // 2, panel.bottom - 30), (176, 188, 206), center=True)

    def handle_human_click(self, board_x, board_y):
        game = self.game

        if game.selected_pos is None:
            player, hp, _, _ = game.board[board_x, board_y]
            if player == game.current_player and hp > 0:
                game.selected_pos = (board_x, board_y)
                game.calculate_possible_moves((board_x, board_y))
            return

        if (board_x, board_y) in game.possible_moves:
            success, message = game.move_soldier(game.selected_pos, (board_x, board_y))
            if success:
                game.log.append(message)
                if game.steps_left <= 0:
                    game.next_player()
            else:
                game.log.append(f'移动失败: {message}')

            game.selected_pos = None
            game.possible_moves = []
            return

        # 点击其他位置：改选或取消
        player, hp, _, _ = game.board[board_x, board_y]
        if player == game.current_player and hp > 0:
            game.selected_pos = (board_x, board_y)
            game.calculate_possible_moves((board_x, board_y))
        else:
            game.selected_pos = None
            game.possible_moves = []

    def run(self):
        while self.running:
            if self.game is None:
                mouse_pos = pygame.mouse.get_pos()
                if self.pending_mode is None:
                    hover_hotseat = self.mode_button_hotseat.collidepoint(mouse_pos)
                    hover_ai = self.mode_button_ai.collidepoint(mouse_pos)

                    for event in pygame.event.get():
                        if event.type == pygame.QUIT:
                            self.running = False
                        elif event.type == pygame.KEYDOWN:
                            if event.key in (pygame.K_1, pygame.K_KP1):
                                self.pending_mode = MODE_HOTSEAT
                            elif event.key in (pygame.K_2, pygame.K_KP2):
                                self.pending_mode = MODE_SINGLE_AI
                            elif event.key == pygame.K_ESCAPE:
                                self.running = False
                        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                            if hover_hotseat:
                                self.pending_mode = MODE_HOTSEAT
                            elif hover_ai:
                                self.pending_mode = MODE_SINGLE_AI

                    self.draw_mode_menu(hover_hotseat, hover_ai)
                else:
                    hover_map_idx = None
                    for idx, rect in enumerate(self.map_buttons):
                        if rect.collidepoint(mouse_pos):
                            hover_map_idx = idx
                            break
                    hover_back = self.map_back_button.collidepoint(mouse_pos)

                    for event in pygame.event.get():
                        if event.type == pygame.QUIT:
                            self.running = False
                        elif event.type == pygame.KEYDOWN:
                            if event.key in (pygame.K_1, pygame.K_KP1):
                                self.start_game(self.pending_mode, MAP_PRESET_ORDER[0])
                            elif event.key in (pygame.K_2, pygame.K_KP2) and len(MAP_PRESET_ORDER) >= 2:
                                self.start_game(self.pending_mode, MAP_PRESET_ORDER[1])
                            elif event.key in (pygame.K_3, pygame.K_KP3) and len(MAP_PRESET_ORDER) >= 3:
                                self.start_game(self.pending_mode, MAP_PRESET_ORDER[2])
                            elif event.key in (pygame.K_BACKSPACE, pygame.K_m):
                                self.pending_mode = None
                            elif event.key == pygame.K_ESCAPE:
                                self.running = False
                        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                            if hover_back:
                                self.pending_mode = None
                                continue
                            if hover_map_idx is not None:
                                self.start_game(self.pending_mode, MAP_PRESET_ORDER[hover_map_idx])

                    if self.game is not None:
                        continue
                    self.draw_map_menu(hover_map_idx, hover_back)
                pygame.display.flip()
                self.clock.tick(FPS)
                continue

            game = self.game
            mouse_pos = pygame.mouse.get_pos()
            human_turn = game.is_human_turn()
            game.button_hovered = human_turn and game.end_turn_button.collidepoint(mouse_pos)
            if (not game.show_help) and (mouse_pos[0] < BOARD_PIXEL_SIZE and mouse_pos[1] < BOARD_PIXEL_SIZE):
                game.hover_pos = (mouse_pos[1] // TILE_SIZE, mouse_pos[0] // TILE_SIZE)
            else:
                game.hover_pos = None

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False

                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_r:
                        self.game = self.game_class(
                            game.game_mode,
                            map_preset_id=getattr(game, 'map_preset_id', DEFAULT_MAP_PRESET),
                        )
                        game = self.game
                    elif event.key in (pygame.K_m, pygame.K_BACKSPACE):
                        self.pending_mode = None
                        self.game = None
                        break
                    elif event.key == pygame.K_h:
                        game.show_help = not game.show_help
                    elif event.key == pygame.K_ESCAPE:
                        self.running = False

                elif event.type == pygame.MOUSEWHEEL:
                    if event.y > 0:
                        game.scroll_log(1)
                    elif event.y < 0:
                        game.scroll_log(-1)

                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 3:
                        game.selected_pos = None
                        game.possible_moves = []
                    elif event.button == 4:
                        game.scroll_log(1)
                    elif event.button == 5:
                        game.scroll_log(-1)
                    elif event.button == 1:
                        x, y = event.pos

                        if game.show_help and game.help_close_button.collidepoint(x, y):
                            game.show_help = False
                            continue

                        if (not game.show_help) and game.help_button.collidepoint(x, y):
                            game.help_button_press_until_ms = pygame.time.get_ticks() + 120
                            game.show_help = True
                            continue
                        if (not game.show_help) and game.mode_menu_button.collidepoint(x, y):
                            self.pending_mode = None
                            self.game = None
                            break

                        if not game.game_over and not game.show_help:
                            human_turn = game.is_human_turn()

                            if game.end_turn_button.collidepoint(x, y) and human_turn:
                                game.button_press_until_ms = pygame.time.get_ticks() + 120
                                game.steps_left = 0
                                game.log.append(f'玩家{game.current_player}主动结束回合')
                                game.next_player()
                                continue

                            if not human_turn:
                                continue

                            if x < BOARD_PIXEL_SIZE and y < BOARD_PIXEL_SIZE:
                                board_x, board_y = y // TILE_SIZE, x // TILE_SIZE
                                self.handle_human_click(board_x, board_y)

            if self.game is None:
                continue

            # AI 自动行动
            game.maybe_run_ai_turn()

            # 绘制游戏
            game.draw(self.screen)

            # 绘制选中的棋子
            if game.selected_pos and not game.show_help:
                x, y = game.selected_pos
                pygame.draw.rect(self.screen, COLORS['SELECTED'], (y * TILE_SIZE, x * TILE_SIZE, TILE_SIZE, TILE_SIZE), 3)

            pygame.display.flip()
            self.clock.tick(FPS)
