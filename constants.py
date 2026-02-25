import pygame

pygame.init()


def get_font(size):
    # 优先尝试像素/中文字体名称，pygame 会自动处理回退
    return pygame.font.SysFont('zpix,simhei,microsoft yahei,wqy-zenhei', size)


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
BOARD_PIXEL_SIZE = BOARD_SIZE * TILE_SIZE
SIDE_PANEL_WIDTH = 320
WIDTH = BOARD_PIXEL_SIZE + SIDE_PANEL_WIDTH
HEIGHT = BOARD_PIXEL_SIZE
FPS = 60


COLORS = {
    'BACKGROUND': (33, 37, 43),
    'GRID': (98, 104, 112),
    'NEUTRAL': (120, 124, 132),
    'PLAIN': (226, 224, 214),
    'FOREST': (175, 194, 168),
    'MOUNTAIN': (188, 190, 194),
    'WATER': (159, 186, 206),
    'GOLD_MINE': (255, 215, 0),
    'BUTTON': (74, 126, 176),
    'BUTTON_HOVER': (102, 153, 202),
    'BUTTON_SHADOW': (48, 86, 126),
    'PANEL': (24, 28, 34),
    'PANEL_BOX': (36, 42, 49),
    'PANEL_STROKE': (112, 122, 136),
    0: (70, 70, 90),
    1: (220, 60, 60),
    2: (60, 150, 220),
    3: (220, 180, 60),
    4: (100, 200, 100),
    'CITY': (180, 160, 140),
    'MAJOR_CITY': (200, 170, 100),
    'CAPITAL': (200, 100, 100),
    'TEXT': (220, 220, 220),
    'AI_THINKING': (110, 210, 255),
    'SELECTED': (255, 255, 200),
    'MOVE_RANGE': (104, 226, 124),
    'HOVER': (255, 255, 255, 36),
    'ATTACK_FLASH': (255, 64, 64, 140),
    'SHADOW': (16, 20, 24),
}


TERRITORY_COLORS = {
    1: (246, 84, 84),
    2: (84, 192, 255),
    3: (246, 210, 88),
    4: (126, 232, 126),
}


TERRAIN_PLAIN = 0
TERRAIN_FOREST = 1
TERRAIN_MOUNTAIN = 2
TERRAIN_WATER = 3

TERRAIN_NAMES = {
    TERRAIN_PLAIN: '平原',
    TERRAIN_FOREST: '森林',
    TERRAIN_MOUNTAIN: '山脉',
    TERRAIN_WATER: '水域',
}


CITY_NONE = 0
CITY_SMALL = 1
CITY_MAJOR = 2
CITY_CAPITAL = 3


RESOURCE_NONE = 0
RESOURCE_GOLD_MINE = 1


MODE_HOTSEAT = 'hotseat_4p'
MODE_SINGLE_AI = 'single_vs_ai'
MODE_LABELS = {
    MODE_HOTSEAT: '4人本地对战',
    MODE_SINGLE_AI: '1人 vs 3AI',
}
