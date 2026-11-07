"""关卡数据模型。

键和形状与游戏端一一对应，细节见 game/world/level.py 的模块说明；这里只额外记着
编辑器自己关心的事：玩家的跳高、速度属于整个游戏（game.json，见 core.game），
不归 Level 管；关卡 json 的 player 里如果还留着这几个键，原样保留当这一关的覆盖值。
动画库在 game.json 里；关卡自己的动画对象（animation_objects）归 Level 管。
关卡名就是文件名（levels/<名字>.json），json 里不再写 name。
这一关的背景音乐（sound）跟着关卡文件走，归 Level 管；标题和制作名单的音乐在 game.json 的
sounds 里，由「游戏配置」的声音页改（见 core.sound）。
"""

import copy
import json

from core import animation, sound
from core.constants import (
    COLS,
    FLIP_AREA_OFFSETS_DEFAULT,
    JUMP_HEIGHT_DEFAULT,
    JUMP_HEIGHT_MIN,
    LEGACY_BUTTON_SIZE,
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
    TRIGGER_DEFAULT_MODE,
    TRIGGER_MODE_VALUES,
    TRIGGER_SOURCE_MODE_DEFAULT,
    TRIGGER_SOURCE_MODE_VALUES,
)
from core.helpers import clamp_float, clamp_int, facing_rect
from core.cutscene import new_state as new_cutscene_state, to_object as cutscene_to_object
from core.sound import fields_of as sound_fields_of, to_object as sound_to_object

# 编辑器认识的顶层键；不认识的（老字段、手写的东西）原样留在 extra 里，保存时一起写回去
LEVEL_KEYS = {
    "width",
    "height",
    "flip_area_offsets",
    "background",
    "sound",
    "cutscene",
    "destination",
    "blocks",
    "planks",
    "movable_blocks",
    "trigger_sources",
    # 老数据的两张表：读进来并进 trigger_sources，保存时不再写它们
    "buttons",
    "items",
    "portals",
    "nozzles",
    "textures",
    "animation_objects",
    "sound_objects",
    "player",
}


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


def _migrate_triggers(entry: dict) -> None:
    """老数据把来源写在 sources（只有 move）、「仅触发一次」写在方块自己身上。

    读的时候补出 triggers 卡片、给卡片补上 mode；老的 once / sources 原样留着——
    编辑器只写自己认识的东西，不删自己没有的键。
    """
    block_once = bool(entry.get("once", False))
    cards = entry.get("triggers")
    if not isinstance(cards, list):
        sources = entry.get("sources")
        if not isinstance(sources, list):
            return
        cards = [
            {"source": str(name), "behavior": "move"} for name in sources if name
        ]
        if not cards:
            return
        entry["triggers"] = cards
    for card in cards:
        if not isinstance(card, dict):
            continue
        if "mode" in card:
            if card["mode"] not in TRIGGER_MODE_VALUES:
                card["mode"] = TRIGGER_DEFAULT_MODE
        else:
            card["mode"] = "once" if bool(card.get("once", block_once)) else "hold"


def _trigger_source_entry(
    entry: dict, mode: str | None = None, jump_offset: float | None = None
) -> dict:
    """一条触发源：补上名字、位置尺寸、模式和跳高变化；老字段顺手清掉。"""
    entry.setdefault("name", "")
    entry.setdefault("pos", [0.0, 0.0])
    entry.setdefault("size", [1.0, 1.0])
    entry.pop("face", None)          # 触发源没有朝向：整块矩形就是触发区
    entry.pop("heavy", None)
    mode = mode or str(entry.get("mode") or TRIGGER_SOURCE_MODE_DEFAULT)
    entry["mode"] = mode if mode in TRIGGER_SOURCE_MODE_VALUES else TRIGGER_SOURCE_MODE_DEFAULT
    offset = jump_offset if jump_offset is not None else _jump_offset(entry)
    entry["jump_offset"] = float(offset)
    return entry


def _jump_offset(entry: dict) -> float:
    """跳高变化量：新数据写 jump_offset；老道具的 heavy=true 当成 -1 格。"""
    if "jump_offset" in entry:
        try:
            return float(entry.get("jump_offset"))
        except (TypeError, ValueError):
            return 0.0
    return -1.0 if bool(entry.get("heavy", False)) else 0.0


