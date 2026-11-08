"""游戏配置：用户挑的 game.json，和它旁边的 levels/。

游戏根就是 game.json 所在的那个文件夹：
    game.json    游戏自己的配置：title 是标题，credits 是制作名单（职位 → 名字数组），
                 backgrounds 是标题画面 / 结算画面的背景；player_animation /
                 player_sound 是所有关卡共用的玩家表现
    levels/      一个 <名字>.json 是一关
编辑器在启动时让用户打开或新建一份 game.json，之后关卡都从它的兄弟目录 levels/ 里找。
配置里只改自己认识的键，别的键原样保留。
"""

import json
import os

from core.constants import LEVEL_FILE_SUFFIX, LEVELS_DIR_NAME

DEFAULT_TITLE = "重力"      # game.json 丢了或没写标题时用它，编辑器照常能用

# 标题画面 / 结算画面的背景图，写在 game.json 的 backgrounds 里
BACKGROUNDS_KEY = "backgrounds"
SCREEN_BACKGROUND_KEYS = ("title", "credits")

# 玩家表现：所有关卡共用一份，放在 game.json 的独立键里，不写进关卡
PLAYER_ANIMATION_KEY = "player_animation"
PLAYER_SOUND_KEY = "player_sound"


def _pair(value, default: tuple[float, float]) -> list[float]:
    try:
        first, second = value
        return [float(first), float(second)]
    except (TypeError, ValueError):
        return [float(default[0]), float(default[1])]


def player_animation_of(settings: dict) -> dict | None:
    """玩家动画：尺寸、相对 AABB 底边中点的偏移、六动作链接；没写返回 None。"""
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
    """玩家音效：六动作声音链接；没写返回 None。"""
    value = settings.get(PLAYER_SOUND_KEY)
    if not isinstance(value, dict):
        return None
    links = value.get("links")
    return {"links": links if isinstance(links, dict) else {}}


def player_views_to_object(animation: dict, sound: dict) -> tuple[dict, dict]:
    """编辑态 → 要写进 game.json 的两块；只保留约定字段。"""
    size = list(animation.get("size") or [1.0, 1.0])
    offset = list(animation.get("offset") or [0.0, 0.0])
    links = animation.get("links")
    sound_links = sound.get("links")
    return (
        {
            "size": [float(size[0]), float(size[1])],
            "offset": [float(offset[0]), float(offset[1])],
            "links": links if isinstance(links, dict) else {},
        },
        {
            "links": sound_links if isinstance(sound_links, dict) else {},
        },
    )


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


def backgrounds_of(settings: dict) -> dict:
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


def credits_of(settings: dict) -> dict[str, list[str]]:
    """制作名单：职位 → 名字数组。

    数组可以是空的；数组里的空字符串也是合法的一项（编辑器里就是一行空名字）。
    写坏了的条目（不是数组）跳过，手写成一个字符串的当成只有一个名字。
    """
    value = settings.get("credits")
    if not isinstance(value, dict):
        return {}
    credits: dict[str, list[str]] = {}
    for job, names in value.items():
        if isinstance(names, str):
            names = [names]
        if not isinstance(names, list):
            continue
        credits[str(job)] = [name if isinstance(name, str) else "" for name in names]
    return credits


def credit_cards(credits: dict[str, list[str]]) -> list[dict]:
    """制作名单 → 面板里的卡片：每张卡片是一个职位和它的名字列表。"""
    return [{"job": job, "names": list(names)} for job, names in credits.items()]


def cards_to_credits(cards: list[dict]) -> dict[str, list[str]]:
    """面板里的卡片 → 制作名单对象：职位空的卡片丢掉，同名职位合并。"""
    credits: dict[str, list[str]] = {}
    for card in cards:
        job = str(card.get("job") or "").strip()
        if not job:
            continue
        names = [str(name) for name in card.get("names") or []]
        credits.setdefault(job, []).extend(names)
    return credits


def game_root_of(path: str) -> str:
    """game.json 所在的文件夹就是游戏根。"""
    return os.path.dirname(os.path.abspath(path))


def levels_dir_of(path: str) -> str:
    """游戏根里放关卡的 levels/（不一定已经存在）。"""
    return os.path.join(game_root_of(path), LEVELS_DIR_NAME)


def level_files(path: str) -> list[str]:
    """levels/ 里的关卡 json（<关卡名>.json），按文件名不分大小写排序。"""
    levels_dir = levels_dir_of(path)
    try:
        names = os.listdir(levels_dir)
    except OSError:
        return []
    return [
        os.path.join(levels_dir, name)
        for name in sorted(names, key=str.lower)
        if name.lower().endswith(LEVEL_FILE_SUFFIX)
        and os.path.isfile(os.path.join(levels_dir, name))
    ]


def unique_level_path(levels_dir: str, file_stem: str) -> str:
    """levels/ 里没被占用的关卡文件：撞名了就加 -2、-3，别把已有的关卡写坏。"""
    candidate = os.path.join(levels_dir, f"{file_stem}{LEVEL_FILE_SUFFIX}")
    index = 2
    while os.path.exists(candidate):
        candidate = os.path.join(levels_dir, f"{file_stem}-{index}{LEVEL_FILE_SUFFIX}")
        index += 1
    return candidate
