"""关卡数据：schema 用设计者的词汇，程序里只有 GameObject。

每个条目都是 {"pos": [x, y], "size": [w, h]}，size 缺省为 1×1。
各对象的内容仍在设计，这里只读取位置与尺寸。
"""

import json

from controller.controller import Controller
from controller.input_source import InputSource
from core.game_object import GameObject, GameObjectKind
from physics.body import Body
from renderer.palette import color_for_kind
from renderer.render_spec import RenderSpec
from world.world import HEIGHT_IN_BLOCKS, WIDTH_IN_BLOCKS, World

LevelDefinition = dict[str, object]

DEFAULT_SIZE = (1.0, 1.0)


def load_level_file(path: str) -> LevelDefinition:
    """读取关卡文件。"""
    with open(path, encoding="utf-8") as file:
        return json.load(file)


def build_world(level_definition: LevelDefinition) -> World:
    return World(
        gravity_acceleration_magnitude=float(level_definition.get("gravity", 0.0)),
        width_in_blocks=int(level_definition.get("width", WIDTH_IN_BLOCKS)),
        height_in_blocks=int(level_definition.get("height", HEIGHT_IN_BLOCKS)),
    )


def _read_position(entry: dict) -> tuple[float, float]:
    x, y = entry["pos"]
    return float(x), float(y)


def _read_size(entry: dict) -> tuple[float, float]:
    width, height = entry.get("size", DEFAULT_SIZE)
    return float(width), float(height)


def _make(
    entry: dict,
    kind: GameObjectKind,
    is_static: bool = False,
    is_sensor: bool = False,
    is_passable_during_flip: bool = False,
    controller: Controller | None = None,
) -> GameObject:
    x, y = _read_position(entry)
    width, height = _read_size(entry)
    return GameObject(
        kind=kind,
        body=Body(
            left=x,
            bottom=y,
            width=width,
            height=height,
            is_static=is_static,
            is_sensor=is_sensor,
            is_passable_during_flip=is_passable_during_flip,
        ),
        controller=controller,
        render=RenderSpec(
            placeholder_size_in_blocks=(width, height),
            placeholder_color=color_for_kind(kind),
            placeholder_label_text=str(kind),
        ),
    )


def build_blocks(level_definition: LevelDefinition) -> list[GameObject]:
    blocks = [
        _make(entry, GameObjectKind.BLOCK, is_static=True)
        for entry in level_definition.get("blocks", [])
    ]
    planks = [
        _make(entry, GameObjectKind.PLANK, is_static=True, is_passable_during_flip=True)
        for entry in level_definition.get("planks", [])
    ]
    return blocks + planks


def build_boundaries(world: World) -> list[GameObject]:
    """地面在天花板之外：可玩带为 0 到 height_in_blocks。"""
    span = float(world.width_in_blocks)
    height = float(world.height_in_blocks)
    return [
        _make({"pos": [0.0, -1.0], "size": [span, 1.0]}, GameObjectKind.GROUND, is_static=True),
        _make({"pos": [0.0, height], "size": [span, 1.0]}, GameObjectKind.CEILING, is_static=True),
    ]


def build_player(level_definition: LevelDefinition) -> list[GameObject]:
    entry = level_definition.get("player")
    if entry is None:
        return []
    return [_make(entry, GameObjectKind.PLAYER, controller=Controller(source=InputSource()))]


def build_destination(level_definition: LevelDefinition) -> list[GameObject]:
    entry = level_definition.get("destination")
    if entry is None:
        return []
    return [_make(entry, GameObjectKind.DESTINATION, is_static=True, is_sensor=True)]


def build_fans(level_definition: LevelDefinition) -> list[GameObject]:
    return [
        _make(entry, GameObjectKind.FAN, is_static=True, is_sensor=True)
        for entry in level_definition.get("fans", [])
    ]


def build_items(level_definition: LevelDefinition) -> list[GameObject]:
    return [
        _make(entry, GameObjectKind.ITEM, is_static=True, is_sensor=True)
        for entry in level_definition.get("items", [])
    ]


def build_buttons(level_definition: LevelDefinition) -> list[GameObject]:
    return [
        _make(entry, GameObjectKind.BUTTON, is_static=True, is_sensor=True)
        for entry in level_definition.get("buttons", [])
    ]


def build_movable_blocks(level_definition: LevelDefinition) -> list[GameObject]:
    return [
        _make(entry, GameObjectKind.MOVABLE_BLOCK, is_static=True)
        for entry in level_definition.get("movable_blocks", [])
    ]
