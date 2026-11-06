"""玩家自己的设置：exe 旁边的 .game/setting.json。

它和 assets/game 里的游戏配置分工不同：
    assets/game/game.json   游戏的内容：标题、版权信息、玩家与关卡的参数
    .game/setting.json      这台机器上的偏好：总音量、音乐音量、音效音量
    .game/saves/            以后的存档（现在还没用上）
这个文件夹和 exe 并排，不进 assets，所以换一份游戏内容不用重新调音量。

音量都是 0~1 的小数，播放时音乐乘总音量、音效乘总音量：总音量对两边一起生效。
文件读不出来（不存在、不是合法 JSON、没有权限）就用默认值；写不进去也只是这次
没保存，游戏照常跑——设置文件出问题不该让游戏起不来。
"""

import json
import os
from pathlib import Path

from game_settings import BASE_DIR

CONFIG_DIR_NAME = ".game"
SETTING_FILE_NAME = "setting.json"

VOLUME_KEYS = ("master", "music", "sfx")
VOLUME_DEFAULTS = {"master": 0.8, "music": 0.7, "sfx": 0.8}
VOLUME_MIN = 0.0
VOLUME_MAX = 1.0
VOLUME_STEP = 0.1          # 设置里点一下「−」「＋」改多少


def config_dir() -> Path:
    """玩家自己的文件夹：和 exe 并排，不在 assets 里。"""
    return BASE_DIR / CONFIG_DIR_NAME


def setting_file() -> Path:
    return config_dir() / SETTING_FILE_NAME


def clamp_volume(value: float) -> float:
    return max(VOLUME_MIN, min(VOLUME_MAX, value))


def default_settings() -> dict:
    return {"volume": dict(VOLUME_DEFAULTS)}


def load_settings() -> dict:
    """读 setting.json；读不出来就当没有，用的全是默认音量。"""
    settings = default_settings()
    try:
        with open(setting_file(), encoding="utf-8") as file:
            value = json.load(file)
    except (OSError, json.JSONDecodeError):
        return settings
    settings["volume"] = volume_of(value if isinstance(value, dict) else {})
    return settings


def volume_of(settings: dict) -> dict[str, float]:
    """总音量、音乐、音效：缺的、写坏的都用默认值，都夹在 0~1。"""
    result = dict(VOLUME_DEFAULTS)
    volume = settings.get("volume")
    if not isinstance(volume, dict):
        return result
    for key in VOLUME_KEYS:
        if key not in volume:
            continue
        try:
            result[key] = clamp_volume(float(volume[key]))
        except (TypeError, ValueError):
            continue
    return result


def set_volume(settings: dict, key: str, value: float) -> dict:
    """改一项音量：夹在 0~1、留两位小数，顺手写回 settings。"""
    volume = volume_of(settings)
    if key in VOLUME_KEYS:
        volume[key] = round(clamp_volume(value), 2)
    settings["volume"] = volume
    return volume


def step_volume(settings: dict, key: str, steps: int) -> dict:
    """按 VOLUME_STEP 加减，设置里的「−」「＋」用这个。"""
    current = volume_of(settings).get(key, VOLUME_DEFAULTS.get(key, 1.0))
    return set_volume(settings, key, current + steps * VOLUME_STEP)


def save_settings(settings: dict) -> bool:
    """写回 setting.json：先写临时文件再换过去，中途失败不会留下半份。

    返回有没有写成；写不进去（只读目录之类）只是静默失败，游戏继续跑。
    """
    directory = config_dir()
    temporary = directory / (SETTING_FILE_NAME + ".tmp")
    try:
        directory.mkdir(parents=True, exist_ok=True)
        with open(temporary, "w", encoding="utf-8", newline="\n") as file:
            json.dump({"volume": volume_of(settings)}, file, ensure_ascii=False, indent=2)
            file.write("\n")
        os.replace(temporary, directory / SETTING_FILE_NAME)
    except OSError:
        try:
            temporary.unlink()
        except OSError:
            pass
        return False
    return True
