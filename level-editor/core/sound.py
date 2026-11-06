"""声音：每一幕一首背景音乐。

写法和游戏端一致（见 game/sound/bgm.py）：
    标题、结局   game.json 的 sounds.title / sounds.ending
    每一关       关卡 json 的 sound：曲子跟着关卡文件走，改名、删关都不牵连别人
一首 BGM 的键：
    bgm       曲子文件，相对 game.json 的路径
    loop      是否循环，缺省 true
    fade_in   切入时淡入几秒，缺省 0.5
    fade_out  离开这一幕时淡出几秒，缺省 1.0
没有 bgm 的这一幕就不写这一项。玩家音效还没有内容，玩家那一页先空着。

编辑器只改这四项，别的键原样保留；改别的关卡文件时先读出来、只换 sound 再写回，
所以那个文件里没打开的内容不会被覆盖。
"""

import json
import os

import pygame

from core.constants import ROOT, SETTING_DIR_NAME, SETTING_FILE_NAME
from core.helpers import clamp_float
from core.level import dump_level

GAME_SOUNDS_KEY = "sounds"   # game.json：一幕一首，标题、结局都在里面
LEVEL_SOUND_KEY = "sound"    # 关卡 json：这一关自己的那一首
TITLE_KEY = "title"
ENDING_KEY = "ending"
PLAYER_KEY = "player"        # 玩家音效：还没定义内容，先占一页

DEFAULT_LOOP = True
DEFAULT_FADE_IN = 0.5
DEFAULT_FADE_OUT = 1.0
MAX_FADE_SECONDS = 10.0
FADE_STEP = 0.5
BGM_PATH_MAX_LENGTH = 200    # 路径字段最多敲几个字符

VOLUME_MASTER_DEFAULT = 0.8
VOLUME_MUSIC_DEFAULT = 0.7


def setting_file() -> str:
    """玩家设置：和游戏共用 exe 旁边的 .game/setting.json（只读，不在这里改）。"""
    return os.path.join(ROOT, SETTING_DIR_NAME, SETTING_FILE_NAME)


# ---- 一页的四项 -----------------------------------------------------
def read_definition(path: str) -> dict | None:
    """读一份 json（game.json 或关卡文件）；读不出来返回 None。"""
    try:
        with open(path, encoding="utf-8") as file:
            value = json.load(file)
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def read_fields(container) -> dict:
    """关卡 json 里 sound 那一幕的四项；没有 sound 就是空的一页。"""
    value = container.get(LEVEL_SOUND_KEY) if isinstance(container, dict) else None
    return fields_of(value)


def fields_of(value) -> dict:
    """json 里的一幕 → 编辑用的四项；数字写成字符串，可以像别的数字字段那样直接敲。"""
    if not isinstance(value, dict):
        value = {}
    return {
        "bgm": str(value.get("bgm") or ""),
        "loop": _read_bool(value.get("loop"), DEFAULT_LOOP),
        "fade_in": f"{_read_seconds(value.get('fade_in'), DEFAULT_FADE_IN):g}",
        "fade_out": f"{_read_seconds(value.get('fade_out'), DEFAULT_FADE_OUT):g}",
    }


def to_object(fields: dict) -> dict | None:
    """编辑用的四项 → 写回 json 的 sound；没有曲子就返回 None（不写这个键）。"""
    if not isinstance(fields, dict):
        return None
    path = str(fields.get("bgm") or "").strip()
    if not path:
        return None
    return {
        "bgm": path,
        "loop": bool(fields.get("loop", DEFAULT_LOOP)),
        "fade_in": round(
            clamp_float(fields.get("fade_in"), 0.0, MAX_FADE_SECONDS, DEFAULT_FADE_IN), 2
        ),
        "fade_out": round(
            clamp_float(fields.get("fade_out"), 0.0, MAX_FADE_SECONDS, DEFAULT_FADE_OUT), 2
        ),
    }


def write_level_sound(path: str, value: dict | None) -> str | None:
    """只换一个关卡文件的 sound 键，别的键原样写回；返回错误说明，None 表示写成功。

    先读后写：这个文件可能不是当前打开的那一关，编辑器内存里的内容不该把它覆盖掉。
    """
    definition = read_definition(path)
    if definition is None:
        return "读不出这个关卡文件"
    if definition.get(LEVEL_SOUND_KEY) == value:
        return None                      # 没有变化：不动这个文件
    if value is None:
        definition.pop(LEVEL_SOUND_KEY, None)
    else:
        definition[LEVEL_SOUND_KEY] = value
    try:
        with open(path, "w", encoding="utf-8", newline="\n") as file:
            file.write(dump_level(definition))
    except OSError as error:
        return str(error)
    return None


def _read_bool(value, default: bool) -> bool:
    """手写 json 时会把 true 写成字符串：认常见的几种写法，其余按默认值。"""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        text = value.strip().lower()
        if text in ("false", "0", "no", "off"):
            return False
        if text in ("true", "1", "yes", "on"):
            return True
        return default
    if isinstance(value, (int, float)):
        return bool(value)
    return default


def _read_seconds(value, default: float) -> float:
    return clamp_float(value, 0.0, MAX_FADE_SECONDS, default)


# ---- 试听 -----------------------------------------------------------
class Preview:
    """试听：编辑器自己的混音器，一次只放一首。

    音量跟游戏共用 exe 旁边的 .game/setting.json（总音量 × 音乐音量）；没有声卡、
    文件读不了都只是没有声音，编辑器照常跑。
    """

    def __init__(self) -> None:
        self.path: str | None = None      # 正在试听的曲子，None 表示没在放

    def toggle(self, path: str, loop: bool, fade_in: float) -> str:
        """放或者停这一首；返回一句给状态栏的话。"""
        if not os.path.isfile(path):
            return f"找不到这首曲子：{path}。"
        if not self._open_mixer():
            return "没有可用的声卡，无法试听。"
        if self.path == path and pygame.mixer.music.get_busy():
            self.stop()
            return "已停止试听。"
        try:
            pygame.mixer.music.load(path)
            pygame.mixer.music.set_volume(preview_volume())
            pygame.mixer.music.play(
                -1 if loop else 0, fade_ms=int(max(0.0, fade_in) * 1000)
            )
        except (pygame.error, OSError) as error:
            self.path = None
            return f"试听失败：{error}。"
        self.path = path
        return f"正在试听 {os.path.basename(path)}。"

    def stop(self) -> None:
        if self.path is None:
            return
        self.path = None
        try:
            pygame.mixer.music.stop()
        except pygame.error:
            pass

    @staticmethod
    def _open_mixer() -> bool:
        try:
            if pygame.mixer.get_init() is None:
                pygame.mixer.init()
        except pygame.error:
            return False
        return True


def preview_volume() -> float:
    """试听音量：和游戏共用 .game/setting.json 里的总音量 × 音乐音量。"""
    settings = read_definition(setting_file()) or {}
    volume = settings.get("volume")
    if not isinstance(volume, dict):
        volume = {}
    master = clamp_float(volume.get("master"), 0.0, 1.0, VOLUME_MASTER_DEFAULT)
    music = clamp_float(volume.get("music"), 0.0, 1.0, VOLUME_MUSIC_DEFAULT)
    return master * music
