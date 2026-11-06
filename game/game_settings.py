"""游戏设置：assets/game/ 里的 game.json，和它旁边的 levels/。

游戏根就是 assets/game 这个文件夹：
    game.json          游戏自己的设置：title 是标题，credits 是版权信息（职位 → 名字数组），
                       player 是玩家默认的跳高、速度与动画
    levels/<名字>.json 一个文件是一关，文件名（去掉 .json）就是关卡名
game.json 和 levels/*.json 里写的相对路径，一律相对 game.json 所在的文件夹（游戏根）；
图片放哪儿都行，只要能按相对路径找到。打包后 game/ 必须和 exe 放在一起。
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
    """版权信息：职位 → 名字数组，结算画面按这个顺序列出来。

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
