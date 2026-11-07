"""动画库：game.json 里 animation_library 的「键 → 一条动画」。

一条动画只有帧和每帧停留秒数；它不知道左右，也不知道预设——左右和预设是动画
对象自己的事（见编辑器里的动画对象弹窗）。循环不让作者配：游戏按动作决定，
idle / run / raise / fall 循环，takeoff / landing 播一遍，通用预设也播一遍。

    general   一条剪辑，没有动作名、没有左右
    player    六个动作（站立 / 移动 / 起跳 / 上升 / 下落 / 落地），每个动作左、右
              两个链接；空着的一侧用另一侧镜像；重力翻转时先取相反一侧，再整体转 180°

老数据把上升写在 jump 里：读链接时当作 raise 的兜底；链接本身也可以是直接写键的
字符串。老 player.animations 在读取时一次性迁进动画库，键名是「动作_left / 动作_right」；
应用游戏配置后旧字段就删掉，之后只认新结构。
"""

import copy

from core.helpers import clamp_float

LIBRARY_KEY = "animation_library"

PRESET_GENERAL = "general"
PRESET_PLAYER = "player"
PRESETS = ((PRESET_GENERAL, "通用"), (PRESET_PLAYER, "玩家"))
GENERAL_CLIP = "clip"
PLAYER_ACTIONS = (
    ("idle", "站立"),
    ("run", "移动"),
    ("takeoff", "起跳"),
    ("raise", "上升"),
    ("fall", "下落"),
    ("landing", "落地"),
)
# 老数据里的动作名：迁移老动画库时还认 jump
LEGACY_ACTION_NAMES = {"idle", "run", "jump", "fall"}
# 循环由动作决定：持续动作循环，其余（takeoff / landing）只播一遍
LOOP_ACTIONS = frozenset({"idle", "run", "raise", "fall"})
SIDES = (("left", "左"), ("right", "右"))

DEFAULT_HOLD = 0.1
MIN_HOLD = 0.01
MAX_HOLD = 10.0
HOLD_STEP = 0.01
DEFAULT_FPS = 8.0
DRAG_THRESHOLD = 4
NAME_MAX_LENGTH = 40


def action_label(action: str) -> str:
    return dict(PLAYER_ACTIONS).get(action, action)


def preset_label(preset: str) -> str:
    return dict(PRESETS).get(preset, preset)


def side_label(side: str) -> str:
    return dict(SIDES).get(side, side)


def loops(action: str) -> bool:
    """这个动作要不要循环（和游戏里的规则一致）。"""
    return action in LOOP_ACTIONS


def hold_text(value) -> str:
    return f"{clamp_float(value, MIN_HOLD, MAX_HOLD, DEFAULT_HOLD):g}"


def new_animation() -> dict:
    """新建一条动画：只有帧和每帧时长。"""
    return {"frames": [], "holds": []}


def new_links() -> dict:
    """动画对象的链接默认值：两套预设、每个动作/方向各一条空链接。"""
    return {
        PRESET_GENERAL: {GENERAL_CLIP: ""},
        PRESET_PLAYER: {
            action: {side: {"clip": ""} for side, _ in SIDES}
            for action, _ in PLAYER_ACTIONS
        },
    }


def links_of(entry: dict, library: dict | None = None) -> dict:
    """条目里的 links 整理成完整形状：缺的预设/动作/方向都补空链接。

    链接写 {"clip": 键}，老数据直接写字符串；老数据把上升写在 jump 里，
    raise 空着时去那里借。
    """
    links = new_links()
    value = entry.get("links") if isinstance(entry, dict) else None
    if not isinstance(value, dict):
        return links
    links[PRESET_GENERAL] = _normalize_link(value.get(PRESET_GENERAL))
    player = value.get(PRESET_PLAYER)
    if isinstance(player, dict):
        for action, _ in PLAYER_ACTIONS:
            pair = player.get(action)
            if not isinstance(pair, dict):
                if action == "raise":
                    pair = player.get("jump")      # 老数据：上升叫 jump
                if not isinstance(pair, dict):
                    continue
            for side, _ in SIDES:
                links[PRESET_PLAYER][action][side] = _normalize_link(
                    pair.get(side)
                )
    return links


