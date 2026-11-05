"""关卡数据：里面用设计者的词汇，程序里只有 GameObject。

每个条目都是 {"pos": [x, y], "size": [w, h]}，size 缺省为 1×1。
按钮与可移动方块用 name 互相引用。

一个关卡是一个文件夹，文件夹名就是关卡名：
    <关卡名>/scene.json        关卡数据
    <关卡名>/background.png    背景图（scene.json 里不写 background 时默认用它）
background 如果写了，路径相对关卡文件夹；图片按可玩区的高度等比缩放后横向重复，
ground/ceiling 那两行不在它的覆盖范围里。
"""

import json
from pathlib import Path

from controller.controller import Controller
from controller.input_source import InputSource
from controller.trigger_source import TriggerSource
from core.game_object import GameObject, GameObjectKind
from nozzle.nozzle import Nozzle
from item.item import Item
from physics.body import Body
from renderer.palette import color_for_kind
from renderer.render_spec import PlaceholderFace, PlaceholderShape, RenderSpec
from world.world import HEIGHT_IN_BLOCKS, WIDTH_IN_BLOCKS, World

LevelDefinition = dict[str, object]

DEFAULT_SIZE = (1.0, 1.0)
PLAYER_SIZE = (0.8, 1.0)   # 玩家比一格窄，过缝与贴墙时更宽容
NOZZLE_DEFAULT_RANGE = 5   # 喷口没写 range 时的风区长度
NOZZLE_DEFAULT_POWER = 7   # 喷口没写 power 时的目标偏移
BACKGROUND_NAME = "background.png"  # 关卡文件夹里背景图的固定名字


def load_level_file(path: str) -> LevelDefinition:
    """读取关卡文件。"""
    with open(path, encoding="utf-8") as file:
        return json.load(file)


def build_world(level_definition: LevelDefinition, base_dir: str | Path | None = None) -> World:
    """重力不出现在关卡数据里，用全局常量。"""
    return World(
        width_in_blocks=int(level_definition.get("width", WIDTH_IN_BLOCKS)),
        height_in_blocks=int(level_definition.get("height", HEIGHT_IN_BLOCKS)),
        background_path=resolve_background(level_definition.get("background"), base_dir),
    )


def resolve_background(value, base_dir: str | Path | None) -> str | None:
    """背景图：相对关卡文件夹解析；scene.json 没写就退回文件夹里的 background.png。"""
    base = Path(base_dir) if base_dir is not None else None
    candidates: list[Path] = []
    if value:
        path = Path(str(value))
        candidates.append(path if path.is_absolute() or base is None else base / path)
    if base is not None:
        candidates.append(base / BACKGROUND_NAME)
    for candidate in candidates:
        candidate = candidate.resolve()     # 把 ../ 这类写法归一化，日志里好读
        if candidate.is_file():
            return str(candidate)
    return None


def resolve_texture(value, base_dir: str | Path | None) -> str | None:
    """贴图路径：相对关卡文件夹；没有兜底，scene.json 不写就是没图。"""
    if not value:
        return None
    path = Path(str(value))
    if not path.is_absolute() and base_dir is not None:
        path = Path(base_dir) / path
    return str(path) if path.is_file() else None


def _read_position(entry: dict) -> tuple[float, float]:
    x, y = entry["pos"]
    return float(x), float(y)


def jump_height_of(level_definition: LevelDefinition) -> int:
    """关卡指定的初始跳高，缺省用跳速表默认档。"""
    return int(level_definition.get("jump_height", InputSource.JUMP_LADDER[InputSource.JUMP_LADDER_INDEX_DEFAULT][0]))


def _read_size(entry: dict) -> tuple[float, float]:
    width, height = entry.get("size", DEFAULT_SIZE)
    return float(width), float(height)


def _read_face(entry: dict) -> PlaceholderFace:
    """按钮朝向，缺省或非法时按向上处理。"""
    try:
        return PlaceholderFace(str(entry.get("face", PlaceholderFace.UP)))
    except ValueError:
        return PlaceholderFace.UP


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
        name=str(entry.get("name", "")),
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


def build_textures(
    level_definition: LevelDefinition, base_dir: str | Path | None = None
) -> list[GameObject]:
    """贴图：整张美术图盖在方块上。位置和尺寸都是浮点世界单位，不吸格子。

    只认 schema 里列出来的条目，不自动扫描 textures/ 目录。
    """
    textures = []
    for entry in level_definition.get("textures", []):
        x, y = _read_position(entry)
        width, height = _read_size(entry)
        textures.append(
            GameObject(
                kind=GameObjectKind.TEXTURE,
                name=str(entry.get("name", "")),
                body=Body(
                    left=x,
                    bottom=y,
                    width=width,
                    height=height,
                    is_static=True,
                    is_sensor=True,   # 只显示：不挡路、不被积分
                ),
                render=RenderSpec(
                    placeholder_size_in_blocks=(width, height),
                    placeholder_color=color_for_kind(GameObjectKind.TEXTURE),
                    placeholder_label_text=str(GameObjectKind.TEXTURE),
                    texture_path=resolve_texture(entry.get("image"), base_dir),
                    texture_smooth=bool(entry.get("smooth", False)),
                ),
            )
        )
    return textures


