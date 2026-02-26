import sys

import pygame

from app_controller import App


def run_app(game_class, initial_mode=None):
    app = App(game_class)
    if initial_mode is not None:
        app.start_game(initial_mode)
    app.run()
    pygame.quit()
    sys.exit()
