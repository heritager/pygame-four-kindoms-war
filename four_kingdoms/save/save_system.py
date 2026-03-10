"""存档/读档系统

支持 3 个存档位，自动存档（每轮结束），JSON 格式存储。
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any

import numpy as np

from ..config.constants import BOARD_SIZE


class SaveSystem:
    """存档系统 - 支持 3 个存档位"""

    def __init__(self):
        self.save_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', 'saves')
        os.makedirs(self.save_dir, exist_ok=True)
        self.save_slots = [1, 2, 3]  # 3 个存档位

    def get_save_path(self, slot: int) -> str:
        """获取存档文件路径"""
        return os.path.join(self.save_dir, f'save_{slot}.json')

    def get_save_info(self, slot: int) -> Optional[Dict[str, Any]]:
        """获取存档信息（不加载完整数据）"""
        path = self.get_save_path(slot)
        if not os.path.exists(path):
            return None

        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return {
                'slot': slot,
                'timestamp': data.get('timestamp', '未知'),
                'round': data.get('round_count', 0),
                'current_player': data.get('current_player', 0),
                'game_mode': data.get('game_mode', 'unknown'),
                'map_name': data.get('map_name', '未知'),
            }
        except (json.JSONDecodeError, IOError):
            return None

    def save_game(self, game, slot: int) -> bool:
        """保存游戏到指定存档位

        Args:
            game: Game 对象
            slot: 存档位 (1-3)

        Returns:
            是否保存成功
        """
        try:
            data = {
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'game_mode': game.game_mode,
                'map_preset_id': game.map_preset_id,
                'map_name': game.map_name,
                'ai_difficulty': game.ai_difficulty,
                'round_count': game.round_count,
                'current_player': game.current_player,
                'steps_left': game.steps_left,
                'players': game.players,
                'human_players': list(game.human_players),
                'ai_players': list(game.ai_players),
                'players_who_played_this_round': list(game.players_who_played_this_round),
                'game_over': game.game_over,
                'winner': game.winner,
                'player_defeated': getattr(game, 'player_defeated', False),

                # 棋盘状态（转换为列表以便 JSON 序列化）
                'board': game.board.tolist(),
                'terrain': game.terrain.tolist(),
                'resource_map': game.resource_map.tolist(),
                'move_count_grid': game.move_count_grid.tolist(),

                # 首都位置
                'capitals': {str(k): list(v) for k, v in game.capitals.items()},

                # 领地计数
                'territory_count': game.territory_count,

                # 日志（只保留最近 50 条）
                'log': game.log[-50:],
                'log_scroll_offset': getattr(game, 'log_scroll_offset', 0),

                # 最后移动
                'last_move': game.last_move,
            }

            path = self.get_save_path(slot)
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            return True
        except Exception as e:
            print(f"保存游戏失败：{e}")
            return False

    def load_game(self, slot: int, game_class) -> Optional[Any]:
        """从指定存档位加载游戏

        Args:
            slot: 存档位 (1-3)
            game_class: Game 类

        Returns:
            加载的 Game 对象，失败返回 None
        """
        try:
            path = self.get_save_path(slot)
            if not os.path.exists(path):
                return None

            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 创建游戏实例
            game = game_class(
                game_mode=data.get('game_mode'),
                map_preset_id=data.get('map_preset_id'),
                ai_difficulty=data.get('ai_difficulty'),
            )

            # 恢复游戏状态
            game.round_count = data.get('round_count', 1)
            game.current_player = data.get('current_player', 1)
            game.steps_left = data.get('steps_left', 3)
            game.players = data.get('players', [1, 2, 3, 4])
            game.human_players = set(data.get('human_players', [1]))
            game.ai_players = set(data.get('ai_players', []))
            game.players_who_played_this_round = set(data.get('players_who_played_this_round', []))
            game.game_over = data.get('game_over', False)
            game.winner = data.get('winner')
            game.player_defeated = data.get('player_defeated', False)

            # 恢复棋盘状态
            game.board = np.array(data.get('board'), dtype=int)
            game.terrain = np.array(data.get('terrain'), dtype=int)
            game.resource_map = np.array(data.get('resource_map'), dtype=int)
            game.move_count_grid = np.array(data.get('move_count_grid'), dtype=int)

            # 恢复首都位置
            game.capitals = {int(k): tuple(v) for k, v in data.get('capitals', {}).items()}

            # 恢复领地计数
            territory_count = data.get('territory_count', {1: 0, 2: 0, 3: 0, 4: 0})
            game.territory_count = {int(k): int(v) for k, v in territory_count.items()}

            # 恢复日志
            game.log = data.get('log', [])
            game.log_scroll_offset = data.get('log_scroll_offset', 0)

            # 恢复最后移动
            game.last_move = data.get('last_move')

            # 重新计算每回合步数
            game.steps_per_turn = game.calculate_steps_per_turn()
            game.selected_pos = None
            game.possible_moves = []
            game.last_ai_action_ms = 0

            # 标记需要重新计算领地
            game.mark_territories_dirty(board_changed=True)
            game.update_territory_count()

            # 重置渲染器缓存
            game.renderer.reset_effects()
            game.renderer.reset_ui_state()
            game.renderer.reset_board_cache()

            return game
        except Exception as e:
            print(f"加载游戏失败：{e}")
            return None

    def has_save(self, slot: int) -> bool:
        """检查存档位是否有存档"""
        return os.path.exists(self.get_save_path(slot))

    def delete_save(self, slot: int) -> bool:
        """删除存档"""
        try:
            path = self.get_save_path(slot)
            if os.path.exists(path):
                os.remove(path)
            return True
        except Exception as e:
            print(f"删除存档失败：{e}")
            return False

    def get_all_save_info(self) -> List[Optional[Dict[str, Any]]]:
        """获取所有存档位信息"""
        return [self.get_save_info(slot) for slot in self.save_slots]


# 全局存档系统实例
_save_system: Optional[SaveSystem] = None


def get_save_system() -> SaveSystem:
    """获取存档系统单例"""
    global _save_system
    if _save_system is None:
        _save_system = SaveSystem()
    return _save_system


def quick_save(game, slot: int = 1) -> bool:
    """快速保存"""
    return get_save_system().save_game(game, slot)


def quick_load(slot: int, game_class) -> Optional[Any]:
    """快速读档"""
    return get_save_system().load_game(slot, game_class)