def _normalize_link(value) -> dict:
    if isinstance(value, dict):
        return {"clip": str(value.get("clip") or "")}
    return {"clip": str(value or "")}


# ---- 读 / 写 -------------------------------------------------------
def from_settings(settings: dict) -> dict:
    """game.json → 动画库；老格式动画在这时一次性迁进来。"""
    library = _read_library((settings or {}).get(LIBRARY_KEY))
    _migrate_legacy(library, settings or {})
    return library


def _read_library(table) -> dict:
    library: dict = {}
    if not isinstance(table, dict):
        return library
    for key, value in table.items():
        name = str(key).strip()
        if not name or not isinstance(value, dict):
            continue
        frames = [
            str(frame)
            for frame in value.get("frames") or []
            if isinstance(frame, str) and frame.strip()
        ]
        given = value.get("holds")
        given = given if isinstance(given, list) else []
        holds = [
            hold_text(given[index] if index < len(given) else None)
            for index in range(len(frames))
        ]
        library[name] = {"frames": frames, "holds": holds}
    return library


def _migrate_legacy(library: dict, settings: dict) -> None:
    """老 player.animations（动作 → 左右两侧）拆成动画库条目。

    每个动作的右侧 → 「动作_right」，左侧 → 「动作_left」；库里已经有同名键就不动。
    老的单张图（player.animation）也按右侧一帧迁过来。
    """
    player = settings.get("player")
    player = player if isinstance(player, dict) else {}
    for table in (settings.get("animations"), player.get("animations")):
        _migrate_action_table(library, table)
    legacy = player.get("animation")
    if isinstance(legacy, dict):
        for action, value in legacy.items():
            if str(action) not in LEGACY_ACTION_NAMES:
                continue
            key = f"{action}_right"
            if key in library or not isinstance(value, str) or not value.strip():
                continue
            library[key] = {
                "frames": [value.strip()],
                "holds": [hold_text(DEFAULT_HOLD)],
            }


def _migrate_action_table(library: dict, table) -> None:
    if not isinstance(table, dict):
        return
    for action, entry in table.items():
        if str(action) not in LEGACY_ACTION_NAMES:
            continue                    # flip 等旧动作不再迁移
        if not isinstance(entry, dict):
            continue
        if "frames" in entry or "holds" in entry or "fps" in entry:
            _migrate_clip(library, f"{action}_right", entry)
            continue
        for side, _ in SIDES:
            value = entry.get(side)
            if isinstance(value, dict):
                _migrate_clip(library, f"{action}_{side}", value)


def _migrate_clip(library: dict, key: str, entry: dict) -> None:
    if key in library:
        return
    frames = [
        str(frame)
        for frame in entry.get("frames") or []
        if isinstance(frame, str) and frame.strip()
    ]
    if not frames:
        return
    given = entry.get("holds")
    given = given if isinstance(given, list) else []
    fps = entry.get("fps")
    fallback = None
    try:
        fallback = 1.0 / float(fps) if fps else None
    except (TypeError, ValueError):
        fallback = None
    library[key] = {
        "frames": frames,
        "holds": [
            hold_text(given[index] if index < len(given) else fallback)
            for index in range(len(frames))
        ],
    }


def to_settings(settings: dict, library: dict) -> dict:
    """编辑状态 → 写回 game.json：写动画库，删掉旧的玩家动画字段。"""
    table = {}
    for key, clip in library.items():
        name = str(key).strip()
        if not name:
            continue
        frames = [
            str(frame).strip()
            for frame in clip.get("frames") or []
            if str(frame).strip()
        ]
        holds = holds_of(clip)[: len(frames)]
        table[name] = {
            "frames": frames,
            "holds": [round(hold, 2) for hold in holds],
        }
    settings[LIBRARY_KEY] = table
    player = settings.get("player")
    if isinstance(player, dict):
        player.pop("animations", None)
        player.pop("animation", None)
    settings.pop("animations", None)
    return settings


