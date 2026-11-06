"""关卡数据：里面用设计者的词汇，程序里只有 GameObject。

一个关卡是一个文件夹（放在 assets/game/levels/ 下），文件夹名就是关卡名：
    <关卡名>/scene.json        关卡数据
    <关卡名>/background.png    背景图（scene.json 里不写 background 时默认用它）
background 和各种图片的路径都相对关卡文件夹（也就是相对 scene.json）；背景图按可玩区
的高度等比缩放后横向重复，ground/ceiling 那两行不在它的覆盖范围里。

scene.json 的键：
    name, width, height      关卡名与尺寸，单位格
    flip_area_offsets        [向上翻带高度, 向下翻带高度]，见 controller.flip_rule
    blocks, planks           方块与木板
    movable_blocks           可移动方块：offset 是目标点相对支点的偏移，sources 引用按钮名
    buttons                  按钮：pos/size 是按钮本身（底边中点），face 是朝向，name 供可移动方块引用
    portals                  传送门：pos/size 是门本身（底边中点），face 是出来的朝向，target 引用另一个门
    items                    道具：heavy 表示变重
    nozzles                  喷口：face 是风区伸出的方向，power 是目标沿朝向离底面多远（不给负的），
                             size 是风区宽高（老数据写的 range 只给长度，宽度按 1 算）
    textures                 贴图：浮点矩形 + image（相对 scene.json 的路径）
    player                   起点；跳高、速度和动画默认来自 game.json，这里写了就覆盖
    destination              终点
    background               背景图，相对 scene.json 的路径；不写就用文件夹里的 background.png

有矩形的对象都写成 {"pos": [x, y], "size": [w, h]}：pos 是左下角，size 缺省 1×1
（传送门缺省 1×0.3），单位格，都是浮点。按钮、传送门和喷口另有一套写法：pos 是
「底面」的中点、size 是没转过的宽高，face（up/right/down/left）决定从底面往哪边
长出去，左右朝向时屏幕上的宽高是对调的。
玩家参数一般写在 game.json 的 player 里（jump_height 格、move_speed 格/秒、
animation 动作名 → 图片路径，动作名不预设；动画系统还没接，先读出来放着）；
scene.json 的 player 里写同名键就是这一关的覆盖值，它的图片路径相对关卡文件夹，
game.json 里写的相对游戏根。
"""

import json
from pathlib import Path

from controller.controller import Controller
from controller.flip_rule import FLIP_AREA_OFFSETS_DEFAULT
from controller.input_source import InputSource
from controller.trigger_source import TriggerSource
from core.game_object import GameObject, GameObjectKind
from nozzle.nozzle import Nozzle
from item.item import Item
from physics.body import Body
from portal.portal import Portal
from renderer.palette import color_for_kind
from renderer.render_spec import PlaceholderFace, PlaceholderShape, RenderSpec
from world.world import HEIGHT_IN_BLOCKS, WIDTH_IN_BLOCKS, World

LevelDefinition = dict[str, object]

DEFAULT_SIZE = (1.0, 1.0)
PORTAL_SIZE = (1.0, 0.3)   # 传送门画出来的那块门：1 格宽、0.3 格高
# 按钮画出来就是它的触发区（和传送门一样）：缺省 1 格宽、0.3 格高
BUTTON_SIZE = (1.0, 0.3)
PLAYER_SIZE = (0.8, 1.0)   # 玩家比一格窄，过缝与贴墙时更宽容
NOZZLE_DEFAULT_RANGE = 5   # 老数据没写 range 时的风区长度（新数据写 size）
NOZZLE_DEFAULT_POWER = 7   # 喷口没写 power 时的目标偏移
NOZZLE_DEFAULT_SIZE = (1.0, 5.0)   # 风区缺省尺寸：宽 1 格、长 5 格
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


def player_settings(level_definition: LevelDefinition) -> dict:
    """关卡自己的 player 条目：位置，外加可以覆盖游戏默认的跳高、速度、动画。"""
    entry = level_definition.get("player")
    return entry if isinstance(entry, dict) else {}


