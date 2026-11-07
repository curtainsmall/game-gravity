"""关卡数据：里面用设计者的词汇，程序里只有 GameObject。

一个关卡是 assets/game/levels/ 下的一个 <关卡名>.json，文件名就是关卡名。
game.json 和关卡 json 里写的相对路径，一律相对 game.json 所在的文件夹（游戏根）；
图片放哪儿都行，只要相对路径写得出来，游戏不要求有 textures/ 这样的目录。
背景图按可玩区的高度等比缩放后横向重复，ground/ceiling 那两行不在它的覆盖范围里。

关卡 json 的键：
    name, width, height      关卡名与尺寸，单位格
    flip_area_offsets        [向上翻带高度, 向下翻带高度]，见 controller.flip_rule
    blocks, planks           方块与木板
    movable_blocks           可移动方块：offset 是目标点相对支点的偏移，triggers 是触发行为卡片
                             （来源是触发源的名字，行为名 move = 沿 offset 走，mode 是 once / hold / switch：一次、按住、切换；
                             老的 sources 只写来源名，老的 once 写在卡片或方块上，真 = once，假 = hold）
    trigger_sources          触发源：整块 pos/size 矩形就是触发区，name 供触发卡片引用；
                             mode 是 hold / once（压着才算 / 第一次压到后一直算），
                             jump_offset 是按下期间跳高的变化量（格，正数跳更高、负数跳更低、
                             0 只是开关）；老数据的 buttons / items 会并进这里：
                             按钮按实际矩形换算成 hold + 0，道具的 persist 变成 hold
    portals                  传送门：pos/size 是门本身（底边中点），face 是出来的朝向，target 引用另一个门
    items                    老数据：道具，读进来并进 trigger_sources（persist 变成 hold，
                             缺省 once 照旧），jump_offset 是按下期间跳高的变化量（格，
                             正数跳更高、负数跳更低、0 不变；heavy=true 当成 -1）；
                             名字照样能当触发卡片的来源
    nozzles                  喷口：face 是风区伸出的方向，power 是目标沿朝向离底面多远（不给负的；
                             编辑器保证它至少比风区沿朝向的长度多 0.5 格，目标点落在风区外），
                             size 是风区宽高（老数据写的 range 只给长度，宽度按 1 算）
    textures                 贴图：浮点矩形 + image（相对 game.json 的路径）；
                             face 是朝向（up/right/down/left，顺时针转，缺省 up），
                             flip 水平镜像；follow 写可移动方块的名字，这张图就跟着它一起动；
                             hide 表示初始隐藏，triggers 的 hide / show 由触发源切换显示
                             （卡片同样带 mode：一次 / 按住 / 切换）
    animation_objects        动画对象：和贴图一样只显示、不碰撞，pos/size 是自己的；
                             follow 写对象名字（或 "@player"）就跟着它平移；
                             preset 是 general（links.general.clip 一条剪辑，播一遍）或
                             player（links.player.<动作>.<left/right> 指向动画库的键），
                             动作是 idle/run/takeoff/raise/fall/landing，来自玩家的
                             物理状态，空着的一侧用另一侧镜像；循环由动作决定
                             （idle/run/raise/fall 循环，takeoff/landing 一次）；
                             帧来自 game.json 的 animation_library
    player                   起点；跳高和速度默认来自 game.json，这里写了就覆盖。
                             玩家自己不再有动画，显示用动画对象（跟随玩家、预设 player）
    destination              终点
    background               背景图，相对 game.json 的路径；不写就退回游戏根里的 background.png
    sound                    这一关的音乐：bgm（相对 game.json 的路径）、loop、fade_in、fade_out

有矩形的对象都写成 {"pos": [x, y], "size": [w, h]}：pos 是左下角，size 缺省 1×1
（传送门缺省 1×0.3），单位格，都是浮点。传送门和喷口另有一套写法：pos 是
「底面」的中点、size 是没转过的宽高，face（up/right/down/left）决定从底面往哪边
长出去，左右朝向时屏幕上的宽高是对调的。
玩家参数一般写在 game.json 的 player 里（jump_height 格、可以是小数，move_speed 格/秒）；
关卡 json 的 player 里写同名键就是这一关的覆盖值。
图片路径都相对游戏根。
"""

import json
from pathlib import Path

from animation.sprite import PRESET_GENERAL, AnimationSprite
from controller.controller import Controller
from controller.flip_rule import FLIP_AREA_OFFSETS_DEFAULT
from controller.input_source import InputSource
from core.game_object import GameObject, GameObjectKind
from nozzle.nozzle import Nozzle
from physics.body import Body
from portal.portal import Portal
from renderer.palette import color_for_kind
from renderer.render_spec import PlaceholderFace, PlaceholderShape, RenderSpec
from sound.objects import SoundSprite
from trigger.trigger import (
    MODE_HOLD,
    MODE_ONCE,
    TriggerBehavior,
    TriggerSheet,
    normalize_mode,
)
from trigger_source.trigger_source import (
    MODE_HOLD as SOURCE_HOLD,
    MODE_ONCE as SOURCE_ONCE,
    TriggerSource,
)
from world.world import HEIGHT_IN_BLOCKS, WIDTH_IN_BLOCKS, World

