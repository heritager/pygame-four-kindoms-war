"""游戏统计系统

跟踪玩家游戏数据，包括战斗、占领、移动等统计信息。
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
import json
import os
from datetime import datetime


@dataclass
class PlayerStats:
    """玩家统计数据"""
    player_id: int
    moves_made: int = 0  # 移动次数
    attacks_made: int = 0  # 攻击次数
    attacks_won: int = 0  # 攻击胜利次数
    attacks_lost: int = 0  # 攻击失败次数
    cities_captured: int = 0  # 城市占领数
    capitals_captured: int = 0  # 首都占领数
    mines_captured: int = 0  # 金矿占领数
    units_produced: int = 0  # 单位生产数
    units_lost: int = 0  # 单位损失数
    territory_peak: int = 0  # 领地峰值
    rounds_survived: int = 0  # 存活轮数

    def to_dict(self) -> Dict[str, Any]:
        return {
            'player_id': self.player_id,
            'moves_made': self.moves_made,
            'attacks_made': self.attacks_made,
            'attacks_won': self.attacks_won,
            'attacks_lost': self.attacks_lost,
            'cities_captured': self.cities_captured,
            'capitals_captured': self.capitals_captured,
            'mines_captured': self.mines_captured,
            'units_produced': self.units_produced,
            'units_lost': self.units_lost,
            'territory_peak': self.territory_peak,
            'rounds_survived': self.rounds_survived,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PlayerStats':
        return cls(**data)


@dataclass
class GameStats:
    """单局游戏统计"""
    timestamp: str
    game_mode: str
    map_name: str
    ai_difficulty: str
    winner: Optional[int]
    total_rounds: int
    player_stats: Dict[int, PlayerStats]
    total_moves: int = 0
    total_attacks: int = 0
    total_captures: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'timestamp': self.timestamp,
            'game_mode': self.game_mode,
            'map_name': self.map_name,
            'ai_difficulty': self.ai_difficulty,
            'winner': self.winner,
            'total_rounds': self.total_rounds,
            'player_stats': {str(k): v.to_dict() for k, v in self.player_stats.items()},
            'total_moves': self.total_moves,
            'total_attacks': self.total_attacks,
            'total_captures': self.total_captures,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GameStats':
        player_stats = {int(k): PlayerStats.from_dict(v) for k, v in data['player_stats'].items()}
        return cls(
            timestamp=data['timestamp'],
            game_mode=data['game_mode'],
            map_name=data['map_name'],
            ai_difficulty=data['ai_difficulty'],
            winner=data.get('winner'),
            total_rounds=data['total_rounds'],
            player_stats=player_stats,
            total_moves=data.get('total_moves', 0),
            total_attacks=data.get('total_attacks', 0),
            total_captures=data.get('total_captures', 0),
        )


class StatisticsManager:
    """统计管理器 - 单例模式"""

    _instance: Optional['StatisticsManager'] = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if StatisticsManager._initialized:
            return
        StatisticsManager._initialized = True

        self.stats_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', 'stats')
        os.makedirs(self.stats_dir, exist_ok=True)

        # 当前游戏统计
        self.current_game_stats: Optional[GameStats] = None
        self.player_stats: Dict[int, PlayerStats] = {}

        # 历史统计
        self.game_history: List[GameStats] = []
        self._load_history()

        # 成就进度
        self.achievements_progress: Dict[str, Any] = {
            'total_wins': 0,
            'total_games': 0,
            'perfect_victories': 0,
            'comeback_victories': 0,
            'total_moves': 0,
            'total_attacks': 0,
            'total_captures': 0,
            'unlocked': [],  # 已解锁成就 ID 列表
        }
        self._load_achievements()

        # 成就定义
        self.achievements = [
            {'id': 'first_win', 'name': '首次胜利', 'desc': '赢得第一局游戏', 'condition': lambda p: p['total_wins'] >= 1},
            {'id': 'ten_wins', 'name': '常胜将军', 'desc': '累计赢得 10 局游戏', 'condition': lambda p: p['total_wins'] >= 10},
            {'id': 'perfect_victory', 'name': '完美胜利', 'desc': '以占领所有首都的方式获胜', 'condition': lambda p: p['perfect_victories'] >= 1},
            {'id': 'hundred_moves', 'name': '行军百里', 'desc': '累计移动 100 次', 'condition': lambda p: p['total_moves'] >= 100},
            {'id': 'warrior', 'name': '勇猛战士', 'desc': '累计发动 50 次攻击', 'condition': lambda p: p['total_attacks'] >= 50},
            {'id': 'conqueror', 'name': '征服者', 'desc': '累计占领 20 个城市', 'condition': lambda p: p['total_captures'] >= 20},
        ]

    def start_new_game(self, game):
        """开始新游戏统计"""
        self.player_stats = {
            player_id: PlayerStats(player_id=player_id)
            for player_id in game.players
        }
        self.current_game_stats = GameStats(
            timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            game_mode=game.game_mode,
            map_name=game.map_name,
            ai_difficulty=game.ai_difficulty,
            winner=None,
            total_rounds=0,
            player_stats=self.player_stats,
        )

    def record_move(self, player_id: int):
        """记录移动"""
        if player_id in self.player_stats:
            self.player_stats[player_id].moves_made += 1
            if self.current_game_stats:
                self.current_game_stats.total_moves += 1
            # 累计成就进度
            self.achievements_progress['total_moves'] += 1

    def record_attack(self, player_id: int, won: bool):
        """记录攻击"""
        if player_id in self.player_stats:
            stats = self.player_stats[player_id]
            stats.attacks_made += 1
            if won:
                stats.attacks_won += 1
            else:
                stats.attacks_lost += 1
            if self.current_game_stats:
                self.current_game_stats.total_attacks += 1
            # 累计成就进度
            self.achievements_progress['total_attacks'] += 1

    def record_capture(self, player_id: int, city_type: int, is_capital: bool = False, is_mine: bool = False):
        """记录占领"""
        if player_id in self.player_stats:
            stats = self.player_stats[player_id]
            if city_type > 0:
                stats.cities_captured += 1
            if is_capital:
                stats.capitals_captured += 1
            if is_mine:
                stats.mines_captured += 1
            if self.current_game_stats:
                self.current_game_stats.total_captures += 1
            # 累计成就进度
            self.achievements_progress['total_captures'] += 1

    def record_unit_produced(self, player_id: int, count: int = 1):
        """记录单位生产"""
        if player_id in self.player_stats:
            self.player_stats[player_id].units_produced += count

    def record_unit_lost(self, player_id: int, count: int = 1):
        """记录单位损失"""
        if player_id in self.player_stats:
            self.player_stats[player_id].units_lost += count

    def update_territory(self, player_id: int, count: int):
        """更新领地计数"""
        if player_id in self.player_stats:
            self.player_stats[player_id].territory_peak = max(
                self.player_stats[player_id].territory_peak,
                count
            )

    def end_game(self, game):
        """结束游戏统计"""
        if self.current_game_stats:
            self.current_game_stats.winner = game.winner
            self.current_game_stats.total_rounds = game.round_count

            # 更新存活轮数
            for player_id, stats in self.player_stats.items():
                stats.rounds_survived = game.round_count if player_id in game.players else 0

            # 保存到历史
            self.game_history.append(self.current_game_stats)
            self._save_history()

            # 更新成就进度
            if game.winner and game.winner in [1]:  # 人类玩家获胜
                self.achievements_progress['total_wins'] += 1
                if len(game.players) == 1:  # 完美胜利（其他玩家都被淘汰）
                    self.achievements_progress['perfect_victories'] += 1
            self.achievements_progress['total_games'] += 1

            # 检查成就解锁
            self._check_achievements()
            self._save_achievements()

            self.current_game_stats = None
            self.player_stats = {}

    def _check_achievements(self):
        """检查成就解锁"""
        for achievement in self.achievements:
            if achievement['id'] not in self.achievements_progress['unlocked']:
                try:
                    if achievement['condition'](self.achievements_progress):
                        self.achievements_progress['unlocked'].append(achievement['id'])
                        print(f"成就解锁：{achievement['name']} - {achievement['desc']}")
                except Exception as e:
                    print(f"检查成就 {achievement['id']} 失败：{e}")

    def get_player_stats(self, player_id: int) -> Optional[PlayerStats]:
        """获取玩家统计"""
        return self.player_stats.get(player_id)

    def get_current_stats(self) -> Optional[GameStats]:
        """获取当前游戏统计"""
        return self.current_game_stats

    def get_history(self, limit: int = 10) -> List[GameStats]:
        """获取历史统计"""
        return self.game_history[-limit:]

    def get_summary(self) -> Dict[str, Any]:
        """获取统计摘要"""
        total_games = len(self.game_history)
        if total_games == 0:
            return {'total_games': 0}

        human_wins = sum(1 for g in self.game_history if g.winner == 1)
        avg_rounds = sum(g.total_rounds for g in self.game_history) / total_games
        avg_moves = sum(g.total_moves for g in self.game_history) / total_games

        return {
            'total_games': total_games,
            'human_wins': human_wins,
            'win_rate': human_wins / total_games if total_games > 0 else 0,
            'avg_rounds': round(avg_rounds, 1),
            'avg_moves': round(avg_moves, 1),
            'achievements': self.achievements_progress,
        }

    def get_achievements(self) -> List[Dict[str, Any]]:
        """获取成就列表（带解锁状态）"""
        result = []
        for achievement in self.achievements:
            unlocked = achievement['id'] in self.achievements_progress['unlocked']
            result.append({
                **achievement,
                'unlocked': unlocked,
            })
        return result

    def get_unlocked_achievements(self) -> List[str]:
        """获取已解锁成就 ID 列表"""
        return self.achievements_progress['unlocked'].copy()

    def _load_history(self):
        """加载历史记录"""
        history_path = os.path.join(self.stats_dir, 'game_history.json')
        if os.path.exists(history_path):
            try:
                with open(history_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.game_history = [GameStats.from_dict(g) for g in data]
            except (json.JSONDecodeError, IOError):
                self.game_history = []

    def _save_history(self):
        """保存历史记录"""
        history_path = os.path.join(self.stats_dir, 'game_history.json')
        try:
            with open(history_path, 'w', encoding='utf-8') as f:
                json.dump([g.to_dict() for g in self.game_history], f, ensure_ascii=False, indent=2)
        except IOError as e:
            print(f"保存历史记录失败：{e}")

    def _load_achievements(self):
        """加载成就进度"""
        achievements_path = os.path.join(self.stats_dir, 'achievements.json')
        if os.path.exists(achievements_path):
            try:
                with open(achievements_path, 'r', encoding='utf-8') as f:
                    self.achievements_progress = json.load(f)
            except (json.JSONDecodeError, IOError):
                pass

    def _save_achievements(self):
        """保存成就进度"""
        achievements_path = os.path.join(self.stats_dir, 'achievements.json')
        try:
            with open(achievements_path, 'w', encoding='utf-8') as f:
                json.dump(self.achievements_progress, f, ensure_ascii=False, indent=2)
        except IOError as e:
            print(f"保存成就进度失败：{e}")


# 全局统计管理器实例
_stats_manager: Optional[StatisticsManager] = None


def get_statistics_manager() -> StatisticsManager:
    """获取统计管理器单例"""
    global _stats_manager
    if _stats_manager is None:
        _stats_manager = StatisticsManager()
    return _stats_manager
