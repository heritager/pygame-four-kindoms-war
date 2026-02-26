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
    MODE_SINGLE_AI,
    TILE_SIZE,
    WIDTH,
)


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
        self.mode_button_hotseat = pygame.Rect(WIDTH // 2 - 180, HEIGHT // 2 - 30, 360, 58)
        self.mode_button_ai = pygame.Rect(WIDTH // 2 - 180, HEIGHT // 2 + 46, 360, 58)

    def start_game(self, mode):
        self.game = self.game_class(mode)

    def draw_text_with_shadow(self, font, text, pos, color, center=False):
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
        self.screen.blit(shadow_surf, shadow_rect)
        self.screen.blit(text_surf, text_rect)

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
        self.draw_text_with_shadow(CHINESE_FONT_TINY, '按键 1/2 也可快速选择', (WIDTH // 2, panel.y + 78), (176, 188, 206), center=True)

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
                hover_hotseat = self.mode_button_hotseat.collidepoint(mouse_pos)
                hover_ai = self.mode_button_ai.collidepoint(mouse_pos)

                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        self.running = False
                    elif event.type == pygame.KEYDOWN:
                        if event.key in (pygame.K_1, pygame.K_KP1):
                            self.start_game(MODE_HOTSEAT)
                        elif event.key in (pygame.K_2, pygame.K_KP2):
                            self.start_game(MODE_SINGLE_AI)
                        elif event.key == pygame.K_ESCAPE:
                            self.running = False
                    elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                        if hover_hotseat:
                            self.start_game(MODE_HOTSEAT)
                        elif hover_ai:
                            self.start_game(MODE_SINGLE_AI)

                self.draw_mode_menu(hover_hotseat, hover_ai)
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
                        self.game = self.game_class(game.game_mode)
                        game = self.game
                    elif event.key == pygame.K_m:
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