LevelDefinition = dict[str, object]

DEFAULT_SIZE = (1.0, 1.0)
PORTAL_SIZE = (1.0, 0.3)   # 传送门画出来的那块门：1 格宽、0.3 格高
# 老数据里的按钮是 1 格宽、0.3 格的棱台：读进来按它的实际矩形并进触发源
LEGACY_BUTTON_SIZE = (1.0, 0.3)
PLAYER_SIZE = (0.8, 1.0)   # 玩家比一格窄，过缝与贴墙时更宽容
NOZZLE_DEFAULT_RANGE = 5   # 老数据没写 range 时的风区长度（新数据写 size）
NOZZLE_DEFAULT_POWER = 7   # 喷口没写 power 时的目标偏移
NOZZLE_DEFAULT_SIZE = (1.0, 5.0)   # 风区缺省尺寸：宽 1 格、长 5 格
BACKGROUND_NAME = "background.png"  # 没写 background 时在游戏根里找它兜底


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
    """背景图：相对 game.json 解析；关卡 json 没写就退回游戏根里的 background.png。"""
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
    """贴图路径：相对 game.json；没有兜底，关卡 json 不写就是没图。"""
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


def jump_height_of(level_definition: LevelDefinition, game_player: dict | None = None) -> float:
    """玩家初始跳高（格，可以是小数）：再按关卡高度夹一下，矮关卡里一蹦不会穿过天花板。"""
    value = _player_value(
        level_definition, game_player, "jump_height", InputSource.JUMP_HEIGHT_DEFAULT, float
    )
    level_height = int(level_definition.get("height", HEIGHT_IN_BLOCKS))
    return max(float(InputSource.JUMP_HEIGHT_MIN), min(value, level_height - 1.0))


def move_speed_of(level_definition: LevelDefinition, game_player: dict | None = None) -> float:
    """玩家水平移动速度（方块/秒）：关卡覆盖 → game.json → 默认值，不给负的。"""
    value = _player_value(
        level_definition, game_player, "move_speed", InputSource.MOVE_SPEED_DEFAULT, float
    )
    return max(0.0, value)


def build_animation_objects(level_definition: LevelDefinition) -> list[GameObject]:
    """动画对象：只显示、不碰撞，和贴图同级。

    条目写 pos / size / follow / preset / links；预设和链接由 animation.sprite 解释，
    帧来自 game.json 的动画库。follow 写名字就跟着那个对象走，写 "@player" 跟玩家。
    位置尺寸是它自己的，跟随只平移。
    """
    sprites = []
    for entry in level_definition.get("animation_objects", []):
        if not isinstance(entry, dict):
            continue
        game_object = _make(
            entry, GameObjectKind.ANIMATION, is_static=True, is_sensor=True
        )
        game_object.follow = str(entry.get("follow") or "").strip()
        game_object.sprite = AnimationSprite(
            str(entry.get("preset") or PRESET_GENERAL), entry.get("links")
        )
        sprites.append(game_object)
    return sprites