def holds_of(clip: dict) -> list:
    """一条动画的每帧停留秒数（浮点，夹好范围），和 frames 一样长。"""
    frames = clip.get("frames") or []
    given = clip.get("holds") or []
    return [
        clamp_float(
            given[index] if index < len(given) else None, MIN_HOLD, MAX_HOLD, DEFAULT_HOLD
        )
        for index in range(len(frames))
    ]


# ---- 动画对象 ------------------------------------------------------
def preset_of(entry: dict) -> str:
    preset = str(entry.get("preset") or PRESET_GENERAL) if isinstance(entry, dict) else ""
    return preset if preset in (PRESET_GENERAL, PRESET_PLAYER) else PRESET_GENERAL


def link_key(links: dict, preset: str, action: str = "", side: str = "") -> str:
    return str(_link_value(links, preset, action, side).get("clip") or "")


def _link_value(links: dict, preset: str, action: str = "", side: str = "") -> dict:
    if preset == PRESET_GENERAL:
        value = links.get(PRESET_GENERAL)
        return value if isinstance(value, dict) else {}
    pair = (links.get(PRESET_PLAYER) or {}).get(action)
    pair = pair if isinstance(pair, dict) else {}
    value = pair.get(side)
    return value if isinstance(value, dict) else {}


def set_link(links: dict, preset: str, action: str, side: str, key: str) -> None:
    """改链接指向的剪辑。"""
    _store_link(links, preset, action, side, {"clip": str(key or "")})


def _store_link(links: dict, preset: str, action: str, side: str, value: dict) -> None:
    if preset == PRESET_GENERAL:
        links[PRESET_GENERAL] = dict(value)
        return
    player = links.setdefault(PRESET_PLAYER, {})
    pair = player.setdefault(action, {})
    pair[side] = dict(value)


def resolve_for_editor(
    library: dict, entry: dict, action: str | None = None, side: str = "right"
) -> tuple[list, list, bool, str]:
    """编辑器画布用：这个动画对象现在该显示哪条剪辑。

    返回 (帧路径, 每帧时长, 要不要镜像, 实际动作名)。玩家预设默认用 idle、右侧；
    找不到剪辑就是空列表。
    """
    links = links_of(entry, library)
    if preset_of(entry) == PRESET_GENERAL:
        key = link_key(links, PRESET_GENERAL)
        clip = library.get(key)
        if clip is None:
            return [], [], False, GENERAL_CLIP
        return list(clip["frames"]), holds_of(clip), False, GENERAL_CLIP
    action = action or "idle"
    candidates = (action, "idle", *[name for name, _ in PLAYER_ACTIONS])
    if action == "raise":
        candidates = ("raise", "jump", *candidates)
    for candidate in candidates:
        key = link_key(links, PRESET_PLAYER, candidate, side)
        mirror = False
        if not key:
            other = "left" if side == "right" else "right"
            key = link_key(links, PRESET_PLAYER, candidate, other)
            mirror = bool(key)
        clip = library.get(key) if key else None
        if clip is not None:
            return list(clip["frames"]), holds_of(clip), mirror, candidate
    return [], [], False, action


def referenced_keys(level_definition: dict) -> set:
    """一个关卡里所有动画对象链接到的动画库键。"""
    keys: set = set()
    entries = level_definition.get("animation_objects")
    if not isinstance(entries, list):
        return keys
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        links = links_of(entry)
        key = link_key(links, PRESET_GENERAL)
        if key:
            keys.add(key)
        for action, _ in PLAYER_ACTIONS:
            for side, _ in SIDES:
                key = link_key(links, PRESET_PLAYER, action, side)
                if key:
                    keys.add(key)
    return keys


def copy_links(links: dict) -> dict:
    return copy.deepcopy(links)
