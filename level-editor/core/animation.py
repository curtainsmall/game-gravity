"""玩家动画：game.json 里 player 的 animations 表。

形状和游戏端一致：
    {"idle": {"frames": [相对路径…], "fps": 8, "loop": true}, ...}
名字固定（见 PLAYER_ANIMATIONS），编辑器里数字写成字符串（和别的数字字段一样）。
老的 player.animation（动作名 → 单张图）读成只有一帧的剪辑；更早一版写在顶层
animations，也读，应用时一并迁进 player。
"""

from core.helpers import clamp_float

PLAYER_ANIMATIONS = (
    ("idle", "站立"),
    ("run", "移动"),
    ("jump", "上升"),
    ("fall", "下落"),
    ("flip", "翻转"),
)
DEFAULT_FPS = 8.0
FPS_MIN = 1.0
FPS_MAX = 60.0
FPS_STEP = 1.0
DRAG_THRESHOLD = 4      # 鼠标挪开几个像素才算开始拖动一帧（免得手一抖就换了顺序）
FRAME_PATH_MAX_LENGTH = 160


def new_state() -> dict:
    """五个状态一开始就都在（没帧的不写盘）。"""
    return {
        name: {"frames": [], "fps": f"{DEFAULT_FPS:g}", "loop": True}
        for name, _ in PLAYER_ANIMATIONS
    }


def from_settings(settings: dict) -> dict:
    """game.json → 编辑用的状态：固定五个状态，剪辑里有帧才覆盖默认。"""
    state = new_state()
    player = settings.get("player")
    player = player if isinstance(player, dict) else {}
    _apply_table(state, settings.get("animations"))   # 更早一版的顶层写法
    _apply_table(state, player.get("animations"))
    # 老格式：player.animation 动作名 → 单张图；新剪辑没帧的状态才用它
    legacy = player.get("animation")
    if isinstance(legacy, dict):
        for name, _ in PLAYER_ANIMATIONS:
            path = legacy.get(name)
            if path and not state[name]["frames"]:
                state[name]["frames"] = [str(path)]
    return state


def _apply_table(state: dict, table) -> None:
    """把一张 animations 表盖到编辑状态上；坏条目、不认识的剪辑名都跳过。"""
    if not isinstance(table, dict):
        return
    for name, _ in PLAYER_ANIMATIONS:
        value = table.get(name)
        if not isinstance(value, dict):
            continue
        state[name]["frames"] = [
            str(frame)
            for frame in value.get("frames") or []
            if isinstance(frame, str) and frame.strip()
        ]
        state[name]["fps"] = f"{clamp_float(value.get('fps'), FPS_MIN, FPS_MAX, DEFAULT_FPS):g}"
        state[name]["loop"] = bool(value.get("loop", True))


def to_table(state: dict) -> dict:
    """编辑状态 → 写回 game.json 的 player.animations；一帧都没有的状态不写。"""
    table = {}
    for name, _ in PLAYER_ANIMATIONS:
        clip = state.get(name) or {}
        frames = [str(frame) for frame in clip.get("frames") or [] if str(frame).strip()]
        if not frames:
            continue
        table[name] = {
            "frames": frames,
            "fps": round(clamp_float(clip.get("fps"), FPS_MIN, FPS_MAX, DEFAULT_FPS), 2),
            "loop": bool(clip.get("loop", True)),
        }
    return table
