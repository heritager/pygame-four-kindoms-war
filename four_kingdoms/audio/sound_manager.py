"""音效管理系统

支持音效、背景音乐播放，可调节音量，静音模式。
"""

import os
from typing import Dict, Optional

import pygame

# 音效类型定义
SOUND_MOVE = 'move'
SOUND_ATTACK = 'attack'
SOUND_CAPTURE = 'capture'
SOUND_CAPTURE_CAPITAL = 'capture_capital'
SOUND_BUILD = 'build'
SOUND_SELECT = 'select'
SOUND_CLICK = 'click'
SOUND_VICTORY = 'victory'
SOUND_DEFEAT = 'defeat'

# 背景音乐类型
MUSIC_MENU = 'menu'
MUSIC_GAME = 'game'
MUSIC_VICTORY = 'victory'


class SoundManager:
    """音效管理器 - 单例模式"""

    _instance: Optional['SoundManager'] = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if SoundManager._initialized:
            return
        SoundManager._initialized = True

        self._sounds: Dict[str, pygame.mixer.Sound] = {}
        self._music_playing: Optional[str] = None
        self._sound_volume = 0.5
        self._music_volume = 0.4
        self._muted = False
        self._music_muted = False
        self._base_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', 'assets', 'audio')

    def initialize(self):
        """初始化 pygame mixer"""
        if not pygame.mixer.get_init():
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)

    def load_sound(self, name: str, filename: str) -> bool:
        """加载单个音效文件

        Args:
            name: 音效标识名
            filename: 音频文件名（相对于 sfx 目录）

        Returns:
            是否加载成功
        """
        try:
            filepath = os.path.join(self._base_path, 'sfx', filename)
            if os.path.exists(filepath):
                self._sounds[name] = pygame.mixer.Sound(filepath)
                self._sounds[name].set_volume(0 if self._muted else self._sound_volume)
                return True
        except pygame.error as e:
            print(f"加载音效失败 {filename}: {e}")
        return False

    def load_all_sounds(self):
        """加载所有预定义音效"""
        # 尝试加载音效（如果文件存在）
        sound_files = {
            SOUND_MOVE: 'move.wav',
            SOUND_ATTACK: 'attack.wav',
            SOUND_CAPTURE: 'capture.wav',
            SOUND_CAPTURE_CAPITAL: 'capture_capital.wav',
            SOUND_BUILD: 'build.wav',
            SOUND_SELECT: 'select.wav',
            SOUND_CLICK: 'click.wav',
            SOUND_VICTORY: 'victory.wav',
            SOUND_DEFEAT: 'defeat.wav',
        }

        for name, filename in sound_files.items():
            self.load_sound(name, filename)

        # 如果没有真实音效，使用合成音效作为备选
        self._create_fallback_sounds()

    def _create_fallback_sounds(self):
        """创建合成音效作为备选（当没有音频文件时）"""
        try:
            # 使用 pygame 生成简单音效
            import array
            import math

            sample_rate = 44100

            def generate_tone(frequency, duration, wave_type='sine', volume=0.3):
                """生成单音音效"""
                n_samples = int(sample_rate * duration)
                samples = array.array('h')

                for i in range(n_samples):
                    t = i / sample_rate
                    if wave_type == 'sine':
                        value = int(volume * 32767 * math.sin(2 * math.pi * frequency * t))
                    elif wave_type == 'square':
                        value = int(volume * 32767 * (1 if math.sin(2 * math.pi * frequency * t) > 0 else -1))
                    else:
                        value = int(volume * 32767 * (t / duration) * math.sin(2 * math.pi * frequency * t))

                    # 淡出效果
                    fade = 1.0 - (i / n_samples)
                    value = int(value * fade)
                    samples.append(max(-32768, min(32767, value)))

                sound = pygame.mixer.Sound(buffer=samples)
                return sound

            # 移动音效 - 短促的"嘟"声
            if SOUND_MOVE not in self._sounds:
                self._sounds[SOUND_MOVE] = generate_tone(440, 0.08, 'sine', 0.2)

            # 攻击音效 - 下降的音调
            if SOUND_ATTACK not in self._sounds:
                self._sounds[SOUND_ATTACK] = generate_tone(600, 0.15, 'square', 0.25)

            # 占领音效 - 上升和弦
            if SOUND_CAPTURE not in self._sounds:
                self._sounds[SOUND_CAPTURE] = generate_tone(523, 0.2, 'sine', 0.3)

            # 占领首都 - 更长的庆祝音
            if SOUND_CAPTURE_CAPITAL not in self._sounds:
                self._sounds[SOUND_CAPTURE_CAPITAL] = generate_tone(784, 0.4, 'sine', 0.35)

            # 建造音效
            if SOUND_BUILD not in self._sounds:
                self._sounds[SOUND_BUILD] = generate_tone(349, 0.12, 'sine', 0.25)

            # 选择音效
            if SOUND_SELECT not in self._sounds:
                self._sounds[SOUND_SELECT] = generate_tone(880, 0.05, 'sine', 0.15)

            # 点击音效
            if SOUND_CLICK not in self._sounds:
                self._sounds[SOUND_CLICK] = generate_tone(1200, 0.03, 'sine', 0.1)

            # 胜利音效 - 长庆祝
            if SOUND_VICTORY not in self._sounds:
                self._sounds[SOUND_VICTORY] = generate_tone(523, 1.0, 'sine', 0.3)

            # 失败音效 - 低沉
            if SOUND_DEFEAT not in self._sounds:
                self._sounds[SOUND_DEFEAT] = generate_tone(196, 0.8, 'sine', 0.3)

        except Exception as e:
            print(f"创建合成音效失败：{e}")

    def play(self, name: str, loops: int = 0, maxtime: int = 0, fade_ms: int = 0):
        """播放音效

        Args:
            name: 音效标识名
            loops: 重复次数（0 表示不重复，-1 表示无限循环）
            maxtime: 最大播放时间（毫秒）
            fade_ms: 淡入时间（毫秒）
        """
        if self._muted or name not in self._sounds:
            return

        try:
            self._sounds[name].play(loops=loops, maxtime=maxtime, fade_ms=fade_ms)
        except pygame.error as e:
            print(f"播放音效失败 {name}: {e}")

    def stop(self, name: Optional[str] = None):
        """停止音效

        Args:
            name: 音效标识名，如果为 None 则停止所有音效
        """
        if name:
            if name in self._sounds:
                self._sounds[name].stop()
        else:
            pygame.mixer.stop()

    def set_sound_volume(self, volume: float):
        """设置音效音量

        Args:
            volume: 0.0 - 1.0
        """
        self._sound_volume = max(0.0, min(1.0, volume))
        for sound in self._sounds.values():
            sound.set_volume(0 if self._muted else self._sound_volume)

    def get_sound_volume(self) -> float:
        """获取音效音量"""
        return self._sound_volume

    def set_music_volume(self, volume: float):
        """设置背景音乐音量

        Args:
            volume: 0.0 - 1.0
        """
        self._music_volume = max(0.0, min(1.0, volume))
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.set_volume(self._music_volume)

    def get_music_volume(self) -> float:
        """获取背景音乐音量"""
        return self._music_volume

    def mute_sounds(self, muted: bool = True):
        """静音/取消静音音效"""
        self._muted = muted
        for sound in self._sounds.values():
            sound.set_volume(0 if muted else self._sound_volume)

    def mute_music(self, muted: bool = True):
        """静音/取消静音背景音乐"""
        self._music_muted = muted
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.set_volume(0 if muted else self._music_volume)

    def is_muted(self) -> bool:
        """检查音效是否静音"""
        return self._muted

    def is_music_muted(self) -> bool:
        """检查背景音乐是否静音"""
        return self._music_muted

    def toggle_mute(self) -> bool:
        """切换静音状态"""
        self._muted = not self._muted
        for sound in self._sounds.values():
            sound.set_volume(0 if self._muted else self._sound_volume)
        return self._muted

    # 背景音乐方法
    def play_music(self, name: str, loops: int = -1, fade_ms: int = 1000):
        """播放背景音乐

        Args:
            name: 音乐标识名
            loops: 重复次数（-1 表示无限循环）
            fade_ms: 淡入时间（毫秒）
        """
        if self._music_muted:
            return

        filepath = os.path.join(self._base_path, 'music', f'{name}.ogg')
        alt_filepath = os.path.join(self._base_path, 'music', f'{name}.mp3')

        try:
            if os.path.exists(filepath):
                pygame.mixer.music.load(filepath)
            elif os.path.exists(alt_filepath):
                pygame.mixer.music.load(alt_filepath)
            else:
                return  # 没有音乐文件

            pygame.mixer.music.play(loops=loops, fade_ms=fade_ms)
            self._music_playing = name
        except pygame.error as e:
            print(f"播放背景音乐失败 {name}: {e}")

    def stop_music(self, fade_ms: int = 500):
        """停止背景音乐"""
        if fade_ms > 0:
            pygame.mixer.music.fadeout(fade_ms)
        else:
            pygame.mixer.music.stop()
        self._music_playing = None

    def get_music_playing(self) -> Optional[str]:
        """获取当前播放的音乐"""
        return self._music_playing

    def fadeout_all(self, fade_ms: int = 500):
        """淡出所有声音"""
        pygame.mixer.fadeout(fade_ms)
        pygame.mixer.music.fadeout(fade_ms)


# 全局便捷访问
_sound_manager: Optional[SoundManager] = None


def get_sound_manager() -> SoundManager:
    """获取音效管理器单例"""
    global _sound_manager
    if _sound_manager is None:
        _sound_manager = SoundManager()
        _sound_manager.initialize()
    return _sound_manager


def play_sound(name: str):
    """便捷函数：播放音效"""
    get_sound_manager().play(name)


def play_music(name: str):
    """便捷函数：播放背景音乐"""
    get_sound_manager().play_music(name)


def stop_music():
    """便捷函数：停止背景音乐"""
    get_sound_manager().stop_music()


def toggle_mute() -> bool:
    """便捷函数：切换静音"""
    return get_sound_manager().toggle_mute()
