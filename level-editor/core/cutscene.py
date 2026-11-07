"""过场数据：关卡 json 或 game.json 里的 cutscene。

形状和游戏端一致（见 game/cutscene/cutscene.py）：
    pictures  [{"path", "fade_in", "hold", "fade_out"}, ...]
    cascade   下一张的淡入是否和上一张的淡出重叠，缺省 false
    sound     false（缺省，静音）/ true（用本幕音乐）/ 一段 sound 对象
编辑器里数字用字符串（和别的数字字段一样），没写的字段按零值算。
播放层的规则：按住空格跳过、Esc 暂停、图片 contain 到窗口。
"""

from core.helpers import clamp_float
from core.sound import fields_of, to_object as sound_to_object

CUTSCENE_KEY = "cutscene"
PICTURE_PATH_MAX_LENGTH = 200
HOLD_MAX_SECONDS = 60.0
FADE_MAX_SECONDS = 10.0
STEP_SECONDS = 0.5

SOUND_MODE_NONE = "none"
SOUND_MODE_SCENE = "scene"
SOUND_MODE_CUSTOM = "custom"
SOUND_ORDER = (SOUND_MODE_NONE, SOUND_MODE_SCENE, SOUND_MODE_CUSTOM)
SOUND_MODE_LABELS = {
    "level": {"none": "无", "scene": "跟随本关", "custom": "指定"},
    "game": {"none": "无", "scene": "跟随制作名单", "custom": "指定"},
}


def new_state() -> dict:
    return {
        "pictures": [],
        "cascade": False,
        "sound_mode": SOUND_MODE_NONE,
        "sound": fields_of(None),
    }


def from_value(value, library: dict | None = None) -> dict:
    """json 里的 cutscene → 编辑用的状态：图片的数字是字符串。"""
    state = new_state()
    if not isinstance(value, dict):
        return state
    state["cascade"] = bool(value.get("cascade", False))
    for entry in value.get("pictures") or []:
        if not isinstance(entry, dict):
            continue
        state["pictures"].append(
            {
                "path": str(entry.get("path") or ""),
                "fade_in": f"{_seconds(entry.get('fade_in'), FADE_MAX_SECONDS):g}",
                "hold": f"{_seconds(entry.get('hold'), HOLD_MAX_SECONDS):g}",
                "fade_out": f"{_seconds(entry.get('fade_out'), FADE_MAX_SECONDS):g}",
            }
        )
    sound = value.get("sound")
    if sound is True:
        state["sound_mode"] = SOUND_MODE_SCENE
    elif isinstance(sound, dict):
        state["sound_mode"] = SOUND_MODE_CUSTOM
        state["sound"] = fields_of(sound, library)
    return state


def to_object(state: dict, keep_all: bool = False) -> dict | None:
    """编辑用的状态 → 写回 json 的 cutscene。

    keep_all 为真时，没有图片也把 pictures / cascade / sound 都写出来（默认值照写）；
    否则没有图片返回 None，调用方就不写这个键。
    """
    pictures = []
    for picture in state.get("pictures") or []:
        path = str(picture.get("path") or "").strip()
        if not path:
            continue
        pictures.append(
            {
                "path": path,
                "fade_in": round(
                    clamp_float(picture.get("fade_in"), 0.0, FADE_MAX_SECONDS, 0.0), 2
                ),
                "hold": round(clamp_float(picture.get("hold"), 0.0, HOLD_MAX_SECONDS, 0.0), 2),
                "fade_out": round(
                    clamp_float(picture.get("fade_out"), 0.0, FADE_MAX_SECONDS, 0.0), 2
                ),
            }
        )
    if not pictures and not keep_all:
        return None
    value: dict = {"pictures": pictures}
    if state.get("cascade"):
        value["cascade"] = True
    elif keep_all:
        value["cascade"] = False
    mode = state.get("sound_mode")
    if mode == SOUND_MODE_SCENE:
        value["sound"] = True
    elif mode == SOUND_MODE_CUSTOM:
        sound = sound_to_object(state.get("sound") or {}, keep_empty=keep_all)
        if sound is not None:
            value["sound"] = sound
    elif keep_all:
        value["sound"] = False
    return value


def new_picture() -> dict:
    """新加的一张图：给一点默认时间，免得三项都是 0、存下去等于没放。"""
    return {"path": "", "fade_in": "0.5", "hold": "2", "fade_out": "0.5"}


def sound_mode_label(scope: str, mode: str) -> str:
    return SOUND_MODE_LABELS.get(scope, SOUND_MODE_LABELS["level"]).get(mode, mode)


def _seconds(value, limit: float) -> float:
    return clamp_float(value, 0.0, limit, 0.0)
