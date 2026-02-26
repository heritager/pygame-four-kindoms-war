import sys

import pygame

from game_main import Game
from app_controller import App
from constants import MODE_SINGLE_AI


def main():
    # 兼容旧入口：直接进入单人对AI模式。
    app = App(Game)
    app.start_game(MODE_SINGLE_AI)
    app.run()
    pygame.quit()
    sys.exit()


if __name__ == '__main__':
    main()