def _player_value(
    level_definition: LevelDefinition,
    game_player: dict | None,
    key: str,
    default,
    cast,
):
    """玩家的某一项：关卡 player 覆盖 → game.json 的 player → 内置默认，写坏了往下退。"""
    for source in (player_settings(level_definition), game_player or {}):
        if key in source:
            try:
                return cast(source[key])
            except (TypeError, ValueError):
                continue
    return default


def jump_height_of(level_definition: LevelDefinition, game_player: dict | None = None) -> int:
    """玩家初始跳高（格）：再按关卡高度夹一下，矮关卡里一蹦不会穿过天花板。"""
    value = _player_value(
        level_definition, game_player, "jump_height", InputSource.JUMP_HEIGHT_DEFAULT, int
    )
    level_height = int(level_definition.get("height", HEIGHT_IN_BLOCKS))
    return max(InputSource.JUMP_HEIGHT_MIN, min(value, level_height - 1))


def move_speed_of(level_definition: LevelDefinition, game_player: dict | None = None) -> float:
    """玩家水平移动速度（方块/秒）：关卡覆盖 → game.json → 默认值，不给负的。"""
    value = _player_value(
        level_definition, game_player, "move_speed", InputSource.MOVE_SPEED_DEFAULT, float
    )
    return max(0.0, value)


def animation_of(
    level_definition: LevelDefinition,
    game_player: dict | None = None,
    base_dir: str | Path | None = None,
    game_base_dir: str | Path | None = None,
) -> dict:
    """玩家动画：动作名 → 图的绝对路径（动画系统还没接，先读出来放着）。

    用哪一份就看它写在哪：关卡 player 里的相对关卡文件夹解析，game.json 里的相对
    游戏根解析；找不到的图直接跳过。
    """
    for source, base in (
        (player_settings(level_definition), base_dir),
        (game_player or {}, game_base_dir),
    ):
        value = source.get("animation")
        if not isinstance(value, dict):
            continue
        animation = {}
        for action, path in value.items():
            found = resolve_texture(path, base)
            if found is not None:
                animation[str(action)] = found
        return animation
    return {}


def flip_area_offsets_of(level_definition: LevelDefinition) -> tuple[float, float]:
    """翻转带的两个高度：第一个贴着关卡顶（向上翻），第二个贴着关卡底（向下翻）。

    没写、写坏了或写成负数都退回默认值，负数按 0 算（等于这一侧翻不了）。
    """
    value = level_definition.get("flip_area_offsets", FLIP_AREA_OFFSETS_DEFAULT)
    try:
        up_offset, down_offset = value
        return (max(0.0, float(up_offset)), max(0.0, float(down_offset)))
    except (TypeError, ValueError):
        return FLIP_AREA_OFFSETS_DEFAULT


def _read_size(entry: dict, default: tuple[float, float] = DEFAULT_SIZE) -> tuple[float, float]:
    width, height = entry.get("size", default)
    return float(width), float(height)


