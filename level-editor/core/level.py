"""关卡数据模型。"""

import copy
import json

from core.constants import (
    COLS,
    JUMP_HEIGHT_DEFAULT,
    LEVEL_HEIGHT_MAX,
    LEVEL_HEIGHT_MIN,
    LEVEL_WIDTH_MAX,
    LEVEL_WIDTH_MIN,
    ROWS,
)
from core.helpers import clamp_int


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


class Level:
    def __init__(self) -> None:
        self.name = ""
        self.width = COLS          # 关卡宽度，格
        self.height = ROWS         # 关卡高度，格
        self.background = ""       # 背景图，相对关卡目录的路径；空串表示没有背景
        self.jump_height = JUMP_HEIGHT_DEFAULT
        self.blocks: list = []
        self.planks: list = []
        self.movable_blocks: list = []
        self.buttons: list = []
        self.items: list = []
        self.nozzles: list = []
        self.player: dict | None = None
        self.destination: dict | None = None

    def to_definition(self) -> dict:
        definition = {
            "name": self.name,
            "width": self.width,
            "height": self.height,
            "jump_height": self.jump_height,
            "blocks": copy.deepcopy(self.blocks),
            "planks": copy.deepcopy(self.planks),
            "movable_blocks": copy.deepcopy(self.movable_blocks),
            "buttons": copy.deepcopy(self.buttons),
            "items": copy.deepcopy(self.items),
            "nozzles": copy.deepcopy(self.nozzles),
        }
        # 起点和终点都只有一份，没有就不写这个键
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
        level.jump_height = int(definition.get("jump_height", JUMP_HEIGHT_DEFAULT))
        level.background = str(definition.get("background", "") or "")
        level.player = copy.deepcopy(definition.get("player"))
        level.destination = copy.deepcopy(definition.get("destination"))
        level.blocks = copy.deepcopy(list(definition.get("blocks", [])))
        level.planks = copy.deepcopy(list(definition.get("planks", [])))
        level.movable_blocks = copy.deepcopy(list(definition.get("movable_blocks", [])))
        level.buttons = copy.deepcopy(list(definition.get("buttons", [])))
        level.items = copy.deepcopy(list(definition.get("items", [])))
        level.nozzles = copy.deepcopy(list(definition.get("nozzles", [])))
        return level


def player_position(level: Level) -> tuple:
    """起点坐标；没有起点时返回 None。"""
    if level.player is None:
        return None
    pos = level.player.get("pos", [0, 0])
    return int(pos[0]), int(pos[1])
