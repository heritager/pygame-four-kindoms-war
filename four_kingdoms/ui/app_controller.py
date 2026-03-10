import pygame

from ..config.constants import (
    AI_DIFFICULTY_DEFAULT,
    AI_DIFFICULTY_EASY,
    AI_DIFFICULTY_HARD,
    AI_DIFFICULTY_LEARNED,
    AI_DIFFICULTY_LABELS,
    AI_DIFFICULTY_NORMAL,
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
from ..config.map_presets import DEFAULT_MAP_PRESET, MAP_PRESET_ORDER, MAP_PRESETS
from ..audio import (
    MUSIC_GAME,
    MUSIC_MENU,
    SOUND_CLICK,
    SOUND_SELECT,
    get_sound_manager,
    play_music,
    play_sound,
    stop_music,
    toggle_mute,
)
from ..save import get_save_system, quick_save, quick_load
from .ui_text import draw_text_with_shadow as draw_text_with_shadow_shared


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
        self.ai_difficulty = AI_DIFFICULTY_DEFAULT
        self.mode_button_hotseat = pygame.Rect(WIDTH // 2 - 180, HEIGHT // 2 - 30, 360, 58)
        self.mode_button_ai = pygame.Rect(WIDTH // 2 - 180, HEIGHT // 2 + 46, 360, 58)
        self.map_buttons = [
            pygame.Rect(WIDTH // 2 - 180, HEIGHT // 2 - 40 + idx * 74, 360, 58)
            for idx in range(len(MAP_PRESET_ORDER))
        ]
        self.map_back_button = pygame.Rect(WIDTH // 2 - 180, HEIGHT // 2 + 200, 360, 42)

        # 初始化音效管理器
        self.sound_manager = get_sound_manager()
        self.sound_manager.load_all_sounds()
        # 播放主菜单背景音乐
        play_music(MUSIC_MENU)

        # 暂停菜单状态
        self.paused = False
        self.pause_buttons = {
            'resume': pygame.Rect(WIDTH // 2 - 150, HEIGHT // 2 - 80, 300, 45),
            'save': pygame.Rect(WIDTH // 2 - 150, HEIGHT // 2 - 30, 140, 40),
            'load': pygame.Rect(WIDTH // 2 + 10, HEIGHT // 2 - 30, 140, 40),
            'restart': pygame.Rect(WIDTH // 2 - 150, HEIGHT // 2 + 20, 300, 45),
            'settings': pygame.Rect(WIDTH // 2 - 150, HEIGHT // 2 + 70, 300, 45),
            'menu': pygame.Rect(WIDTH // 2 - 150, HEIGHT // 2 + 120, 300, 45),
        }
        self.save_system = None

        # 存档/读档界面
        self.show_save_load = False
        self.save_mode = 'save'  # 'save' or 'load'
        self.save_slot_buttons = {
            slot: pygame.Rect(WIDTH // 2 - 180, HEIGHT // 2 - 60 + (slot - 1) * 55, 360, 48)
            for slot in [1, 2, 3]
        }
        self.save_back_button = pygame.Rect(WIDTH // 2 - 100, HEIGHT // 2 + 105, 200, 42)

        # 开发者选项
        self.show_fps = False
        self.debug_mode = False
        self.infinite_steps = False
        self.fps_counter = 0
        self.fps_timer = 0

        self.settings_buttons = {
            'sound_vol_down': pygame.Rect(WIDTH // 2 - 180, HEIGHT // 2 - 30, 50, 40),
            'sound_vol_up': pygame.Rect(WIDTH // 2 + 130, HEIGHT // 2 - 30, 50, 40),
            'music_vol_down': pygame.Rect(WIDTH // 2 - 180, HEIGHT // 2 + 30, 50, 40),
            'music_vol_up': pygame.Rect(WIDTH // 2 + 130, HEIGHT // 2 + 30, 50, 40),
            'back': pygame.Rect(WIDTH // 2 - 100, HEIGHT // 2 + 100, 200, 45),
        }
        self.show_settings = False

        # 确认对话框状态
        self.show_confirm_dialog = False
        self.confirm_action = None
        self.confirm_message = ""
        self.confirm_buttons = {
            'yes': pygame.Rect(WIDTH // 2 - 100, HEIGHT // 2 + 20, 90, 45),
            'no': pygame.Rect(WIDTH // 2 + 10, HEIGHT // 2 + 20, 90, 45),
        }

    def start_game(self, mode, map_preset_id=DEFAULT_MAP_PRESET, ai_difficulty=None):
        if ai_difficulty is None:
            ai_difficulty = self.ai_difficulty
        if ai_difficulty in AI_DIFFICULTY_LABELS:
            self.ai_difficulty = ai_difficulty
        self.game = self.game_class(mode, map_preset_id=map_preset_id, ai_difficulty=self.ai_difficulty)
        self.pending_mode = None
        # 切换到游戏背景音乐
        play_music(MUSIC_GAME)
        # 自动加载存档系统
        self.save_system = get_save_system()

    def return_to_mode_menu(self):
        self.pending_mode = None
        self.game = None
        self.paused = False
        self.show_settings = False
        self.show_save_load = False
        stop_music()
        play_music(MUSIC_MENU)

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
        self.draw_text_with_shadow(
            CHINESE_FONT_TINY,
            f'AI难度: {AI_DIFFICULTY_LABELS[self.ai_difficulty]} (F1/F2/F3/F4切换)',
            (WIDTH // 2, self.mode_button_ai.bottom + 20),
            (176, 188, 206),
            center=True,
        )

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
        help_text = '按键 1/2/3 选择关卡，Backspace 返回模式选择'
        if self.pending_mode == MODE_SINGLE_AI:
            help_text = (
                f'按键 1/2/3 选择关卡，F1/F2/F3/F4调难度({AI_DIFFICULTY_LABELS[self.ai_difficulty]})，Backspace 返回模式'
            )
        self.draw_text_with_shadow(CHINESE_FONT_TINY, help_text, (WIDTH // 2, panel.y + 96), (176, 188, 206), center=True)

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

    def cycle_selected_unit(self):
        game = self.game
        if game is None or not game.is_human_turn() or game.renderer.show_help:
            return

        movable_units = []
        for pos in game.get_player_soldiers(game.current_player):
            if game.get_possible_moves_for(pos):
                movable_units.append(pos)

        if not movable_units:
            return

        movable_units.sort()
        if game.selected_pos in movable_units:
            current_idx = movable_units.index(game.selected_pos)
            next_pos = movable_units[(current_idx + 1) % len(movable_units)]
        else:
            next_pos = movable_units[0]

        game.selected_pos = next_pos
        game.calculate_possible_moves(next_pos)

    def draw_pause_button(self, rect, text, hovered):
        """绘制暂停菜单按钮"""
        base = (64, 104, 146)
        hover = (90, 138, 186)
        shadow = (42, 72, 102)
        color = hover if hovered else base

        shadow_rect = pygame.Rect(rect.x, rect.y + 3, rect.width, rect.height)
        pygame.draw.rect(self.screen, shadow, shadow_rect, border_radius=8)
        pygame.draw.rect(self.screen, color, rect, border_radius=8)
        pygame.draw.rect(self.screen, (218, 226, 236), rect, 2, border_radius=8)

        self.draw_text_with_shadow(CHINESE_FONT_MEDIUM, text, rect.center, (255, 255, 255), center=True)

    def draw_pause_menu(self, mouse_pos):
        """绘制暂停菜单"""
        # 半透明遮罩
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))

        # 菜单面板
        panel = pygame.Rect(WIDTH // 2 - 180, HEIGHT // 2 - 100, 360, 280)
        pygame.draw.rect(self.screen, (36, 42, 49), panel, border_radius=14)
        pygame.draw.rect(self.screen, (112, 122, 136), panel, 3, border_radius=14)

        # 标题
        self.draw_text_with_shadow(CHINESE_FONT_LARGE, '游戏暂停', (WIDTH // 2, panel.y + 20), (236, 240, 248), center=True)
        self.draw_text_with_shadow(CHINESE_FONT_TINY, '按 P 键返回游戏', (WIDTH // 2, panel.y + 52), (176, 188, 206), center=True)

        # 按钮
        button_labels = {
            'resume': '继续游戏',
            'save': '保存游戏',
            'load': '加载游戏',
            'restart': '重新开始',
            'settings': '设置',
            'menu': '返回主菜单',
        }

        for key, label in button_labels.items():
            hovered = self.pause_buttons[key].collidepoint(mouse_pos)
            self.draw_pause_button(self.pause_buttons[key], label, hovered)

    def draw_settings_menu(self, mouse_pos):
        """绘制设置菜单"""
        # 半透明遮罩
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))

        # 菜单面板
        panel = pygame.Rect(WIDTH // 2 - 200, HEIGHT // 2 - 80, 400, 240)
        pygame.draw.rect(self.screen, (36, 42, 49), panel, border_radius=14)
        pygame.draw.rect(self.screen, (112, 122, 136), panel, 3, border_radius=14)

        # 标题
        self.draw_text_with_shadow(CHINESE_FONT_LARGE, '设置', (WIDTH // 2, panel.y + 15), (236, 240, 248), center=True)

        # 音效音量
        self.draw_text_with_shadow(CHINESE_FONT_SMALL, '音效音量', (panel.x + 20, panel.y + 55), (220, 220, 220))
        sound_vol = self.sound_manager.get_sound_volume()
        vol_bar_width = 120
        vol_bar_x = panel.x + 140
        vol_bar_y = panel.y + 58
        pygame.draw.rect(self.screen, (50, 50, 50), (vol_bar_x, vol_bar_y, vol_bar_width, 20), border_radius=4)
        pygame.draw.rect(self.screen, (64, 104, 146), (vol_bar_x, vol_bar_y, int(vol_bar_width * sound_vol), 20), border_radius=4)
        self.draw_text_with_shadow(CHINESE_FONT_TINY, f'{int(sound_vol * 100)}%', (vol_bar_x + vol_bar_width + 10, vol_bar_y - 2), (200, 200, 200))

        # 音乐音量
        self.draw_text_with_shadow(CHINESE_FONT_SMALL, '背景音乐', (panel.x + 20, panel.y + 95), (220, 220, 220))
        music_vol = self.sound_manager.get_music_volume()
        pygame.draw.rect(self.screen, (50, 50, 50), (vol_bar_x, vol_bar_y + 40, vol_bar_width, 20), border_radius=4)
        pygame.draw.rect(self.screen, (64, 104, 146), (vol_bar_x, vol_bar_y + 40, int(vol_bar_width * music_vol), 20), border_radius=4)
        self.draw_text_with_shadow(CHINESE_FONT_TINY, f'{int(music_vol * 100)}%', (vol_bar_x + vol_bar_width + 10, vol_bar_y + 38), (200, 200, 200))

        # 音量调节按钮
        for key in self.settings_buttons:
            hovered = self.settings_buttons[key].collidepoint(mouse_pos)
            color = (100, 140, 180) if hovered else (70, 110, 150)
            pygame.draw.rect(self.screen, color, self.settings_buttons[key], border_radius=6)
            pygame.draw.rect(self.screen, (200, 200, 200), self.settings_buttons[key], 1, border_radius=6)

        # 按钮文字
        self.draw_text_with_shadow(CHINESE_FONT_TINY, '-', self.settings_buttons['sound_vol_down'].center, (255, 255, 255), center=True)
        self.draw_text_with_shadow(CHINESE_FONT_TINY, '+', self.settings_buttons['sound_vol_up'].center, (255, 255, 255), center=True)
        self.draw_text_with_shadow(CHINESE_FONT_TINY, '-', self.settings_buttons['music_vol_down'].center, (255, 255, 255), center=True)
        self.draw_text_with_shadow(CHINESE_FONT_TINY, '+', self.settings_buttons['music_vol_up'].center, (255, 255, 255), center=True)
        self.draw_text_with_shadow(CHINESE_FONT_SMALL, '返回', self.settings_buttons['back'].center, (255, 255, 255), center=True)

    def toggle_pause(self):
        """切换暂停状态"""
        if self.game and not self.game.game_over:
            self.paused = not self.paused
            if self.paused:
                self.show_settings = False

    def handle_pause_click(self, mouse_pos):
        """处理暂停菜单点击"""
        if self.show_settings:
            # 设置菜单点击处理
            if self.settings_buttons['sound_vol_down'].collidepoint(mouse_pos):
                self.sound_manager.set_sound_volume(self.sound_manager.get_sound_volume() - 0.1)
                play_sound(SOUND_CLICK)
            elif self.settings_buttons['sound_vol_up'].collidepoint(mouse_pos):
                self.sound_manager.set_sound_volume(self.sound_manager.get_sound_volume() + 0.1)
                play_sound(SOUND_CLICK)
            elif self.settings_buttons['music_vol_down'].collidepoint(mouse_pos):
                self.sound_manager.set_music_volume(self.sound_manager.get_music_volume() - 0.1)
                play_sound(SOUND_CLICK)
            elif self.settings_buttons['music_vol_up'].collidepoint(mouse_pos):
                self.sound_manager.set_music_volume(self.sound_manager.get_music_volume() + 0.1)
                play_sound(SOUND_CLICK)
            elif self.settings_buttons['back'].collidepoint(mouse_pos):
                self.show_settings = False
                play_sound(SOUND_CLICK)
        else:
            # 暂停菜单点击处理
            if self.pause_buttons['resume'].collidepoint(mouse_pos):
                self.paused = False
                play_sound(SOUND_CLICK)
            elif self.pause_buttons['save'].collidepoint(mouse_pos):
                self.save_mode = 'save'
                self.show_save_load = True
                play_sound(SOUND_CLICK)
            elif self.pause_buttons['load'].collidepoint(mouse_pos):
                self.save_mode = 'load'
                self.show_save_load = True
                play_sound(SOUND_CLICK)
            elif self.pause_buttons['restart'].collidepoint(mouse_pos):
                play_sound(SOUND_CLICK)
                self.show_confirm("确定要重新开始游戏吗？", 'restart')
            elif self.pause_buttons['settings'].collidepoint(mouse_pos):
                self.show_settings = True
                play_sound(SOUND_CLICK)
            elif self.pause_buttons['menu'].collidepoint(mouse_pos):
                play_sound(SOUND_CLICK)
                self.show_confirm("确定要返回主菜单吗？", 'menu')

    def show_confirm(self, message, action):
        """显示确认对话框"""
        self.show_confirm_dialog = True
        self.confirm_message = message
        self.confirm_action = action

    def draw_confirm_dialog(self, mouse_pos):
        """绘制确认对话框"""
        # 半透明遮罩
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        self.screen.blit(overlay, (0, 0))

        # 对话框
        dialog = pygame.Rect(WIDTH // 2 - 180, HEIGHT // 2 - 40, 360, 140)
        pygame.draw.rect(self.screen, (36, 42, 49), dialog, border_radius=12)
        pygame.draw.rect(self.screen, (112, 122, 136), dialog, 3, border_radius=12)

        # 消息文字（自动换行）
        words = self.confirm_message.split()
        lines = []
        current_line = ""
        for word in words:
            test_line = current_line + " " + word if current_line else word
            if CHINESE_FONT_SMALL.size(test_line)[0] < 320:
                current_line = test_line
            else:
                lines.append(current_line)
                current_line = word
        if current_line:
            lines.append(current_line)

        for i, line in enumerate(lines[:3]):
            self.draw_text_with_shadow(CHINESE_FONT_SMALL, line, (WIDTH // 2, dialog.y + 15 + i * 28), (236, 240, 248), center=True)

        # 按钮
        yes_hover = self.confirm_buttons['yes'].collidepoint(mouse_pos)
        no_hover = self.confirm_buttons['no'].collidepoint(mouse_pos)

        for key, hovered in [('yes', yes_hover), ('no', no_hover)]:
            color = (100, 180, 100) if hovered else (60, 140, 60)
            rect = self.confirm_buttons[key]
            pygame.draw.rect(self.screen, color, rect, border_radius=6)
            pygame.draw.rect(self.screen, (200, 255, 200), rect, 1, border_radius=6)
            label = "确认" if key == 'yes' else "取消"
            self.draw_text_with_shadow(CHINESE_FONT_SMALL, label, rect.center, (255, 255, 255), center=True)

    def draw_save_load_menu(self, mouse_pos):
        """绘制存档/读档界面"""
        # 半透明遮罩
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))

        # 面板
        panel = pygame.Rect(WIDTH // 2 - 200, HEIGHT // 2 - 100, 400, 280)
        pygame.draw.rect(self.screen, (36, 42, 49), panel, border_radius=14)
        pygame.draw.rect(self.screen, (112, 122, 136), panel, 3, border_radius=14)

        title = '保存游戏' if self.save_mode == 'save' else '加载游戏'
        self.draw_text_with_shadow(CHINESE_FONT_LARGE, title, (WIDTH // 2, panel.y + 15), (236, 240, 248), center=True)
        self.draw_text_with_shadow(CHINESE_FONT_TINY, 'F5 快速保存 | F9 快速加载', (WIDTH // 2, panel.y + 45), (176, 188, 206), center=True)

        # 存档位按钮
        for slot in [1, 2, 3]:
            rect = self.save_slot_buttons[slot]
            hovered = rect.collidepoint(mouse_pos)
            save_info = self.save_system.get_save_info(slot) if self.save_system else None

            # 背景
            color = (50, 70, 90) if hovered else (40, 55, 70)
            pygame.draw.rect(self.screen, color, rect, border_radius=8)
            pygame.draw.rect(self.screen, (100, 120, 140), rect, 2, border_radius=8)

            # 存档信息
            if save_info:
                self.draw_text_with_shadow(CHINESE_FONT_SMALL, f'存档 {slot} - {save_info["timestamp"]}', (rect.x + 15, rect.y + 8), (255, 255, 255))
                self.draw_text_with_shadow(CHINESE_FONT_TINY, f'第{save_info["round"]}轮 | 玩家{save_info["current_player"]} | {save_info["map_name"]}', (rect.x + 15, rect.y + 28), (180, 190, 200))
            else:
                status = '空存档位' if self.save_mode == 'save' else '无存档'
                self.draw_text_with_shadow(CHINESE_FONT_SMALL, f'存档 {slot} - {status}', (rect.x + 15, rect.y + 18), (150, 160, 170))

        # 返回按钮
        back_hover = self.save_back_button.collidepoint(mouse_pos)
        color = (100, 140, 180) if back_hover else (70, 110, 150)
        pygame.draw.rect(self.screen, color, self.save_back_button, border_radius=6)
        self.draw_text_with_shadow(CHINESE_FONT_SMALL, '返回', self.save_back_button.center, (255, 255, 255), center=True)

    def handle_save_load_click(self, mouse_pos):
        """处理存档/读档界面点击"""
        # 存档位点击
        for slot, rect in self.save_slot_buttons.items():
            if rect.collidepoint(mouse_pos):
                play_sound(SOUND_CLICK)
                if self.save_mode == 'save':
                    if quick_save(self.game, slot):
                        self.game.log.append(f"游戏已保存到存档 {slot}")
                    else:
                        self.game.log.append("保存失败")
                    self.show_save_load = False
                else:
                    loaded_game = quick_load(slot, self.game_class)
                    if loaded_game:
                        self.game = loaded_game
                        self.game.log.append(f"游戏已从存档 {slot} 加载")
                        self.show_save_load = False
                        self.paused = False
                    else:
                        self.game.log.append("加载失败或存档不存在")
                return

        # 返回按钮
        if self.save_back_button.collidepoint(mouse_pos):
            play_sound(SOUND_CLICK)
            self.show_save_load = False

    def handle_confirm_click(self, mouse_pos):
        """处理确认对话框点击"""
        if self.confirm_buttons['yes'].collidepoint(mouse_pos):
            play_sound(SOUND_CLICK)
            # 执行确认的操作
            if self.confirm_action == 'restart':
                self.game = self.game_class(
                    self.game.game_mode,
                    map_preset_id=getattr(self.game, 'map_preset_id', DEFAULT_MAP_PRESET),
                    ai_difficulty=getattr(self.game, 'ai_difficulty', self.ai_difficulty),
                )
            elif self.confirm_action == 'quit':
                self.running = False
            elif self.confirm_action == 'menu':
                self.return_to_mode_menu()
            self.show_confirm_dialog = False
            self.confirm_action = None
        elif self.confirm_buttons['no'].collidepoint(mouse_pos):
            play_sound(SOUND_CLICK)
            self.show_confirm_dialog = False
            self.confirm_action = None

    def run(self):
        while self.running:
            # 确认对话框事件处理（最高优先级）
            if self.show_confirm_dialog:
                mouse_pos = pygame.mouse.get_pos()
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        self.running = False
                    elif event.type == pygame.KEYDOWN:
                        if event.key in (pygame.K_ESCAPE, pygame.K_n):
                            self.show_confirm_dialog = False
                            self.confirm_action = None
                        elif event.key in (pygame.K_RETURN, pygame.K_y):
                            self.handle_confirm_click(mouse_pos)
                    elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                        self.handle_confirm_click(mouse_pos)

                # 绘制游戏（背景）和确认对话框
                if self.game:
                    self.game.draw(self.screen)
                self.draw_confirm_dialog(mouse_pos)
                pygame.display.flip()
                self.clock.tick(FPS)
                continue

            # 存档/读档界面事件处理
            if self.show_save_load:
                mouse_pos = pygame.mouse.get_pos()
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        self.running = False
                    elif event.type == pygame.KEYDOWN:
                        if event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                            self.show_save_load = False
                    elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                        self.handle_save_load_click(mouse_pos)

                # 绘制游戏（背景）和存档/读档界面
                if self.game:
                    self.game.draw(self.screen)
                self.draw_save_load_menu(mouse_pos)
                pygame.display.flip()
                self.clock.tick(FPS)
                continue

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
                            elif event.key == pygame.K_F1:
                                self.ai_difficulty = AI_DIFFICULTY_EASY
                            elif event.key == pygame.K_F2:
                                self.ai_difficulty = AI_DIFFICULTY_NORMAL
                            elif event.key == pygame.K_F3:
                                self.ai_difficulty = AI_DIFFICULTY_HARD
                            elif event.key == pygame.K_F4:
                                self.ai_difficulty = AI_DIFFICULTY_LEARNED
                            elif event.key == pygame.K_ESCAPE:
                                self.running = False
                        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                            if hover_hotseat:
                                play_sound(SOUND_CLICK)
                                self.pending_mode = MODE_HOTSEAT
                            elif hover_ai:
                                play_sound(SOUND_CLICK)
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
                                self.start_game(self.pending_mode, MAP_PRESET_ORDER[0], self.ai_difficulty)
                            elif event.key in (pygame.K_2, pygame.K_KP2) and len(MAP_PRESET_ORDER) >= 2:
                                self.start_game(self.pending_mode, MAP_PRESET_ORDER[1], self.ai_difficulty)
                            elif event.key in (pygame.K_3, pygame.K_KP3) and len(MAP_PRESET_ORDER) >= 3:
                                self.start_game(self.pending_mode, MAP_PRESET_ORDER[2], self.ai_difficulty)
                            elif event.key == pygame.K_F1:
                                self.ai_difficulty = AI_DIFFICULTY_EASY
                            elif event.key == pygame.K_F2:
                                self.ai_difficulty = AI_DIFFICULTY_NORMAL
                            elif event.key == pygame.K_F3:
                                self.ai_difficulty = AI_DIFFICULTY_HARD
                            elif event.key == pygame.K_F4:
                                self.ai_difficulty = AI_DIFFICULTY_LEARNED
                            elif event.key in (pygame.K_BACKSPACE, pygame.K_m):
                                self.pending_mode = None
                            elif event.key == pygame.K_ESCAPE:
                                self.running = False
                        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                            if hover_back:
                                play_sound(SOUND_CLICK)
                                self.pending_mode = None
                                continue
                            if hover_map_idx is not None:
                                play_sound(SOUND_CLICK)
                                self.start_game(self.pending_mode, MAP_PRESET_ORDER[hover_map_idx], self.ai_difficulty)

                    if self.game is not None:
                        continue
                    self.draw_map_menu(hover_map_idx, hover_back)
                pygame.display.flip()
                self.clock.tick(FPS)
                continue

            if self.paused:
                mouse_pos = pygame.mouse.get_pos()
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        self.running = False
                    elif event.type == pygame.KEYDOWN:
                        if event.key in (pygame.K_p, pygame.K_ESCAPE):
                            self.toggle_pause()
                    elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                        self.handle_pause_click(event.pos)

                if self.game is None:
                    continue

                self.game.draw(self.screen)
                if self.show_settings:
                    self.draw_settings_menu(mouse_pos)
                else:
                    self.draw_pause_menu(mouse_pos)
                pygame.display.flip()
                self.clock.tick(FPS)
                continue

            game = self.game
            renderer = game.renderer
            mouse_pos = pygame.mouse.get_pos()
            human_turn = game.is_human_turn()
            renderer.button_hovered = human_turn and renderer.end_turn_button.collidepoint(mouse_pos)
            if (not renderer.show_help) and (mouse_pos[0] < BOARD_PIXEL_SIZE and mouse_pos[1] < BOARD_PIXEL_SIZE):
                renderer.hover_pos = (mouse_pos[1] // TILE_SIZE, mouse_pos[0] // TILE_SIZE)
            else:
                renderer.hover_pos = None

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False

                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_p:
                        # 切换暂停
                        self.toggle_pause()
                    elif event.key == pygame.K_F5:
                        # 快速保存
                        if self.game and not self.paused:
                            if quick_save(self.game, 1):
                                game.log.append("快速保存成功 (存档 1)")
                            else:
                                game.log.append("快速保存失败")
                            play_sound(SOUND_CLICK)
                    elif event.key == pygame.K_F9:
                        # 快速加载
                        if self.game and not self.paused:
                            loaded_game = quick_load(1, self.game_class)
                            if loaded_game:
                                self.game = loaded_game
                                game = self.game
                                renderer = game.renderer
                                game.log.append("快速加载成功 (存档 1)")
                                self.paused = False
                            else:
                                game.log.append("快速加载失败或存档不存在")
                            play_sound(SOUND_CLICK)
                    elif event.key == pygame.K_r:
                        self.game = self.game_class(
                            game.game_mode,
                            map_preset_id=getattr(game, 'map_preset_id', DEFAULT_MAP_PRESET),
                            ai_difficulty=getattr(game, 'ai_difficulty', self.ai_difficulty),
                        )
                        game = self.game
                        renderer = game.renderer
                        self.paused = False
                    elif event.key == pygame.K_TAB:
                        self.cycle_selected_unit()
                    elif event.key == pygame.K_SPACE:
                        if (not game.game_over) and game.is_human_turn() and (not renderer.show_help) and (not self.paused):
                            renderer.button_press_until_ms = pygame.time.get_ticks() + 120
                            game.steps_left = 0
                            game.log.append(f'玩家{game.current_player}主动结束回合')
                            game.next_player()
                    elif event.key == pygame.K_F1:
                        self.ai_difficulty = AI_DIFFICULTY_EASY
                        if game.game_mode == MODE_SINGLE_AI:
                            game.set_ai_difficulty(AI_DIFFICULTY_EASY)
                    elif event.key == pygame.K_F2:
                        self.ai_difficulty = AI_DIFFICULTY_NORMAL
                        if game.game_mode == MODE_SINGLE_AI:
                            game.set_ai_difficulty(AI_DIFFICULTY_NORMAL)
                    elif event.key == pygame.K_F3:
                        self.ai_difficulty = AI_DIFFICULTY_HARD
                        if game.game_mode == MODE_SINGLE_AI:
                            game.set_ai_difficulty(AI_DIFFICULTY_HARD)
                    elif event.key == pygame.K_F4:
                        self.ai_difficulty = AI_DIFFICULTY_LEARNED
                        if game.game_mode == MODE_SINGLE_AI:
                            game.set_ai_difficulty(AI_DIFFICULTY_LEARNED)
                    elif event.key == pygame.K_F10:
                        # 切换 FPS 显示
                        self.show_fps = not self.show_fps
                    elif event.key == pygame.K_F11:
                        # 切换调试模式
                        self.debug_mode = not self.debug_mode
                        game.log.append(f"调试模式已{'开启' if self.debug_mode else '关闭'}")
                    elif event.key == pygame.K_F12:
                        # 无限行动点（调试用）
                        self.infinite_steps = not self.infinite_steps
                        game.log.append(f"无限行动点已{'开启' if self.infinite_steps else '关闭'}")
                    elif event.key == pygame.K_m:
                        # 切换静音
                        muted = toggle_mute()
                        game.log.append(f"音效{'已静音' if muted else '已取消静音'}")
                    elif event.key in (pygame.K_BACKSPACE,):
                        # 返回主菜单需要确认
                        self.show_confirm("确定要返回主菜单吗？", 'menu')
                    elif event.key == pygame.K_h:
                        renderer.show_help = not renderer.show_help
                    elif event.key == pygame.K_ESCAPE:
                        # 游戏中按 ESC 打开暂停菜单
                        if self.game and not self.game.game_over:
                            self.toggle_pause()
                        else:
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

                        if renderer.show_help and renderer.help_close_button.collidepoint(x, y):
                            renderer.show_help = False
                            continue

                        if (not renderer.show_help) and renderer.help_button.collidepoint(x, y):
                            renderer.help_button_press_until_ms = pygame.time.get_ticks() + 120
                            renderer.show_help = True
                            continue
                        if (not renderer.show_help) and renderer.mode_menu_button.collidepoint(x, y):
                            self.return_to_mode_menu()
                            break

                        if not game.game_over and not renderer.show_help:
                            human_turn = game.is_human_turn()

                            if renderer.end_turn_button.collidepoint(x, y) and human_turn:
                                renderer.button_press_until_ms = pygame.time.get_ticks() + 120
                                if not self.infinite_steps:
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
            if game.selected_pos and not game.renderer.show_help:
                x, y = game.selected_pos
                pygame.draw.rect(self.screen, COLORS['SELECTED'], (y * TILE_SIZE, x * TILE_SIZE, TILE_SIZE, TILE_SIZE), 3)

            # 显示 FPS
            if self.show_fps:
                self.fps_counter = self.clock.get_fps()
                self.draw_text_with_shadow(CHINESE_FONT_TINY, f'FPS: {self.fps_counter:.1f}', (10, HEIGHT - 20), (150, 150, 150))

            # 调试模式显示额外信息
            if self.debug_mode:
                self.draw_text_with_shadow(CHINESE_FONT_TINY, f'步骤：{game.steps_left}/{game.steps_per_turn}', (10, 10), (200, 200, 200))
                self.draw_text_with_shadow(CHINESE_FONT_TINY, f'轮：{game.round_count} | 玩家：{game.current_player}', (10, 28), (200, 200, 200))
                if game.last_move:
                    f, t = game.last_move
                    self.draw_text_with_shadow(CHINESE_FONT_TINY, f'最后移动：{f} -> {t}', (10, 46), (200, 200, 200))

            pygame.display.flip()
            self.clock.tick(FPS)