def _read_trigger_sources(definition: dict) -> list:
    """触发源：新表直接读，老数据的 buttons / items 并进来（按钮按实际矩形换算）。"""
    sources = []
    for entry in copy.deepcopy(list(definition.get("trigger_sources", []))):
        if isinstance(entry, dict):
            sources.append(_trigger_source_entry(entry))
    for entry in copy.deepcopy(list(definition.get("buttons", []))):
        if not isinstance(entry, dict):
            continue
        left, bottom, width, height = facing_rect(entry, LEGACY_BUTTON_SIZE)
        sources.append(
            _trigger_source_entry(
                {
                    "name": str(entry.get("name") or ""),
                    "pos": [left, bottom],
                    "size": [width, height],
                },
                mode="hold",
                jump_offset=0.0,
            )
        )
    for entry in copy.deepcopy(list(definition.get("items", []))):
        if not isinstance(entry, dict):
            continue
        legacy = str(entry.get("mode") or "once")
        sources.append(
            _trigger_source_entry(
                entry,
                mode="once" if legacy == "once" else "hold",
            )
        )
    return sources


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
        self.name = ""             # 关卡名 = 文件名（levels/<名字>.json）；不写进 json
        self.extra: dict = {}      # 关卡 json 里编辑器不认识的键，保存时原样写回去
        self.width = COLS          # 关卡宽度，格
        self.height = ROWS         # 关卡高度，格
        self.background = ""       # 背景图，相对游戏根的路径；空串表示没有背景
        self.sound: dict | None = None  # 这一关的音乐：{sound, loop, fade_in, fade_out}；None 表示没有
        self.cutscene: dict | None = None  # 进这一关之前的过场；None 表示没有
        self.flip_area_offsets = list(FLIP_AREA_OFFSETS_DEFAULT)  # 翻转带的高度
        self.blocks: list = []
        self.planks: list = []
        self.movable_blocks: list = []
        self.trigger_sources: list = []   # 触发源：整块矩形是触发区，模式 + 跳高变化
        self.portals: list = []
        self.nozzles: list = []
        self.textures: list = []   # 贴图：浮点世界矩形 + 图片名，不吸格子
        self.animation_objects: list = []  # 动画对象：pos/size + follow + 预设 + 链接
        self.sound_objects: list = []      # 声音对象：预设 + 跟随 + 链接（没有位置、大小和左右）
        self.player: dict | None = None
        self.destination: dict | None = None

    def to_definition(self) -> dict:
        # 编辑器不认识的键先铺进来；认识的字段后面覆盖自己那几项
        definition = copy.deepcopy(self.extra)
        definition.update(
            {
                "width": self.width,
                "height": self.height,
                "flip_area_offsets": list(self.flip_area_offsets),
                "blocks": copy.deepcopy(self.blocks),
                "planks": copy.deepcopy(self.planks),
                "movable_blocks": copy.deepcopy(self.movable_blocks),
                "trigger_sources": copy.deepcopy(self.trigger_sources),
                "portals": copy.deepcopy(self.portals),
                "nozzles": copy.deepcopy(self.nozzles),
                "textures": copy.deepcopy(self.textures),
                "animation_objects": copy.deepcopy(self.animation_objects),
                "sound_objects": copy.deepcopy(self.sound_objects),
            }
        )
        # 起点和终点都只有一份，没有就不写这个键。跳高、速度属于整个游戏，
        # 写在 game.json 里；这一关原本写过的覆盖值原样留着，不动它。
        # 起点以前那两个预览字段不再写（编辑器已经不做起点预览了）。
        if self.player is not None:
            player = copy.deepcopy(self.player)
            player.pop("preview_animation", None)
            player.pop("preview_side", None)
            definition["player"] = player
        if self.destination is not None:
            definition["destination"] = copy.deepcopy(self.destination)
        # 背景、音乐、过场这三项在编辑器里都有字段，空着也照写（空值表示没有）
        definition["background"] = self.background
        definition["sound"] = sound_to_object(
            self.sound or {}, keep_empty=True
        )
        definition["cutscene"] = (
            copy.deepcopy(self.cutscene)
            if self.cutscene
            else cutscene_to_object(new_cutscene_state(), keep_all=True)
        )
        return definition

    @classmethod
    def from_definition(
        cls,
        definition: dict,
        animation_library: dict | None = None,
        sound_library: dict | None = None,
    ) -> "Level":
        level = cls()
        # 编辑器不认识的顶层键（老字段、手写的东西）原样留着，保存时照写回去
        level.extra = {
            key: copy.deepcopy(value)
            for key, value in definition.items()
            if key not in LEVEL_KEYS
        }
        # 关卡名来自文件名，json 里的 name 不读；它在 extra 里原样保留
        level.width = clamp_int(definition.get("width"), LEVEL_WIDTH_MIN, LEVEL_WIDTH_MAX, COLS)
        level.height = clamp_int(definition.get("height"), LEVEL_HEIGHT_MIN, LEVEL_HEIGHT_MAX, ROWS)
        level.flip_area_offsets = _read_flip_area_offsets(definition, level.height)
        level.background = str(definition.get("background", "") or "")
        # 音乐是一段链接（声音库的键 + 循环 + 淡入淡出）；老写的 bgm 路径在这里换成键
        sound_value = definition.get("sound")
        level.sound = (
            sound_fields_of(sound_value, sound_library)
            if isinstance(sound_value, dict)
            else None
        )
        cutscene = definition.get("cutscene")
        level.cutscene = copy.deepcopy(cutscene) if isinstance(cutscene, dict) else None
        level.destination = copy.deepcopy(definition.get("destination"))
        level.blocks = copy.deepcopy(list(definition.get("blocks", [])))
        level.planks = copy.deepcopy(list(definition.get("planks", [])))
        level.movable_blocks = copy.deepcopy(list(definition.get("movable_blocks", [])))
        for entry in level.movable_blocks:
            if isinstance(entry, dict):
                _migrate_triggers(entry)
        # 触发源：新表 + 老数据的 buttons / items 合并进来，整块矩形就是触发区
        level.trigger_sources = _read_trigger_sources(definition)
        # 门本身就是触发区；老数据里的 range 原样留着，不删
        level.portals = copy.deepcopy(list(definition.get("portals", [])))
        for entry in level.portals:
            if isinstance(entry, dict):
                entry.setdefault("size", list(PORTAL_SIZE))
        # 喷口的风区现在是 size；老数据写的 range 补出 size 之外原样留着
        level.nozzles = []
        for entry in copy.deepcopy(list(definition.get("nozzles", []))):
            if not isinstance(entry, dict):
                continue
            if "size" not in entry and "range" in entry:
                entry["size"] = [1.0, entry.get("range")]
            entry.setdefault("size", list(NOZZLE_DEFAULT_SIZE))
            level.nozzles.append(entry)
        level.textures = copy.deepcopy(list(definition.get("textures", [])))
        for entry in level.textures:
            if isinstance(entry, dict):
                _migrate_triggers(entry)
        # 动画对象：位置尺寸、跟随、预设、两套链接；链接缺的项补空
        level.animation_objects = []
        for entry in copy.deepcopy(list(definition.get("animation_objects", []))):
            if not isinstance(entry, dict):
                continue
            entry.setdefault("size", [1.0, 1.0])
            entry.setdefault("follow", "")
            entry.setdefault("preset", animation.PRESET_GENERAL)
            entry["links"] = animation.links_of(entry, animation_library)
            level.animation_objects.append(entry)
        # 声音对象：只有预设和链接；没有位置、大小，也没有左右
        level.sound_objects = []
        for entry in copy.deepcopy(list(definition.get("sound_objects", []))):
            if not isinstance(entry, dict):
                continue
            entry.pop("pos", None)
            entry.pop("size", None)
            entry.setdefault("preset", sound.PRESET_GENERAL)
            entry.setdefault("follow", "")
            entry["links"] = sound.object_links_of(entry)
            level.sound_objects.append(entry)

        # 玩家：这里只放位置和大小，跳高/速度属于整个游戏（game.json，编辑器不写）；
        # 老关卡里写过的这几项原样留着，游戏读的时候当成这一关的覆盖值
        player = definition.get("player")
        level.player = copy.deepcopy(player) if isinstance(player, dict) else None
        if level.player is not None:
            # 起点预览已经删掉，这两个旧字段不再保留
            level.player.pop("preview_animation", None)
            level.player.pop("preview_side", None)
        return level
