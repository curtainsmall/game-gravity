"""声音库与 BGM 链接。

game.json 里有一张声音库（键 → 文件），音乐和音效都从这里取：
    "sound_library": {"雨": {"path": "sounds/rain.ogg"}, ...}
链接写的是键，不是路径：
    sound     声音库里的键
    loop      是否循环，缺省 true
    fade_in   切入时淡入几秒，缺省 0.5
    fade_out  离开这一幕时淡出几秒，缺省 1.0
标题、制作名单在 game.json 的 sounds 里；每一关在关卡 json 的 sound 里；过场自定义也一样。
老数据写的是 bgm（文件路径）：读进来时登记进声音库、换成链接，键取文件名（重名加 -2）。
"""

import json
import os

import pygame

from core.constants import ROOT, SETTING_DIR_NAME, SETTING_FILE_NAME
from core.helpers import clamp_float

LIBRARY_KEY = "sound_library"
GAME_SOUNDS_KEY = "sounds"   # game.json：一幕一首，标题、制作名单都在里面
TITLE_KEY = "title"
CREDITS_KEY = "credits"      # 结算画面（制作名单）
# game.json 里的两幕（也是编辑器里两个声音板块的顺序）：(键, 界面上叫它什么)
SCENE_KEYS = ((TITLE_KEY, "标题"), (CREDITS_KEY, "制作名单"))

DEFAULT_LOOP = True
DEFAULT_FADE_IN = 0.5
DEFAULT_FADE_OUT = 1.0
MAX_FADE_SECONDS = 10.0
FADE_STEP = 0.5

VOLUME_MASTER_DEFAULT = 0.8
VOLUME_MUSIC_DEFAULT = 0.7


def setting_file() -> str:
    """玩家设置：和游戏共用 exe 旁边的 .game/setting.json（只读，不在这里改）。"""
    return os.path.join(ROOT, SETTING_DIR_NAME, SETTING_FILE_NAME)


def read_definition(path: str) -> dict | None:
    """读一份 json；读不出来返回 None。"""
    try:
        with open(path, encoding="utf-8") as file:
            value = json.load(file)
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


# ---- 声音库 ---------------------------------------------------------
def library_of(settings: dict) -> dict:
    """game.json → 声音库（键 → {"path": …}）；坏条目跳过。"""
    table = (settings or {}).get(LIBRARY_KEY)
    library: dict = {}
    if not isinstance(table, dict):
        return library
    for key, value in table.items():
        name = str(key).strip()
        path = entry_path(value)
        if name and path:
            library[name] = {"path": path}
    return library


def to_settings(settings: dict, library: dict) -> dict:
    """编辑好的声音库写回 game.json；空名字、空路径的条目丢掉。"""
    table = {}
    for key, value in (library or {}).items():
        name = str(key).strip()
        path = entry_path(value)
        if name and path:
            table[name] = {"path": path}
    settings[LIBRARY_KEY] = table
    return settings


def entry_path(value) -> str:
    """库条目 → 相对路径：条目是 {"path": …}，也认直接写字符串的写法。"""
    if isinstance(value, dict):
        value = value.get("path")
    return str(value or "").strip()


def path_of(library: dict, key: str) -> str:
    """键 → 文件路径；不认识的键返回空字符串。"""
    value = (library or {}).get(str(key or ""))
    return entry_path(value)


def ensure_path(library: dict, path: str) -> str:
    """把一份文件登记进声音库，返回它的键。

    同一份文件已经有键就复用；不然拿文件名当键，重名时往后加 -2、-3。
    """
    path = str(path or "").strip()
    if not path:
        return ""
    for key, value in (library or {}).items():
        if entry_path(value) == path:
            return key
    stem = os.path.splitext(os.path.basename(path))[0].strip() or "声音"
    key = stem
    index = 2
    while key in library:
        key = f"{stem}-{index}"
        index += 1
    library[key] = {"path": path}
    return key


def key_label(library: dict, key: str) -> str:
    """界面上显示什么：键加文件名；没有就是（无）。"""
    key = str(key or "").strip()
    if not key:
        return "（无）"
    path = path_of(library, key)
    name = os.path.basename(path) if path else ""
    return f"{key}（{name}）" if name and name != key else key


# ---- 一幕的链接 -----------------------------------------------------
def fields_of(value, library: dict | None = None) -> dict:
    """json 里的一段链接 → 编辑用的四项；数字写成字符串，可以像别的数字字段那样敲。

    老数据只有 bgm（路径）：给了声音库就登记进去、换成键。
    """
    if not isinstance(value, dict):
        value = {}
    key = str(value.get("sound") or "").strip()
    if not key:
        legacy = str(value.get("bgm") or "").strip()
        if legacy and library is not None:
            key = ensure_path(library, legacy)
    return {
        "sound": key,
        "loop": _read_bool(value.get("loop"), DEFAULT_LOOP),
        "fade_in": f"{_read_seconds(value.get('fade_in'), DEFAULT_FADE_IN):g}",
        "fade_out": f"{_read_seconds(value.get('fade_out'), DEFAULT_FADE_OUT):g}",
    }


