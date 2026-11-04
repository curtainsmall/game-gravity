"""关卡数据：schema 用设计者的词汇（方块），程序里只有 GameObject。"""

import json

from core.game_object import GameObject
from physics.body import Body
from renderer.render_spec import RenderSpec
from world.world import HEIGHT_IN_BLOCKS, WIDTH_IN_BLOCKS, World

BLOCK_LABEL = "block"
GROUND_LABEL = "ground"
CEILING_LABEL = "ceiling"


def load_level_file(path: str) -> dict:
    """读取关卡文件。"""
    with open(path, encoding="utf-8") as file:
        return json.load(file)


def build_world(level_definition: dict) -> World:
    return World(
        gravity_acceleration_magnitude=float(level_definition.get("gravity", 0.0)),
        width_in_blocks=int(level_definition.get("width", WIDTH_IN_BLOCKS)),
        height_in_blocks=int(level_definition.get("height", HEIGHT_IN_BLOCKS)),
    )


def build_blocks(level_definition: dict) -> list:
    """schema 里的每个方块是一个 [x, y, w, h] 矩形，已是合并后的形状。"""
    blocks = []
    for x, y, width, height in level_definition.get("blocks", []):
        blocks.append(
            GameObject(
                kind=BLOCK_LABEL,
                body=Body(
                    left=float(x),
                    bottom=float(y),
                    width=float(width),
                    height=float(height),
                    is_static=True,
                ),
                render=RenderSpec(
                    placeholder_size_in_blocks=(float(width), float(height)),
                    placeholder_label_text=BLOCK_LABEL,
                ),
            )
        )
    return blocks


def build_boundaries(world: World) -> list:
    """地面在天花板之外：可玩带为 0 到 height_in_blocks。"""
    span = float(world.width_in_blocks)
    height = float(world.height_in_blocks)
    return [
        GameObject(
            kind=GROUND_LABEL,
            body=Body(left=0.0, bottom=-1.0, width=span, height=1.0, is_static=True),
            render=RenderSpec(placeholder_size_in_blocks=(span, 1.0), placeholder_label_text=GROUND_LABEL),
        ),
        GameObject(
            kind=CEILING_LABEL,
            body=Body(left=0.0, bottom=height, width=span, height=1.0, is_static=True),
            render=RenderSpec(placeholder_size_in_blocks=(span, 1.0), placeholder_label_text=CEILING_LABEL),
        ),
    ]
