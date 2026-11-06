"""游戏设置：assets/game/ 里的 game.json，和它旁边的 levels/。

游戏根就是 assets/game 这个文件夹：
    game.json    游戏自己的设置：title 是标题，credits 是版权信息（职位 → 名字数组）
    levels/      一个文件夹是一关，内容和以前完全一样
打包后 game/ 必须和 exe 放在一起，关卡和设置都从那里读。
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

    credits 是一个对象，字段名是职位、值是名字的数组；写坏了的条目直接跳过，
    名字全是空白的职位也不列出来。
    """
    value = settings.get("credits")
    if not isinstance(value, dict):
        return {}
    credits: dict[str, list[str]] = {}
    for job, names in value.items():
        if not isinstance(names, list):
            continue
        cleaned = [str(name) for name in names if isinstance(name, str) and name.strip()]
        if cleaned:
            credits[str(job)] = cleaned
    return credits