def to_object(fields: dict, keep_empty: bool = False) -> dict | None:
    """编辑用的四项 → 写回 json 的链接。

    keep_empty 为真时，没有声音也把四项都写出来（sound 是空字符串）；否则返回 None，
    调用方就不会写这个键。
    """
    if not isinstance(fields, dict):
        return None
    key = str(fields.get("sound") or "").strip()
    if not key and not keep_empty:
        return None
    return {
        "sound": key,
        "loop": bool(fields.get("loop", DEFAULT_LOOP)),
        "fade_in": round(
            clamp_float(fields.get("fade_in"), 0.0, MAX_FADE_SECONDS, DEFAULT_FADE_IN), 2
        ),
        "fade_out": round(
            clamp_float(fields.get("fade_out"), 0.0, MAX_FADE_SECONDS, DEFAULT_FADE_OUT), 2
        ),
    }


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


# ---- 声音对象（关卡里的音效） ---------------------------------------
PRESET_GENERAL = "general"
PRESET_PLAYER = "player"
PRESETS = ((PRESET_GENERAL, "通用"), (PRESET_PLAYER, "玩家"))
PLAYER_ACTIONS = (
    ("idle", "站立"),
    ("run", "移动"),
    ("takeoff", "起跳"),
    ("raise", "上升"),
    ("fall", "下落"),
    ("landing", "落地"),
)
PLAYER_ACTION_NAMES = {name for name, _ in PLAYER_ACTIONS}
# 老数据里的动作名：迁移时还认 jump
LEGACY_ACTION_NAMES = {"idle", "run", "jump", "fall"}


def preset_of(entry: dict) -> str:
    preset = str(entry.get("preset") or PRESET_GENERAL) if isinstance(entry, dict) else ""
    return preset if preset in (PRESET_GENERAL, PRESET_PLAYER) else PRESET_GENERAL


def preset_label(preset: str) -> str:
    return dict(PRESETS).get(preset, preset)


def action_label(action: str) -> str:
    return dict(PLAYER_ACTIONS).get(action, action)


def new_object_link() -> dict:
    return {"sound": ""}


def new_object_links() -> dict:
    """声音对象的链接：通用一条，玩家按六个动作各一条（没有左右）。"""
    return {
        PRESET_GENERAL: new_object_link(),
        PRESET_PLAYER: {action: new_object_link() for action, _ in PLAYER_ACTIONS},
    }


def object_links_of(entry: dict) -> dict:
    """条目里的 links 补成完整形状：缺的预设/动作补空链接。

    老数据把上升写在 jump 里，raise 空着时去那里借。
    """
    links = new_object_links()
    value = entry.get("links") if isinstance(entry, dict) else None
    if not isinstance(value, dict):
        return links
    links[PRESET_GENERAL] = _object_link(value.get(PRESET_GENERAL))
    player = value.get(PRESET_PLAYER)
    if isinstance(player, dict):
        for action, _ in PLAYER_ACTIONS:
            source = player.get(action)
            if source is None and action == "raise":
                source = player.get("jump")
            links[PRESET_PLAYER][action] = _object_link(source)
    return links


def _object_link(value) -> dict:
    if isinstance(value, dict):
        return {"sound": str(value.get("sound") or "")}
    return {"sound": str(value or "")}


def object_link(links: dict, preset: str, action: str = "") -> dict:
    """一条链接：预设 + 动作（通用预设没有动作）。"""
    if preset == PRESET_GENERAL:
        value = links.get(PRESET_GENERAL)
        return value if isinstance(value, dict) else new_object_link()
    pair = (links.get(PRESET_PLAYER) or {}).get(action)
    return pair if isinstance(pair, dict) else new_object_link()


def set_object_link(links: dict, preset: str, action: str, sound_key: str) -> None:
    """改链接指向的声音。"""
    _store_object_link(links, preset, action, {"sound": str(sound_key or "")})


def _store_object_link(
    links: dict, preset: str, action: str, value: dict
) -> None:
    if preset == PRESET_GENERAL:
        links[PRESET_GENERAL] = dict(value)
        return
    player = links.setdefault(PRESET_PLAYER, {})
    player[action] = dict(value)


def object_link_label(library: dict, link: dict) -> str:
    """声音对象链接上显示什么：声音名；没有就（未选择）。"""
    key = str((link or {}).get("sound") or "")
    return key_label(library, key) if key else "（未选择）"


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
            return f"找不到这个声音：{path}。"
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
