from .game_core import Game


def main():
    from ..entry.launcher import run_app

    run_app(Game)


if __name__ == '__main__':
    main()