def build_sound_objects(level_definition: LevelDefinition) -> list[GameObject]:
    """声音对象：只出声、不画不碰撞，和动画对象同级。

    条目写 preset / follow / links；预设和链接由 sound.objects 解释，声音来自 game.json 的
    声音库。声音对象不参与物理，所以没有位置、大小和 body，也不进关卡对象列表。
    """
    sprites = []
    for entry in level_definition.get("sound_objects", []):
        if not isinstance(entry, dict):
            continue
        game_object = GameObject(
            kind=GameObjectKind.SOUND, follow=str(entry.get("follow") or "")
        )
        game_object.sound = SoundSprite(
            str(entry.get("preset") or "general"), entry.get("links")
        )
        sprites.append(game_object)
    return sprites


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
    """传送门和喷口风区的矩形：pos 是「底面」的中点，矩形从底面朝 face 指的方向长出去。

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
    """朝向（老按钮、传送门和喷口用），缺省或非法时按向上处理。"""
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
    triggers: TriggerSheet | None = None,
    default_size: tuple[float, float] = DEFAULT_SIZE,
    facing: bool = False,
) -> GameObject:
    if facing:
        # 传送门（和老的按钮）：pos 是底边中点，宽高按朝向摆正
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
        triggers=triggers,
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

    face 是图自己的朝向（顺时针转 90° 一档，缺省 up），flip 是转完再水平镜像；
    follow 写了可移动方块的名字，加载后这张图就跟着那个方块走（见 world.follower）；
    hide 是初始隐藏，triggers 卡片里的 hide / show 由触发源切换显示。
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
                follow=str(entry.get("follow") or "").strip(),
                triggers=_trigger_sheet(entry),
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
                    texture_face=_texture_face(entry),
                    texture_flip=bool(entry.get("flip", False)),
                    hidden=bool(entry.get("hide", False)),
                ),
            )
        )
    return textures


def _trigger_sheet(entry: dict) -> TriggerSheet | None:
    """条目里的 triggers 卡片 → TriggerSheet；老数据写在 sources 里的当成 move 卡片。

    卡片没有来源的跳过；一张有效卡片都没有就返回 None（这个对象不接触发器）。
    模式读卡片的 mode；老数据把「仅触发一次」写成 once（卡片上的优先，否则用方块自己的），
    真 = once，假 = hold。
    """
    block_once = bool(entry.get("once", False))
    behaviors = []
    cards = entry.get("triggers")
    if isinstance(cards, list):
        for card in cards:
            if not isinstance(card, dict):
                continue
            source = str(card.get("source") or "").strip()
            if not source:
                continue
            behaviors.append(
                TriggerBehavior(
                    source,
                    str(card.get("behavior") or "").strip(),
                    _trigger_mode(card, block_once),
                )
            )
    elif isinstance(entry.get("sources"), list):
        behaviors = [
            TriggerBehavior(str(name), "move", MODE_ONCE if block_once else MODE_HOLD)
            for name in entry["sources"]
            if name
        ]
    return TriggerSheet(behaviors) if behaviors else None


def _trigger_mode(card: dict, block_once: bool) -> str:
    """卡片的模式：新数据写 mode，老数据的 once 真就是一次、假就是按住。"""
    if "mode" in card:
        return normalize_mode(card.get("mode"))
    return MODE_ONCE if bool(card.get("once", block_once)) else MODE_HOLD


def _texture_face(entry: dict) -> str:
    """贴图朝向：缺省或写坏了都按向上，顺时针一档 90°（up/right/down/left）。"""
    face = str(entry.get("face", "up"))
    return face if face in ("up", "right", "down", "left") else "up"


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
                    # 风区就是触发区：和其他机关一样画成实心矩形
                    placeholder_size_in_blocks=(width, height),
                    placeholder_color=color_for_kind(GameObjectKind.NOZZLE),
                    placeholder_label_text=str(GameObjectKind.NOZZLE),
                ),
                nozzle=Nozzle(face=str(face), power=power, origin=(x, y)),
            )
        )
    return nozzles


def build_trigger_sources(level_definition: LevelDefinition) -> list[GameObject]:
    """触发源：矩形就是触发区，玩家压上去算按下。

    新数据写在 trigger_sources 里：{name, pos, size, mode, jump_offset}。
    老数据里的 buttons（棱台，pos 是底面中点）和 items（道具）在这里并进来：
    按钮按它的实际矩形换算成 hold + jump_offset 0，道具的 persist 换成 hold。
    """
    sources = []
    for entry in level_definition.get("trigger_sources", []):
        if isinstance(entry, dict):
            sources.append(
                _make_trigger_source(
                    entry,
                    str(entry.get("mode") or SOURCE_HOLD),
                    _jump_offset(entry),
                )
            )
    for entry in level_definition.get("buttons", []):
        if not isinstance(entry, dict):
            continue
        left, bottom, width, height = facing_rect(entry, LEGACY_BUTTON_SIZE)
        sources.append(
            _make_trigger_source(
                {
                    "name": str(entry.get("name") or ""),
                    "pos": [left, bottom],
                    "size": [width, height],
                },
                SOURCE_HOLD,
                0.0,
            )
        )
    for entry in level_definition.get("items", []):
        if not isinstance(entry, dict):
            continue
        legacy_mode = str(entry.get("mode") or "once")
        sources.append(
            _make_trigger_source(
                entry,
                SOURCE_ONCE if legacy_mode == "once" else SOURCE_HOLD,
                _jump_offset(entry),
            )
        )
    return sources


def _make_trigger_source(
    entry: dict, mode: str, jump_offset: float
) -> GameObject:
    game_object = _make(
        entry, GameObjectKind.TRIGGER_SOURCE, is_static=True, is_sensor=True
    )
    game_object.trigger_source = TriggerSource(mode=mode, jump_offset=jump_offset)
    return game_object


def _jump_offset(entry: dict) -> float:
    """跳高变化量：新数据写 jump_offset；老道具的 heavy=true 当成 -1 格。"""
    if "jump_offset" in entry:
        try:
            return float(entry.get("jump_offset"))
        except (TypeError, ValueError):
            return 0.0
    return -1.0 if bool(entry.get("heavy", False)) else 0.0


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


def build_movable_blocks(level_definition: LevelDefinition) -> list[GameObject]:
    """可移动方块：offset 是它自己的属性，triggers 卡片决定谁把它叫走、要不要保持。"""
    movable_blocks = []
    for entry in level_definition.get("movable_blocks", []):
        controller = Controller(offset=entry.get("offset", [0, 0]))
        movable_blocks.append(
            _make(
                entry,
                GameObjectKind.MOVABLE_BLOCK,
                is_static=True,
                controller=controller,
                triggers=_trigger_sheet(entry),
            )
        )
    return movable_blocks
