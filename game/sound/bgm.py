"""一幕的背景音乐：放哪首曲子、怎么放。

音乐写在两处：标题和结局在 game.json 的 sounds 里（sounds.title、sounds.ending），
每一关在它自己的关卡 json 的 sound 里——曲子跟着关卡文件走，改名、删关都不牵连别人。
一首 BGM 的键：
    bgm       曲子文件，和别的路径一样相对 game.json 所在的文件夹
    loop      循环播放，缺省 true
    fade_in   切入时淡入几秒，缺省 0.5
    fade_out  离开这一幕时淡出几秒，缺省 1.0
没有 bgm、或者文件找不到，这一幕就是没音乐，游戏照常跑。
"""

from dataclasses import dataclass
from pathlib import Path

GAME_SOUNDS_KEY = "sounds"     # game.json：一幕一首，标题、结局都在里面
LEVEL_SOUND_KEY = "sound"      # 关卡 json：这一关自己的那一首
TITLE_KEY = "title"
ENDING_KEY = "ending"

DEFAULT_LOOP = True
DEFAULT_FADE_IN = 0.5
DEFAULT_FADE_OUT = 1.0
MAX_FADE_SECONDS = 10.0


@dataclass(frozen=True)
class Bgm:
    """一首要放的曲子：路径已经解析成绝对路径，直接交给混音器。"""

    path: str
    loop: bool = DEFAULT_LOOP
    fade_in: float = DEFAULT_FADE_IN
    fade_out: float = DEFAULT_FADE_OUT


def game_bgm(game_settings: dict, key: str, base_dir: str | Path | None) -> Bgm | None:
    """game.json 里 sounds.<key> 那一首：标题用 title，结局用 ending。"""
    value = game_settings.get(GAME_SOUNDS_KEY) if isinstance(game_settings, dict) else None
    if not isinstance(value, dict):
        return None
    return _bgm(value.get(key), base_dir)


def level_bgm(level_definition: dict, base_dir: str | Path | None) -> Bgm | None:
    """关卡 json 里的 sound：这一关自己的音乐。"""
    if not isinstance(level_definition, dict):
        return None
    return _bgm(level_definition.get(LEVEL_SOUND_KEY), base_dir)


def _bgm(value, base_dir: str | Path | None) -> Bgm | None:
    if not isinstance(value, dict):
        return None
    path = _resolve(value.get("bgm"), base_dir)
    if path is None:
        return None
    return Bgm(
        path=path,
        loop=_read_bool(value.get("loop"), DEFAULT_LOOP),
        fade_in=_read_seconds(value.get("fade_in"), DEFAULT_FADE_IN),
        fade_out=_read_seconds(value.get("fade_out"), DEFAULT_FADE_OUT),
    )


def _resolve(value, base_dir: str | Path | None) -> str | None:
    """曲子的绝对路径：相对 game.json；不是现成的文件就当没有（安静总比报错好）。"""
    if not value:
        return None
    path = Path(str(value))
    if not path.is_absolute():
        if base_dir is None:
            return None
        path = Path(base_dir) / path
    path = path.resolve()
    return str(path) if path.is_file() else None


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
    """淡入淡出几秒：不给负的，太长也没意义，写坏了用默认值。"""
    try:
        seconds = float(value)
    except (TypeError, ValueError):
        return default
    return max(0.0, min(MAX_FADE_SECONDS, seconds))
