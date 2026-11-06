"""关卡数据模型。

键和形状与游戏端一一对应，细节见 game/world/level.py 的模块说明；这里只额外记着
编辑器自己关心的事：玩家的跳高、速度、动画属于整个游戏（game.json，见 core.game），
不归 Level 管；scene.json 的 player 里如果还留着这几个键，原样保留当这一关的覆盖值。
"""

import copy
import json

from core.constants import (
    BUTTON_SIZE,
    COLS,
    FLIP_AREA_OFFSETS_DEFAULT,
    JUMP_HEIGHT_DEFAULT,
    JUMP_HEIGHT_MIN,
    LEVEL_HEIGHT_MAX,
    LEVEL_HEIGHT_MIN,
    LEVEL_WIDTH_MAX,
    LEVEL_WIDTH_MIN,
    MOVE_SPEED_DEFAULT,
    MOVE_SPEED_MAX,
    MOVE_SPEED_MIN,
    NOZZLE_DEFAULT_SIZE,
    PORTAL_SIZE,
    ROWS,
)
from core.helpers import clamp_float, clamp_int


def dump_level(definition: dict) -> str:
    """把关卡排成 JSON 文本：对象缩进 2，纯标量数组保持一行。

    json.dump 会把 pos/size 这种数组也拆成一行一个数，手写和看 diff 都很难受，
    所以自己排版：只有里面还装着对象或数组的数组才换行。
    """
    return _format_block(definition, 0) + "\n"


def _format_block(value, depth: int) -> str:
    if isinstance(value, dict):
        if not value:
            return "{}"
        pad = "  " * (depth + 1)
        items = [
            f"{pad}{json.dumps(key, ensure_ascii=False)}: {_format_block(item, depth + 1)}"
            for key, item in value.items()
        ]
        return "{\n" + ",\n".join(items) + "\n" + "  " * depth + "}"
    if isinstance(value, list):
        if all(not isinstance(item, (dict, list)) for item in value):
            return "[" + ", ".join(json.dumps(item, ensure_ascii=False) for item in value) + "]"
        pad = "  " * (depth + 1)
        items = [pad + _format_block(item, depth + 1) for item in value]
        return "[\n" + ",\n".join(items) + "\n" + "  " * depth + "]"
    return json.dumps(value, ensure_ascii=False)


def _read_flip_area_offsets(definition: dict, level_height: int) -> list[float]:
    """翻转区两个起点：缺字段、写坏了都退回默认值，夹在 0 ~ 关卡高度之间。"""
    value = definition.get("flip_area_offsets", FLIP_AREA_OFFSETS_DEFAULT)
    try:
        up_offset, down_offset = value
    except (TypeError, ValueError):
        up_offset, down_offset = FLIP_AREA_OFFSETS_DEFAULT
    limit = float(level_height)
    return [
        clamp_float(up_offset, 0.0, limit, 0.0),
        clamp_float(down_offset, 0.0, limit, 0.0),
    ]


class Level:
    def __init__(self) -> None:
        self.name = ""
        self.width = COLS          # 关卡宽度，格
        self.height = ROWS         # 关卡高度，格
        self.background = ""       # 背景图，相对关卡目录的路径；空串表示没有背景
        self.flip_area_offsets = list(FLIP_AREA_OFFSETS_DEFAULT)  # 翻转带的高度
        self.blocks: list = []
        self.planks: list = []
        self.movable_blocks: list = []
        self.buttons: list = []
        self.portals: list = []
        self.items: list = []
        self.nozzles: list = []
        self.textures: list = []   # 贴图：浮点世界矩形 + 图片名，不吸格子
        self.player: dict | None = None
        self.destination: dict | None = None

    def to_definition(self) -> dict:
        definition = {
            "name": self.name,
            "width": self.width,
            "height": self.height,
            "flip_area_offsets": list(self.flip_area_offsets),
            "blocks": copy.deepcopy(self.blocks),
            "planks": copy.deepcopy(self.planks),
            "movable_blocks": copy.deepcopy(self.movable_blocks),
            "buttons": copy.deepcopy(self.buttons),
            "portals": copy.deepcopy(self.portals),
            "items": copy.deepcopy(self.items),
            "nozzles": copy.deepcopy(self.nozzles),
            "textures": copy.deepcopy(self.textures),
        }
        # 起点和终点都只有一份，没有就不写这个键。跳高、速度、动画属于整个游戏，
        # 写在 game.json 里；这一关原本写过的覆盖值原样留着，不动它。
        if self.player is not None:
            definition["player"] = copy.deepcopy(self.player)
        if self.destination is not None:
            definition["destination"] = copy.deepcopy(self.destination)
        # 没有背景就不写这个键
        if self.background:
            definition["background"] = self.background
        return definition

    @classmethod
    def from_definition(cls, definition: dict) -> "Level":
        level = cls()
        level.name = str(definition.get("name", ""))
        level.width = clamp_int(definition.get("width"), LEVEL_WIDTH_MIN, LEVEL_WIDTH_MAX, COLS)
        level.height = clamp_int(definition.get("height"), LEVEL_HEIGHT_MIN, LEVEL_HEIGHT_MAX, ROWS)
        level.flip_area_offsets = _read_flip_area_offsets(definition, level.height)
        level.background = str(definition.get("background", "") or "")
        level.destination = copy.deepcopy(definition.get("destination"))
        level.blocks = copy.deepcopy(list(definition.get("blocks", [])))
        level.planks = copy.deepcopy(list(definition.get("planks", [])))
        level.movable_blocks = copy.deepcopy(list(definition.get("movable_blocks", [])))
        level.buttons = copy.deepcopy(list(definition.get("buttons", [])))
        # 门本身就是触发区了：老数据里的 range 读进来就丢掉，省得存回去又冒出来
        level.portals = [
            {key: value for key, value in entry.items() if key != "range"}
            for entry in copy.deepcopy(list(definition.get("portals", [])))
            if isinstance(entry, dict)
        ]
        # 按钮和门的「画出来的矩形」就是触发区，缺 size 时按默认补上，别和游戏里不一致
        for entries, default in ((level.buttons, BUTTON_SIZE), (level.portals, PORTAL_SIZE)):
            for entry in entries:
                if isinstance(entry, dict):
                    entry.setdefault("size", list(default))
        level.items = copy.deepcopy(list(definition.get("items", [])))
        # 喷口的风区现在是 size；老数据写的 range 读进来换成 [1, range]
        level.nozzles = []
        for entry in copy.deepcopy(list(definition.get("nozzles", []))):
            if not isinstance(entry, dict):
                continue
            if "size" not in entry and "range" in entry:
                entry["size"] = [1.0, entry.pop("range")]
            entry.pop("range", None)
            entry.setdefault("size", list(NOZZLE_DEFAULT_SIZE))
            level.nozzles.append(entry)
        level.textures = copy.deepcopy(list(definition.get("textures", [])))

        # 玩家：这里只放位置和大小，跳高/速度/动画属于整个游戏（game.json，编辑器不写）；
        # 老关卡里写过的这几项原样留着，游戏读的时候当成这一关的覆盖值
        player = definition.get("player")
        level.player = copy.deepcopy(player) if isinstance(player, dict) else None
        return level
