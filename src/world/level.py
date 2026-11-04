"""关卡数据：schema 用设计者的词汇（方块、木板），程序里只有 GameObject。"""

import json

from core.game_object import GameObject, GameObjectKind
from physics.body import Body
from renderer.render_spec import RenderSpec
from world.world import HEIGHT_IN_BLOCKS, WIDTH_IN_BLOCKS, World

LevelDefinition = dict[str, object]


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


def _make_solid(
    x: float,
    y: float,
    width: float,
    height: float,
    kind: GameObjectKind,
    is_passable_during_flip: bool,
) -> GameObject:
    return GameObject(
        kind=kind,
        body=Body(
            left=float(x),
            bottom=float(y),
            width=float(width),
            height=float(height),
            is_static=True,
            is_passable_during_flip=is_passable_during_flip,
        ),
        render=RenderSpec(
            placeholder_size_in_blocks=(float(width), float(height)),
            placeholder_label_text=str(kind),
        ),
    )


def build_blocks(level_definition: LevelDefinition) -> list[GameObject]:
    """schema 里的每个条目是一个 [x, y, w, h] 矩形，已是合并后的形状。"""
    blocks = [
        _make_solid(x, y, width, height, GameObjectKind.BLOCK, False)
        for x, y, width, height in level_definition.get("blocks", [])
    ]
    planks = [
        _make_solid(x, y, width, height, GameObjectKind.PLANK, True)
        for x, y, width, height in level_definition.get("planks", [])
    ]
    return blocks + planks


def build_boundaries(world: World) -> list[GameObject]:
    """地面在天花板之外：可玩带为 0 到 height_in_blocks。"""
    span = float(world.width_in_blocks)
    height = float(world.height_in_blocks)
    return [
        _make_solid(0.0, -1.0, span, 1.0, GameObjectKind.GROUND, False),
        _make_solid(0.0, height, span, 1.0, GameObjectKind.CEILING, False),
    ]
