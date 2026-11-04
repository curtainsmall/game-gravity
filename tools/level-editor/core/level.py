"""关卡数据模型。"""

import copy

from core.constants import COLS, JUMP_HEIGHT_DEFAULT, ROWS


class Level:
    def __init__(self) -> None:
        self.name = ""
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
            "width": COLS,
            "height": ROWS,
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
        return definition

    @classmethod
    def from_definition(cls, definition: dict) -> "Level":
        level = cls()
        level.name = str(definition.get("name", ""))
        level.jump_height = int(definition.get("jump_height", JUMP_HEIGHT_DEFAULT))
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