def build_boundaries(world: World) -> list[GameObject]:
    """地面在天花板之外：可玩带为 0 到 height_in_blocks。"""
    span = float(world.width_in_blocks)
    height = float(world.height_in_blocks)
    return [
        _make({"pos": [0.0, -1.0], "size": [span, 1.0]}, GameObjectKind.GROUND, is_static=True),
        _make({"pos": [0.0, height], "size": [span, 1.0]}, GameObjectKind.CEILING, is_static=True),
        _make({"pos": [-1.0, -1.0], "size": [1.0, height + 2.0]}, GameObjectKind.WALL, is_static=True),
        _make({"pos": [span, -1.0], "size": [1.0, height + 2.0]}, GameObjectKind.WALL, is_static=True),
    ]


def build_player(level_definition: LevelDefinition) -> list[GameObject]:
    """玩家比一格窄，关卡可用 size 覆盖。"""
    entry = level_definition.get("player")
    if entry is None:
        return []
    entry = dict(entry)
    entry.setdefault("size", list(PLAYER_SIZE))
    return [_make(entry, GameObjectKind.PLAYER, controller=Controller(source=InputSource()))]


def build_destination(level_definition: LevelDefinition) -> list[GameObject]:
    entry = level_definition.get("destination")
    if entry is None:
        return []
    return [_make(entry, GameObjectKind.DESTINATION, is_static=True, is_sensor=True)]


def build_nozzles(level_definition: LevelDefinition) -> list[GameObject]:
    """喷口的 pos 是三角形底边中点；range 是风区长度，power 是目标偏移。"""
    nozzles = []
    for entry in level_definition.get("nozzles", []):
        power = int(entry.get("power", NOZZLE_DEFAULT_POWER))
        length = int(entry.get("range", NOZZLE_DEFAULT_RANGE))
        x, y = _read_position(entry)
        bottom = y if power >= 0 else y - length
        nozzles.append(
            GameObject(
                kind=GameObjectKind.NOZZLE,
                name=str(entry.get("name", "")),
                body=Body(
                    left=x - 0.5,          # 底边中点落在 x 上，风区横跨 x±0.5
                    bottom=float(bottom),
                    width=1.0,
                    height=float(length),
                    is_static=True,
                    is_sensor=True,
                ),
                render=RenderSpec(
                    placeholder_shape=PlaceholderShape.TRIANGLE,
                    placeholder_size_in_blocks=(1.0, 1.0),
                    placeholder_color=color_for_kind(GameObjectKind.NOZZLE),
                    placeholder_label_text=str(GameObjectKind.NOZZLE),
                    placeholder_direction=1 if power >= 0 else -1,
                    placeholder_has_axis=True,
                ),
                nozzle=Nozzle(power=power, length=length, origin_y=y),
            )
        )
    return nozzles


def build_items(level_definition: LevelDefinition) -> list[GameObject]:
    items = []
    for entry in level_definition.get("items", []):
        game_object = _make(entry, GameObjectKind.ITEM, is_static=True, is_sensor=True)
        game_object.render.placeholder_shape = PlaceholderShape.PENTAGON
        game_object.item = Item(heavy=bool(entry.get("heavy", False)))
        items.append(game_object)
    return items


def build_buttons(level_definition: LevelDefinition) -> list[GameObject]:
    buttons = []
    for entry in level_definition.get("buttons", []):
        game_object = _make(entry, GameObjectKind.BUTTON, is_static=True, is_sensor=True)
        game_object.render.placeholder_shape = PlaceholderShape.FRUSTUM
        game_object.render.placeholder_face = _read_face(entry)
        buttons.append(game_object)
    return buttons


def build_movable_blocks(level_definition: LevelDefinition, triggers_by_name: dict) -> list[GameObject]:
    movable_blocks = []
    for entry in level_definition.get("movable_blocks", []):
        triggers = [
            triggers_by_name[name]
            for name in entry.get("sources", [])
            if name in triggers_by_name
        ]
        source = TriggerSource(
            triggers=triggers,
            offset=entry.get("offset", [0, 0]),
            once=bool(entry.get("once", False)),
        )
        movable_blocks.append(
            _make(
                entry,
                GameObjectKind.MOVABLE_BLOCK,
                is_static=True,
                controller=Controller(source=source),
            )
        )
    return movable_blocks
