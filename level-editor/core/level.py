"""关卡数据模型。

键和形状与游戏端一一对应，细节见 game/world/level.py 的模块说明；这里只额外记着
编辑器自己关心的事：玩家的跳高、速度和动画存在 Level 上，保存时才塞进 player。
"""

import copy
import json

from core.constants import (
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
        self.jump_height = JUMP_HEIGHT_DEFAULT
        self.move_speed = MOVE_SPEED_DEFAULT   # 水平移动速度，方块/秒
        self.animation: dict = {}  # 玩家动画：动作名 → 图片路径，动作名先不限
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
        # 起点和终点都只有一份，没有就不写这个键；跳高、速度、动画都挂在玩家身上
        if self.player is not None:
            player = copy.deepcopy(self.player)
            player["jump_height"] = self.jump_height
            player["move_speed"] = self.move_speed
            player["animation"] = copy.deepcopy(self.animation)
            definition["player"] = player
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
        level.items = copy.deepcopy(list(definition.get("items", [])))
        level.nozzles = copy.deepcopy(list(definition.get("nozzles", [])))
        level.textures = copy.deepcopy(list(definition.get("textures", [])))

        # 玩家：跳高、速度、动画都挂在它身上；老文件写在外层的，读的时候搬进来
        player = definition.get("player")
        level.player = copy.deepcopy(player) if isinstance(player, dict) else None
        source = level.player if level.player is not None else {}
        level.jump_height = clamp_int(
            source.get("jump_height", definition.get("jump_height")),
            JUMP_HEIGHT_MIN,
            max(JUMP_HEIGHT_MIN, level.height - 1),   # 跳高不超过关卡高度 - 1
            JUMP_HEIGHT_DEFAULT,
        )
        level.move_speed = clamp_float(
            source.get("move_speed", definition.get("move_speed")),
            MOVE_SPEED_MIN,
            MOVE_SPEED_MAX,
            MOVE_SPEED_DEFAULT,
        )
        animation = source.get("animation", definition.get("animation"))
        level.animation = copy.deepcopy(animation) if isinstance(animation, dict) else {}
        if level.player is not None:
            # 面板上玩家只编辑位置和大小，这三项存在 Level 上
            for key in ("jump_height", "move_speed", "animation"):
                level.player.pop(key, None)
        return level
