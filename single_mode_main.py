from constants import MODE_SINGLE_AI
from game_main import Game
from launcher import run_app


def main():
    # 兼容旧入口：直接进入单人对AI模式。
    run_app(Game, MODE_SINGLE_AI)


if __name__ == '__main__':
    main()
