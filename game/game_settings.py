"""游戏设置：assets/game/ 里的 game.json，和它旁边的 levels/。

游戏根就是 assets/game 这个文件夹：
    game.json          游戏自己的设置：title 是标题，credits 是制作名单（职位 → 名字数组），
                       player 是玩家默认的跳高和速度，player_animation / player_sound 是
                       所有关卡共用的玩家表现（size + 相对玩家 AABB 底边中点的 offset +
                       动画/音效 links），animation_library 是动画库，
                       sounds 是标题与制作名单的音乐，backgrounds 是标题画面和结算画面的背景图
    levels/<名字>.json 一个文件是一关，文件名（去掉 .json）就是关卡名
game.json 和 levels/*.json 里写的相对路径，一律相对 game.json 所在的文件夹（游戏根）；
图片、曲目放哪儿都行，只要能按相对路径找到。打包后 game/ 必须和 exe 放在一起。
玩家自己的偏好（音量）不在这里，在 exe 旁边的 .game/setting.json（见 user_settings）。
"""

import json
import sys
from pathlib import Path

# 打包成 exe 后，资源放在 exe 旁边；直接跑源码时放在仓库根目录
BASE_DIR = (
    Path(sys.executable).resolve().parent
    if getattr(sys, "frozen", False)
    else Path(__file__).resolve().parent.parent
)
GAME_DIR = BASE_DIR / "assets" / "game"
GAME_FILE_NAME = "game.json"
LEVELS_DIR = GAME_DIR / "levels"

DEFAULT_TITLE = "重力"      # game.json 读不出来时用这个，启动不会因为缺设置就崩

# 玩家表现：所有关卡共用一份。player 里的跳高/速度仍按关卡覆盖，这两份不覆盖。
PLAYER_ANIMATION_KEY = "player_animation"
PLAYER_SOUND_KEY = "player_sound"


def _pair(value, default: tuple[float, float]) -> list[float]:
    """读 [x, y]：写坏了就退回默认值。"""
    try:
        first, second = value
        return [float(first), float(second)]
    except (TypeError, ValueError):
        return [float(default[0]), float(default[1])]


def player_animation_of(settings: dict) -> dict | None:
    """全局玩家动画：尺寸、相对玩家 AABB 底边中点的偏移、六个动作的链接。

    没写这块就返回 None（这一份配置没有玩家精灵），不猜尺寸。
    """
    value = settings.get(PLAYER_ANIMATION_KEY)
    if not isinstance(value, dict):
        return None
    try:
        width, height = value.get("size")
        size = [max(0.01, float(width)), max(0.01, float(height))]
    except (TypeError, ValueError):
        return None
    links = value.get("links")
    return {
        "size": size,
        "offset": _pair(value.get("offset"), (0.0, 0.0)),
        "links": links if isinstance(links, dict) else {},
    }


def player_sound_of(settings: dict) -> dict | None:
    """全局玩家音效：六个动作的声音链接；没写就返回 None。"""
    value = settings.get(PLAYER_SOUND_KEY)
    if not isinstance(value, dict):
        return None
    links = value.get("links")
    return {"links": links if isinstance(links, dict) else {}}


def load_game_settings() -> dict:
    """读 game.json。读不出来、不是合法 JSON 或不是对象，都当作没有设置。"""
    try:
        with open(GAME_DIR / GAME_FILE_NAME, encoding="utf-8") as file:
            value = json.load(file)
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def title_of(settings: dict) -> str:
    """游戏标题：窗口标题和标题画面都用它。"""
    return str(settings.get("title") or DEFAULT_TITLE)


def credits_of(settings: dict) -> dict[str, list[str]]:
    """制作名单：职位 → 名字数组，结算画面按这个顺序列出来。

    credits 是一个对象，字段名是职位、值是名字的数组；数组可以是空的，空数组的
    职位不列出来。数组里的空字符串照样留着并显示（名字位置就是空白）。
    """
    value = settings.get("credits")
    if not isinstance(value, dict):
        return {}
    credits: dict[str, list[str]] = {}
    for job, names in value.items():
        if not isinstance(names, list):
            continue
        cleaned = [str(name) if isinstance(name, str) else "" for name in names]
        if cleaned:
            credits[str(job)] = cleaned
    return credits


def player_of(settings: dict) -> dict:
    """玩家的默认参数：跳高、速度、动画；没写就是空表（关卡也能各自覆盖）。"""
    value = settings.get("player")
    return value if isinstance(value, dict) else {}


def game_root() -> Path:
    """game.json 所在的文件夹：game.json 里的相对路径都相对它。"""
    return GAME_DIR


# 标题画面 / 结算画面的背景图，写在 game.json 的 backgrounds 里
BACKGROUNDS_KEY = "backgrounds"
SCREEN_BACKGROUND_KEYS = ("title", "credits")


def screen_backgrounds_of(settings: dict) -> dict:
    """两个画面的背景：{"title": 相对路径, "credits": 相对路径}；没写或写坏了就是空表。"""
    value = settings.get(BACKGROUNDS_KEY)
    if not isinstance(value, dict):
        return {}
    result = {}
    for key in SCREEN_BACKGROUND_KEYS:
        path = value.get(key)
        if isinstance(path, str) and path.strip():
            result[key] = path
    return result


def screen_background(settings: dict, key: str, base_dir: str | Path | None) -> str | None:
    """某个画面的背景图（绝对路径）；没写、写坏了或文件找不到都返回 None。"""
    relative = screen_backgrounds_of(settings).get(key)
    if relative is None:
        return None
    path = Path(relative)
    if not path.is_absolute() and base_dir is not None:
        path = Path(base_dir) / path
    return str(path) if path.is_file() else None
