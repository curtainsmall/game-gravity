"""玩家动画：game.json 里 player 的 animations 表。

每个动作分左右两侧，各自一组帧、每帧一个停留时长：
    {"idle": {"right": {"frames": [相对路径…], "holds": [0.1, …], "loop": true},
              "left":  {"frames": [], "holds": [], "loop": true}}, ...}
动作名固定（见 PLAYER_ANIMATIONS），方向固定（见 PLAYER_SIDES）。编辑器里每帧的时长
写成字符串（和别的数字字段一样），存盘时再变成数字。两侧没有主次：空着的一侧在游戏里
用另一侧的帧镜像出来，所以预览时也要能算出「实际会放什么」（见 resolved）。
老格式（动作 → 一套 frames + fps + loop）读成右侧，fps 换算成每帧 1/fps 秒；更早一版
把动画表写在顶层 animations、把动作写成单张图放在 player.animation，也都读。
"""

from core.helpers import clamp_float

PLAYER_ANIMATIONS = (
    ("idle", "站立"),
    ("run", "移动"),
    ("jump", "上升"),
    ("fall", "下落"),
    ("flip", "翻转"),
)
PLAYER_SIDES = (
    ("right", "向右"),
    ("left", "向左"),
)
SIDE_NAMES = {"right": "右侧", "left": "左侧"}
PREVIEW_KEY = "preview_animation"   # 起点里记着显示哪一套动画；游戏不读，只给编辑器看
DEFAULT_PREVIEW = "idle"
DEFAULT_HOLD = 0.1          # 一帧默认停 0.1 秒
MIN_HOLD = 0.01
MAX_HOLD = 10.0
HOLD_STEP = 0.01
DEFAULT_FPS = 8.0           # 老数据没写 fps 时的默认值
DRAG_THRESHOLD = 4          # 鼠标挪开几个像素才算开始拖一帧（免得手一抖就换了顺序）


def other_side(side: str) -> str:
    return "left" if side == "right" else "right"


def hold_text(value) -> str:
    """停顿秒数 → 编辑框里的文字（夹在 0.01–10 之间）。"""
    return f"{clamp_float(value, MIN_HOLD, MAX_HOLD, DEFAULT_HOLD):g}"


def new_side() -> dict:
    return {"frames": [], "holds": [], "loop": True}


def new_state() -> dict:
    """五个动作、两个方向一开始就都在（没帧的也留着，存盘时写空表）。"""
    return {
        name: {"right": new_side(), "left": new_side()}
        for name, _ in PLAYER_ANIMATIONS
    }


def from_settings(settings: dict) -> dict:
    """game.json → 编辑用的状态：固定五个动作、两个方向，写了帧的才盖掉默认。"""
    state = new_state()
    player = settings.get("player")
    player = player if isinstance(player, dict) else {}
    _apply_table(state, settings.get("animations"))       # 更早一版的顶层写法
    _apply_table(state, player.get("animations"))
    # 老格式：player.animation 动作名 → 单张图；对应右侧还没帧才用它
    legacy = player.get("animation")
    if isinstance(legacy, dict):
        for name, _ in PLAYER_ANIMATIONS:
            path = legacy.get(name)
            clip = state[name]["right"]
            if path and not clip["frames"]:
                clip["frames"] = [str(path)]
                clip["holds"] = [hold_text(DEFAULT_HOLD)]
    return state


def _apply_table(state: dict, table) -> None:
    """把一张 animations 表盖到编辑状态上；坏条目、不认识的动作名都跳过。"""
    if not isinstance(table, dict):
        return
    for name, _ in PLAYER_ANIMATIONS:
        value = table.get(name)
        if not isinstance(value, dict):
            continue
        if "frames" in value or "holds" in value or "fps" in value:
            _apply_side(state[name]["right"], value)       # 老格式：整套就在这一层
            continue
        for side, _ in PLAYER_SIDES:
            side_value = value.get(side)
            if isinstance(side_value, dict):
                _apply_side(state[name][side], side_value)


def _apply_side(clip: dict, value: dict) -> None:
    """一侧的 frames / holds / loop；没有 holds 时按 fps 换算。"""
    frames = [
        str(frame)
        for frame in value.get("frames") or []
        if isinstance(frame, str) and frame.strip()
    ]
    given = value.get("holds")
    given = given if isinstance(given, list) else []
    fps = value.get("fps")
    fallback = None
    try:
        fallback = 1.0 / float(fps) if fps else None
    except (TypeError, ValueError):
        fallback = None
    clip["frames"] = frames
    clip["holds"] = [
        hold_text(given[index] if index < len(given) else fallback)
        for index in range(len(frames))
    ]
    clip["loop"] = bool(value.get("loop", True))


def to_table(state: dict) -> dict:
    """编辑状态 → 写回 game.json 的 player.animations。

    五个动作、两个方向全写：这一页管的就是整张表。没帧的侧写空 frames / holds。
    """
    table = {}
    for name, _ in PLAYER_ANIMATIONS:
        entry = state.get(name) or {}
        table[name] = {}
        for side, _ in PLAYER_SIDES:
            clip = entry.get(side) or {}
            frames = [
                str(frame).strip()
                for frame in clip.get("frames") or []
                if str(frame).strip()
            ]
            holds = holds_of(clip)[: len(frames)]
            table[name][side] = {
                "frames": frames,
                "holds": [round(hold, 2) for hold in holds],
                "loop": bool(clip.get("loop", True)),
            }
    return table


def holds_of(clip: dict) -> list:
    """一侧每帧停留多少秒（浮点、夹好范围），和 frames 一样长。"""
    frames = clip.get("frames") or []
    given = clip.get("holds") or []
    return [
        clamp_float(given[index] if index < len(given) else None, MIN_HOLD, MAX_HOLD, DEFAULT_HOLD)
        for index in range(len(frames))
    ]


def resolved(state: dict, action: str, side: str) -> tuple:
    """这一侧实际会播什么：(frames, holds, loop, 镜像自哪一侧或 None)。

    本侧有帧就用本侧；本侧空着就用另一侧，播放时水平镜像（见游戏端的 PlayerAnimator）；
    两侧都没有就是空，游戏里退到 idle。
    """
    entry = state.get(action) or {}
    clip = entry.get(side) or {}
    frames = [str(frame) for frame in clip.get("frames") or []]
    if frames:
        return frames, holds_of(clip), bool(clip.get("loop", True)), None
    other = other_side(side)
    fallback = entry.get(other) or {}
    frames = [str(frame) for frame in fallback.get("frames") or []]
    if frames:
        return frames, holds_of(fallback), bool(fallback.get("loop", True)), other
    return [], [], True, None
