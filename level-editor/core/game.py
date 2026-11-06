"""游戏配置：用户挑的 game.json，和它旁边的 levels/。

游戏根就是 game.json 所在的那个文件夹：
    game.json    游戏自己的配置：title 是标题，credits 是版权信息（职位 → 名字数组）
    levels/      一个文件夹是一关
编辑器在启动时让用户打开或新建一份 game.json，之后关卡都从它的兄弟目录 levels/ 里找。
配置里只改自己认识的键，别的键原样保留。
"""

import json
import os

from core.constants import LEVEL_SCENE_NAME, LEVELS_DIR_NAME

DEFAULT_TITLE = "重力"      # game.json 丢了或没写标题时用它，编辑器照常能用
NAME_SEPARATOR = ","        # 一条版权里多个名字之间的分隔符
NAME_SEPARATORS = ",、，;；"   # 手写时也认这几种，写回时统一成「,」


def new_settings() -> dict:
    """一份新建 game.json 的内容。"""
    return {"title": DEFAULT_TITLE, "credits": {}}


def load_settings(path: str) -> dict:
    """读 game.json。读不出来、不是合法 JSON 或不是对象，都当作没有设置。"""
    try:
        with open(path, encoding="utf-8") as file:
            value = json.load(file)
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def save_settings(settings: dict, path: str) -> None:
    """写回 game.json，顺便把缺的文件夹建出来。"""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as file:
        json.dump(settings, file, ensure_ascii=False, indent=2)
        file.write("\n")


def title_of(settings: dict) -> str:
    """游戏标题：game.json 里的 title，没写就用默认标题。"""
    return str(settings.get("title") or DEFAULT_TITLE)


def player_of(settings: dict) -> dict:
    """玩家的默认参数：跳高、速度、动画；没写就是空表（关卡里的 player 可以覆盖）。"""
    value = settings.get("player")
    return value if isinstance(value, dict) else {}


def credits_of(settings: dict) -> dict[str, list[str]]:
    """版权信息：职位 → 名字数组。写坏了的条目跳过，名字全是空白的职位也留着。"""
    value = settings.get("credits")
    if not isinstance(value, dict):
        return {}
    credits: dict[str, list[str]] = {}
    for job, names in value.items():
        if isinstance(names, str):                  # 手写成一个名字也认
            names = [names]
        if not isinstance(names, list):
            continue
        credits[str(job)] = [str(name) for name in names if isinstance(name, str) and name.strip()]
    return credits


def credits_to_rows(credits: dict[str, list[str]]) -> list[dict]:
    """版权信息 → 面板里可编辑的行：每行是职位和名字文本（名字用「, 」隔开）。"""
    return [
        {"job": job, "names": f"{NAME_SEPARATOR} ".join(names)}
        for job, names in credits.items()
    ]


def split_names(text: str) -> list[str]:
    """把「a,b」这样的文本拆成名字数组（也认、，；这几种分隔符）。"""
    for separator in NAME_SEPARATORS[1:]:
        text = text.replace(separator, NAME_SEPARATOR)
    return [name.strip() for name in text.split(NAME_SEPARATOR) if name.strip()]


def rows_to_credits(rows: list[dict]) -> dict[str, list[str]]:
    """面板里的行 → 版权信息对象：职位空的丢掉，同名的合并。"""
    credits: dict[str, list[str]] = {}
    for row in rows:
        job = str(row.get("job") or "").strip()
        if not job:
            continue
        credits.setdefault(job, []).extend(split_names(str(row.get("names") or "")))
    return credits


def game_root_of(path: str) -> str:
    """game.json 所在的文件夹就是游戏根。"""
    return os.path.dirname(os.path.abspath(path))


def levels_dir_of(path: str) -> str:
    """游戏根里放关卡的 levels/（不一定已经存在）。"""
    return os.path.join(game_root_of(path), LEVELS_DIR_NAME)


def level_folders(path: str) -> list[str]:
    """levels/ 里带 scene.json 的关卡文件夹，按文件夹名不分大小写排序。"""
    levels_dir = levels_dir_of(path)
    try:
        names = os.listdir(levels_dir)
    except OSError:
        return []
    return [
        os.path.join(levels_dir, name)
        for name in sorted(names, key=str.lower)
        if os.path.isfile(os.path.join(levels_dir, name, LEVEL_SCENE_NAME))
    ]


def unique_level_folder(levels_dir: str, folder_name: str) -> str:
    """levels/ 里没被占用的文件夹：撞名了就加 -2、-3，别把已有的关卡写坏。"""
    candidate = os.path.join(levels_dir, folder_name)
    index = 2
    while os.path.exists(candidate):
        candidate = os.path.join(levels_dir, f"{folder_name}-{index}")
        index += 1
    return candidate