def facing_rect(entry: dict, default_size) -> tuple[float, float, float, float]:
    """按钮、传送门和喷口风区的矩形：pos 是「底面」的中点，矩形从底面朝 face 指的方向长出去。

    up：底面是下边、往上长；down：底面是上边、往下长；
    right：底面是左边、往右长；left：底面是右边、往左长。
    左右朝向时把宽高对调（竖起来），pos 就落在侧面那条边的中点上。
    """
    x, y = _read_position(entry)
    width, height = _read_size(entry, default_size)
    face = str(entry.get("face", PlaceholderFace.UP))
    if face == "right":
        return x, y - width / 2.0, height, width
    if face == "left":
        return x - height, y - width / 2.0, height, width
    if face == "down":
        return x - width / 2.0, y - height, width, height
    return x - width / 2.0, y, width, height


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
    default_size: tuple[float, float] = DEFAULT_SIZE,
    facing: bool = False,
) -> GameObject:
    if facing:
        # 按钮和传送门：pos 是底边中点，宽高按朝向摆正
        left, bottom, width, height = facing_rect(entry, default_size)
    else:
        left, bottom = _read_position(entry)
        width, height = _read_size(entry, default_size)
    return GameObject(
        kind=kind,
        name=str(entry.get("name", "")),
        body=Body(
            left=left,
            bottom=bottom,
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


def _nozzle_size(entry: dict) -> tuple[float, float]:
    """喷口风区的宽高：新数据写 size，老数据写 range（只有长度，宽度按 1 算）。"""
    value = entry.get("size")
    if value is not None:
        try:
            width, height = value
            return float(width), float(height)
        except (TypeError, ValueError):
            pass
    try:
        return 1.0, float(entry.get("range", NOZZLE_DEFAULT_RANGE))
    except (TypeError, ValueError):
        return 1.0, float(NOZZLE_DEFAULT_RANGE)


def build_nozzles(level_definition: LevelDefinition) -> list[GameObject]:
    """喷口：pos 是风区底面中点，face 是伸出的方向，power 是目标离它多远（不给负的）。"""
    nozzles = []
    for entry in level_definition.get("nozzles", []):
        normalized = dict(entry)
        normalized["size"] = list(_nozzle_size(entry))
        power = max(0.0, float(entry.get("power", NOZZLE_DEFAULT_POWER)))
        face = _read_face(entry)
        x, y = _read_position(entry)
        left, bottom, width, height = facing_rect(normalized, NOZZLE_DEFAULT_SIZE)
        vertical = str(face) in (str(PlaceholderFace.UP), str(PlaceholderFace.DOWN))
        nozzles.append(
            GameObject(
                kind=GameObjectKind.NOZZLE,
                name=str(entry.get("name", "")),
                body=Body(
                    left=left,              # 风区从底面中点朝 face 长出去
                    bottom=bottom,
                    width=width,
                    height=height,
                    is_static=True,
                    is_sensor=True,
                ),
                render=RenderSpec(
                    # 上下朝向画三角，左右朝向画棱台：都是「窄端指向吹风方向」的标记
                    placeholder_shape=(
                        PlaceholderShape.TRIANGLE
                        if vertical
                        else PlaceholderShape.FRUSTUM
                    ),
                    placeholder_size_in_blocks=(1.0, 1.0),
                    placeholder_color=color_for_kind(GameObjectKind.NOZZLE),
                    placeholder_label_text=str(GameObjectKind.NOZZLE),
                    placeholder_direction=1 if str(face) == str(PlaceholderFace.UP) else -1,
                    placeholder_face=face,
                    placeholder_has_axis=vertical,
                ),
                nozzle=Nozzle(face=str(face), power=power, origin=(x, y)),
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
    """按钮画出来的那块矩形就是它的触发区（和传送门一样），缺省 1×0.3 格。"""
    buttons = []
    for entry in level_definition.get("buttons", []):
        game_object = _make(
            entry,
            GameObjectKind.BUTTON,
            is_static=True,
            is_sensor=True,
            default_size=BUTTON_SIZE,
            facing=True,
        )
        game_object.render.placeholder_shape = PlaceholderShape.FRUSTUM
        game_object.render.placeholder_face = _read_face(entry)
        buttons.append(game_object)
    return buttons


def build_portals(level_definition: LevelDefinition) -> list[GameObject]:
    """传送门：pos/size 是画出来的那块门，range 是触发区（以门为中心），target 是目标门的名字。"""
    portals = []
    for entry in level_definition.get("portals", []):
        game_object = _make(
            entry,
            GameObjectKind.PORTAL,
            is_static=True,
            is_sensor=True,
            default_size=PORTAL_SIZE,
            facing=True,
        )
        game_object.portal = Portal(
            target=str(entry.get("target", "")),
            face=str(entry.get("face", PlaceholderFace.UP)),
        )
        portals.append(game_object)
    return portals


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
