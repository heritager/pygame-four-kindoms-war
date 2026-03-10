import os

os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')

import numpy as np

from ..config.constants import AI_DIFFICULTY_NORMAL, MODE_SINGLE_AI, RESOURCE_GOLD_MINE
from ..config.map_presets import DEFAULT_MAP_PRESET
from ..core.game_core import Game
from .action_encoder import action_from_id, encode_observation, enumerate_legal_actions, extract_action_features


class HeadlessGameEnv:
    """Low-memory training environment that reuses core game logic without the UI loop."""

    def __init__(
        self,
        game_mode=MODE_SINGLE_AI,
        map_preset_id=DEFAULT_MAP_PRESET,
        ai_difficulty=AI_DIFFICULTY_NORMAL,
        all_ai=False,
    ):
        self.game_mode = game_mode
        self.map_preset_id = map_preset_id
        self.ai_difficulty = ai_difficulty
        self.all_ai = all_ai
        self.game = None

    def reset(self):
        self.game = Game(
            game_mode=self.game_mode,
            map_preset_id=self.map_preset_id,
            ai_difficulty=self.ai_difficulty,
        )
        if self.all_ai:
            self.game.human_players = set()
            self.game.ai_players = set(self.game.players)
        return self.get_observation()

    def get_observation(self):
        return encode_observation(self.game)

    def get_legal_actions(self):
        return enumerate_legal_actions(self.game)

    def get_legal_action_features(self):
        actions = self.get_legal_actions()
        if not actions:
            return actions, np.zeros((0, 0), dtype=np.float32)

        current_analysis = self.game.analyze_board_state(self.game.current_player, self.game.board)
        turn_steps = self.game.calculate_steps_per_turn()
        feature_rows = [
            extract_action_features(self.game, action, current_analysis=current_analysis, turn_steps=turn_steps)
            for action in actions
        ]
        return actions, np.stack(feature_rows, axis=0)

    def pass_turn(self):
        actor = self.game.current_player
        before = self._snapshot_actor(actor)
        self.game.steps_left = 0
        self.game.next_player()
        return self.get_observation(), self._compute_reward(actor, before), self.game.game_over, {
            'actor': actor,
            'passed': True,
        }

    def step(self, action):
        if action is None:
            return self.pass_turn()

        if isinstance(action, int):
            from_pos, to_pos = action_from_id(action)
        else:
            from_pos, to_pos = action.from_pos, action.to_pos

        actor = self.game.current_player
        before = self._snapshot_actor(actor)
        success, message = self.game.move_soldier(from_pos, to_pos)
        if not success:
            raise ValueError(message)

        if self.game.steps_left <= 0 and not self.game.game_over:
            self.game.next_player()

        return self.get_observation(), self._compute_reward(actor, before), self.game.game_over, {
            'actor': actor,
            'passed': False,
            'message': message,
        }

    def _snapshot_actor(self, actor):
        capital_pos = self.game.capitals.get(actor)
        capital_owner = actor
        if capital_pos is not None:
            capital_owner = int(self.game.board[capital_pos[0], capital_pos[1], 0])
        return {
            'territory': int(self.game.territory_count.get(actor, 0)),
            'mines': self._count_owned_mines(actor),
            'alive': actor in self.game.players,
            'enemy_alive': sum(1 for player in self.game.players if player != actor),
            'capital_owner': capital_owner,
        }

    def _count_owned_mines(self, actor):
        owned_mines = 0
        for i in range(self.game.board.shape[0]):
            for j in range(self.game.board.shape[1]):
                if self.game.resource_map[i, j] == RESOURCE_GOLD_MINE and int(self.game.board[i, j, 0]) == actor:
                    owned_mines += 1
        return owned_mines

    def _compute_reward(self, actor, before):
        capital_pos = self.game.capitals.get(actor)
        capital_owner = actor
        if capital_pos is not None:
            capital_owner = int(self.game.board[capital_pos[0], capital_pos[1], 0])
        after = {
            'territory': int(self.game.territory_count.get(actor, 0)),
            'mines': self._count_owned_mines(actor),
            'alive': actor in self.game.players,
            'enemy_alive': sum(1 for player in self.game.players if player != actor),
            'capital_owner': capital_owner,
        }

        reward = (after['territory'] - before['territory']) * 0.08
        reward += (after['mines'] - before['mines']) * 0.45
        reward += (before['enemy_alive'] - after['enemy_alive']) * 1.0
        if before['capital_owner'] == actor and after['capital_owner'] != actor:
            reward -= 4.5
        if before['alive'] and not after['alive']:
            reward -= 6.0
        if after['alive'] and self.game.winner == actor:
            reward += 5.0
        return float(reward)
