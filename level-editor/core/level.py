"""关卡数据模型。

键和形状与游戏端一一对应，细节见 game/world/level.py 的模块说明；这里只额外记着
编辑器自己关心的事：玩家的跳高、速度、动画属于整个游戏（game.json，见 core.game），
不归 Level 管；关卡 json 的 player 里如果还留着这几个键，原样保留当这一关的覆盖值。
关卡名就是文件名（levels/<名字>.json），json 里不再写 name。
这一关的背景音乐（sound）跟着关卡文件走，归 Level 管；标题和制作名单的音乐在 game.json 的
sounds 里，由「游戏配置」的声音页改（见 core.sound）。
"""

import copy
import json

from core import animation
from core.constants import (
    BUTTON_SIZE,
    COLS,
    FLIP_AREA_OFFSETS_DEFAULT,
    ITEM_MODE_DEFAULT,
    ITEM_MODE_VALUES,
    JUMP_HEIGHT_DEFAULT,
    JUMP_HEIGHT_MIN,
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
)
from core.helpers import clamp_float, clamp_int
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
    "buttons",
    "portals",
    "items",
    "nozzles",
    "textures",
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


def _migrate_item_jump_offset(entry: dict) -> None:
    """道具：老数据用 heavy 表示变重（跳高降 1 格），读出来补一个 jump_offset。

    heavy 键原样留着，不删。
    """
    heavy = bool(entry.get("heavy", False))
    if "jump_offset" not in entry:
        entry["jump_offset"] = -1.0 if heavy else 0.0


def _migrate_item_mode(entry: dict) -> None:
    """道具的触发模式：这是编辑器认识的字段，缺了补默认值，写坏了也按默认值。"""
    if entry.get("mode") not in ITEM_MODE_VALUES:
        entry["mode"] = ITEM_MODE_DEFAULT


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
        self.sound: dict | None = None  # 这一关的音乐：{bgm, loop, fade_in, fade_out}；None 表示没有
        self.cutscene: dict | None = None  # 进这一关之前的过场；None 表示没有
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
                "buttons": copy.deepcopy(self.buttons),
                "portals": copy.deepcopy(self.portals),
                "items": copy.deepcopy(self.items),
                "nozzles": copy.deepcopy(self.nozzles),
                "textures": copy.deepcopy(self.textures),
            }
        )
        # 起点和终点都只有一份，没有就不写这个键。跳高、速度、动画属于整个游戏，
        # 写在 game.json 里；这一关原本写过的覆盖值原样留着，不动它。
        # preview_animation / preview_side 是起点自己的属性：在编辑器里显示哪一套动画的
        # 哪一侧，默认站立、右侧。
        if self.player is not None:
            player = copy.deepcopy(self.player)
            action = str(player.get(animation.PREVIEW_KEY) or animation.DEFAULT_PREVIEW)
            names = [name for name, _ in animation.PLAYER_ANIMATIONS]
            player[animation.PREVIEW_KEY] = (
                action if action in names else animation.DEFAULT_PREVIEW
            )
            side = str(player.get(animation.PREVIEW_SIDE_KEY) or animation.DEFAULT_PREVIEW_SIDE)
            sides = [name for name, _ in animation.PLAYER_SIDES]
            player[animation.PREVIEW_SIDE_KEY] = (
                side if side in sides else animation.DEFAULT_PREVIEW_SIDE
            )
            definition["player"] = player
        if self.destination is not None:
            definition["destination"] = copy.deepcopy(self.destination)
        # 背景、音乐、过场这三项在编辑器里都有字段，空着也照写（空值表示没有）
        definition["background"] = self.background
        definition["sound"] = (
            copy.deepcopy(self.sound)
            if self.sound
            else sound_to_object(sound_fields_of(None), keep_empty=True)
        )
        definition["cutscene"] = (
            copy.deepcopy(self.cutscene)
            if self.cutscene
            else cutscene_to_object(new_cutscene_state(), keep_all=True)
        )
        return definition

    @classmethod
    def from_definition(cls, definition: dict) -> "Level":
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
        sound = definition.get("sound")
        level.sound = copy.deepcopy(sound) if isinstance(sound, dict) else None
        cutscene = definition.get("cutscene")
        level.cutscene = copy.deepcopy(cutscene) if isinstance(cutscene, dict) else None
        level.destination = copy.deepcopy(definition.get("destination"))
        level.blocks = copy.deepcopy(list(definition.get("blocks", [])))
        level.planks = copy.deepcopy(list(definition.get("planks", [])))
        level.movable_blocks = copy.deepcopy(list(definition.get("movable_blocks", [])))
        for entry in level.movable_blocks:
            if isinstance(entry, dict):
                _migrate_triggers(entry)
        level.buttons = copy.deepcopy(list(definition.get("buttons", [])))
        # 门本身就是触发区；老数据里的 range 原样留着，不删
        level.portals = copy.deepcopy(list(definition.get("portals", [])))
        # 按钮和门的「画出来的矩形」就是触发区，缺 size 时按默认补上，别和游戏里不一致
        for entries, default in ((level.buttons, BUTTON_SIZE), (level.portals, PORTAL_SIZE)):
            for entry in entries:
                if isinstance(entry, dict):
                    entry.setdefault("size", list(default))
        level.items = copy.deepcopy(list(definition.get("items", [])))
        for entry in level.items:
            if isinstance(entry, dict):
                _migrate_item_jump_offset(entry)
                _migrate_item_mode(entry)
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

        # 玩家：这里只放位置和大小，跳高/速度/动画属于整个游戏（game.json，编辑器不写）；
        # 老关卡里写过的这几项原样留着，游戏读的时候当成这一关的覆盖值
        player = definition.get("player")
        level.player = copy.deepcopy(player) if isinstance(player, dict) else None
        return level
