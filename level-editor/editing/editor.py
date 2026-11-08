"""Editor：编辑器状态与所有编辑操作。"""

import copy
import json
import os
from typing import TYPE_CHECKING

from core import animation, cutscene, game, item, sound
from core.constants import (
    BACKGROUND_MAX_LENGTH,
    COLS,
    FACE_LABELS,
    FACE_ORDER,
    GAME_ANIMATION_TAB,
    GAME_CUTSCENE_TAB,
    GAME_ITEM_TAB,
    GAME_PLAYER_VIEW_TAB,
    GAME_SETTINGS_TABS,
    GAME_SOUND_LIBRARY_TAB,
    GLOBAL_KINDS,
    HANDLE_PIXELS,
    HEADER,
    JUMP_HEIGHT_DEFAULT,
    JUMP_HEIGHT_MAX,
    JUMP_HEIGHT_MIN,
    JUMP_HEIGHT_STEP,
    KIND_BEHAVIORS,
    KIND_ANIMATION,
    KIND_BLOCK,
    KIND_DESTINATION,
    KIND_GLOBAL_ANIMATION,
    KIND_GLOBAL_HEADER,
    KIND_GLOBAL_SOUND,
    KIND_HAS_NAME,
    KIND_MOVABLE,
    KIND_NOZZLE,
    KIND_ORDER,
    KIND_PLANK,
    KIND_PLAYER,
    KIND_PORTAL,
    KIND_SOUND,
    KIND_TEXTURE,
    KIND_TITLES,
    KIND_TRIGGER_SOURCE,
    LEVEL_HEIGHT_MAX,
    LEVEL_HEIGHT_MIN,
    LEVEL_WIDTH_MAX,
    LEVEL_WIDTH_MIN,
    MARGIN,
    MIN_SIZE,
    MOVE_SPEED_DEFAULT,
    MOVE_SPEED_MAX,
    MOVE_SPEED_MIN,
    NAME_MAX_LENGTH,
    NOZZLE_DEFAULT_POWER,
    NOZZLE_DEFAULT_SIZE,
    NUMBER_TEXT_MAX_LENGTH,
    PLAYER_FACE_LABELS,
    PLAYER_FACE_ORDER,
    PORTAL_SIZE,
    ROWS,
    SCROLL_STEP,
    SETTINGS_CUTSCENE_TAB,
    SETTINGS_TABS,
    TOOL_BLOCK,
    TOOL_DEST,
    TOOL_NOZZLE,
    TOOL_PLANK,
    TOOL_PLAYER,
    TOOL_PORTAL,
    TOOL_SPECS,
    TOOL_ANIMATION,
    TOOL_SOUND,
    TOOL_TEXTURE,
    TOOL_TRIGGER_SOURCE,
    DESTINATION_TRIGGER_DEFAULT_MODE,
    TRIGGER_DEFAULT_MODE,
    TRIGGER_MODES,
    TRIGGER_SOURCE_MODE_DEFAULT,
    TRIGGER_SOURCE_MODE_LABELS,
    TRIGGER_SOURCE_MODE_VALUES,
    TRIGGER_SOURCE_MODES,
    TRIGGER_JUMP_OFFSET_MAX,
    TRIGGER_JUMP_OFFSET_MIN,
)
from core.helpers import (
    SNAP_STEP,
    clamp_float,
    clamp_int,
    clamp_nozzle_power,
    display_path,
    file_name_for,
    level_name_of,
    normalize_rect,
    nozzle_face_axis,
    nozzle_power_tip,
    number_text,
    object_box,
    relative_level_path,
    resolve_level_path,
    round_rect,
    snap,
)
from core.level import Level, dump_level
from editing.anim_import import AnimationImportError, import_animation_frames
from editing.files import ask_audio_path, ask_game_file, ask_game_file_to_create, ask_image_path
from view.texture import image_size, load_scaled

if TYPE_CHECKING:
    from view.layout import Layout

# 触发卡片上的三个格子不是普通属性行，字段号从这里往后排：
# 1000 + 卡片下标 * 3 + (0 = 来源 / 1 = 行为 / 2 = 模式)
TRIGGER_FIELD_BASE = 1000
TRIGGER_PARTS = ("source", "behavior", "mode")

# 对象列表排序用：种类在 KIND_ORDER 里的位置
KIND_ORDER_INDEX = {kind: index for index, kind in enumerate(KIND_ORDER)}


def _cycle_key(library: dict, current, delta: int) -> str:
    """在声音库的键和「无」之间前后挪一格：空字符串表示这一幕没有声音。"""
    options = [""] + sorted(library)
    value = str(current or "")
    index = options.index(value) if value in options else 0
    return options[(index + int(delta)) % len(options)]


def _uses_sound(value, key: str) -> bool:
    """一段链接是不是指向这个声音键。"""
    return isinstance(value, dict) and str(value.get("sound") or "").strip() == key


class Editor:
    def __init__(self) -> None:
        self.level = Level()
        self.game_path: str | None = None          # 打开的游戏：game.json 的路径
        self.level_in_view = False                 # 视图里有没有关卡（没有就什么都不画）
        self.path: str | None = None               # 当前关卡的文件夹，新关卡还没保存时是 None
        self.dirty = False
        self.undo_stack: list = []
        self.tool = TOOL_BLOCK
        self.zoom: float | None = None
        self.pan_x = 0.0
        self.pan_y = 0.0
        self.hovered = None
        self.selection: list = []               # 选中的对象：(kind, entry)
        self.pick_menu: dict | None = None      # Alt+点击的取对象列表：{"stack": [...], "position": (...)}
        self.marquee_start: tuple | None = None  # 左键拖出的框选，世界坐标
        self.marquee_current: tuple | None = None
        self.marquee_additive = False            # 框选开始时是否按着 Ctrl
        self.drag_start: tuple | None = None
        self.drag_current: tuple | None = None
        self.pan_drag: tuple | None = None
        self.dialog: dict | None = None
        self.dialog_field = 0
        self.detail_scroll = 0.0                 # 属性面板内容滚了多少像素
        self.dropdown_field: int | None = None   # 正在展开下拉列表的选择型字段
        self.name_focused = False
        self.number_buffer: str | None = None   # 正在键盘输入的数字字段，None 表示没在输入
        self.object_grab: dict | None = None    # 正在用鼠标拖对象：移动或缩放
        self.snapping = False                   # 按住 Shift：吸附到整格
        self.keep_ratio = False                 # 按住 Ctrl：贴图等比缩放
        self.click_through = False              # 按住 Alt：穿透最上层
        self.last_mouse = (0, 0)
        self.file_menu_open = False             # 工具栏「文件」下拉菜单
        self.view_menu_open = False
        # 视图设置：只影响编辑器自己的显示，从不写进关卡数据、不落盘
        self.view_settings: dict = {
            "background": True,
            "textures": True,
            "grid": True,
            "debug": True,
            "dock": True,
        }
        # 右侧面板：哪一页（属性 / 对象列表），列表自己的筛选、滚动和筛选下拉
        self.panel_tab = "properties"
        self.go_list_filter = ""
        self.go_list_scroll = 0.0
        self.go_list_menu = False
        self.menu_open = False
        self.menu_origin = (MARGIN, HEADER)
        self.creating = False
        self.settings: dict | None = None
        self.settings_tab = 0                      # 关卡设置停在哪一页：常规/玩家/声音/过场
        self.settings_field = 0
        self.cutscene: dict | None = None           # 过场页编辑中的状态
        self.cutscene_scope = "level"               # "level" / "game"：声音选项的叫法
        self.cutscene_field = 0                     # 过场页选中的格（cell 下标）
        self.cutscene_scroll = 0                    # 过场卡片滚了多少像素
        self.cutscene_area_height = 0.0             # 过场卡片可视区有多高（几何算出来）
        self.cutscene_card_step = 0.0               # 过场卡片一行占多高（几何算出来）
        self.game_player: dict = {}                # game.json 里的玩家参数（跳高、速度）
        self.animation_library: dict = {}          # game.json 的动画库（只读快照，画布和链接弹窗用）
        self.animation_library_scroll = 0.0        # 动画集页的列表滚了多少像素
        self.game_animation_library: dict = {}     # 游戏配置浮层里正在编辑的动画库
        self.animation_selected = ""               # 动画集页选中的键
        self.animation_edit: dict | None = None    # 编辑单条动画的弹窗状态
        self.animation_link: dict | None = None    # 动画对象的「动画…」弹窗状态
        self.sound_link: dict | None = None        # 声音对象的「声音…」弹窗状态
        # 全局玩家表现：game.json 里的 player_animation / player_sound。编辑在属性面板，
        # 改动先进这份 pending，应用后才写盘；撤销也只动这两块。
        self.player_animation: dict = self._default_player_animation()
        self.player_sound: dict = self._default_player_sound()
        self.player_animation_saved: dict = copy.deepcopy(self.player_animation)
        self.player_sound_saved: dict = copy.deepcopy(self.player_sound)
        self.global_undo_stack: list = []
        self.global_prompt: dict | None = None      # 离开全局页时等确认的保存提示
        self.global_grab: dict | None = None        # 画布上拖玩家动画的全局 gizmo
        self.global_frame_index = 0                 # 画布预览用：idle 播到第几帧
        self.global_frame_elapsed = 0.0
        self.animation_object_states: dict = {}    # 画布上每个动画对象的播放状态：id(entry) → {…}
        self.game_settings: dict | None = None     # 游戏配置浮层：game.json 的内容
        self.game_numbers: dict = {}               # 浮层里的跳高与速度（编辑期间是字符串）
        self.game_backgrounds: dict = {}           # 浮层里的标题 / 结算背景：键 → 相对路径
        self.game_cards: list = []                 # 浮层里的制作名单卡片：{job, names: [名字…]}
        self.game_card_scroll = 0                  # 制作名单滚轮滚了多少像素
        self.game_field = 0                        # 浮层里选中的格：标题、跳高、速度、职位、名字…
        self.game_tab = 0                          # 游戏配置停在哪一页：常规/动画集/制作名单/声音/声音库/物品/过场
        self.game_sound: dict = {}                 # 声音页：键 → {sound, loop, fade_in, fade_out}
        # 声音库：game.json 的 sound_library（键 → {"path"}）；关卡和音乐链接都从这里取键
        self.sound_library: dict = {}
        self.sound_library_scroll = 0.0            # 声音库页的列表滚了多少像素
        self.sound_selected = ""                   # 声音库页选中的键
        self.sound_library_dirty = False           # 库里有还没写回 game.json 的改动
        # 物品库：game.json 的 item_library（id → {"icon", "description"}）；触发源按 id 解锁
        self.item_library: dict = {}
        self.item_library_saved: dict | None = None  # 打开游戏配置时的快照：取消就还原
        self.item_library_scroll = 0.0
        self.item_selected = ""
        # 选 BGM 的下拉：{"target": 目标, "scroll": 滚了几行}；target 见 open_sound_menu
        self.sound_menu: dict | None = None
        self.preview = sound.Preview()             # 试听（和游戏共用一个混音器）
        self.level_select_open = False             # 关卡列表浮层
        self.level_select_scroll = 0               # 关卡列表滚了多少像素
        self.pending_switch: tuple[str, str] | None = None  # 等确认的切换：("level"/"game"/"new", 目标)
        self.save_notice = ""                      # 存完弹的那句提示：这关缺起点/终点（空串=不弹）
        self.confirm_quit = False
        self.startup = True
        self.status = "请打开或新建游戏配置文件（game.json）。"

    # ---- 查询 -------------------------------------------------------
    @property
    def levels_dir(self) -> str | None:
        """当前游戏的 levels/；还没打开游戏配置时是 None。"""
        return game.levels_dir_of(self.game_path) if self.game_path else None

    @property
    def media_base_dir(self) -> str | None:
        """图片路径的基准目录：game.json 所在的文件夹（游戏根），关卡里的路径也相对它。"""
        return game.game_root_of(self.game_path) if self.game_path else None

    @staticmethod
    def _default_player_animation() -> dict:
        """新建游戏或 game.json 还没写玩家动画时的默认形状：尺寸/偏移用第一关的数值。"""
        return {
            "size": [2.02, 2.68],
            "offset": [-0.115, -0.14],
            "links": animation.new_links(),
        }

    @staticmethod
    def _default_player_sound() -> dict:
        return {"links": sound.new_object_links()}

    def _load_player_views(self, settings: dict) -> None:
        """从 game.json 读全局玩家动画/音效；缺了就用默认形状。"""
        loaded = game.player_animation_of(settings)
        if loaded is None:
            self.player_animation = self._default_player_animation()
        else:
            loaded["links"] = animation.links_of(loaded, self.animation_library)
            self.player_animation = loaded
        loaded_sound = game.player_sound_of(settings)
        if loaded_sound is None:
            self.player_sound = self._default_player_sound()
        else:
            self.player_sound = {
                "links": sound.object_links_of(loaded_sound)
            }
        self.player_animation_saved = copy.deepcopy(self.player_animation)
        self.player_sound_saved = copy.deepcopy(self.player_sound)
        self.global_undo_stack.clear()
        self.global_prompt = None
        self.global_grab = None

    def player_face(self) -> str:
        """这一关玩家的初始朝向：left / right，缺省 right。"""
        if self.level_in_view and isinstance(self.level.player, dict):
            face = str(self.level.player.get("face") or "right").strip().lower()
            return face if face in PLAYER_FACE_LABELS else "right"
        return "right"

    def player_stats(self) -> tuple[float, float, bool]:
        """当前关卡实际用的跳高和速度：关卡 player 里写了就盖住 game.json 的玩家参数。

        第三个返回值是「这一关有没有覆盖」，顶栏用它标一下。
        """
        override = {}
        if self.level_in_view and isinstance(self.level.player, dict):
            override = self.level.player
        overridden = "jump_height" in override or "move_speed" in override
        jump = clamp_float(
            override.get("jump_height", self.game_player.get("jump_height")),
            JUMP_HEIGHT_MIN,
            JUMP_HEIGHT_MAX,
            JUMP_HEIGHT_DEFAULT,
        )
        speed = clamp_float(
            override.get("move_speed", self.game_player.get("move_speed")),
            MOVE_SPEED_MIN,
            MOVE_SPEED_MAX,
            MOVE_SPEED_DEFAULT,
        )
        return jump, speed, overridden

    def show_textures(self) -> bool:
        """视图菜单里的「显示贴图」：关掉时贴图不画、也点不中（像被藏起来一样）。"""
        return bool(self.view_settings.get("textures", True))

    def stacked_entries(self) -> list:
        """所有能点选的对象，按绘制顺序从下到上：(kind, entry)。

        和画布一致：按钮、道具、喷口画在贴图下面，传送门、起点、终点画在贴图上面。
        贴图被视图开关藏起来时不算在内：看不见的图不该抢点击，也不该被框选中。
        """
        pairs = []
        for entries, kind in (
            (self.level.blocks, KIND_BLOCK),
            (self.level.planks, KIND_PLANK),
            (self.level.movable_blocks, KIND_MOVABLE),
            (self.level.trigger_sources, KIND_TRIGGER_SOURCE),
            (self.level.nozzles, KIND_NOZZLE),
            (self.level.textures, KIND_TEXTURE),
            (self.level.animation_objects, KIND_ANIMATION),
            (self.level.portals, KIND_PORTAL),
        ):
            if kind == KIND_TEXTURE and not self.show_textures():
                continue
            pairs += [(kind, entry) for entry in entries]
        if self.level.player is not None:
            pairs.append((KIND_PLAYER, self.level.player))
        if self.level.destination is not None:
            pairs.append((KIND_DESTINATION, self.level.destination))
        return pairs

    def object_stack_at(self, position: tuple, layout: Layout) -> list:
        """屏幕上该点压着的所有对象，最上层的在前（和绘制顺序相反）。

        命中用的就是画出来的那个矩形（object_box + layout.entry_rect），所以只要眼睛
        看得见、不管它延伸到关卡外面还是顶到底部状态栏，都点得到。选中只认最上层那个：
        不能隔着另一个对象点到它后面的东西。
        """
        return [
            (kind, entry)
            for kind, entry in reversed(self.stacked_entries())
            if self._hit(position, layout, kind, entry)
        ]

    @staticmethod
    def _hit(position: tuple, layout: Layout, kind: str, entry: dict) -> bool:
        return layout.entry_rect(object_box(kind, entry)).collidepoint(position)

    def object_at(self, position: tuple, layout: Layout):
        """最上层的那个对象。

        单选时，选中的那个在自己的矩形里算最上层：被别的对象盖住也能直接拖它。
        按住 Alt 不做这层优先，返回视觉上最上层的（要选叠在下面的，Alt+点击会列出列表）。
        """
        stack = self.object_stack_at(position, layout)
        if not stack:
            return None
        if not self.click_through:
            selected = self.selected_entry()
            if selected is not None:
                for kind, entry in stack:
                    if entry is selected[1]:
                        return kind, entry
        return stack[0]

    def selected_entry(self):
        """唯一选中的那个 (kind, entry)；没选中或者多选都返回 None。"""
        return self.selection[0] if len(self.selection) == 1 else None

    def handle_target(self):
        """有缩放手柄的对象：拖动中的那个，或者唯一选中的那个（和画出来的手柄一致）。"""
        if self.object_grab is not None:
            return self.object_grab["kind"], self.object_grab["entry"]
        target = self.selected_entry()
        if target is not None and target[0] in GLOBAL_KINDS:
            return None
        return target

    # ---- 取光标下的对象（Alt+点击） --------------------------------
    def open_pick_menu(self, position: tuple, layout: Layout) -> bool:
        """叠着两个以上对象时，把它们列出来让用户挑；只有一个就不弹。返回开没开。"""
        stack = self.object_stack_at(position, layout)
        if len(stack) < 2:
            return False
        self.pick_menu = {"stack": stack, "position": (position[0], position[1])}
        self.status = "光标下叠着多个对象，点一行选中它。"
        return True

    def close_pick_menu(self) -> None:
        self.pick_menu = None

    def choose_pick(self, index: int) -> None:
        """在取对象列表里点了一行：选中那个对象。"""
        menu = self.pick_menu
        if menu is None or not 0 <= index < len(menu["stack"]):
            return
        kind, entry = menu["stack"][index]
        self.pick_menu = None
        self.select(kind, entry)

    def handle_at(self, layout: Layout, kind: str, entry: dict, position: tuple):
        """光标离哪个缩放手柄够近：四角 + 四条边的中点，都不够近返回 None。

        角名是 bl/br/tl/tr，边名是 b/t/l/r；拉边只动一个方向，拉角两个方向都动。
        """
        rect = layout.entry_rect(object_box(kind, entry))
        for name, point in (
            ("bl", rect.bottomleft),
            ("br", rect.bottomright),
            ("tl", rect.topleft),
            ("tr", rect.topright),
            ("l", rect.midleft),
            ("r", rect.midright),
            ("b", rect.midbottom),
            ("t", rect.midtop),
        ):
            if (
                abs(position[0] - point[0]) <= HANDLE_PIXELS
                and abs(position[1] - point[1]) <= HANDLE_PIXELS
            ):
                return name
        return None

    def object_handle_at(self, position: tuple, layout: Layout):
        """光标压在哪个手柄上：只有唯一选中的那个有手柄（和画出来的一致）。"""
        target = self.handle_target()
        if target is None:
            return None
        kind, entry = target
        name = self.handle_at(layout, kind, entry, position)
        return (kind, entry, name) if name is not None else None

    def power_handle_at(self, position: tuple, layout: Layout):
        """光标压在选中喷口的力度箭头末端：只有选中的喷口才有这条可拖的线。"""
        for kind, entry in self.selection:
            if kind != KIND_NOZZLE:
                continue
            tip_x, tip_y = nozzle_power_tip(entry)
            tip_rect = layout.world_rect(tip_x - 0.5, tip_y - 0.2, 1.0, 0.4)
            if (
                tip_rect.left - HANDLE_PIXELS <= position[0] <= tip_rect.right + HANDLE_PIXELS
                and abs(position[1] - tip_rect.centery) <= HANDLE_PIXELS
            ):
                return KIND_NOZZLE, entry, "power"
        return None

    def update_hover(self, position: tuple, layout: Layout) -> None:
        """挑出光标下的对象：选中的那个优先，其次是最上层那个。"""
        self.last_mouse = (position[0], position[1])
        self.hovered = None
        # 画布铺满整个窗口：顶部信息栏、底部状态栏只是画字，不挡对象，
        # 所以整个窗口都算工作区，对象长到哪就点到哪
        if not (0 <= position[0] < layout.window[0] and 0 <= position[1] < layout.window[1]):
            return
        self.hovered = self.object_at(position, layout)

    # ---- 创建 / 删除 -----------------------------------------------
    def begin_drag(self, point: tuple) -> None:
        """从世界坐标点开始拖一个新矩形；不吸格子，只有按住 Shift 才对齐。"""
        self.drag_start = point
        self.drag_current = point

    def press_canvas(self, position: tuple, layout: Layout) -> None:
        """新建状态里的左键按下：矩形工具开始拖，单点工具就地放下。"""
        point = layout.world_point(position)
        if self.snapping:
            point = layout.snap_point(*point)
        if TOOL_SPECS[self.tool][1] == "rect":
            self.begin_drag(point)
        else:
            self.place_single(point)

    def drag_to(self, position: tuple, layout: Layout) -> None:
        if self.drag_start is None:
            return
        self.last_mouse = (position[0], position[1])
        point = layout.world_point(position)
        if self.snapping:
            point = layout.snap_point(*point)
        self.drag_current = point

    def finish_drag(self) -> None:
        if self.drag_start is None:
            return
        start = self.drag_start
        current = self.drag_current or start
        self.drag_start = None
        self.drag_current = None
        x, y, w, h = round_rect(normalize_rect(start, current, MIN_SIZE))
        self.push_undo()
        if self.tool == TOOL_BLOCK:
            self.level.blocks.append({"pos": [x, y], "size": [w, h]})
        elif self.tool == TOOL_PLANK:
            self.level.planks.append({"pos": [x, y], "size": [w, h]})
        elif self.tool == TOOL_TRIGGER_SOURCE:
            # 触发源：整块矩形就是触发区，拖多大就多大
            self.level.trigger_sources.append(
                {
                    "name": "",
                    "pos": [x, y],
                    "size": [w, h],
                    "mode": TRIGGER_SOURCE_MODE_DEFAULT,
                    "jump_offset": 0.0,
                }
            )
        else:
            self.level.movable_blocks.append(
                {
                    "name": "",
                    "pos": [x, y],
                    "size": [w, h],
                    "offset": [0, 0],
                    "triggers": [],
                }
            )
        self.dirty = True
        self.status = f"已添加{TOOL_SPECS[self.tool][0]}（{x}, {y}）{w}×{h}。"

    def place_single(self, point: tuple) -> None:
        """喷口/起点/终点/传送门/动画：就地放下一个对象。"""
        x, y = point
        size = [1.0, 1.0]
        level = self.level
        self.push_undo()
        self.dirty = True
        # 新对象的数值/布尔/字符串一律给中性默认值，具体参数再在面板里调
        if self.tool == TOOL_PORTAL:
            # 门本身固定 1×0.3，它就是触发区；目标和朝向在面板里调
            level.portals.append(
                {
                    "name": "",
                    "pos": [x, y],
                    "size": list(PORTAL_SIZE),
                    "face": FACE_ORDER[0],
                    "target": "",
                }
            )
        elif self.tool == TOOL_NOZZLE:
            # 喷口的 size 就是风区（宽 × 长），face 是伸出的方向，power 是目标离底面多远
            nozzle = {
                "pos": [x, y],
                "face": FACE_ORDER[0],
                "power": 0,
                "size": list(NOZZLE_DEFAULT_SIZE),
            }
            clamp_nozzle_power(nozzle)     # 力度至少比风区长 0.5 格
            level.nozzles.append(nozzle)
        elif self.tool == TOOL_PLAYER:
            # 起点只有一份：再放一次就是把它挪过去
            level.player = {"pos": [x, y], "size": list(size)}
        elif self.tool == TOOL_ANIMATION:
            # 动画对象：默认通用预设、一条链接都没选，跟随先空着
            level.animation_objects.append(
                {
                    "pos": [x, y],
                    "size": list(size),
                    "follow": "",
                    "preset": animation.PRESET_GENERAL,
                    "links": animation.new_links(),
                }
            )
        elif self.tool == TOOL_DEST:
            # 终点也只有一份
            level.destination = {"pos": [x, y], "size": list(size)}
        self.status = f"已添加{TOOL_SPECS[self.tool][0]}（{x}, {y}）。"

    def add_sound_object(self) -> None:
        """新建一个声音对象：没有位置和大小，建好就选中、属性面板跟着打开。"""
        self.push_undo()
        entry = {
            "preset": sound.PRESET_GENERAL,
            "follow": "",
            "links": sound.new_object_links(),
        }
        self.level.sound_objects.append(entry)
        self.creating = False
        self.menu_open = False
        self.dirty = True
        self.select(KIND_SOUND, entry)
        self.status = "已添加声音对象：在属性面板里选预设，再点「声音…」选声音。"

    def delete_entry(self, kind: str, entry: dict) -> None:
        if kind in GLOBAL_KINDS:
            self.status = "全局玩家表现不能删除，只能在属性面板里改。"
            return
        self.push_undo()
        self.dirty = True
        self.remove_entry(kind, entry)
        self.dialog = None
        self.dropdown_field = None
        self.selection = []
        self.hovered = None
        self.pick_menu = None
        self.number_buffer = None
        self.status = f"已删除{KIND_TITLES.get(kind, '对象')}。"

    # ---- 撤销 -------------------------------------------------------
    def push_undo(self) -> None:
        self.undo_stack.append(copy.deepcopy(self.level.to_definition()))
        if len(self.undo_stack) > 200:
            self.undo_stack.pop(0)

    def undo(self) -> None:
        if not self.undo_stack:
            self.status = "当前没有可撤销的操作。"
            return
        # 关卡名就是文件名，不写在快照里：撤销时从当前关卡带过去，别把名字丢了
        name = self.level.name
        self.level = Level.from_definition(
            self.undo_stack.pop(), self.animation_library, self.sound_library
        )
        self.level.name = name
        self.dialog = None
        self.dropdown_field = None
        self.selection = []
        self.marquee_start = None
        self.marquee_current = None
        self.pick_menu = None
        self.reset_go_list()
        self.dirty = True
        self.status = "已撤销上一步操作。"

    # ---- 全局玩家表现：game.json 的 player_animation / player_sound ----
    def global_active(self) -> bool:
        return self.dialog is not None and self.dialog["kind"] in GLOBAL_KINDS

    def global_kind(self) -> str | None:
        return self.dialog["kind"] if self.global_active() else None

    def global_entry(self, kind: str) -> dict | None:
        if kind == KIND_GLOBAL_ANIMATION:
            return self.player_animation
        if kind == KIND_GLOBAL_SOUND:
            return self.player_sound
        return None

    def global_dirty(self) -> bool:
        return (
            self.player_animation != self.player_animation_saved
            or self.player_sound != self.player_sound_saved
        )

    def select_global(self, kind: str) -> None:
        """选中全局项：直接打开属性页，不经过关卡对象的选择。"""
        entry = self.global_entry(kind)
        if entry is None:
            return
        self.selection = [(kind, entry)]
        self.dialog = {"kind": kind, "entry": entry}
        self.dialog_field = 0
        self.detail_scroll = 0.0
        self.dropdown_field = None
        self.name_focused = False
        self.number_buffer = None
        self.go_list_menu = False
        self.panel_tab = "properties"
        self.global_frame_index = 0
        self.global_frame_elapsed = 0.0
        self.status = f"已选中{KIND_TITLES.get(kind, '全局项')}（所有关卡共用）。"

    def _defer_global(self, action: tuple) -> bool:
        """有没应用的全局改动、又要离开全局页：先挂起等用户选应用/放弃。"""
        if not self.global_active() or not self.global_dirty():
            return False
        self.global_prompt = {"action": action}
        self.status = "玩家表现有未应用的修改：先应用或放弃再离开。"
        return True

    def resolve_global_prompt(self, choice: str | None) -> str | None:
        """保存提示的结果：apply / discard / None；返回 "quit" 表示外层可以退出。"""
        prompt = self.global_prompt
        if prompt is None:
            return None
        if choice is None:
            self.global_prompt = None
            self.status = "已取消离开。"
            return None
        if choice == "apply":
            if not self.apply_global():
                return None
        elif choice == "discard":
            self.discard_global()
        self.global_prompt = None
        return self._run_global_action(prompt["action"])

    def _run_global_action(self, action: tuple) -> str | None:
        """全局保存提示处理完，继续用户原来要做的事。"""
        name = action[0]
        if name == "select":
            self.select(action[1], action[2])
        elif name == "select_many":
            self.select_many(action[1])
        elif name == "clear":
            self.select_many([])
        elif name == "open_game_settings":
            self.open_game_settings()
        elif name == "open_settings":
            self.open_settings()
        elif name == "open_level_select":
            self.open_level_select()
        elif name == "choose_level":
            self.choose_level(action[1])
        elif name == "create_level":
            self.create_level()
        elif name == "request_open_game":
            self.request_open_game()
        elif name == "quit":
            return "quit" if self.request_quit() else None
        return None

    def push_global_undo(self) -> None:
        """全局撤销只记 player_animation / player_sound，不碰关卡和别的游戏配置。"""
        self.global_undo_stack.append(
            {
                "animation": copy.deepcopy(self.player_animation),
                "sound": copy.deepcopy(self.player_sound),
            }
        )
        if len(self.global_undo_stack) > 200:
            self.global_undo_stack.pop(0)

    def undo_global(self) -> None:
        if not self.global_undo_stack:
            self.status = "当前没有可撤销的全局修改。"
            return
        snapshot = self.global_undo_stack.pop()
        self.player_animation = copy.deepcopy(snapshot["animation"])
        self.player_sound = copy.deepcopy(snapshot["sound"])
        if self.global_active():
            kind = self.dialog["kind"]
            self.dialog = {"kind": kind, "entry": self.global_entry(kind)}
        self.number_buffer = None
        self.dropdown_field = None
        self.global_frame_index = 0
        self.global_frame_elapsed = 0.0
        self.status = "已撤销上一步全局修改（尚未应用）。"

    def apply_global(self) -> bool:
        """把 pending 的玩家动画/音效写进 game.json；不动关卡 dirty。"""
        if self.game_path is None:
            self.status = "尚未打开游戏配置，无法应用玩家表现。"
            return False
        animation_data, sound_data = game.player_views_to_object(
            self.player_animation, self.player_sound
        )
        settings = game.load_settings(self.game_path)
        settings[game.PLAYER_ANIMATION_KEY] = animation_data
        settings[game.PLAYER_SOUND_KEY] = sound_data
        try:
            game.save_settings(settings, self.game_path)
        except OSError as error:
            self.status = f"无法保存 game.json：{error}。"
            return False
        self.player_animation_saved = copy.deepcopy(self.player_animation)
        self.player_sound_saved = copy.deepcopy(self.player_sound)
        self.status = "玩家表现已应用到 game.json（所有关卡共用）。"
        return True

    def discard_global(self) -> None:
        """放弃 pending：回到最近一次应用（或读盘时）的状态。"""
        self.player_animation = copy.deepcopy(self.player_animation_saved)
        self.player_sound = copy.deepcopy(self.player_sound_saved)
        self.global_undo_stack.clear()
        if self.global_active():
            kind = self.dialog["kind"]
            self.dialog = {"kind": kind, "entry": self.global_entry(kind)}
        self.number_buffer = None
        self.dropdown_field = None
        self.global_frame_index = 0
        self.global_frame_elapsed = 0.0
        self.status = "已放弃未应用的玩家表现修改。"

    def global_animation_box(self) -> dict | None:
        """玩家动画在关卡里的世界矩形：玩家 AABB 底边中点 + 全局 offset。"""
        player = self.level.player if self.level_in_view else None
        if not isinstance(player, dict) or not isinstance(player.get("pos"), list):
            return None
        size = self.player_animation.get("size") or [1.0, 1.0]
        offset = self.player_animation.get("offset") or [0.0, 0.0]
        player_size = player.get("size") or [1.0, 1.0]
        left = (
            float(player["pos"][0])
            + float(player_size[0]) / 2.0
            + float(offset[0])
            - float(size[0]) / 2.0
        )
        bottom = float(player["pos"][1]) + float(offset[1])
        return {"pos": [left, bottom], "size": [float(size[0]), float(size[1])]}

    def global_animation_frame(self) -> tuple[str, bool] | None:
        """全局玩家动画在画布上的一帧：按玩家初始朝向取 idle；找不到就是没有。"""
        entry = {
            "preset": animation.PRESET_PLAYER,
            "links": self.player_animation.get("links"),
        }
        frames, _, mirror, _ = animation.resolve_for_editor(
            self.animation_library, entry, side=self.player_face()
        )
        if not frames:
            return None
        index = max(0, min(self.global_frame_index, len(frames) - 1))
        path = resolve_level_path(frames[index], self.media_base_dir)
        if path is None:
            return None
        return path, mirror

    def advance_global_animation(self, seconds: float) -> None:
        entry = {
            "preset": animation.PRESET_PLAYER,
            "links": self.player_animation.get("links"),
        }
        frames, holds, _, _ = animation.resolve_for_editor(
            self.animation_library, entry, side=self.player_face()
        )
        if not frames:
            self.global_frame_index = 0
            self.global_frame_elapsed = 0.0
            return
        if len(frames) <= 1:
            self.global_frame_index = 0
            return
        self.global_frame_elapsed += max(0.0, seconds)
        index = max(0, min(self.global_frame_index, len(frames) - 1))
        for _ in range(1000):
            hold = holds[index] if index < len(holds) else animation.DEFAULT_HOLD
            if self.global_frame_elapsed < hold - 1e-9:
                break
            self.global_frame_elapsed = max(0.0, self.global_frame_elapsed - hold)
            index = index + 1 if index + 1 < len(frames) else 0
        self.global_frame_index = index

    def begin_global_grab(self, position: tuple, layout: Layout) -> bool:
        """全局玩家动画的 gizmo：拖框改 offset，拖角改尺寸。"""
        if self.global_kind() != KIND_GLOBAL_ANIMATION:
            return False
        box = self.global_animation_box()
        if box is None:
            return False
        corner = self.handle_at(layout, KIND_ANIMATION, box, position)
        rect = layout.entry_rect(box)
        if corner is None and not rect.collidepoint(position):
            return False
        self.push_global_undo()
        self.global_grab = {
            "corner": corner,
            "start": layout.world_point(position),
            "box": (
                float(box["pos"][0]),
                float(box["pos"][1]),
                float(box["size"][0]),
                float(box["size"][1]),
            ),
            "offset": list(self.player_animation.get("offset") or [0.0, 0.0]),
            "moved": False,
        }
        return True

    def update_global_grab(self, position: tuple, layout: Layout) -> None:
        grab = self.global_grab
        if grab is None:
            return
        point = layout.world_point(position)
        dx = point[0] - grab["start"][0]
        dy = point[1] - grab["start"][1]
        if not grab["moved"] and abs(dx) * layout.tile < 1 and abs(dy) * layout.tile < 1:
            return
        grab["moved"] = True
        corner = grab["corner"]
        if corner is None:
            offset = [
                grab["offset"][0] + dx,
                grab["offset"][1] + dy,
            ]
            if self.snapping:
                offset = [snap(value) for value in offset]
            self.player_animation["offset"] = [round(value, 2) for value in offset]
            return
        left, bottom, width, height = grab["box"]
        right, top = left + width, bottom + height
        if "l" in corner:
            left = point[0]
        if "r" in corner:
            right = point[0]
        if "b" in corner:
            bottom = point[1]
        if "t" in corner:
            top = point[1]
        if self.snapping:
            left, bottom, right, top = (snap(value) for value in (left, bottom, right, top))
        width = max(MIN_SIZE, right - left)
        height = max(MIN_SIZE, top - bottom)
        player = self.level.player if self.level_in_view else None
        if not isinstance(player, dict):
            return
        player_size = player.get("size") or [1.0, 1.0]
        center_x = left + width / 2.0
        self.player_animation["size"] = [round(width, 2), round(height, 2)]
        self.player_animation["offset"] = [
            round(center_x - (float(player["pos"][0]) + float(player_size[0]) / 2.0), 2),
            round(bottom - float(player["pos"][1]), 2),
        ]

    def end_global_grab(self) -> bool:
        grab = self.global_grab
        self.global_grab = None
        if grab is None:
            return False
        if not grab["moved"] and self.global_undo_stack:
            self.global_undo_stack.pop()
        return True

    # ---- 文件：游戏（game.json） ------------------------------------
    def open_game(self, path: str | None = None) -> None:
        """打开一份 game.json：没给路径就弹选择框；打开后请用户挑关卡。"""
        if path is None:
            path = ask_game_file("打开游戏配置文件")
            if not path:
                self.status = "已取消打开游戏配置。"
                return
        settings = game.load_settings(path)
        self.game_path = os.path.abspath(path)
        self.game_player = game.player_of(settings)
        # 动画库快照：画布上的动画对象和「动画…」弹窗都要用；改过并应用之后再刷新
        self.animation_library = animation.from_settings(settings)
        self.animation_object_states = {}
        # 声音库：标题、制作名单、关卡音乐和声音对象都从这里取键
        self.sound_library = sound.library_of(settings)
        self.sound_library_scroll = 0.0
        self.sound_selected = next(iter(self.sound_library), "")
        self.sound_library_dirty = False
        # 物品库：触发源的「物品」链接和 B 背包都从这里取 id
        self.item_library = item.library_of(settings)
        self.item_library_scroll = 0.0
        self.item_selected = next(iter(self.item_library), "")
        self._load_player_views(settings)
        self.startup = False
        self.level = Level()
        self.level_in_view = False
        self.path = None
        self.undo_stack.clear()
        self.dirty = False
        self.dialog = None
        self.dropdown_field = None
        self.selection = []
        self.pick_menu = None
        self.reset_go_list()
        self.marquee_start = None
        self.marquee_current = None
        self.object_grab = None
        self.drag_start = self.drag_current = None
        self.creating = False
        self.name_focused = False
        self.number_buffer = None
        self.zoom = None
        self.pan_x = self.pan_y = 0.0
        self.status = (
            f"已打开游戏配置 {display_path(self.game_path)}"
            f"（标题：{game.title_of(settings)}），请选择关卡。"
        )
        # 打开游戏之后直接把关卡列表摊开：有就挑一关，没有就新建一关
        self.open_level_select()

    def create_game(self) -> None:
        """新建 game.json：选个保存位置，写一份默认设置，然后当成刚打开的游戏。"""
        path = ask_game_file_to_create("新建游戏配置文件")
        if not path:
            self.status = "已取消新建游戏配置。"
            return
        try:
            game.save_settings(game.new_settings(), path)
        except OSError as error:
            self.status = f"无法写入 game.json：{error}。"
            return
        self.open_game(path)

    def request_open_game(self) -> None:
        """换一个游戏：先选 game.json，当前关卡有没保存的修改再问一句。"""
        if self._defer_global(("request_open_game",)):
            return
        path = ask_game_file("打开游戏配置文件")
        if not path:
            self.status = "已取消打开游戏配置。"
            return
        if self.dirty:
            self.pending_switch = ("game", os.path.abspath(path))
            self.status = "当前关卡尚未保存，是否先保存？"
            return
        self.open_game(path)

    # ---- 文件：关卡 -------------------------------------------------
    def begin_new_level(self) -> None:
        """真的开一个新的空关卡：视图里就有它了，关卡设置跟着摊开。"""
        self.level = Level()
        self.level_in_view = True
        self.path = None
        self.pick_menu = None
        self.undo_stack.clear()
        self.dirty = False
        self.dialog = None
        self.dropdown_field = None
        self.selection = []
        self.reset_go_list()
        self.marquee_start = None
        self.marquee_current = None
        self.name_focused = False
        self.number_buffer = None
        self.zoom = None
        self.pan_x = self.pan_y = 0.0
        self.drag_start = self.drag_current = None
        self.level_select_open = False
        self.status = "已新建关卡（尚未保存）。"
        # 新建之后先把关卡设置摊开：名字、尺寸、跳高这些一上来就能填
        self.open_settings()

    def create_level(self) -> None:
        """关卡列表里的「新建关卡」：有没保存的修改就先问。"""
        if self._defer_global(("create_level",)):
            return
        if self.dirty:
            self.level_select_open = False
            self.pending_switch = ("new", "")
            self.status = "当前关卡尚未保存，是否先保存？"
            return
        self.begin_new_level()

    def level_files(self) -> list[str]:
        """当前游戏的 levels/ 里能打开的关卡（列表浮层的内容）。"""
        if self.game_path is None:
            return []
        return game.level_files(self.game_path)

    def open_level_select(self) -> None:
        """摊开关卡列表浮层。"""
        if self._defer_global(("open_level_select",)):
            return
        self.level_select_open = True
        self.level_select_scroll = 0
        self.view_menu_open = False
        self.file_menu_open = False

    def scroll_level_select(self, delta: float) -> None:
        """关卡列表的滚轮：按像素滚（上界在绘制时按内容高度夹住）。"""
        self.level_select_scroll = max(
            0.0, self.level_select_scroll + float(delta) * SCROLL_STEP
        )

    def choose_level(self, path: str) -> None:
        """在列表里选一关：有没保存的修改就先问，别直接丢掉。"""
        name = level_name_of(path)
        if self.path is not None and os.path.normpath(path) == os.path.normpath(self.path):
            self.level_select_open = False
            self.status = f"当前已打开关卡「{name}」。"
            return
        if self._defer_global(("choose_level", path)):
            return
        if self.dirty:
            self.pending_switch = ("level", path)
            self.level_select_open = False
            self.status = f"「{name}」：当前关卡尚未保存，是否先保存？"
            return
        self.load(path)

    def resolve_pending_switch(self, save: bool | None) -> None:
        """等确认的那一步的结果：True 先保存再走，False 直接走，None 取消。"""
        action = self.pending_switch
        if action is None:
            return
        if save is None:
            self.pending_switch = None
            self.status = "已取消操作。"
            return
        if save and not self.save():     # 写盘失败：留在原来这关
            self.pending_switch = None
            return
        self.pending_switch = None
        self.perform_switch(action)

    def perform_switch(self, action: tuple) -> None:
        """真正执行那次切换：打开另一关、换一个游戏，或者新建关卡。"""
        kind, value = action
        if kind == "level":
            self.load(value)
        elif kind == "game":
            self.open_game(value)
        else:
            self.begin_new_level()

    def pending_switch_label(self) -> str:
        """确认框里那个「要切到哪」的名字（后面会接「之前是否保存」）。"""
        if self.pending_switch is None:
            return ""
        kind, value = self.pending_switch
        if kind == "level":
            return f"切换至「{level_name_of(value)}」"
        if kind == "game":
            return f"打开「{display_path(value)}」"
        return "新建关卡"

    def load(self, path: str) -> None:
        """打开关卡的 json：<关卡名>.json 就是这一关的全部数据。"""
        try:
            with open(path, encoding="utf-8") as file:
                definition = json.load(file)
        except (OSError, json.JSONDecodeError) as error:
            self.status = f"打开失败：{error}。"
            return
        before = len(self.sound_library)
        self.level = Level.from_definition(
            definition, self.animation_library, self.sound_library
        )
        if len(self.sound_library) != before:
            self.sound_library_dirty = True        # 老关卡的音乐刚登记进库，保存时一起写
        self.level.name = level_name_of(path)      # 关卡名就是文件名，json 里不写
        self.path = path
        self.level_in_view = True
        self.pick_menu = None
        self.undo_stack.clear()
        self.dirty = False
        self.dialog = None
        self.dropdown_field = None
        self.selection = []                 # 上一个关卡的选中项不能带过来
        self.reset_go_list()
        self.marquee_start = None
        self.marquee_current = None
        self.name_focused = False
        self.number_buffer = None
        self.startup = False
        self.level_select_open = False
        self.zoom = None
        self.pan_x = self.pan_y = 0.0
        self.drag_start = self.drag_current = None
        self.status = f"已打开关卡 {display_path(path)}。"

    def save(self) -> bool:
        """保存当前关卡：写进游戏根里 levels/<关卡名>.json，图片只记相对路径。

        关卡名就是文件名，所以在设置里改了名字，保存时会写到新文件、删掉旧文件。
        缺起点或终点照样写，只是存完弹一句提示（游戏里会跳过这种关卡）。
        返回有没有写下去。
        """
        if not self.level_in_view:
            self.status = "当前视图中没有关卡。"
            return False
        old_path = os.path.normpath(self.path) if self.path else None
        wanted = file_name_for(self.level.name)
        if not str(self.level.name or "").strip() and old_path is not None:
            # 名字空着（比如老版本撤销把名字弄丢过）：沿用当前文件名，别改成「新关卡」
            wanted = level_name_of(old_path)
        if self.levels_dir is None:
            self.status = "尚未打开游戏配置，无法保存关卡。"
            return False
        if self.sound_library_dirty:
            # 老关卡的音乐登记进了声音库：先把库写回 game.json，关卡里的键才不会悬空
            self.write_sound_library()
        if old_path is None:
            path = game.unique_level_path(self.levels_dir, wanted)
        else:
            current_stem = level_name_of(old_path)
            if wanted == current_stem:
                path = old_path
            else:
                # 改了名字：写到新文件，旧文件等写成功再删
                path = game.unique_level_path(self.levels_dir, wanted)
        try:
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
            self.normalize_media_paths()
            with open(path, "w", encoding="utf-8", newline="\n") as file:
                file.write(dump_level(self.level.to_definition()))
        except OSError as error:
            self.status = f"保存失败：{error}。"
            return False
        if old_path is not None and os.path.normpath(path) != old_path:
            try:
                os.remove(old_path)
            except OSError:
                pass                            # 旧文件删不掉也不影响新的
        self.level.name = level_name_of(path)
        self.path = path
        self.dirty = False
        self.status = f"已保存至 {display_path(path)}。"
        missing = self.missing_for_play()
        if missing:
            # 游戏里会把这种关卡跳过：状态栏留一句，另外弹个小提示
            self.status += f" 注意：这一关{missing}，游戏里会跳过它。"
            self.save_notice = missing
        return True

    def close_save_notice(self) -> None:
        """关掉「这关缺起点/终点」的提示。"""
        self.save_notice = ""

    def missing_for_play(self) -> str:
        """这一关还缺什么才能玩：没有起点、没有终点，或者两样都缺。"""
        if self.level.player is None and self.level.destination is None:
            return "既没有起点也没有终点"
        if self.level.player is None:
            return "没有起点"
        if self.level.destination is None:
            return "没有终点"
        return ""

    def normalize_media_paths(self) -> None:
        """背景、贴图、声音库和过场图都只记相对 game.json 的路径，一个文件都不复制。

        相对路径统一写成相对游戏根的正斜杠形式；解析不到的路径原样留着，
        别把用户填的值抹掉。
        """
        base = self.media_base_dir

        def rebased(value: str) -> str | None:
            source = resolve_level_path(value, base)
            if source is None:
                return None
            return relative_level_path(source, base)

        if self.level.background:
            path = rebased(self.level.background)
            if path is not None:
                self.level.background = path
        # 声音库的条目是文件路径；音乐和声音对象只存库里的键，不用改
        for key, entry in self.sound_library.items():
            path = rebased(sound.entry_path(entry))
            if path is not None:
                self.sound_library[key] = {"path": path}
        # 物品库的图标和说明图也都是文件路径
        for entry in self.item_library.values():
            if not isinstance(entry, dict):
                continue
            for field in ("icon", "description"):
                path = rebased(str(entry.get(field) or ""))
                if path is not None:
                    entry[field] = path
        if self.level.cutscene:
            for picture in self.level.cutscene.get("pictures", []):
                value = picture.get("path")
                if not value:
                    continue
                path = rebased(value)
                if path is not None:
                    picture["path"] = path
        for entry in self.level.textures:
            value = entry.get("image")
            if not value:
                continue
            path = rebased(value)
            if path is not None:
                entry["image"] = path

    # ---- 游戏配置（game.json） --------------------------------------
    def open_game_settings(self) -> None:
        """打开游戏配置：常规（标题、玩家参数、画面背景）、动画、制作名单、声音与结尾过场。"""
        if self._defer_global(("open_game_settings",)):
            return
        if self.game_path is None:
            self.status = "尚未打开游戏配置。"
            return
        settings = game.load_settings(self.game_path)
        settings["title"] = game.title_of(settings)
        self.game_settings = settings
        player = game.player_of(settings)
        self.game_numbers = {
            "jump_height": f"{clamp_float(
                player.get('jump_height'), JUMP_HEIGHT_MIN, JUMP_HEIGHT_MAX, JUMP_HEIGHT_DEFAULT
            ):g}",
            "move_speed": f"{clamp_float(
                player.get('move_speed'), MOVE_SPEED_MIN, MOVE_SPEED_MAX, MOVE_SPEED_DEFAULT
            ):g}",
        }
        self.game_cards = game.credit_cards(game.credits_of(settings))
        backgrounds = game.backgrounds_of(settings)
        self.game_backgrounds = {
            key: backgrounds.get(key, "") for key in game.SCREEN_BACKGROUND_KEYS
        }
        block = settings.get(sound.GAME_SOUNDS_KEY)
        block = block if isinstance(block, dict) else {}
        # 声音库先读进来：两幕的声音链接用它换键（老数据的 bgm 路径在这里登记进库）
        before = len(self.sound_library)
        self.game_sound = {
            key: sound.fields_of(block.get(key), self.sound_library)
            for key, _ in sound.SCENE_KEYS
        }
        if len(self.sound_library) != before:
            self.sound_library_dirty = True
        self.sound_selected = next(iter(self.sound_library), "")
        self.sound_library_scroll = 0.0
        self.game_animation_library = animation.from_settings(settings)
        self.animation_selected = next(iter(self.game_animation_library), "")
        self.animation_library_scroll = 0.0
        self.animation_edit = None
        self.animation_link = None
        self.item_library = item.library_of(settings)
        self.item_library_saved = copy.deepcopy(self.item_library)
        self.item_selected = next(iter(self.item_library), "")
        self.item_library_scroll = 0.0
        self.game_card_scroll = 0
        self.game_tab = 0
        self.game_field = 0
        self.cutscene = cutscene.from_value(
            settings.get(cutscene.CUTSCENE_KEY), self.sound_library
        )
        self.cutscene_scope = "game"
        self.cutscene_field = 0
        self.cutscene_scroll = 0
        self.preview.stop()
        self.level_select_open = False
        self.status = (
            "游戏配置：常规、动画集、制作名单、音乐、物品与结尾过场将写入 game.json。"
        )

    def close_game_settings(self, commit: bool) -> None:
        settings = self.game_settings
        cards = self.game_cards
        numbers = self.game_numbers
        sounds = self.game_sound
        cutscene_state = self.cutscene
        animations = self.game_animation_library
        backgrounds = dict(self.game_backgrounds)
        items_saved = self.item_library_saved
        self.item_library_saved = None
        self.game_settings = None
        self.game_cards = []
        self.game_numbers = {}
        self.game_sound = {}
        self.game_backgrounds = {}
        self.game_animation_library = {}
        self.animation_selected = ""
        self.animation_edit = None
        self.animation_link = None
        self.animation_object_states = {}
        self.cutscene = None
        self.preview.stop()                # 试听只在面板开着的时候有意义
        self.sound_menu = None
        if settings is None or not commit or self.game_path is None:
            if not commit and items_saved is not None:
                self.item_library = items_saved      # 取消：物品页的改动一起丢掉
                if self.item_selected not in self.item_library:
                    self.item_selected = next(iter(self.item_library), "")
            return
        title = str(settings.get("title") or "").strip() or game.DEFAULT_TITLE
        settings["title"] = title
        settings["credits"] = game.cards_to_credits(cards)
        player = dict(game.player_of(settings))
        player["jump_height"] = round(
            clamp_float(
                numbers.get("jump_height"), JUMP_HEIGHT_MIN, JUMP_HEIGHT_MAX, JUMP_HEIGHT_DEFAULT
            ),
            2,
        )
        player["move_speed"] = round(
            clamp_float(
                numbers.get("move_speed"), MOVE_SPEED_MIN, MOVE_SPEED_MAX, MOVE_SPEED_DEFAULT
            ),
            2,
        )
        settings["player"] = player
        # 声音：每一幕的四项一直都在，没有声音也写（sound 是空字符串）
        block = {
            key: sound.to_object(sounds.get(key) or {}, keep_empty=True)
            for key, _ in sound.SCENE_KEYS
        }
        settings[sound.GAME_SOUNDS_KEY] = block
        # 声音库：整张表写进去，关卡和声音对象引用的键都在这里
        settings = sound.to_settings(settings, self.sound_library)
        # 标题 / 结算画面的背景：这两个字段一直都在，空着也照写（空字符串就是没有背景）
        settings[game.BACKGROUNDS_KEY] = {
            key: str(backgrounds.get(key) or "").strip()
            for key in game.SCREEN_BACKGROUND_KEYS
        }
        # 结尾过场：图片、级联、声音三个字段一直都在，没有图片也照写
        cutscene_value = cutscene.to_object(
            cutscene_state or cutscene.new_state(), keep_all=True
        )
        settings[cutscene.CUTSCENE_KEY] = cutscene_value
        # 动画库：整张表写进去，老的玩家动画字段顺手删掉
        settings = animation.to_settings(settings, animations)
        # 物品库：触发源按 id 解锁，背包按 id 取图
        settings = item.to_settings(settings, self.item_library)
        try:
            game.save_settings(settings, self.game_path)
        except OSError as error:
            self.status = f"无法保存 game.json：{error}。"
            return
        # 顶栏显示的跳高、速度跟着更新；动画库快照也换成刚保存的这一份
        self.game_player = player
        self.animation_library = animation.from_settings(settings)
        self.sound_library = sound.library_of(settings)
        self.item_library = item.library_of(settings)
        self.sound_library_dirty = False
        names = sum(len(names) for names in settings["credits"].values())
        pictures = len(cutscene_value["pictures"])
        tracks = sum(1 for spec in block.values() if spec.get("sound"))
        library = settings.get(animation.LIBRARY_KEY) or {}
        frames = sum(
            len(clip.get("frames") or [])
            for clip in library.values()
            if isinstance(clip, dict)
        )
        self.status = (
            f"游戏配置已保存：{title}，跳高 {player['jump_height']:g}，"
            f"速度 {player['move_speed']:g}，动画 {len(library)} 条、"
            f"{frames} 帧，制作名单 {len(settings['credits'])} 个职位、"
            f"{names} 个名字，音乐 {tracks} 幕，"
            f"结尾过场 {pictures} 张图。"
        )

    # ---- 游戏配置的分页 ---------------------------------------------
    def game_cutscene_tab(self) -> bool:
        return self.game_tab == GAME_CUTSCENE_TAB

    def game_animation_tab(self) -> bool:
        return self.game_tab == GAME_ANIMATION_TAB

    def game_sound_library_tab(self) -> bool:
        return self.game_tab == GAME_SOUND_LIBRARY_TAB

    def game_item_tab(self) -> bool:
        return self.game_tab == GAME_ITEM_TAB

    def select_game_tab(self, index: int) -> None:
        """点页签切页；换页时把试听停下，选中格回到这一页的第一格。"""
        if not 0 <= index < len(GAME_SETTINGS_TABS) or index == self.game_tab:
            return
        self.preview.stop()
        self.sound_menu = None
        self.game_tab = index
        self.game_field = 0
        self.game_card_scroll = 0
        self.animation_edit = None
        self.animation_link = None
        if index == GAME_CUTSCENE_TAB:
            self.cutscene_field = 0
            self.cutscene_scroll = 0
        elif index == GAME_ANIMATION_TAB:
            self.animation_selected = next(iter(self.game_animation_library), "")
            self.animation_library_scroll = 0.0
            self.animation_edit = None
        elif index == GAME_SOUND_LIBRARY_TAB:
            self.sound_selected = next(iter(self.sound_library), "")
            self.sound_library_scroll = 0.0
        elif index == GAME_ITEM_TAB:
            self.item_selected = next(iter(self.item_library), "")
            self.item_library_scroll = 0.0

    def switch_game_tab(self, delta: int) -> None:
        """Tab / Shift+Tab：在常规、动画集、制作名单、声音、声音库、物品、过场之间转。"""
        self.select_game_tab((self.game_tab + delta) % len(GAME_SETTINGS_TABS))

    # 每一页的格子：常规是标题与两个玩家参数；动画集页没有这种格子；
    # 制作名单是每张卡片的职位、每个名字；声音是标题和制作名单各四项（路径、循环、淡入淡出）。
    def game_cells(self) -> list[tuple]:
        if self.game_tab == 0:
            return [
                ("title",),
                ("jump",),
                ("speed",),
                ("title_bg",),
                ("credits_bg",),
            ]
        if self.game_tab in (
            GAME_ANIMATION_TAB,
            GAME_CUTSCENE_TAB,
            GAME_SOUND_LIBRARY_TAB,
            GAME_ITEM_TAB,
            GAME_PLAYER_VIEW_TAB,
        ):
            return []
        if self.game_tab == 2:              # 制作名单
            cells: list[tuple] = []
            for index, card in enumerate(self.game_cards):
                cells.append(("job", index))
                for name_index in range(len(card["names"])):
                    cells.append(("name", index, name_index))
            return cells
        cells = []
        for key, _ in sound.SCENE_KEYS:
            cells += [("sound", key), ("loop", key), ("fade_in", key), ("fade_out", key)]
        return cells

    def current_game_cell(self) -> tuple:
        cells = self.game_cells()
        if not cells:
            return ("title",)
        return cells[max(0, min(self.game_field, len(cells) - 1))]

    def game_card_index(self) -> int | None:
        """光标所在卡片的下标；光标不在制作名单卡片上时返回 None。"""
        cell = self.current_game_cell()
        return cell[1] if cell[0] in ("job", "name") else None

    def game_field_text(self) -> str:
        """当前选中的那一格里的文字。"""
        if self.game_settings is None:
            return ""
        cell = self.current_game_cell()
        kind = cell[0]
        if kind == "title":
            return str(self.game_settings.get("title") or "")
        if kind == "jump":
            return str(self.game_numbers.get("jump_height") or "")
        if kind == "speed":
            return str(self.game_numbers.get("move_speed") or "")
        if kind in ("title_bg", "credits_bg"):
            return str(self.game_backgrounds.get(kind.removesuffix("_bg")) or "")
        if kind in ("sound", "fade_in", "fade_out"):
            return str(self.game_sound.get(cell[1], {}).get(kind, ""))
        if kind == "loop":
            return ""
        index = cell[1]
        if index >= len(self.game_cards):
            return ""
        card = self.game_cards[index]
        if kind == "job":
            return str(card["job"])
        if cell[2] >= len(card["names"]):
            return ""
        return str(card["names"][cell[2]])

    def set_game_field_text(self, text: str) -> None:
        if self.game_settings is None:
            return
        cell = self.current_game_cell()
        kind = cell[0]
        if kind == "title":
            self.game_settings["title"] = text
        elif kind in ("jump", "speed"):
            key = "jump_height" if kind == "jump" else "move_speed"
            self.game_numbers[key] = text
        elif kind in ("title_bg", "credits_bg"):
            key = kind.removesuffix("_bg")
            if key in self.game_backgrounds:
                self.game_backgrounds[key] = text
        elif kind in ("sound", "fade_in", "fade_out"):
            if cell[1] in self.game_sound:
                self.game_sound[cell[1]][kind] = text
        elif kind == "job" and cell[1] < len(self.game_cards):
            self.game_cards[cell[1]]["job"] = text
        elif kind == "name" and cell[1] < len(self.game_cards):
            card = self.game_cards[cell[1]]
            if cell[2] < len(card["names"]):
                card["names"][cell[2]] = text

    def type_game_settings(self, char: str) -> None:
        """键盘输入：跳高、速度、淡入淡出吃数字和小数点，路径与文字什么都能打。"""
        if self.game_tab == GAME_PLAYER_VIEW_TAB:
            return                  # 玩家表现页只有两个跳转按钮，没有输入格
        if self.game_cutscene_tab():
            self.type_cutscene(char)
            return
        if self.game_animation_tab():
            self.type_animation_delay(char)
            return
        if self.game_sound_library_tab():
            return                      # 声音库页没有输入格
        if self.game_item_tab():
            return                      # 物品页没有输入格
        cell = self.current_game_cell()
        text = self.game_field_text()
        kind = cell[0]
        if kind == "loop":
            return
        if kind == "jump":
            if (char.isdigit() or char == ".") and len(text) < 4:
                self.set_game_field_text(text + char)
            return
        if kind in ("title_bg", "credits_bg"):
            if char.isprintable() and len(text) < BACKGROUND_MAX_LENGTH:
                self.set_game_field_text(text + char)
            return
        if kind == "speed":
            if (char.isdigit() or char == ".") and len(text) < 5:
                self.set_game_field_text(text + char)
            return
        if kind == "sound":
            return                  # 声音是库里的键：用左右键换，不直接敲字
        if kind in ("fade_in", "fade_out"):
            if (char.isdigit() or char == ".") and len(text) < 5:
                self.set_game_field_text(text + char)
            return
        if char.isprintable() and len(text) < NAME_MAX_LENGTH:
            self.set_game_field_text(text + char)

    def erase_game_settings_char(self) -> None:
        if self.game_tab == GAME_PLAYER_VIEW_TAB:
            return
        if self.game_cutscene_tab():
            self.erase_cutscene_char()
            return
        if self.game_animation_tab():
            self.erase_animation_delay_char()
            return
        if self.game_sound_library_tab():
            return                      # 声音库页没有输入格
        if self.game_item_tab():
            return                      # 物品页没有输入格
        if self.current_game_cell()[0] == "sound":
            return                  # 声音是库里的键，退格不删它
        self.set_game_field_text(self.game_field_text()[:-1])

    def adjust_game_number(self, delta: int) -> None:
        """跳高、速度和高低音淡入淡出都按 0.5 一格，循环是开关。"""
        if self.game_cutscene_tab():
            self.adjust_cutscene(delta)
            return
        if self.game_animation_tab():
            self.adjust_animation_hold(delta)
            return
        if self.game_sound_library_tab():
            return                      # 声音库页没有格子
        if self.game_item_tab():
            return                      # 物品页没有数字格
        cell = self.current_game_cell()
        kind = cell[0]
        if kind == "sound":
            fields = self.game_sound.get(cell[1])
            if fields is not None:
                fields["sound"] = _cycle_key(self.sound_library, fields.get("sound"), delta)
            return
        if kind == "loop":
            fields = self.game_sound.get(cell[1])
            if fields is not None:
                fields["loop"] = not bool(fields["loop"])
            return
        if kind in ("fade_in", "fade_out"):
            fields = self.game_sound.get(cell[1])
            if fields is None:
                return
            fallback = (
                sound.DEFAULT_FADE_IN if kind == "fade_in" else sound.DEFAULT_FADE_OUT
            )
            current = clamp_float(fields[kind], 0.0, sound.MAX_FADE_SECONDS, fallback)
            stepped = max(
                0.0, min(sound.MAX_FADE_SECONDS, current + sound.FADE_STEP * delta)
            )
            fields[kind] = f"{stepped:g}"
            return
        if kind == "jump":
            current = clamp_float(
                self.game_numbers.get("jump_height"),
                JUMP_HEIGHT_MIN,
                JUMP_HEIGHT_MAX,
                JUMP_HEIGHT_DEFAULT,
            )
            stepped = max(
                JUMP_HEIGHT_MIN, min(JUMP_HEIGHT_MAX, current + JUMP_HEIGHT_STEP * delta)
            )
            self.game_numbers["jump_height"] = f"{stepped:g}"
            return
        if kind == "speed":
            current = clamp_float(
                self.game_numbers.get("move_speed"),
                MOVE_SPEED_MIN,
                MOVE_SPEED_MAX,
                MOVE_SPEED_DEFAULT,
            )
            stepped = max(MOVE_SPEED_MIN, min(MOVE_SPEED_MAX, current + 0.5 * delta))
            self.game_numbers["move_speed"] = f"{stepped:g}"

    def move_game_field(self, delta: int) -> None:
        """上下键只在当前这一页的格子之间走（动画集页是编辑弹窗里的帧）。"""
        if self.game_cutscene_tab():
            self.move_cutscene_field(delta)
            return
        if self.game_animation_tab():
            self.move_animation_frame(delta)
            return
        if self.game_sound_library_tab():
            return                      # 声音库页用点击选行
        if self.game_item_tab():
            return                      # 物品页用点击选行
        cells = self.game_cells()
        self.game_field = max(0, min(self.game_field + delta, len(cells) - 1))

    # ---- 动画库（游戏配置的「动画集」页） ---------------------------
    def animation_library_items(self) -> list:
        """编辑中的动画库：按名字字母序的 (键, 剪辑)，不分大小写。"""
        return sorted(
            self.game_animation_library.items(), key=lambda pair: pair[0].casefold()
        )

    def animation_library_clip(self, key: str) -> dict | None:
        clip = self.game_animation_library.get(key)
        return clip if isinstance(clip, dict) else None

    def select_animation_key(self, key: str) -> None:
        self.animation_selected = str(key)

    def scroll_animation_page(self, delta: float) -> None:
        """滚轮：编辑弹窗里滚帧格子，否则滚动画列表。"""
        edit = self.animation_edit
        if edit is not None:
            edit["scroll"] = max(0.0, edit["scroll"] + float(delta) * SCROLL_STEP)
            return
        self.animation_library_scroll = max(
            0.0, self.animation_library_scroll + float(delta) * SCROLL_STEP
        )

    def new_animation_name(self) -> str:
        index = 1
        while f"动画{index}" in self.game_animation_library:
            index += 1
        return f"动画{index}"

    def open_animation_edit(self, key: str | None = None) -> None:
        """打开一条动画的编辑弹窗；key 为空就是新建。"""
        if self.animation_edit is not None:
            return
        if key is None:
            original = None
            name = self.new_animation_name()
            clip = animation.new_animation()
        else:
            clip = self.animation_library_clip(key)
            if clip is None:
                self.status = f"找不到动画 {key}。"
                return
            original = key
            name = key
            clip = copy.deepcopy(clip)
        self.animation_edit = {
            "original": original,
            "name": name,
            "frames": list(clip["frames"]),
            "holds": list(clip["holds"]),
            "selected": 0,
            "scroll": 0.0,
            "delay": None,
            "drag": None,
            "name_focus": False,
            "previewing": False,
            "preview_frame": 0,
            "preview_elapsed": 0.0,
            # 弹窗自己的一句提示：校验没过、被引用时都写在这里，别只丢到状态栏
            "notice": "",
            "references": self.animation_key_references(original) if original else [],
        }
        self.status = f"正在编辑动画 {name}。"

    def close_animation_edit(self, commit: bool) -> None:
        """关掉动画弹窗：确定时校验名字、写入动画库并立刻落盘。"""
        edit = self.animation_edit
        if edit is None:
            return
        if not commit:
            self.animation_edit = None
            self.status = "已取消编辑动画。"
            return
        self.commit_animation_delay()
        edit["name_focus"] = False
        name = str(edit["name"]).strip()
        if not name:
            edit["notice"] = "动画名不能为空。"
            self.status = edit["notice"]
            return
        original = edit["original"]
        if name != original and name in self.game_animation_library:
            edit["notice"] = f"已经有一条叫 {name} 的动画了。"
            self.status = edit["notice"]
            return
        if original and name != original:
            references = self.animation_key_references(original)
            if references:
                edit["references"] = references
                edit["notice"] = f"被这些关卡引用着，不能改名：{'、'.join(references)}。"
                self.status = edit["notice"]
                return
        if original:
            self.game_animation_library.pop(original, None)
        self.game_animation_library[name] = {
            "frames": list(edit["frames"]),
            "holds": list(edit["holds"]),
        }
        self.animation_selected = name
        self.animation_edit = None
        self.animation_object_states = {}
        self.write_animation_library()
        self.status = f"已保存动画 {name}（{len(edit['frames'])} 帧）。"

    def animation_key_references(self, key: str) -> list:
        """哪些关卡里还有动画对象链接到这个键（当前关 + 所有已保存关卡）。"""
        if not key:
            return []
        names = []
        current = animation.referenced_keys(
            {"animation_objects": self.level.animation_objects}
        )
        if key in current:
            names.append(self.level.name or "当前关卡")
        if self.game_path is not None:
            for path in game.level_files(self.game_path):
                try:
                    with open(path, encoding="utf-8") as file:
                        definition = json.load(file)
                except (OSError, json.JSONDecodeError):
                    continue
                if not isinstance(definition, dict):
                    continue
                if key not in animation.referenced_keys(definition):
                    continue
                name = level_name_of(path)
                if name not in names:
                    names.append(name)
        return names

    def delete_animation(self, key: str) -> None:
        """删一条动画：被任何关卡引用就拒绝。"""
        if key not in self.game_animation_library:
            return
        references = self.animation_key_references(key)
        if references:
            if self.animation_edit is not None and self.animation_edit["original"] == key:
                self.animation_edit["references"] = references
                self.animation_edit["notice"] = (
                    f"被这些关卡引用着，不能删除：{'、'.join(references)}。"
                )
            self.status = f"动画 {key} 还被这些关卡引用着，不能删除：{'、'.join(references)}。"
            return
        self.game_animation_library.pop(key, None)
        if self.animation_selected == key:
            self.animation_selected = next(iter(self.game_animation_library), "")
        if self.animation_edit is not None and self.animation_edit["original"] == key:
            self.animation_edit = None
        self.animation_object_states = {}
        self.write_animation_library()
        self.status = f"已删除动画 {key}。"

    def write_animation_library(self) -> None:
        """把编辑中的动画库单独写进 game.json（不用等游戏配置的「应用」）。"""
        if self.game_path is None:
            return
        settings = game.load_settings(self.game_path)
        settings = animation.to_settings(settings, self.game_animation_library)
        try:
            game.save_settings(settings, self.game_path)
        except OSError as error:
            self.status = f"无法保存 game.json：{error}。"
            return
        self.animation_library = animation.from_settings(settings)

    # ---- 声音库 -----------------------------------------------------
    def sound_library_items(self) -> list:
        """声音库页的列表：键 → 条目，按名字字母序，不分大小写。"""
        return sorted(
            self.sound_library.items(), key=lambda pair: pair[0].casefold()
        )

    def sound_library_path(self, key: str) -> str | None:
        """键 → 文件的绝对路径；找不到文件返回 None。"""
        return resolve_level_path(sound.path_of(self.sound_library, key), self.media_base_dir)

    def select_sound(self, key: str) -> None:
        self.sound_selected = str(key)

    def scroll_sound_library(self, delta: float) -> None:
        """声音库页的滚轮：按像素滚（上界在绘制时按内容高度夹住）。"""
        self.sound_library_scroll = max(
            0.0, self.sound_library_scroll + float(delta) * SCROLL_STEP
        )

    def import_sound(self) -> str:
        """挑一份音频登记进声音库：只记相对路径，不复制文件；返回新键（取消就是空串）。"""
        path = ask_audio_path("导入声音", self.media_base_dir)
        if not path:
            self.status = "已取消导入声音。"
            return ""
        relative = relative_level_path(path, self.media_base_dir)
        key = sound.ensure_path(self.sound_library, relative)
        self.sound_selected = key
        self.sound_library_dirty = True
        self.write_sound_library()
        self.status = f"已导入声音 {key}：仅记录相对 game.json 的路径，不复制文件。"
        return key

    def delete_sound(self, key: str) -> None:
        """从声音库删掉一个键；还被关卡引用的不许删。"""
        key = str(key or "")
        if key not in self.sound_library:
            self.status = "先选中声音库里的一条。"
            return
        references = self.sound_key_references(key)
        if references:
            self.status = f"声音 {key} 还被这些关卡引用着，不能删除：{'、'.join(references)}。"
            return
        self.sound_library.pop(key, None)
        if self.sound_selected == key:
            self.sound_selected = next(iter(self.sound_library), "")
        self.sound_library_dirty = True
        self.write_sound_library()
        self.status = f"已删除声音 {key}。"

    def sound_key_references(self, key: str) -> list:
        """哪些地方还在引用这个声音：当前关、已保存关卡、游戏配置的两幕和过场。"""
        if not key:
            return []
        names = []
        for scene_key, label in sound.SCENE_KEYS:
            if _uses_sound((self.game_sound or {}).get(scene_key), key):
                names.append(f"游戏配置的{label}音乐")
        if self.cutscene is not None and _uses_sound(self.cutscene.get("sound"), key):
            names.append("过场音乐")
        if _uses_sound(self.level.sound, key):
            names.append(self.level.name or "当前关卡")
        if self.game_path is not None:
            for path in game.level_files(self.game_path):
                if self.path is not None and os.path.normpath(path) == os.path.normpath(self.path):
                    continue
                definition = sound.read_definition(path)
                if definition is None:
                    continue
                if _uses_sound(definition.get("sound"), key):
                    names.append(level_name_of(path))
        return names

    def preview_sound(self, key: str) -> None:
        """试听声音库里的一条；再点一次停。"""
        path = self.sound_library_path(key)
        if path is None:
            self.status = f"找不到这个声音的文件：{sound.key_label(self.sound_library, key)}。"
            return
        self.status = self.preview.toggle(path, False, 0.0)

    # ---- 选 BGM 的下拉 ------------------------------------------------
    def open_sound_menu(self, target: tuple) -> None:
        """在「选择…」按钮下面摊开声音库：target 记着选完写回哪一格。

        target 的写法：("level",) 这一关的音乐、("game", 场景键) 标题/制作名单、
        ("cutscene",) 过场音乐。
        """
        if not self.sound_library:
            self.status = "声音库还是空的：先到游戏配置的「声音库」页导入声音。"
            return
        self.sound_menu = {"target": target, "scroll": 0}
        self.status = "从声音库里挑一个；「（无）」表示这一幕不放音乐。"

    def close_sound_menu(self) -> None:
        self.sound_menu = None

    def sound_menu_value(self) -> str:
        """下拉打开的那一格现在是哪个键。"""
        menu = self.sound_menu
        if menu is None:
            return ""
        target = menu.get("target") or ()
        if target[:1] == ("level",):
            return str((self.settings or {}).get("sound") or "")
        if target[:1] == ("game",) and len(target) > 1:
            return str(self.game_sound.get(target[1], {}).get("sound") or "")
        if target[:1] == ("cutscene",) and self.cutscene is not None:
            return str(self.cutscene.get("sound", {}).get("sound") or "")
        return ""

    def choose_sound_menu(self, key: str) -> None:
        """下拉里点了一条：写回对应的那一格。"""
        menu = self.sound_menu
        if menu is None:
            return
        target = menu.get("target") or ()
        key = str(key or "")
        if target[:1] == ("level",) and self.settings is not None:
            self.settings["sound"] = key
        elif target[:1] == ("game",) and len(target) > 1:
            if target[1] in self.game_sound:
                self.game_sound[target[1]]["sound"] = key
        elif target[:1] == ("cutscene",) and self.cutscene is not None:
            self.cutscene["sound"]["sound"] = key
        self.sound_menu = None
        self.status = f"声音：{sound.key_label(self.sound_library, key)}。"

    def scroll_sound_menu(self, delta: float) -> None:
        """下拉比可视区多时用滚轮翻（上界在绘制时按条数夹住）。"""
        if self.sound_menu is None:
            return
        self.sound_menu["scroll"] = int(self.sound_menu.get("scroll") or 0) + int(delta)

    def write_sound_library(self) -> None:
        """把声音库写进 game.json（导入、删除、老数据登记之后用）。"""
        if self.game_path is None:
            return
        settings = game.load_settings(self.game_path)
        settings = sound.to_settings(settings, self.sound_library)
        try:
            game.save_settings(settings, self.game_path)
        except OSError as error:
            self.status = f"无法保存 game.json：{error}。"
            return
        self.sound_library = sound.library_of(settings)
        self.sound_library_dirty = False

    # ---- 物品库（游戏配置的「物品」页） -----------------------------
    def item_library_items(self) -> list:
        """物品库：按 id 字母序的 (id, 条目)。"""
        return sorted(
            self.item_library.items(), key=lambda pair: pair[0].casefold()
        )

    def item_picture(self, key: str, which: str, size: int):
        """物品条目的图标或说明图，缩成 size×size 给列表/预览；找不到返回 None。"""
        entry = self.item_library.get(str(key or ""))
        if not isinstance(entry, dict):
            return None
        path = resolve_level_path(
            str(entry.get(which) or ""), self.media_base_dir
        )
        if path is None:
            return None
        return load_scaled(path, (size, size), True)

    def select_item(self, key: str) -> None:
        self.item_selected = str(key)

    def scroll_item_library(self, delta: float) -> None:
        """物品页的滚轮：按像素滚（上界在绘制时按内容高度夹住）。"""
        self.item_library_scroll = max(
            0.0, self.item_library_scroll + float(delta) * SCROLL_STEP
        )

    def add_item(self) -> None:
        """选两张图登记一个物品：图标 + 说明图；同一张图标已有条目就更新。"""
        base = self.media_base_dir
        if base is None:
            self.status = "尚未打开游戏配置，无法添加物品。"
            return
        icon = ask_image_path("选择物品图标", base)
        if not icon:
            self.status = "已取消添加物品。"
            return
        description = ask_image_path("选择物品说明图", base)
        if not description:
            self.status = "已取消添加物品。"
            return
        icon_path = relative_level_path(icon, base)
        description_path = relative_level_path(description, base)
        if not icon_path or not description_path:
            self.status = "物品图必须放在游戏根目录里，路径没能换算出来。"
            return
        key = item.key_for(self.item_library, icon_path)
        existed = key in self.item_library
        self.item_library[key] = {
            "icon": icon_path,
            "description": description_path,
        }
        self.item_selected = key
        self.status = (
            f"已更新物品 {key}；点「应用」后写入 game.json。"
            if existed
            else f"已添加物品 {key}；点「应用」后写入 game.json。"
        )

    def replace_item_picture(self, which: str) -> None:
        """换选中物品的图标或说明图；id 不变，触发源的链接也就不断。"""
        key = self.item_selected
        if key not in self.item_library:
            self.status = "先选中物品库里的一条。"
            return
        base = self.media_base_dir
        if base is None:
            return
        title = "选择物品图标" if which == "icon" else "选择物品说明图"
        path = ask_image_path(title, base)
        if not path:
            self.status = "已取消更换物品图片。"
            return
        relative = relative_level_path(path, base)
        if not relative:
            self.status = "图片必须放在游戏根目录里，路径没能换算出来。"
            return
        self.item_library[key][which] = relative
        self.status = f"已更新物品 {key}；点「应用」后写入 game.json。"

    def delete_item(self, key: str) -> None:
        """删掉一个物品；还被触发源引用着的不能删。"""
        key = str(key or "")
        if key not in self.item_library:
            self.status = "先选中物品库里的一条。"
            return
        references = self.item_key_references(key)
        if references:
            self.status = (
                f"物品 {key} 还被这些关卡引用着，不能删除："
                f"{'、'.join(references)}。"
            )
            return
        keys = [name for name, _ in self.item_library_items()]
        index = keys.index(key)
        self.item_library.pop(key, None)
        keys.remove(key)
        self.item_selected = keys[min(index, len(keys) - 1)] if keys else ""
        self.status = f"已删除物品 {key}；点「应用」后写入 game.json。"

    def item_key_references(self, key: str) -> list:
        """哪些关卡还有触发源引用这个物品：当前关卡 + 已保存的关卡。"""
        if not key:
            return []
        names = []
        if self.level_in_view and any(
            str(source.get("item") or "").strip() == key
            for source in self.level.trigger_sources
            if isinstance(source, dict)
        ):
            names.append(self.level.name or "当前关卡")
        if self.game_path is not None:
            for path in game.level_files(self.game_path):
                if self.path is not None and os.path.normpath(path) == os.path.normpath(
                    self.path
                ):
                    continue
                definition = sound.read_definition(path)
                if definition is not None and item.references_in(definition, key):
                    names.append(level_name_of(path))
        return names

    # ---- 动画弹窗里的帧 ---------------------------------------------
    def animation_edit_frames(self) -> list:
        edit = self.animation_edit
        return list(edit["frames"]) if edit is not None else []

    def animation_edit_holds(self) -> list:
        edit = self.animation_edit
        return list(edit["holds"]) if edit is not None else []

    def select_animation_frame(self, index: int) -> None:
        edit = self.animation_edit
        if edit is None:
            return
        frames = edit["frames"]
        edit["selected"] = 0 if not frames else max(0, min(index, len(frames) - 1))
        edit["previewing"] = False

    def move_animation_frame(self, delta: int) -> None:
        edit = self.animation_edit
        if edit is not None:
            self.select_animation_frame(edit["selected"] + delta)

    def add_animation_frames(self) -> None:
        """给正在编辑的动画加帧：一张图片加一帧，GIF 拆成同名文件夹里的一串 PNG。"""
        edit = self.animation_edit
        if edit is None:
            return
        path = ask_image_path("添加动画帧", self.media_base_dir)
        if not path:
            self.status = "已取消添加动画帧。"
            return
        try:
            frames, holds = import_animation_frames(path, self.media_base_dir)
        except AnimationImportError as error:
            self.status = f"添加动画帧失败：{error}"
            return
        first = len(edit["frames"])
        if holds is None:                   # 单张图片：沿用上一帧的时长
            hold = (
                edit["holds"][-1]
                if edit["holds"]
                else animation.hold_text(animation.DEFAULT_HOLD)
            )
            holds = [hold]
        edit["frames"].extend(frames)
        edit["holds"].extend(animation.hold_text(value) for value in holds)
        edit["selected"] = first
        edit["previewing"] = False
        if len(frames) > 1:
            folder = os.path.splitext(os.path.basename(path))[0]
            self.status = f"已把 GIF 拆成 {len(frames)} 帧放进 {folder}/。"
        else:
            self.status = f"已加一帧，共 {len(edit['frames'])} 帧。"

    def remove_animation_frame(self) -> None:
        edit = self.animation_edit
        if edit is None or not edit["frames"]:
            return
        index = max(0, min(edit["selected"], len(edit["frames"]) - 1))
        del edit["frames"][index]
        if index < len(edit["holds"]):
            del edit["holds"][index]
        edit["selected"] = max(0, min(index, len(edit["frames"]) - 1))
        edit["previewing"] = False
        self.status = "已删除一帧。"

    def move_animation_frame_to(self, frame_index: int, slot: int) -> bool:
        """编辑弹窗里拖动换顺序：帧和它的时长一起挪。"""
        edit = self.animation_edit
        if edit is None:
            return False
        frames = edit["frames"]
        if not 0 <= frame_index < len(frames):
            return False
        target = slot - (1 if frame_index < slot else 0)
        target = max(0, min(target, len(frames) - 1))
        if target == frame_index:
            return False
        frames.insert(target, frames.pop(frame_index))
        holds = edit["holds"]
        if frame_index < len(holds):
            hold = holds.pop(frame_index)
            holds.insert(min(target, len(holds)), hold)
        edit["selected"] = target
        edit["previewing"] = False
        return True

    def begin_animation_frame_drag(self, index: int, position: tuple) -> None:
        edit = self.animation_edit
        if edit is None:
            return
        edit["drag"] = {
            "from": index,
            "slot": index,
            "start": position,
            "moved": False,
        }

    def update_animation_frame_drag(self, position: tuple, page: dict) -> None:
        edit = self.animation_edit
        if edit is None or edit["drag"] is None:
            return
        drag = edit["drag"]
        if not drag["moved"]:
            dx = position[0] - drag["start"][0]
            dy = position[1] - drag["start"][1]
            if abs(dx) < animation.DRAG_THRESHOLD and abs(dy) < animation.DRAG_THRESHOLD:
                return
            drag["moved"] = True
        grid = page["grid"]
        columns = max(1, int(page.get("columns") or 1))
        step_x = page.get("cell_width", 100) + page.get("cell_gap", 8)
        step_y = page.get("cell_height", 100) + page.get("cell_gap", 8)
        local_x = position[0] - grid.left
        local_y = position[1] - grid.top + float(page.get("scroll") or 0.0)
        column = max(0, min(columns - 1, int(local_x // step_x)))
        row = max(0, int(local_y // step_y))
        slot = row * columns + column
        if local_x % step_x > step_x / 2:
            slot += 1
        drag["slot"] = max(0, min(slot, int(page.get("count") or 0)))

    def finish_animation_frame_drag(self) -> None:
        edit = self.animation_edit
        if edit is None or edit["drag"] is None:
            return
        drag = edit["drag"]
        edit["drag"] = None
        if not drag["moved"]:
            return
        if self.move_animation_frame_to(drag["from"], drag["slot"]):
            self.status = f"已把第 {drag['from'] + 1} 帧挪到第 {edit['selected'] + 1} 帧。"

    def cancel_animation_frame_drag(self) -> None:
        if self.animation_edit is not None:
            self.animation_edit["drag"] = None

    # ---- 每帧时长的输入 ---------------------------------------------
    def animation_delay_active(self) -> bool:
        edit = self.animation_edit
        return edit is not None and edit["delay"] is not None

    def begin_animation_delay_edit(self, index: int) -> None:
        edit = self.animation_edit
        if edit is None or not 0 <= index < len(edit["frames"]):
            return
        self.commit_animation_delay()
        edit["selected"] = index
        edit["previewing"] = False
        edit["delay"] = {
            "index": index,
            "text": animation.hold_text(edit["holds"][index]),
            "fresh": True,
        }
        self.status = f"第 {index + 1} 帧的停留秒数：敲数字后回车，Esc 取消。"

    def type_animation_delay(self, char: str) -> None:
        edit = self.animation_edit
        if edit is None or edit["delay"] is None:
            return
        if not (char.isdigit() or char == "."):
            return
        delay = edit["delay"]
        if delay["fresh"]:
            delay["text"] = char
            delay["fresh"] = False
            return
        if len(delay["text"]) < 5:
            delay["text"] += char

    def erase_animation_delay_char(self) -> None:
        edit = self.animation_edit
        if edit is None or edit["delay"] is None:
            return
        delay = edit["delay"]
        if delay["fresh"]:
            delay["text"] = ""
            delay["fresh"] = False
            return
        delay["text"] = delay["text"][:-1]

    def commit_animation_delay(self) -> None:
        edit = self.animation_edit
        if edit is None or edit["delay"] is None:
            return
        delay = edit["delay"]
        edit["delay"] = None
        index = delay["index"]
        if 0 <= index < len(edit["holds"]):
            edit["holds"][index] = animation.hold_text(delay["text"])

    def cancel_animation_delay(self) -> None:
        edit = self.animation_edit
        if edit is not None and edit["delay"] is not None:
            edit["delay"] = None
            self.status = "已取消修改时长。"

    def adjust_animation_hold(self, delta: int) -> None:
        edit = self.animation_edit
        if edit is None or not edit["frames"]:
            return
        index = max(0, min(edit["selected"], len(edit["frames"]) - 1))
        current = animation.holds_of({"frames": edit["frames"], "holds": edit["holds"]})[index]
        value = max(
            animation.MIN_HOLD,
            min(animation.MAX_HOLD, current + animation.HOLD_STEP * delta),
        )
        edit["holds"][index] = animation.hold_text(round(value, 2))
        edit["selected"] = index
        edit["previewing"] = False
        self.status = f"第 {index + 1} 帧：停留 {edit['holds'][index]} 秒。"

    def toggle_animation_edit_preview(self) -> None:
        edit = self.animation_edit
        if edit is None or not edit["frames"]:
            return
        self.commit_animation_delay()
        edit["previewing"] = not edit["previewing"]
        edit["preview_frame"] = max(0, min(edit["selected"], len(edit["frames"]) - 1))
        edit["preview_elapsed"] = 0.0

    def close_animation_preview(self) -> None:
        """关掉预览弹窗，回到编辑帧的界面。"""
        edit = self.animation_edit
        if edit is not None and edit["previewing"]:
            edit["previewing"] = False

    def advance_animation_edit(self, seconds: float) -> None:
        """弹窗里的预览：按每帧时长循环播放（编辑器里只看效果，不跟 loop 停住）。"""
        edit = self.animation_edit
        if edit is None or not edit["previewing"] or not edit["frames"]:
            return
        frames = edit["frames"]
        holds = animation.holds_of({"frames": frames, "holds": edit["holds"]})
        index = max(0, min(edit["preview_frame"], len(frames) - 1))
        edit["preview_elapsed"] += max(0.0, seconds)
        for _ in range(1000):
            hold = holds[index] if index < len(holds) else animation.DEFAULT_HOLD
            if edit["preview_elapsed"] < hold - 1e-9:
                break
            edit["preview_elapsed"] = max(0.0, edit["preview_elapsed"] - hold)
            index = (index + 1) % len(frames)
        edit["preview_frame"] = index

    def animation_edit_shown_frame(self) -> int:
        edit = self.animation_edit
        if edit is None:
            return 0
        if edit["previewing"] and edit["frames"]:
            return max(0, min(edit["preview_frame"], len(edit["frames"]) - 1))
        return max(0, min(edit["selected"], max(0, len(edit["frames"]) - 1)))

    # ---- 动画名的输入 -----------------------------------------------
    def focus_animation_name(self) -> None:
        edit = self.animation_edit
        if edit is None:
            return
        self.commit_animation_delay()
        edit["name_focus"] = True
        self.status = "正在改动画名；回车或点别处结束。"

    def blur_animation_name(self) -> None:
        if self.animation_edit is not None:
            self.animation_edit["name_focus"] = False

    def type_animation_name(self, char: str) -> None:
        edit = self.animation_edit
        if edit is None or not edit["name_focus"] or not char.isprintable():
            return
        if len(edit["name"]) < animation.NAME_MAX_LENGTH:
            edit["name"] += char
            edit["notice"] = ""

    def erase_animation_name_char(self) -> None:
        edit = self.animation_edit
        if edit is None or not edit["name_focus"]:
            return
        edit["name"] = edit["name"][:-1]
        edit["notice"] = ""

    # ---- 画布上的动画对象 -------------------------------------------
    def animation_object_frame(self, entry: dict) -> tuple[str, bool] | None:
        """动画对象这一刻该画的图：(绝对路径, 要不要镜像)；没有就不画。"""
        frames, _, mirror, _ = animation.resolve_for_editor(self.animation_library, entry)
        if not frames:
            return None
        state = self.animation_object_states.get(id(entry)) or {}
        index = max(0, min(int(state.get("frame") or 0), len(frames) - 1))
        path = resolve_level_path(frames[index], self.media_base_dir)
        if path is None:
            return None
        return path, mirror

    def advance_animation_objects(self, seconds: float) -> None:
        """画布上的动画对象按自己的帧、时长和动作的循环规则播放。"""
        for entry in self.level.animation_objects:
            frames, holds, _, action = animation.resolve_for_editor(
                self.animation_library, entry
            )
            loop = animation.loops(action)
            signature = (action, tuple(frames), bool(loop))
            state = self.animation_object_states.get(id(entry))
            if state is None or state.get("signature") != signature:
                state = {"signature": signature, "frame": 0, "elapsed": 0.0}
                self.animation_object_states[id(entry)] = state
            if len(frames) <= 1:
                state["frame"] = 0
                continue
            state["elapsed"] += max(0.0, seconds)
            index = state["frame"]
            for _ in range(1000):
                hold = holds[index] if index < len(holds) else animation.DEFAULT_HOLD
                if state["elapsed"] < hold - 1e-9:
                    break
                state["elapsed"] = max(0.0, state["elapsed"] - hold)
                if index + 1 < len(frames):
                    index += 1
                elif loop:
                    index = 0
                else:
                    state["elapsed"] = 0.0
                    break
            state["frame"] = index

    # ---- 动画对象：跟随与链接弹窗 -----------------------------------
    def animation_follow_options(self) -> list:
        """跟随下拉：无 / 关卡里有名字的对象；玩家现在由全局玩家动画单独负责。"""
        options = [("无", "")]
        seen = set()
        for entries in (
            self.level.movable_blocks,
            self.level.trigger_sources,
            self.level.portals,
        ):
            for entry in entries:
                name = str(entry.get("name") or "").strip()
                if name and name not in seen:
                    seen.add(name)
                    options.append((name, name))
        return options

    def animation_follow_label(self, value) -> str:
        value = str(value or "")
        if not value:
            return "无"
        if value == "@player":
            return "玩家"
        return value

    def animation_link_button_label(self, entry: dict) -> str:
        return f"动画…（{animation.preset_label(animation.preset_of(entry))}）"

    def open_animation_link(self, entry: dict) -> None:
        if not isinstance(entry, dict):
            return
        self.commit_animation_delay()
        self.animation_link = {
            "entry": entry,
            "preset": animation.preset_of(entry),
            "links": copy.deepcopy(animation.links_of(entry, self.animation_library)),
            "dropdown": None,
            "dropdown_scroll": 0,
        }
        self.status = "编辑这个动画对象的动画链接；确定后随关卡保存。"

    def open_global_animation_link(self) -> None:
        """全局玩家动画的链接弹窗：预设固定玩家，不碰关卡。"""
        self.animation_link = {
            "entry": self.player_animation,
            "preset": animation.PRESET_PLAYER,
            "links": copy.deepcopy(
                animation.links_of(self.player_animation, self.animation_library)
            ),
            "dropdown": None,
            "dropdown_scroll": 0,
            "global": True,
        }
        self.status = "编辑所有关卡共用的玩家动画链接；应用后写入 game.json。"

    def close_animation_link(self, commit: bool) -> None:
        link = self.animation_link
        self.animation_link = None
        if link is None or not commit:
            if link is not None:
                self.status = "已取消编辑动画链接。"
            return
        if link.get("global"):
            new_links = copy.deepcopy(link["links"])
            if new_links == self.player_animation.get("links"):
                self.status = "玩家动画链接没有变化。"
                return
            self.push_global_undo()
            self.player_animation["links"] = new_links
            self.status = "玩家动画链接已更新（尚未应用）。"
            return
        entry = link["entry"]
        self.push_undo()
        entry["preset"] = link["preset"]
        entry["links"] = copy.deepcopy(link["links"])
        self.dirty = True
        self.status = (
            f"动画对象：预设 {animation.preset_label(link['preset'])}，链接已更新。"
        )

    def set_animation_link_preset(self, preset: str) -> None:
        link = self.animation_link
        if link is None or link.get("global"):
            return
        if preset not in (animation.PRESET_GENERAL, animation.PRESET_PLAYER):
            return
        link["preset"] = preset
        link["dropdown"] = None

    def animation_link_value(self, field: tuple) -> str:
        link = self.animation_link
        if link is None:
            return ""
        preset, action, side = field
        return animation.link_key(link["links"], preset, action, side)

    def animation_link_options(self) -> list:
        return [("（未选择）", "")] + [
            (key, key) for key in sorted(self.animation_library)
        ]

    def toggle_animation_link_dropdown(self, field: tuple) -> None:
        link = self.animation_link
        if link is None:
            return
        link["dropdown"] = None if link["dropdown"] == field else field
        link["dropdown_scroll"] = 0

    def close_animation_link_dropdown(self) -> None:
        if self.animation_link is not None:
            self.animation_link["dropdown"] = None

    def scroll_animation_link_popup(self, delta: float) -> None:
        """下拉列表比能放的多时，用滚轮往下翻。"""
        link = self.animation_link
        if link is None or link["dropdown"] is None:
            return
        options = (
            2 if link["dropdown"] == "preset" else len(self.animation_link_options())
        )
        visible = min(8, options)
        limit = max(0, options - visible)
        scroll = int(link.get("dropdown_scroll") or 0) + int(delta)
        link["dropdown_scroll"] = max(0, min(scroll, limit))

    def choose_animation_link(self, key: str) -> None:
        link = self.animation_link
        if link is None or link["dropdown"] is None:
            return
        preset, action, side = link["dropdown"]
        animation.set_link(link["links"], preset, action, side, str(key or ""))
        link["dropdown"] = None

    # ---- 声音对象的链接弹窗 -----------------------------------------
    def sound_link_button_label(self, entry: dict) -> str:
        return f"声音…（{sound.preset_label(sound.preset_of(entry))}）"

    def open_sound_link(self, entry: dict) -> None:
        """打开声音对象的链接弹窗：通用一条，玩家按六个动作各一条。"""
        if not isinstance(entry, dict):
            return
        self.sound_link = {
            "entry": entry,
            "preset": sound.preset_of(entry),
            "links": copy.deepcopy(sound.object_links_of(entry)),
            "dropdown": None,
            "dropdown_scroll": 0,
        }
        self.status = "编辑这个声音对象的链接；确定后随关卡保存。"

    def open_global_sound_link(self) -> None:
        """全局玩家音效的链接弹窗：预设固定玩家，不碰关卡。"""
        self.sound_link = {
            "entry": self.player_sound,
            "preset": sound.PRESET_PLAYER,
            "links": copy.deepcopy(sound.object_links_of(self.player_sound)),
            "dropdown": None,
            "dropdown_scroll": 0,
            "global": True,
        }
        self.status = "编辑所有关卡共用的玩家音效；应用后写入 game.json。"

    def close_sound_link(self, commit: bool) -> None:
        link = self.sound_link
        self.sound_link = None
        if link is None:
            return
        if not commit:
            self.status = "已取消编辑声音链接。"
            return
        if link.get("global"):
            new_links = copy.deepcopy(link["links"])
            if new_links == self.player_sound.get("links"):
                self.status = "玩家音效链接没有变化。"
                return
            self.push_global_undo()
            self.player_sound["links"] = new_links
            self.status = "玩家音效链接已更新（尚未应用）。"
            return
        entry = link["entry"]
        self.push_undo()
        entry["preset"] = link["preset"]
        entry["links"] = copy.deepcopy(link["links"])
        self.dirty = True
        self.status = (
            f"声音对象：预设 {sound.preset_label(link['preset'])}，链接已更新。"
        )

    def sound_link_field(self, field: tuple) -> tuple:
        """弹窗里的字段号：(预设, 动作)；通用预设没有动作。"""
        preset = field[0] if field else sound.PRESET_GENERAL
        action = field[1] if len(field) > 1 else ""
        return preset, action

    def sound_link_value(self, field: tuple) -> str:
        link = self.sound_link
        if link is None:
            return ""
        preset, action = self.sound_link_field(field)
        return str(sound.object_link(link["links"], preset, action).get("sound") or "")

    def sound_link_options(self) -> list:
        return [("（未选择）", "")] + [
            (sound.key_label(self.sound_library, key), key)
            for key in sorted(self.sound_library)
        ]

    def toggle_sound_link_dropdown(self, field: tuple) -> None:
        link = self.sound_link
        if link is None:
            return
        link["dropdown"] = None if link["dropdown"] == field else field
        link["dropdown_scroll"] = 0

    def close_sound_link_dropdown(self) -> None:
        if self.sound_link is not None:
            self.sound_link["dropdown"] = None

    def scroll_sound_link_popup(self, delta: float) -> None:
        """下拉列表比能放的多时，用滚轮往下翻。"""
        link = self.sound_link
        if link is None or link["dropdown"] is None:
            return
        total = len(self.sound_link_options())
        visible = min(8, total)
        limit = max(0, total - visible)
        scroll = int(link.get("dropdown_scroll") or 0) + int(delta)
        link["dropdown_scroll"] = max(0, min(scroll, limit))

    def choose_sound_link(self, key: str) -> None:
        link = self.sound_link
        if link is None or link["dropdown"] is None:
            return
        preset, action = self.sound_link_field(link["dropdown"])
        sound.set_object_link(link["links"], preset, action, str(key or ""))
        link["dropdown"] = None

    def scroll_game_cards(self, delta: float) -> None:
        """滚轮：制作名单按像素上下滚（上界在几何里按内容高度夹住）；过场页走它自己的滚动。"""
        if self.game_cutscene_tab():
            self.scroll_cutscene(delta)
            return
        if self.game_animation_tab():
            self.scroll_animation_page(delta)
            return
        if self.game_item_tab():
            self.scroll_item_library(delta)
            return
        self.game_card_scroll = max(
            0.0, self.game_card_scroll + float(delta) * SCROLL_STEP
        )

    def add_credit_card(self) -> None:
        """加一张职位卡片：职位和名字都空着，光标落在职位上。"""
        self.game_cards.append({"job": "", "names": []})
        self.game_field = self.game_cells().index(("job", len(self.game_cards) - 1))
        self.status = "已添加一个职位，请填写职位名，再用「＋」添加名字。"

    def remove_credit_card(self) -> None:
        """删掉光标所在的那张职位卡片。"""
        index = self.game_card_index()
        if index is None or index >= len(self.game_cards):
            self.status = "请先选中一个职位卡片，再执行删除。"
            return
        del self.game_cards[index]
        self.game_field = min(self.game_field, len(self.game_cells()) - 1)
        self.status = "已删除一个职位卡片。"

    def add_credit_name(self, card_index: int) -> None:
        """给某张卡片加一个空名字，光标落到新名字上。"""
        if not 0 <= card_index < len(self.game_cards):
            return
        names = self.game_cards[card_index]["names"]
        names.append("")
        self.game_field = self.game_cells().index(("name", card_index, len(names) - 1))
        self.status = "已添加一个名字，直接输入内容即可。"

    def remove_credit_name(self, card_index: int, name_index: int) -> None:
        """删掉某个名字；一个名字都不剩也是合法的（空数组）。"""
        if not 0 <= card_index < len(self.game_cards):
            return
        names = self.game_cards[card_index]["names"]
        if not 0 <= name_index < len(names):
            return
        del names[name_index]
        self.game_field = min(self.game_field, len(self.game_cells()) - 1)
        self.status = "已删除一个名字。"

    # ---- 游戏配置的声音页 -------------------------------------------
    def preview_game_audio(self, key: str) -> None:
        """试听标题或制作名单：按这一页的循环与淡入放，再点一次停。"""
        fields = self.game_sound.get(key)
        if fields is None:
            return
        path = self.sound_library_path(fields.get("sound"))
        if path is None:
            self.preview.stop()
            self.status = f"找不到这首曲子：{sound.key_label(self.sound_library, fields.get('sound'))}。"
            return
        self.status = self.preview.toggle(
            path,
            bool(fields["loop"]),
            clamp_float(fields["fade_in"], 0.0, sound.MAX_FADE_SECONDS, sound.DEFAULT_FADE_IN),
        )

    def pick_game_background(self, key: str) -> None:
        """给标题或结算画面挑一张背景：只记路径，不复制文件。"""
        if self.game_settings is None or key not in self.game_backgrounds:
            return
        path = ask_image_path("选择背景图片", self.media_base_dir)
        if not path:
            self.status = "已取消选择背景图片。"
            return
        self.game_backgrounds[key] = relative_level_path(path, self.media_base_dir)
        self.game_field = self.game_cells().index((f"{key}_bg",))
        self.status = "已选择背景图片：仅记录相对 game.json 的路径，不复制文件。"

    def _rebase_sound(self, fields: dict) -> dict:
        """声音链接只存库里的键，路径在库里，打开游戏时不用改。"""
        return fields

    # ---- 过场编辑（关卡设置 / 游戏配置的过场页） ---------------------
    def cutscene_cells(self) -> list[tuple]:
        """过场页的格子，顺序就是上下键的方向：级联、声音，然后每张图四格。"""
        state = self.cutscene
        if state is None:
            return []
        cells: list[tuple] = [("cascade",), ("sound_mode",)]
        if state["sound_mode"] == cutscene.SOUND_MODE_CUSTOM:
            cells += [
                ("sound_bgm",),
                ("sound_loop",),
                ("sound_fade_in",),
                ("sound_fade_out",),
            ]
        for index in range(len(state["pictures"])):
            cells += [("path", index), ("fade_in", index), ("hold", index), ("fade_out", index)]
        return cells

    def current_cutscene_cell(self) -> tuple:
        cells = self.cutscene_cells()
        if not cells:
            return ("cascade",)
        return cells[max(0, min(self.cutscene_field, len(cells) - 1))]

    def set_cutscene_field(self, cell: tuple) -> None:
        cells = self.cutscene_cells()
        if cell in cells:
            self.cutscene_field = cells.index(cell)
            self.keep_cutscene_visible()

    def cutscene_picture_index(self) -> int | None:
        """选中的是某张图的格子时返回图片下标，否则 None。"""
        cell = self.current_cutscene_cell()
        return cell[1] if cell[0] in ("path", "fade_in", "hold", "fade_out") else None

    def set_cutscene_cascade(self) -> None:
        if self.cutscene is None:
            return
        self.cutscene["cascade"] = not bool(self.cutscene["cascade"])
        self.set_cutscene_field(("cascade",))

    def set_cutscene_sound_mode(self, mode: str) -> None:
        """过场声音：无 / 跟随本幕 / 指定。"""
        if self.cutscene is None or mode not in cutscene.SOUND_ORDER:
            return
        self.cutscene["sound_mode"] = mode
        self.set_cutscene_field(("sound_mode",))
        self.status = (
            f"过场声音：{cutscene.sound_mode_label(self.cutscene_scope, mode)}。"
        )

    def cutscene_field_text(self) -> str:
        state = self.cutscene
        if state is None:
            return ""
        cell = self.current_cutscene_cell()
        kind = cell[0]
        if kind in ("path", "fade_in", "hold", "fade_out"):
            index = cell[1]
            if index >= len(state["pictures"]):
                return ""
            return str(state["pictures"][index][kind])
        if kind == "sound_bgm":
            return str(state["sound"]["sound"])
        if kind in ("sound_fade_in", "sound_fade_out"):
            key = "fade_in" if kind == "sound_fade_in" else "fade_out"
            return str(state["sound"][key])
        return ""

    def set_cutscene_field_text(self, text: str) -> None:
        state = self.cutscene
        if state is None:
            return
        cell = self.current_cutscene_cell()
        kind = cell[0]
        if kind in ("path", "fade_in", "hold", "fade_out"):
            index = cell[1]
            if index < len(state["pictures"]):
                state["pictures"][index][kind] = text
        elif kind in ("sound_fade_in", "sound_fade_out"):
            state["sound"]["fade_in" if kind == "sound_fade_in" else "fade_out"] = text

    def move_cutscene_field(self, delta: int) -> None:
        cells = self.cutscene_cells()
        if not cells:
            return
        self.cutscene_field = max(0, min(self.cutscene_field + delta, len(cells) - 1))
        self.keep_cutscene_visible()

    def keep_cutscene_visible(self) -> None:
        """光标落在某张图的格子上时，把那张卡片滚进视野。"""
        index = self.cutscene_picture_index()
        if index is None or self.cutscene_card_step <= 0.0:
            return
        top = index * self.cutscene_card_step
        bottom = top + self.cutscene_card_step
        height = max(1.0, self.cutscene_area_height)
        if top < self.cutscene_scroll:
            self.cutscene_scroll = top
        elif bottom > self.cutscene_scroll + height:
            self.cutscene_scroll = bottom - height

    def scroll_cutscene(self, delta: float) -> None:
        """过场卡片的滚轮：按像素滚（上界在绘制时按内容高度夹住）。"""
        if self.cutscene is None:
            return
        self.cutscene_scroll = max(
            0.0, self.cutscene_scroll + float(delta) * SCROLL_STEP
        )

    def adjust_cutscene(self, delta: int) -> None:
        """←→ 和面板上的加减：时间 ±0.5，复选框/声音模式切换。"""
        state = self.cutscene
        if state is None:
            return
        cell = self.current_cutscene_cell()
        kind = cell[0]
        if kind in ("fade_in", "fade_out", "hold"):
            index = cell[1]
            if index >= len(state["pictures"]):
                return
            limit = cutscene.HOLD_MAX_SECONDS if kind == "hold" else cutscene.FADE_MAX_SECONDS
            current = clamp_float(state["pictures"][index][kind], 0.0, limit, 0.0)
            value = max(0.0, min(limit, current + cutscene.STEP_SECONDS * delta))
            state["pictures"][index][kind] = f"{value:g}"
        elif kind == "cascade":
            self.set_cutscene_cascade()
        elif kind == "sound_mode":
            index = cutscene.SOUND_ORDER.index(state["sound_mode"])
            mode = cutscene.SOUND_ORDER[(index + delta) % len(cutscene.SOUND_ORDER)]
            self.set_cutscene_sound_mode(mode)
        elif kind == "sound_loop":
            state["sound"]["loop"] = not bool(state["sound"]["loop"])
        elif kind == "sound_bgm":
            state["sound"]["sound"] = _cycle_key(
                self.sound_library, state["sound"].get("sound"), delta
            )
        elif kind in ("sound_fade_in", "sound_fade_out"):
            key = "fade_in" if kind == "sound_fade_in" else "fade_out"
            current = clamp_float(
                state["sound"][key], 0.0, sound.MAX_FADE_SECONDS, sound.DEFAULT_FADE_IN
            )
            value = max(
                0.0, min(sound.MAX_FADE_SECONDS, current + sound.FADE_STEP * delta)
            )
            state["sound"][key] = f"{value:g}"

    def type_cutscene(self, char: str) -> None:
        """键盘输入：路径什么都能打，时间只吃数字和小数点。"""
        if self.cutscene is None:
            return
        cell = self.current_cutscene_cell()
        kind = cell[0]
        text = self.cutscene_field_text()
        if kind == "path":
            if char.isprintable() and len(text) < cutscene.PICTURE_PATH_MAX_LENGTH:
                self.set_cutscene_field_text(text + char)
        elif kind in ("fade_in", "fade_out", "hold", "sound_fade_in", "sound_fade_out"):
            if (char.isdigit() or char == ".") and len(text) < 5:
                self.set_cutscene_field_text(text + char)

    def erase_cutscene_char(self) -> None:
        if self.cutscene is None:
            return
        cell = self.current_cutscene_cell()
        if cell[0] in ("cascade", "sound_mode", "sound_loop", "sound_bgm"):
            return
        self.set_cutscene_field_text(self.cutscene_field_text()[:-1])

    def add_cutscene_picture(self) -> None:
        if self.cutscene is None:
            return
        self.cutscene["pictures"].append(cutscene.new_picture())
        index = len(self.cutscene["pictures"]) - 1
        self.set_cutscene_field(("path", index))
        self.status = "已添加一张过场图，请填路径和三个时间。"

    def remove_cutscene_picture(self, index: int) -> None:
        if self.cutscene is None or not 0 <= index < len(self.cutscene["pictures"]):
            return
        del self.cutscene["pictures"][index]
        self.cutscene_field = min(self.cutscene_field, max(0, len(self.cutscene_cells()) - 1))
        self.keep_cutscene_visible()
        self.status = "已删除一张过场图。"

    def move_cutscene_picture(self, index: int, delta: int) -> None:
        if self.cutscene is None:
            return
        pictures = self.cutscene["pictures"]
        target = index + delta
        if not 0 <= index < len(pictures) or not 0 <= target < len(pictures):
            return
        pictures[index], pictures[target] = pictures[target], pictures[index]
        self.set_cutscene_field(("path", target))
        self.status = "已调整图片顺序。"

    def pick_cutscene_image(self, index: int) -> None:
        """给某张过场图挑一张图：只记路径，不复制文件。"""
        if self.cutscene is None or not 0 <= index < len(self.cutscene["pictures"]):
            return
        path = ask_image_path("选择过场图片", self.media_base_dir)
        if not path:
            self.status = "已取消选择过场图片。"
            return
        self.cutscene["pictures"][index]["path"] = relative_level_path(
            path, self.media_base_dir
        )
        self.set_cutscene_field(("path", index))
        self.status = "已选择过场图片：仅记录相对 game.json 的路径，不复制文件。"

    def preview_cutscene_sound(self) -> None:
        if self.cutscene is None:
            return
        fields = self.cutscene["sound"]
        path = self.sound_library_path(fields.get("sound"))
        if path is None:
            self.preview.stop()
            self.status = (
                f"找不到这首曲子：{sound.key_label(self.sound_library, fields.get('sound'))}。"
            )
            return
        self.status = self.preview.toggle(
            path,
            bool(fields["loop"]),
            clamp_float(fields["fade_in"], 0.0, sound.MAX_FADE_SECONDS, sound.DEFAULT_FADE_IN),
        )

    # ---- 新建状态 ---------------------------------------------------
    def open_create_menu(self, position: tuple) -> None:
        """右键弹出新建菜单，光标位置就是菜单的左上角。"""
        self.menu_open = True
        self.menu_origin = (position[0], position[1])

    def start_creating(self, tool: int, layout: Layout | None = None) -> None:
        # 贴图不进创建模式：直接弹文件选择、导进来就完事
        if tool == TOOL_TEXTURE:
            self.menu_open = False          # 先把右键菜单收掉，文件框别压在菜单上
            if layout is not None:
                self.import_texture(layout)
            return
        # 声音对象也没有位置：不进创建模式，直接建一个并选中
        if tool == TOOL_SOUND:
            self.add_sound_object()
            return
        self.tool = tool
        self.creating = True
        self.menu_open = False
        action = "左键拖出矩形" if TOOL_SPECS[tool][1] == "rect" else "左键单击放置"
        self.status = f"新建模式：{TOOL_SPECS[tool][0]}（{action}，右键退出）"

    # ---- 贴图 -------------------------------------------------------
    def import_texture(self, layout: Layout) -> None:
        """直接导入一张贴图：不复制，只记一个相对 game.json 的路径。

        图片按游戏比例（可玩行 400px）换算成世界格尺寸，位置和大小之后在详情里调。
        """
        path = ask_image_path("导入贴图", self.media_base_dir)
        if not path:
            self.status = "已取消导入贴图。"
            return
        pixels = image_size(path)
        if pixels is None:
            self.status = f"无法读取图片：{os.path.basename(path)}。"
            return
        tile = max(1.0, layout.game_tile)
        width = max(MIN_SIZE, round(pixels[0] / tile, 2))
        height = max(MIN_SIZE, round(pixels[1] / tile, 2))
        at = layout.world_point(self.menu_origin)
        image = relative_level_path(path, self.media_base_dir)
        self.push_undo()
        self.dirty = True
        self.creating = False
        self.level.textures.append(
            {
                "pos": [round(at[0], 2), round(at[1], 2)],
                "size": [width, height],
                "image": image,
                "smooth": False,
            }
        )
        self.status = f"已导入贴图 {os.path.basename(path)}（{width}×{height} 格）。"

    # ---- 鼠标拖动 / 缩放（所有对象） --------------------------------
    def begin_object_grab(self, position: tuple, layout: Layout) -> bool:
        """左键按下：先看是不是压在某个角把手上（缩放），再看是不是落在对象里（移动）。

        只动按下的那一个：多选只是列清单，不做整组编辑。
        """
        hit = self.power_handle_at(position, layout)   # 力度箭头末端优先
        if hit is None:
            hit = self.object_handle_at(position, layout)
        if hit is not None:
            kind, entry, corner = hit
        elif self.hovered is not None:
            kind, entry = self.hovered
            corner = None                  # 点在对象本体上：整体挪，不缩放
        else:
            return False
        self.push_undo()                   # 先记下拖动前的状态，没动过就弹掉
        box = object_box(kind, entry)      # 屏幕上那块矩形：朝向型对象和喷口都要先摆正
        if corner is not None:
            # 抓的是缩放手柄：老数据里没写 size 的对象（木板、道具）也补上，别当成移动
            entry.setdefault("size", [1.0, 1.0])
        self.object_grab = {
            "kind": kind,
            "entry": entry,
            "corner": corner,
            "start": layout.world_point(position),
            "pos": list(entry["pos"]),
            "box": (float(box["pos"][0]), float(box["pos"][1]), *box.get("size", [1.0, 1.0])),
            "moved": False,
            "additive": self.keep_ratio,   # 按下时就按住 Ctrl：松手时是加选而不是单选
        }
        return True

    def update_object_grab(self, position: tuple, layout: Layout) -> None:
        grab = self.object_grab
        if grab is None:
            return
        self.last_mouse = (position[0], position[1])
        point = layout.world_point(position)
        dx = point[0] - grab["start"][0]
        dy = point[1] - grab["start"][1]
        if not grab["moved"] and abs(dx) * layout.tile < 1 and abs(dy) * layout.tile < 1:
            return                          # 还不到 1 像素，当作抖动
        grab["moved"] = True
        self.dirty = True
        kind = grab["kind"]
        entry = grab["entry"]
        x, y = grab["pos"]
        corner = grab["corner"]
        if corner == "power":
            # 拖力度箭头末端：末端到 pos 的距离（沿朝向）就是 power，目标点必须留在风区外
            step_x, step_y = nozzle_face_axis(entry)
            reach = (point[0] - x) * step_x + (point[1] - y) * step_y
            if self.snapping:
                reach = snap(reach)
            entry["power"] = round(reach, 2)
            clamp_nozzle_power(entry)
            return
        if corner is None:
            entry["pos"] = [round(x + dx, 2), round(y + dy, 2)]
            if self.snapping:
                entry["pos"] = [snap(value) for value in entry["pos"]]
            return
        box_left, box_bottom, width, height = grab["box"]
        left, right, bottom, top = box_left, box_left + width, box_bottom, box_bottom + height
        if self.keep_ratio and width > 0 and height > 0:
            # 等比缩放（所有能缩放的对象通用）：以对角为锚点，
            # 取鼠标在横竖两个方向上缩放比例的较大者
            anchor_x = box_left + width if "l" in corner else box_left
            anchor_y = box_bottom + height if "b" in corner else box_bottom
            scale = max(abs(point[0] - anchor_x) / width, abs(point[1] - anchor_y) / height)
            new_width = max(MIN_SIZE, round(width * scale, 2))
            new_height = max(MIN_SIZE, round(height * scale, 2))
            self._set_box(
                kind,
                entry,
                round(anchor_x - new_width if "l" in corner else anchor_x, 2),
                round(anchor_y - new_height if "b" in corner else anchor_y, 2),
                new_width,
                new_height,
            )
            return
        if "l" in corner:
            left = point[0]
        if "r" in corner:
            right = point[0]
        if "b" in corner:
            bottom = point[1]
        if "t" in corner:
            top = point[1]
        if self.snapping:
            left, right, bottom, top = snap(left), snap(right), snap(bottom), snap(top)
        self._set_box(
            kind,
            entry,
            round(min(left, right), 2),
            round(min(bottom, top), 2),
            max(MIN_SIZE, round(abs(right - left), 2)),
            max(MIN_SIZE, round(abs(top - bottom), 2)),
        )

    @staticmethod
    def _set_box(kind: str, entry: dict, left: float, bottom: float, width: float, height: float) -> None:
        """把算好的屏幕矩形写回条目。

        传送门和喷口的 pos 都是「底面」的中心、size 是没转过的宽高（左右朝向时
        屏幕上的宽高是反的），所以缩放后都要换算回这种写法。
        """
        if kind in (KIND_PORTAL, KIND_NOZZLE):
            face = str(entry.get("face", FACE_ORDER[0]))
            if face in ("left", "right"):
                entry["size"] = [round(height, 2), round(width, 2)]
                if face == "right":
                    entry["pos"] = [round(left, 2), round(bottom + height / 2.0, 2)]
                else:
                    entry["pos"] = [round(left + width, 2), round(bottom + height / 2.0, 2)]
            else:
                entry["size"] = [round(width, 2), round(height, 2)]
                edge = bottom + height if face == "down" else bottom
                entry["pos"] = [round(left + width / 2.0, 2), round(edge, 2)]
            if kind == KIND_NOZZLE:
                clamp_nozzle_power(entry)  # 风区拉长了，力度跟着顶上去
            return
        entry["pos"] = [round(left, 2), round(bottom, 2)]
        entry["size"] = [width, height]

    def refresh_grab(self, layout: Layout) -> None:
        """修饰键按下/松开时：用最近一次鼠标位置把正在进行的拖动重算一遍。

        鼠标不动只按 Ctrl 也要立刻切成等比，所以不能等 MOUSEMOTION。
        """
        if self.object_grab is not None:
            self.update_object_grab(self.last_mouse, layout)
        elif self.drag_start is not None:
            self.drag_to(self.last_mouse, layout)
        else:
            self.update_hover(self.last_mouse, layout)

    def end_object_grab(self) -> bool:
        """松开鼠标：拖过就算一步编辑；只是点了一下就选中那个对象。"""
        grab = self.object_grab
        self.object_grab = None
        if grab is None:
            return False
        kind = grab["kind"]
        entry = grab["entry"]
        if not grab["moved"]:
            if self.undo_stack:
                self.undo_stack.pop()      # 没动过，把刚压进去的撤销弹掉
            # 点角也是点这个对象，别去选下面的；按住 Ctrl 时是逐个加选
            if grab.get("additive"):
                self.toggle_selection(kind, entry)
            else:
                self.select(kind, entry)
            return True
        size = entry.get("size")
        text = f"{KIND_TITLES.get(kind, '对象')}（{entry['pos'][0]}, {entry['pos'][1]}）"
        if size:
            text += f" {size[0]}×{size[1]}"
        self.status = text
        return True

    # ---- 选择 -------------------------------------------------------
    def select(self, kind: str, entry: dict) -> None:
        """单选：同时打开属性面板。"""
        if kind not in GLOBAL_KINDS and self._defer_global(("select", kind, entry)):
            return
        self.selection = [(kind, entry)]
        self.dialog = {"kind": kind, "entry": entry}
        self.dialog_field = 0
        self.detail_scroll = 0.0
        self.dropdown_field = None
        self.name_focused = False
        self.number_buffer = None
        if kind in GLOBAL_KINDS:
            self.panel_tab = "properties"
        self.status = f"已选中{KIND_TITLES.get(kind, '对象')}。"

    def select_many(self, pairs: list) -> None:
        """多选：面板只列清单和数量，不给属性；正好一个时回到属性面板。"""
        global_only = len(pairs) == 1 and pairs[0][0] in GLOBAL_KINDS
        if not global_only and self._defer_global(("select_many", pairs)):
            return
        self.selection = list(pairs)
        self.pick_menu = None
        self.detail_scroll = 0.0
        if len(self.selection) == 1:
            kind, entry = self.selection[0]
            self.dialog = {"kind": kind, "entry": entry}
            self.dialog_field = 0
        else:
            self.dialog = None
        self.dropdown_field = None
        self.name_focused = False
        self.number_buffer = None
        self.status = f"已选中 {len(self.selection)} 个对象。" if self.selection else "已取消选择。"

    def clear_selection(self) -> None:
        self.select_many([])

    def select_at(self, position: tuple, layout: Layout, additive: bool = False) -> None:
        """点一下：选最上层那个；按住 Ctrl 就逐个加选/取消。"""
        self.update_hover(position, layout)
        if self.hovered is None:
            if not additive:
                self.clear_selection()
            return
        kind, entry = self.hovered
        if additive:
            self.toggle_selection(kind, entry)
        else:
            self.select(kind, entry)

    def toggle_selection(self, kind: str, entry: dict) -> None:
        """Ctrl 点选：已选中的取消，没选中的加进去。"""
        rest = [(k, e) for k, e in self.selection if e is not entry]
        if len(rest) == len(self.selection):
            rest.append((kind, entry))
        self.select_many(rest)

    def label_of(self, kind: str, entry: dict) -> str:
        if kind == KIND_SOUND or "pos" not in entry:
            return self.go_list_label(kind, entry)
        pos = entry["pos"]
        name = entry.get("name") or KIND_TITLES.get(kind, "对象")
        return f"{name}（{pos[0]}, {pos[1]}）"

    # ---- 右侧面板：属性 / 对象列表 -----------------------------------
    def set_panel_tab(self, tab: str) -> None:
        """右侧面板切页：属性跟着选中项走，对象列表列这一关的对象。"""
        if tab not in ("properties", "objects"):
            return
        self.panel_tab = tab
        self.go_list_menu = False
        # 换页时把属性页上没结束的下拉和输入收掉，免得留在背后
        self.dropdown_field = None
        self.name_focused = False
        self.number_buffer = None
        self.status = "右侧面板：" + ("属性。" if tab == "properties" else "对象列表。")

    def go_list_objects(self) -> list:
        """列表里的对象：这一关能点选的全部对象，按种类排好，种类里保持原顺序。

        画布上的对象来自 stacked_entries（视图菜单里关掉「显示贴图」时贴图不列）；
        声音对象没有位置和大小、不在画布上，但同样列在这里，点一行就能改它。
        """
        entries = self.stacked_entries() + [
            (KIND_SOUND, entry) for entry in self.level.sound_objects
        ]
        return sorted(
            entries,
            key=lambda pair: KIND_ORDER_INDEX.get(pair[0], len(KIND_ORDER_INDEX)),
        )
    def go_list_counts(self) -> list:
        """筛选菜单的内容：这一关里有的种类和各自的个数。"""
        counts: dict = {}
        for kind, _ in self.go_list_objects():
            counts[kind] = counts.get(kind, 0) + 1
        return [(kind, counts[kind]) for kind in KIND_ORDER if kind in counts]

    def go_list_items(self) -> list:
        """列表最上面是固定的「全局」组，再是按种类筛过的关卡对象。

        全局项只属于 game.json，不写进关卡，也不能删除；选中后进属性页编辑。
        """
        rows = [
            (KIND_GLOBAL_HEADER, None),
            (KIND_GLOBAL_ANIMATION, self.player_animation),
            (KIND_GLOBAL_SOUND, self.player_sound),
        ]
        entries = self.go_list_objects()
        if not self.go_list_filter:
            return rows + entries
        return rows + [
            (kind, entry) for kind, entry in entries if kind == self.go_list_filter
        ]

    def go_list_label(self, kind: str, entry: dict) -> str:
        """一行写什么：种类、名字（有的话）和位置（格，去掉多余的小数位）。

        声音对象没有位置，写预设就够了；全局组单独成一组。
        """
        if kind == KIND_GLOBAL_HEADER:
            return "全局（游戏配置）"
        if kind == KIND_GLOBAL_ANIMATION:
            return "玩家动画（全局）"
        if kind == KIND_GLOBAL_SOUND:
            return "玩家音效（全局）"
        title = KIND_TITLES.get(kind, "对象")
        if kind == KIND_SOUND:
            return f"{title}（{sound.preset_label(sound.preset_of(entry))}）"
        name = str(entry.get("name") or "").strip()
        position = entry.get("pos") or [0.0, 0.0]
        x, y = (f"{float(value):g}" for value in list(position)[:2])
        if name:
            return f"{title} {name}（{x}, {y}）"
        return f"{title}（{x}, {y}）"

    def go_list_filter_label(self) -> str:
        if not self.go_list_filter:
            return "全部"
        return KIND_TITLES.get(self.go_list_filter, "全部")

    def set_go_list_filter(self, kind: str) -> None:
        """筛选菜单里选一种：只列那种对象；空字符串是全部。"""
        kind = str(kind or "")
        if kind and kind not in KIND_ORDER:
            return
        self.go_list_filter = kind
        self.go_list_scroll = 0.0
        self.go_list_menu = False
        self.status = f"对象列表：{self.go_list_filter_label()}。"

    def toggle_go_list_menu(self) -> None:
        self.go_list_menu = not self.go_list_menu

    def close_go_list_menu(self) -> None:
        self.go_list_menu = False

    def scroll_go_list(self, delta: float) -> None:
        """对象列表的滚轮：按像素滚（上界在绘制时按内容高度夹住）。"""
        self.go_list_scroll = max(0.0, self.go_list_scroll + float(delta) * SCROLL_STEP)

    def select_go_list_item(self, kind: str, entry: dict) -> None:
        """点一行：全局项直接进属性页，关卡对象在画布上选中。"""
        self.go_list_menu = False
        if kind == KIND_GLOBAL_HEADER:
            return
        if kind in GLOBAL_KINDS:
            self.select_global(kind)
            return
        self.select(kind, entry)

    def reset_go_list(self) -> None:
        """换关卡时：筛选、滚动和展开的筛选菜单都回到初始状态。"""
        self.go_list_filter = ""
        self.go_list_scroll = 0.0
        self.go_list_menu = False

    def delete_selection(self) -> None:
        """删掉所有选中的对象，算一步撤销。"""
        if not self.selection:
            self.status = "当前没有选中的对象。"
            return
        if any(kind in GLOBAL_KINDS for kind, _ in self.selection):
            self.status = "全局玩家表现不能删除。"
            return
        self.push_undo()
        count = len(self.selection)
        for kind, entry in self.selection:
            self.remove_entry(kind, entry)
        self.select_many([])
        self.hovered = None
        self.dirty = True
        self.status = f"已删除 {count} 个对象。"

    def duplicate_selection(self) -> None:
        """Ctrl+D 和面板上的「复制」：复制选中的贴图，错开半格放在原图上面一层。"""
        entries = [entry for kind, entry in self.selection if kind == KIND_TEXTURE]
        if not entries:
            self.status = "只有贴图可以复制：先选中贴图。"
            return
        self.push_undo()
        copies = []
        for entry in entries:
            duplicated = copy.deepcopy(entry)
            x, y = duplicated.get("pos", [0.0, 0.0])
            duplicated["pos"] = [round(x + SNAP_STEP, 2), round(y - SNAP_STEP, 2)]
            index = next(
                (index for index, item in enumerate(self.level.textures) if item is entry),
                len(self.level.textures) - 1,
            )
            self.level.textures.insert(index + 1, duplicated)
            copies.append((KIND_TEXTURE, duplicated))
        self.dirty = True
        self.select_many(copies)
        self.status = f"已复制 {len(copies)} 张贴图（Ctrl+Z 可撤销）。"

    def rotate_selection_cw(self) -> None:
        """R：把选中的贴图朝向顺时针转一格；转回向上也照样写 up，不删这个键。"""
        entries = [entry for kind, entry in self.selection if kind == KIND_TEXTURE]
        if not entries:
            self.status = "先选中贴图，再按 R 顺时针旋转。"
            return
        self.push_undo()
        for entry in entries:
            face = str(entry.get("face", FACE_ORDER[0]))
            index = FACE_ORDER.index(face) if face in FACE_ORDER else 0
            entry["face"] = FACE_ORDER[(index + 1) % len(FACE_ORDER)]
        self.dirty = True
        self.status = "贴图朝向已顺时针转一格。"

    def remove_entry(self, kind: str, entry: dict) -> None:
        if kind == KIND_BLOCK:
            self.level.blocks = [e for e in self.level.blocks if e is not entry]
        elif kind == KIND_PLANK:
            self.level.planks = [e for e in self.level.planks if e is not entry]
        elif kind == KIND_MOVABLE:
            self.level.movable_blocks = [e for e in self.level.movable_blocks if e is not entry]
        elif kind == KIND_TRIGGER_SOURCE:
            self.level.trigger_sources = [
                e for e in self.level.trigger_sources if e is not entry
            ]
        elif kind == KIND_PORTAL:
            self.level.portals = [e for e in self.level.portals if e is not entry]
        elif kind == KIND_NOZZLE:
            self.level.nozzles = [e for e in self.level.nozzles if e is not entry]
        elif kind == KIND_TEXTURE:
            self.level.textures = [e for e in self.level.textures if e is not entry]
        elif kind == KIND_ANIMATION:
            self.level.animation_objects = [
                e for e in self.level.animation_objects if e is not entry
            ]
        elif kind == KIND_SOUND:
            self.level.sound_objects = [
                e for e in self.level.sound_objects if e is not entry
            ]
        elif kind == KIND_PLAYER:
            self.level.player = None
        elif kind == KIND_DESTINATION:
            self.level.destination = None

    # ---- 框选 -------------------------------------------------------
    def begin_marquee(self, position: tuple, layout: Layout) -> None:
        point = layout.world_point(position)
        self.marquee_start = point
        self.marquee_current = point
        self.marquee_additive = self.keep_ratio   # 按住 Ctrl：框里的对象加进已选
        self.last_mouse = (position[0], position[1])

    def update_marquee(self, position: tuple, layout: Layout) -> None:
        if self.marquee_start is None:
            return
        self.last_mouse = (position[0], position[1])
        self.marquee_current = layout.world_point(position)

    def finish_marquee(self, layout: Layout) -> bool:
        """松开左键：拖出框就框选，几乎没动就当成一次点击。"""
        start = self.marquee_start
        current = self.marquee_current or start
        self.marquee_start = None
        self.marquee_current = None
        if start is None:
            return False
        moved = (
            abs(current[0] - start[0]) * layout.tile >= 3
            or abs(current[1] - start[1]) * layout.tile >= 3
        )
        if not moved:
            self.select_at(self.last_mouse, layout, additive=getattr(self, "marquee_additive", False))
            return True
        x0, x1 = sorted((start[0], current[0]))
        y0, y1 = sorted((start[1], current[1]))
        picked = [
            (kind, entry)
            for kind, entry in self.stacked_entries()
            if self._in_marquee(kind, entry, x0, y0, x1, y1)
        ]
        if getattr(self, "marquee_additive", False):
            # 加选：把已选的和框里的一起保留（同一对象只算一次）
            merged = list(self.selection)
            for pair in picked:
                if not any(pair[1] is entry for _, entry in merged):
                    merged.append(pair)
            picked = merged
        self.select_many(picked)
        return True

    @staticmethod
    def _in_marquee(kind: str, entry: dict, x0: float, y0: float, x1: float, y1: float) -> bool:
        """贴图要整个框住才算（它是背景皮，一划就中的话太容易误选），其余相交即选。"""
        box = object_box(kind, entry)
        px, py = box["pos"]
        width, height = box.get("size", [1.0, 1.0])
        if kind == KIND_TEXTURE:
            return px >= x0 and py >= y0 and px + width <= x1 and py + height <= y1
        return px < x1 and px + width > x0 and py < y1 and py + height > y0

    def stop_creating(self) -> None:
        self.creating = False
        self.status = "已退出新建模式；左键用于设置或框选，右键用于新建。"

    # ---- 退出确认 ---------------------------------------------------
    def request_quit(self) -> bool:
        """真能退出就返回 True；有未保存的改动就先弹确认。"""
        if self._defer_global(("quit",)):
            return False
        if self.dirty:
            self.confirm_quit = True
            return False
        return True

    def close_dialog(self) -> None:
        self.dialog = None
        self.detail_scroll = 0.0
        self.dropdown_field = None
        self.name_focused = False
        self.number_buffer = None

    def scroll_detail(self, delta: float) -> None:
        """属性面板的滚轮：内容按像素上下滚（上界在几何里按内容高度夹住）。"""
        self.detail_scroll = max(0.0, self.detail_scroll + float(delta) * SCROLL_STEP)

    def keep_detail_focus_visible(self, surface) -> None:
        """上下键换格时，把选中的格子滚进属性面板的可视区。"""
        if self.dialog is None:
            return
        from view import panel as panel_view

        panel = panel_view.detail_panel_rect(surface)
        viewport = panel_view.detail_viewport(panel)
        rect = None
        if self.name_focused:
            rect = panel_view.detail_slot_rect(surface, self, "name")
        else:
            for row_rect, kind, index in panel_view.detail_slots(surface, self):
                if kind == "row" and index == self.dialog_field:
                    rect = row_rect
                    break
            if rect is None:
                trigger = panel_view.trigger_geometry(surface, self)
                for layout in trigger["cards"] if trigger is not None else []:
                    for part in TRIGGER_PARTS:
                        if self.trigger_field(layout["index"], part) == self.dialog_field:
                            rect = layout[part]
                            break
                    if rect is not None:
                        break
        if rect is None or viewport.height <= 0:
            return
        _, max_scroll = panel_view.detail_scroll_limits(surface, self)
        if rect.top < viewport.top:
            self.detail_scroll = max(
                0.0, self.detail_scroll - (viewport.top - rect.top)
            )
        elif rect.bottom > viewport.bottom:
            self.detail_scroll = min(
                max_scroll, self.detail_scroll + (rect.bottom - viewport.bottom)
            )

    # ---- 名称输入 ---------------------------------------------------
    def focus_name(self) -> None:
        if self.dialog is None or self.dialog["kind"] not in KIND_HAS_NAME:
            return
        if not self.name_focused:
            self.push_undo()
        self.name_focused = True
        self.dialog_field = -1
        self.status = "正在输入名称；按 Enter 或点击其他位置结束输入。"

    def blur_name(self) -> None:
        if self.dialog_field < 0:
            self.dialog_field = 0
        self.name_focused = False

    def type_name(self, char: str) -> None:
        if not self.name_focused or self.dialog is None:
            return
        name = self.dialog["entry"].get("name", "")
        if char.isprintable() and len(name) < NAME_MAX_LENGTH:
            self.dialog["entry"]["name"] = name + char
            self.dirty = True

    def erase_name_char(self) -> None:
        if not self.name_focused or self.dialog is None:
            return
        name = self.dialog["entry"].get("name", "")
        if name:
            self.dialog["entry"]["name"] = name[:-1]
            self.dirty = True

    # ---- 属性面板的字段 ---------------------------------------------
    def dialog_rows(self) -> list:
        if self.dialog is None:
            return []
        kind = self.dialog["kind"]
        entry = self.dialog["entry"]
        if kind == KIND_GLOBAL_ANIMATION:
            size = entry.get("size") or [1.0, 1.0]
            offset = entry.get("offset") or [0.0, 0.0]
            return [
                ("宽度", number_text(size[0])),
                ("高度", number_text(size[1])),
                ("横向偏移", number_text(offset[0])),
                ("纵向偏移", number_text(offset[1])),
                ("范围", "所有关卡共用"),
            ]
        if kind == KIND_GLOBAL_SOUND:
            return [("范围", "所有关卡共用")]
        if kind == KIND_SOUND:
            # 声音没有位置和大小：只有预设和跟随两格
            return [
                ("预设", sound.preset_label(sound.preset_of(entry))),
                ("跟随", self.animation_follow_label(entry.get("follow"))),
            ]
        pos = entry["pos"]
        rows = [("横坐标", number_text(pos[0])), ("纵坐标", number_text(pos[1]))]
        size = entry.get("size", [1.0, 1.0])
        rows += [("宽度", number_text(size[0])), ("高度", number_text(size[1]))]
        if kind == KIND_MOVABLE:
            offset = entry.get("offset", [0, -3])
            rows += [
                ("横向偏移", number_text(offset[0])),
                ("纵向偏移", number_text(offset[1])),
            ]
        elif kind == KIND_PLAYER:
            face = self.player_face()
            rows.append(("初始朝向", PLAYER_FACE_LABELS[face]))
        elif kind == KIND_TRIGGER_SOURCE:
            mode = str(entry.get("mode") or TRIGGER_SOURCE_MODE_DEFAULT)
            rows.append(("模式", TRIGGER_SOURCE_MODE_LABELS.get(mode, mode)))
            rows.append(("跳高变化", number_text(entry.get("jump_offset", 0.0))))
            rows.append(("物品", item.label(self.item_library, entry.get("item"))))
        elif kind == KIND_PORTAL:
            rows += [
                ("朝向", FACE_LABELS.get(entry.get("face", ""), FACE_LABELS[FACE_ORDER[0]])),
                ("目标", entry.get("target") or "无"),
            ]
        elif kind == KIND_NOZZLE:
            rows += [
                ("朝向", FACE_LABELS.get(entry.get("face", "up"), FACE_LABELS[FACE_ORDER[0]])),
                ("力度", number_text(entry.get("power", NOZZLE_DEFAULT_POWER))),
            ]
        elif kind == KIND_TEXTURE:
            rows.append(("图片", entry.get("image") or "（未选择）"))
            rows.append(
                ("朝向", FACE_LABELS.get(str(entry.get("face", "up")), FACE_LABELS["up"]))
            )
            rows.append(("水平翻转", "是" if entry.get("flip") else "否"))
            rows.append(("跟随", entry.get("follow") or "无"))
            rows.append(("隐藏", "是" if entry.get("hide") else "否"))
        elif kind == KIND_ANIMATION:
            rows.append(("跟随", self.animation_follow_label(entry.get("follow"))))
        return rows

    def dialog_checkbox(self, index: int) -> bool | None:
        """这一行是不是复选框：是的话返回当前勾没勾，不是返回 None。

        「是 / 否」的两项：贴图的「水平翻转」和「初始隐藏」。
        """
        if self.dialog is None:
            return None
        kind = self.dialog["kind"]
        entry = self.dialog["entry"]
        if kind == KIND_TEXTURE and index == 6:
            return bool(entry.get("flip", False))
        if kind == KIND_TEXTURE and index == 8:
            return bool(entry.get("hide", False))
        return None

    # ---- 触发行为卡片 -----------------------------------------------
    def trigger_cards(self) -> list | None:
        """当前对象的触发卡片；不接触发器的种类返回 None。终点也用这套卡片。"""
        if self.dialog is None or self.dialog["kind"] not in KIND_BEHAVIORS:
            return None
        cards = self.dialog["entry"].get("triggers")
        return cards if isinstance(cards, list) else []

    def trigger_field(self, index: int, part: str) -> int:
        """卡片上某个格子的字段号：来源、行为、模式各占一个。"""
        return (
            TRIGGER_FIELD_BASE + index * len(TRIGGER_PARTS) + TRIGGER_PARTS.index(part)
        )

    def trigger_field_parts(self, field: int) -> tuple[int, str] | None:
        """字段号 → (卡片下标, "source" / "behavior" / "mode")；不是卡片字段就返回 None。"""
        if field < TRIGGER_FIELD_BASE:
            return None
        offset = field - TRIGGER_FIELD_BASE
        return offset // len(TRIGGER_PARTS), TRIGGER_PARTS[offset % len(TRIGGER_PARTS)]

    def trigger_storage(self) -> list:
        """要写卡片时才建列表：没接触发器的对象，json 里不会凭空多一个空 triggers。"""
        entry = self.dialog["entry"]
        cards = entry.get("triggers")
        if not isinstance(cards, list):
            cards = []
            entry["triggers"] = cards
        return cards

    def trigger_sources(self) -> list:
        """可以当触发来源的名字：关卡里所有触发源（同名的只列一次）。"""
        names = [
            str(entry.get("name") or "")
            for entry in self.level.trigger_sources
            if entry.get("name")
        ]
        return list(dict.fromkeys(names))

    def add_trigger_card(self) -> None:
        """面板上的「＋ 添加触发器」：加一张空来源的卡片，行为取这个种类的第一项。"""
        cards = self.trigger_cards()
        if cards is None:
            return
        self.push_undo()
        kind = self.dialog["kind"]
        behaviors = KIND_BEHAVIORS[kind]
        default_mode = (
            DESTINATION_TRIGGER_DEFAULT_MODE
            if kind == KIND_DESTINATION
            else TRIGGER_DEFAULT_MODE
        )
        cards = self.trigger_storage()
        cards.append(
            {"source": "", "behavior": behaviors[0][1], "mode": default_mode}
        )
        self.dialog_field = self.trigger_field(len(cards) - 1, "source")
        self.dropdown_field = None
        self.number_buffer = None
        self.detail_scroll = float("inf")   # 下一帧按内容高度夹到底，新卡片就在眼前
        self.dirty = True
        self.status = (
            "已添加一条触发条件，请选择来源。"
            if kind == KIND_DESTINATION
            else "已添加一条触发行为，请选择来源。"
        )

    def remove_trigger_card(self, index: int) -> None:
        """删掉第 index 张卡片；光标落到留下那张卡片的来源上。"""
        cards = self.trigger_cards()
        if cards is None or not 0 <= index < len(cards):
            return
        self.push_undo()
        del self.trigger_storage()[index]
        remaining = self.trigger_cards() or []
        self.dialog_field = (
            self.trigger_field(min(index, len(remaining) - 1), "source")
            if remaining
            else 0
        )
        self.dropdown_field = None
        self.number_buffer = None
        self.dirty = True
        self.status = (
            "已删除一条触发条件。"
            if self.dialog["kind"] == KIND_DESTINATION
            else "已删除一条触发行为。"
        )

    def adjust_trigger_field(self, field: int, delta: int) -> None:
        """卡片上的 ←→：来源 / 行为 / 模式都在各自的选项里循环。"""
        parts = self.trigger_field_parts(field)
        if parts is None:
            return
        cards = self.trigger_storage()
        index, part = parts
        if index >= len(cards):
            return
        options = self.dialog_options(field)
        if not options:
            return
        values = [value for _, value in options]
        current = str(cards[index].get(part) or "")
        if current in values:
            chosen = values[(values.index(current) + delta) % len(values)]
        else:
            chosen = values[0]
        cards[index][part] = chosen

    def dialog_fields(self) -> list:
        """属性面板能聚焦的格子：先是属性行，再是触发卡片的来源 / 行为 / 模式。"""
        fields = [
            index
            for index in range(len(self.dialog_rows()))
            if self.dialog_focusable(index)
        ]
        for index in range(len(self.trigger_cards() or [])):
            fields += [self.trigger_field(index, part) for part in TRIGGER_PARTS]
        return fields

    def dialog_focusable(self, index: int) -> bool:
        """这一格能不能选中：数字、下拉、开关和触发卡片可以，纯显示的行不行。"""
        if self.dialog is None:
            return False
        parts = self.trigger_field_parts(index)
        if parts is not None:
            cards = self.trigger_cards()
            return cards is not None and parts[0] < len(cards)
        return (
            self.dialog_number_value(index) is not None
            or self.dialog_options(index) is not None
            or self.dialog_checkbox(index) is not None
        )

    def dialog_title(self) -> str:
        if self.dialog is None:
            return ""
        kind = self.dialog["kind"]
        if kind == KIND_GLOBAL_ANIMATION:
            return "玩家动画（全局）"
        if kind == KIND_GLOBAL_SOUND:
            return "玩家音效（全局）"
        name = self.dialog["entry"].get("name", "")
        return f"{KIND_TITLES.get(kind, '')} {name}".strip()

    def adjust_dialog(self, delta: int) -> None:
        """方向键与加减按钮：数字字段加 delta，其余字段循环切换。"""
        if self.dialog is None:
            return
        if (
            self.global_active()
            and self.dialog_number_value(self.dialog_field) is None
            and self.trigger_field_parts(self.dialog_field) is None
        ):
            return                      # 全局页只有数字字段，不要在说明行上记空撤销
        self.number_buffer = None          # 改用加减就把键盘输入状态收起来
        if self.global_active():
            self.push_global_undo()
        else:
            self.push_undo()
            self.dirty = True
        kind = self.dialog["kind"]
        entry = self.dialog["entry"]
        field = self.dialog_field

        current_number = self.dialog_number_value(field)
        if current_number is not None:
            # 数字字段统一半格一步（位置、尺寸、偏移、力度、长度都是方块单位）
            self.set_dialog_number(field, current_number + 0.5 * delta)
            return

        if self.trigger_field_parts(field) is not None:
            self.adjust_trigger_field(field, delta)
            return

        if kind == KIND_TRIGGER_SOURCE:
            if field == 4:                 # 模式：按住 / 一次 循环
                current = str(entry.get("mode") or TRIGGER_SOURCE_MODE_DEFAULT)
                values = [value for _, value in TRIGGER_SOURCE_MODES]
                index = values.index(current) if current in values else 0
                entry["mode"] = values[(index + delta) % len(values)]
            elif field == 6:               # 物品：无 / 物品库里的 id 循环
                values = [""] + [key for key, _ in self.item_library_items()]
                current = str(entry.get("item") or "")
                index = values.index(current) if current in values else 0
                chosen = values[(index + delta) % len(values)]
                if chosen:
                    entry["item"] = chosen
                else:
                    entry.pop("item", None)
        elif kind == KIND_PLAYER:
            if field == 4:                 # 初始朝向：右 / 左 循环
                current = self.player_face()
                index = PLAYER_FACE_ORDER.index(current)
                entry["face"] = PLAYER_FACE_ORDER[
                    (index + delta) % len(PLAYER_FACE_ORDER)
                ]
        elif kind == KIND_PORTAL:
            if field == 4:                 # 朝向：按 up/right/down/left 循环
                current_face = entry.get("face", FACE_ORDER[0])
                entry["face"] = (
                    FACE_ORDER[(FACE_ORDER.index(current_face) + delta) % len(FACE_ORDER)]
                    if current_face in FACE_ORDER
                    else FACE_ORDER[0]
                )
            elif field == 5:               # 目标：在「无」和别的传送门名字之间循环
                names = [
                    portal.get("name", "")
                    for portal in self.level.portals
                    if portal.get("name") and portal is not entry
                ]
                options = [None, *names]
                current = entry.get("target") or None
                chosen = (
                    options[(options.index(current) + delta) % len(options)]
                    if current in options
                    else names[0]
                    if names
                    else None
                )
                entry["target"] = chosen or ""
        elif kind == KIND_NOZZLE:
            if field == 4:                 # 朝向：按 up/right/down/left 循环
                current_face = entry.get("face", FACE_ORDER[0])
                entry["face"] = (
                    FACE_ORDER[(FACE_ORDER.index(current_face) + delta) % len(FACE_ORDER)]
                    if current_face in FACE_ORDER
                    else FACE_ORDER[0]
                )
        elif kind == KIND_ANIMATION:
            if field == 4:                 # 跟随：无 / 玩家 / 有名字的对象循环
                options = self.animation_follow_options()
                values = [value for _, value in options]
                current = str(entry.get("follow") or "")
                index = values.index(current) if current in values else 0
                entry["follow"] = values[(index + delta) % len(values)]
        elif kind == KIND_SOUND:
            if field == 0:                 # 预设：通用 / 玩家 循环
                values = [value for _, value in sound.PRESETS]
                current = sound.preset_of(entry)
                index = values.index(current) if current in values else 0
                entry["preset"] = values[(index + delta) % len(values)]
            elif field == 1:               # 跟随：无 / 玩家 / 有名字的对象循环
                options = self.animation_follow_options()
                values = [value for _, value in options]
                current = str(entry.get("follow") or "")
                index = values.index(current) if current in values else 0
                entry["follow"] = values[(index + delta) % len(values)]
        elif kind == KIND_TEXTURE:
            if field == 5:                 # 朝向：顺时针转一格（向上也照样写 up）
                face = str(entry.get("face", FACE_ORDER[0]))
                index = FACE_ORDER.index(face) if face in FACE_ORDER else 0
                entry["face"] = FACE_ORDER[(index + delta) % len(FACE_ORDER)]
            elif field == 6:               # 水平翻转：开关，取消也把 false 留着
                entry["flip"] = not bool(entry.get("flip", False))
            elif field == 7:               # 跟随：在「无」和可移动方块的名字之间循环
                names = [
                    block.get("name", "")
                    for block in self.level.movable_blocks
                    if block.get("name")
                ]
                options = [None, *names]
                current = entry.get("follow") or None
                chosen = (
                    options[(options.index(current) + delta) % len(options)]
                    if current in options
                    else names[0]
                    if names
                    else None
                )
                entry["follow"] = chosen or ""
            elif field == 8:               # 隐藏：开关（初始状态）
                entry["hide"] = not bool(entry.get("hide", False))

    # ---- 选择型字段的下拉列表 ---------------------------------------
    def dialog_options(self, field: int) -> list | None:
        """选择型字段的可选项 [(显示文字, 值)]；数字、开关字段返回 None。

        朝向、传送门的目标、贴图的跟随、起点显示的动画与方向，以及触发卡片上的来源、
        行为和模式都从这里出下拉列表。
        """
        if self.dialog is None:
            return None
        kind = self.dialog["kind"]
        entry = self.dialog["entry"]
        parts = self.trigger_field_parts(field)
        if parts is not None:
            cards = self.trigger_cards()
            if cards is None or parts[0] >= len(cards):
                return None
            if parts[1] == "source":
                return [("无", "")] + [(name, name) for name in self.trigger_sources()]
            if parts[1] == "mode":
                return list(TRIGGER_MODES)
            return list(KIND_BEHAVIORS[kind])
        if kind in (KIND_PORTAL, KIND_NOZZLE) and field == 4:
            return [(FACE_LABELS[face], face) for face in FACE_ORDER]
        if kind == KIND_TRIGGER_SOURCE and field == 4:
            return list(TRIGGER_SOURCE_MODES)
        if kind == KIND_TRIGGER_SOURCE and field == 6:
            return [("无", "")] + [
                (item.label(self.item_library, key), key)
                for key, _ in self.item_library_items()
            ]
        if kind == KIND_PLAYER and field == 4:
            return [(PLAYER_FACE_LABELS[face], face) for face in PLAYER_FACE_ORDER]
        if kind == KIND_PORTAL and field == 5:
            names = [
                portal.get("name", "")
                for portal in self.level.portals
                if portal.get("name") and portal is not entry
            ]
            return [("无", "")] + [(name, name) for name in names]
        if kind == KIND_TEXTURE and field == 5:
            return [(FACE_LABELS[face], face) for face in FACE_ORDER]
        if kind == KIND_TEXTURE and field == 7:
            names = [
                block.get("name", "")
                for block in self.level.movable_blocks
                if block.get("name")
            ]
            return [("无", "")] + [(name, name) for name in names]
        if kind == KIND_ANIMATION and field == 4:
            return self.animation_follow_options()
        if kind == KIND_SOUND and field == 0:
            return [(label, value) for value, label in sound.PRESETS]
        if kind == KIND_SOUND and field == 1:
            return self.animation_follow_options()
        return None

    def dialog_option_value(self, field: int):
        """选择型字段当前的值，用来在下拉列表里标出选中项。"""
        if self.dialog is None:
            return None
        kind = self.dialog["kind"]
        entry = self.dialog["entry"]
        parts = self.trigger_field_parts(field)
        if parts is not None:
            cards = self.trigger_cards()
            if cards is None or parts[0] >= len(cards):
                return ""
            card = cards[parts[0]]
            if parts[1] == "mode":
                return str(card.get("mode") or TRIGGER_DEFAULT_MODE)
            return str(card.get(parts[1]) or "")
        if kind == KIND_PORTAL and field == 5:
            return entry.get("target") or ""
        if kind == KIND_TRIGGER_SOURCE and field == 4:
            return str(entry.get("mode") or TRIGGER_SOURCE_MODE_DEFAULT)
        if kind == KIND_TRIGGER_SOURCE and field == 6:
            return str(entry.get("item") or "")
        if kind == KIND_PLAYER and field == 4:
            return self.player_face()
        if kind == KIND_TEXTURE and field == 7:
            return entry.get("follow") or ""
        if kind == KIND_ANIMATION and field == 4:
            return str(entry.get("follow") or "")
        if kind == KIND_SOUND and field == 0:
            return sound.preset_of(entry)
        if kind == KIND_SOUND and field == 1:
            return str(entry.get("follow") or "")
        return entry.get("face", FACE_ORDER[0])

    def toggle_dropdown(self, field: int) -> bool:
        """点选择型字段：没展开就展开，已经展开就收起。返回这个字段是不是选择型。"""
        if self.dialog_options(field) is None:
            return False
        if self.dropdown_field == field:
            self.dropdown_field = None
            return True
        self.dialog_field = field
        self.dropdown_field = field
        self.number_buffer = None
        self.name_focused = False
        return True

    def close_dropdown(self) -> None:
        self.dropdown_field = None

    def choose_dropdown(self, value) -> None:
        """在下拉列表里选了一项：写回字段并收起列表。"""
        field = self.dropdown_field
        if field is None or self.dialog is None:
            return
        self.push_undo()
        parts = self.trigger_field_parts(field)
        if parts is not None:
            cards = self.trigger_storage()
            index, part = parts
            if index < len(cards):
                cards[index][part] = "" if value is None else str(value)
        else:
            kind = self.dialog["kind"]
            entry = self.dialog["entry"]
            if kind == KIND_PORTAL and field == 5:
                entry["target"] = value or ""
            elif kind == KIND_TRIGGER_SOURCE and field == 4:
                entry["mode"] = (
                    value if value in TRIGGER_SOURCE_MODE_VALUES
                    else TRIGGER_SOURCE_MODE_DEFAULT
                )
            elif kind == KIND_TRIGGER_SOURCE and field == 6:
                chosen = str(value or "").strip()
                if chosen:
                    entry["item"] = chosen
                else:
                    entry.pop("item", None)
            elif kind == KIND_PLAYER and field == 4:
                entry["face"] = value if value in PLAYER_FACE_ORDER else "right"
            elif kind == KIND_TEXTURE and field == 5:
                entry["face"] = value or FACE_ORDER[0]
            elif kind == KIND_TEXTURE and field == 7:
                entry["follow"] = value or ""
            elif kind == KIND_ANIMATION and field == 4:
                entry["follow"] = value or ""
            elif kind == KIND_SOUND and field == 0:
                entry["preset"] = (
                    value if value in (sound.PRESET_GENERAL, sound.PRESET_PLAYER)
                    else sound.PRESET_GENERAL
                )
            elif kind == KIND_SOUND and field == 1:
                entry["follow"] = value or ""
            else:
                entry["face"] = value
        self.dropdown_field = None
        self.number_buffer = None
        self.dirty = True

    # ---- 数字字段的键盘输入 -----------------------------------------
    def dialog_number_value(self, field: int):
        """字段是数字就返回当前值；朝向、跟随、触发卡片这类枚举返回 None。"""
        if self.dialog is None:
            return None
        kind = self.dialog["kind"]
        entry = self.dialog["entry"]
        if kind == KIND_GLOBAL_ANIMATION:
            size = entry.get("size") or [1.0, 1.0]
            offset = entry.get("offset") or [0.0, 0.0]
            values = (size[0], size[1], offset[0], offset[1])
            return values[field] if 0 <= field < len(values) else None
        if kind == KIND_GLOBAL_SOUND:
            return None
        if kind == KIND_SOUND:
            return None                     # 声音只有预设一格，没有数字字段
        if field == 0:
            return entry["pos"][0]
        if field == 1:
            return entry["pos"][1]
        if field in (2, 3):
            return entry.get("size", [1.0, 1.0])[field - 2]
        if kind == KIND_MOVABLE and field in (4, 5):
            return entry.get("offset", [0, -3])[field - 4]
        if kind == KIND_NOZZLE and field == 5:
            return entry.get("power", NOZZLE_DEFAULT_POWER)
        if kind == KIND_TRIGGER_SOURCE and field == 5:
            return entry.get("jump_offset", 0.0)
        return None

    def set_dialog_number(self, field: int, value: float) -> None:
        """把一个数字字段设成 value：位置、尺寸、偏移、力度都可以带小数。"""
        kind = self.dialog["kind"]
        entry = self.dialog["entry"]
        if kind == KIND_GLOBAL_ANIMATION:
            size = list(entry.get("size") or [1.0, 1.0])
            offset = list(entry.get("offset") or [0.0, 0.0])
            if field in (0, 1):
                size[field] = max(MIN_SIZE, round(value, 2))
                entry["size"] = size
            elif field in (2, 3):
                offset[field - 2] = round(value, 2)
                entry["offset"] = offset
            return
        pos = entry["pos"]
        if field == 0:
            pos[0] = round(value, 2)
        elif field == 1:
            pos[1] = round(value, 2)
        elif field in (2, 3):
            size = list(entry.get("size", [1.0, 1.0]))
            size[field - 2] = max(MIN_SIZE, round(value, 2))
            entry["size"] = size
            if kind == KIND_NOZZLE:
                clamp_nozzle_power(entry)  # 风区变长，力度至少要比它多 0.5 格
        elif kind == KIND_MOVABLE and field in (4, 5):
            # 偏移不许超过关卡本身：横向看关卡宽度，纵向看关卡高度
            limit = float(self.level.width if field == 4 else self.level.height)
            offset = list(entry.get("offset", [0, -3]))
            offset[field - 4] = round(clamp_float(value, -limit, limit, 0.0), 2)
            entry["offset"] = offset
        elif kind == KIND_NOZZLE and field == 5:
            # 力度是沿着朝向走出去多远：下限是风区长度 + 0.5 格
            entry["power"] = round(value, 2)
            clamp_nozzle_power(entry)
        elif kind == KIND_TRIGGER_SOURCE and field == 5:
            # 跳高变化量：正数跳更高、负数跳更低，按下期间生效
            entry["jump_offset"] = round(
                clamp_float(value, TRIGGER_JUMP_OFFSET_MIN, TRIGGER_JUMP_OFFSET_MAX, 0.0),
                2,
            )

    def type_dialog_number(self, char: str) -> bool:
        """数字字段键盘输入：第一次敲键起一个新值，之后追加，可以带一个小数点。

        负号只允许打头（偏移可以是负的，力度敲了负号也会被夹回 0）；直接敲小数点就当
        用户想打「0.」。返回是否吃掉了字符。
        """
        if self.dialog is None or self.name_focused:
            return False
        if self.dialog_number_value(self.dialog_field) is None:
            return False
        if char.isdigit():
            if self.number_buffer is None:
                self.number_buffer = ""
                if self.global_active():
                    self.push_global_undo()
                else:
                    self.push_undo()       # 一次完整输入只记一步撤销
            if len(self.number_buffer) < NUMBER_TEXT_MAX_LENGTH:
                self.number_buffer += char
        elif char == "-" and self.number_buffer is None:
            self.number_buffer = "-"       # 负号只允许打头（力度回头会被夹到 0）
            if self.global_active():
                self.push_global_undo()
            else:
                self.push_undo()
        elif char == "." and "." not in (self.number_buffer or ""):
            if self.number_buffer is None:
                self.number_buffer = "0"   # 空着就敲小数点：当成在打「0.」
                self.push_undo()
            if len(self.number_buffer) < NUMBER_TEXT_MAX_LENGTH:
                self.number_buffer += "."
        else:
            return False
        self.apply_number_buffer()
        return True

    def apply_number_buffer(self) -> None:
        """把输入框里的文本写回字段；还没构成数字（空串、「-」、「-.」）时先不动。"""
        text = self.number_buffer or ""
        if not text or text == "-":
            return
        try:
            value = float(text)
        except ValueError:
            return
        self.set_dialog_number(self.dialog_field, value)
        if not self.global_active():
            self.dirty = True

    def erase_dialog_number(self) -> None:
        if not self.number_buffer:
            return
        self.number_buffer = self.number_buffer[:-1]
        self.apply_number_buffer()

    def blur_number(self) -> None:
        self.number_buffer = None

    def move_dialog_field(self, delta: int) -> None:
        """上下键换一格：属性行和触发卡片的格子排成一串，纯显示的行跳过。"""
        self.number_buffer = None
        fields = self.dialog_fields()
        if not fields:
            return
        current = self.dialog_field
        index = fields.index(current) if current in fields else 0
        self.dialog_field = fields[(index + delta) % len(fields)]

    # ---- 关卡设置 ---------------------------------------------------
    def settings_override(self, key: str) -> str:
        """这一关覆盖的玩家参数；空串表示跟随游戏配置。"""
        player = self.level.player
        if not isinstance(player, dict) or key not in player:
            return ""
        return f"{player[key]:g}" if isinstance(player[key], (int, float)) else str(player[key])

    def open_settings(self) -> None:
        if self._defer_global(("open_settings",)):
            return
        # 名称以外的数字项都按字符串编辑：可以直接敲数字，也可以点右边的加减
        flip_up, flip_down = self.level.flip_area_offsets
        music = sound.fields_of(self.level.sound)
        self.settings = {            "name": self.level.name,
            "width": str(self.level.width),
            "height": str(self.level.height),
            "flip_up": f"{flip_up:g}",
            "flip_down": f"{flip_down:g}",
            "background": self.level.background,
            # 玩家参数默认来自 game.json；这两格空着就是跟随，填了就覆盖
            "jump_height": self.settings_override("jump_height"),
            "move_speed": self.settings_override("move_speed"),
            # 这一关的音乐跟着关卡文件走，在「声音」页里改：库里的键 + 循环 + 淡入淡出
            "sound": music["sound"],
            "loop": music["loop"],
            "fade_in": music["fade_in"],
            "fade_out": music["fade_out"],
        }
        self.settings_tab = 0
        self.settings_field = 0
        self.cutscene = cutscene.from_value(self.level.cutscene, self.sound_library)
        self.cutscene_scope = "level"
        self.cutscene_field = 0
        self.cutscene_scroll = 0
        self.preview.stop()
        self.push_undo()

    # ---- 关卡设置的分页 ---------------------------------------------
    def settings_fields(self) -> tuple:
        """当前这一页有哪几个字段（下标）；过场页是卡片，没有这种字段。"""
        tab = max(0, min(self.settings_tab, len(SETTINGS_TABS) - 1))
        return SETTINGS_TABS[tab][1]

    def settings_cutscene_tab(self) -> bool:
        return self.settings_tab == SETTINGS_CUTSCENE_TAB

    def select_settings_tab(self, index: int) -> None:
        """点页签切页；换页时把试听停下。"""
        if not 0 <= index < len(SETTINGS_TABS) or index == self.settings_tab:
            return
        self.preview.stop()
        self.sound_menu = None
        self.settings_tab = index
        if index == SETTINGS_CUTSCENE_TAB:
            self.cutscene_field = 0
            self.cutscene_scroll = 0
            return
        fields = self.settings_fields()
        if fields:
            self.settings_field = fields[0]

    def switch_settings_tab(self, delta: int) -> None:
        """Tab / Shift+Tab：在常规、玩家、声音、过场之间转。"""
        self.select_settings_tab((self.settings_tab + delta) % len(SETTINGS_TABS))

    def move_settings_field(self, delta: int) -> None:
        """上下键只在当前这一页里走。"""
        if self.settings_cutscene_tab():
            self.move_cutscene_field(delta)
            return
        fields = self.settings_fields()
        index = fields.index(self.settings_field) if self.settings_field in fields else 0
        self.settings_field = fields[(index + delta) % len(fields)]

    def close_settings(self, commit: bool) -> None:
        self.preview.stop()                # 试听只在面板开着的时候有意义
        self.sound_menu = None
        if self.settings is not None and commit:
            name = self.settings["name"]
            self.level.name = name
            self.level.width = clamp_int(
                self.settings["width"], LEVEL_WIDTH_MIN, LEVEL_WIDTH_MAX, COLS
            )
            self.level.height = clamp_int(
                self.settings["height"], LEVEL_HEIGHT_MIN, LEVEL_HEIGHT_MAX, ROWS
            )
            # 翻转带的高度最多到关卡高度
            flip_limit = float(self.level.height)
            self.level.flip_area_offsets = [
                clamp_float(self.settings["flip_up"], 0.0, flip_limit, 0.0),
                clamp_float(self.settings["flip_down"], 0.0, flip_limit, 0.0),
            ]
            self.level.background = self.settings["background"]
            self._apply_player_override()
            # 这一关的音乐：选了库里的声音才写 sound，空着就把它删掉
            self.level.sound = sound.to_object(
                {
                    "sound": self.settings["sound"],
                    "loop": self.settings["loop"],
                    "fade_in": self.settings["fade_in"],
                    "fade_out": self.settings["fade_out"],
                }
            )
            # 这一关的过场：没有图片就把 cutscene 键整个去掉
            self.level.cutscene = cutscene.to_object(self.cutscene) if self.cutscene else None
            self.dirty = True
            background = self.level.background or "无"
            flip_up, flip_down = self.level.flip_area_offsets
            jump, speed, overridden = self.player_stats()
            music = (
                sound.key_label(self.sound_library, self.level.sound.get("sound"))
                if self.level.sound
                else "无"
            )
            pictures = len(self.level.cutscene["pictures"]) if self.level.cutscene else 0
            self.status = (
                f"关卡设置：名称 {self.level.name or '（空）'}，"
                f"尺寸 {self.level.width}×{self.level.height}，"
                f"翻转带 上 {flip_up:g} / 下 {flip_down:g}，背景 {background}，"
                f"跳高 {jump:g} / 速度 {speed:g}"
                f"{'（本关覆盖游戏配置）' if overridden else '（跟随游戏配置）'}，"
                f"音乐 {music}，过场 {pictures} 张图。"
            )
        self.settings = None
        self.cutscene = None

    def _apply_player_override(self) -> None:
        """把关卡设置里填的跳高、速度写进 player；空格子表示跟随游戏配置，删掉这个键。"""
        if self.settings is None:
            return
        if not isinstance(self.level.player, dict):
            # 没有起点就没有玩家，这两项没地方挂
            return
        jump_text = str(self.settings.get("jump_height") or "").strip()
        speed_text = str(self.settings.get("move_speed") or "").strip()
        limit = max(JUMP_HEIGHT_MIN, float(self.level.height) - 1.0)
        if jump_text:
            self.level.player["jump_height"] = round(
                clamp_float(jump_text, JUMP_HEIGHT_MIN, limit, JUMP_HEIGHT_DEFAULT), 2
            )
        else:
            self.level.player.pop("jump_height", None)
        if speed_text:
            self.level.player["move_speed"] = round(
                clamp_float(speed_text, MOVE_SPEED_MIN, MOVE_SPEED_MAX, MOVE_SPEED_DEFAULT), 2
            )
        else:
            self.level.player.pop("move_speed", None)
        if not self.level.player:
            # 空表没意义，但起点本身要留着
            self.level.player["pos"] = [0, 0]

    def pick_background(self) -> None:
        """挑一张背景图：只记路径，不复制文件。"""
        if self.settings is None:
            return
        path = ask_image_path("选择背景图", self.media_base_dir)
        if not path:
            self.status = "已取消选择背景。"
            return
        self.settings["background"] = relative_level_path(path, self.media_base_dir)
        self.settings_field = 5
        self.status = "已选择背景：仅记录相对 game.json 的路径，不复制文件。"

    def preview_level_audio(self) -> None:
        """试听这一关的声音页：按这一页的循环与淡入放，再点一次停。"""
        if self.settings is None:
            return
        path = self.sound_library_path(self.settings.get("sound"))
        if path is None:
            self.preview.stop()
            self.status = (
                f"找不到这首曲子：{sound.key_label(self.sound_library, self.settings.get('sound'))}。"
            )
            return
        self.status = self.preview.toggle(
            path,
            bool(self.settings["loop"]),
            clamp_float(
                self.settings["fade_in"],
                0.0,
                sound.MAX_FADE_SECONDS,
                sound.DEFAULT_FADE_IN,
            ),
        )

    def pick_texture_image(self) -> None:
        """给当前贴图换一张图：只记相对 game.json 的路径，不复制文件。"""
        if self.dialog is None or self.dialog["kind"] != KIND_TEXTURE:
            return
        path = ask_image_path("选择贴图", self.media_base_dir)
        if not path:
            self.status = "已取消选择贴图。"
            return
        self.push_undo()
        self.dirty = True
        self.dialog["entry"]["image"] = relative_level_path(path, self.media_base_dir)
        self.number_buffer = None
        self.status = "已更换贴图：路径相对 game.json。"

    def adjust_settings(self, delta: int) -> None:
        if self.settings is None:
            return
        if self.settings_cutscene_tab():
            self.adjust_cutscene(delta)
            return
        field = self.settings_field
        if field == 1:
            self._step_size("width", delta, LEVEL_WIDTH_MIN, LEVEL_WIDTH_MAX, COLS)
        elif field == 2:
            self._step_size("height", delta, LEVEL_HEIGHT_MIN, LEVEL_HEIGHT_MAX, ROWS)
        elif field in (3, 4):
            # 翻转带高度：按 0.5 加减，最多到关卡高度
            key = "flip_up" if field == 3 else "flip_down"
            height = clamp_int(
                self.settings["height"], LEVEL_HEIGHT_MIN, LEVEL_HEIGHT_MAX, self.level.height
            )
            current = clamp_float(self.settings[key], 0.0, float(height), 0.0)
            self.settings[key] = f"{max(0.0, min(float(height), current + 0.5 * delta)):g}"
        elif field == 6:
            # 跳高覆盖：空着时从游戏配置的值起步，±0.5 格（可以填小数）
            height = clamp_int(
                self.settings["height"], LEVEL_HEIGHT_MIN, LEVEL_HEIGHT_MAX, self.level.height
            )
            limit = max(JUMP_HEIGHT_MIN, float(height) - 1.0)
            fallback = clamp_float(
                self.game_player.get("jump_height"), JUMP_HEIGHT_MIN, limit, JUMP_HEIGHT_DEFAULT
            )
            current = clamp_float(
                self.settings["jump_height"], JUMP_HEIGHT_MIN, limit, fallback
            )
            stepped = max(
                JUMP_HEIGHT_MIN, min(limit, current + JUMP_HEIGHT_STEP * delta)
            )
            self.settings["jump_height"] = f"{stepped:g}"
        elif field == 7:
            # 速度覆盖：空着时从游戏配置的值起步，±0.5
            fallback = clamp_float(
                self.game_player.get("move_speed"),
                MOVE_SPEED_MIN,
                MOVE_SPEED_MAX,
                MOVE_SPEED_DEFAULT,
            )
            current = clamp_float(
                self.settings["move_speed"], MOVE_SPEED_MIN, MOVE_SPEED_MAX, fallback
            )
            stepped = max(MOVE_SPEED_MIN, min(MOVE_SPEED_MAX, current + 0.5 * delta))
            self.settings["move_speed"] = f"{stepped:g}"
        elif field == 8:
            # 声音：在声音库的键和「无」之间前后换
            self.settings["sound"] = _cycle_key(
                self.sound_library, self.settings["sound"], delta
            )
        elif field == 9:
            # 循环播放：左右键（或点整行）切换
            self.settings["loop"] = not bool(self.settings["loop"])
        elif field in (10, 11):
            # 淡入淡出：按 0.5 秒一步，0~10 秒
            key = "fade_in" if field == 10 else "fade_out"
            fallback = sound.DEFAULT_FADE_IN if field == 10 else sound.DEFAULT_FADE_OUT
            current = clamp_float(self.settings[key], 0.0, sound.MAX_FADE_SECONDS, fallback)
            stepped = max(
                0.0, min(sound.MAX_FADE_SECONDS, current + sound.FADE_STEP * delta)
            )
            self.settings[key] = f"{stepped:g}"

    def _step_size(self, key: str, delta: int, low: int, high: int, fallback: int) -> None:
        """宽高在编辑期间是字符串：先夹回合法区间再加，空字符串按默认值算。"""
        current = clamp_int(self.settings[key], low, high, fallback)
        self.settings[key] = str(max(low, min(high, current + delta)))

    def type_settings(self, char: str) -> None:
        if self.settings is None:
            return
        if self.settings_cutscene_tab():
            self.type_cutscene(char)
            return
        field = self.settings_field
        if field == 0:
            if char.isprintable() and len(self.settings["name"]) < 24:
                self.settings["name"] += char
        elif field in (1, 2):
            # 数字项只吃数字：宽度最多 4 位（1000 格上限），高度 2 位够用
            key = {1: "width", 2: "height"}[field]
            if char.isdigit() and len(str(self.settings[key])) < (4 if field == 1 else 2):
                self.settings[key] = str(self.settings[key]) + char
        elif field in (3, 4):
            # 翻转带高度：数字和小数点，最多 5 位
            key = "flip_up" if field == 3 else "flip_down"
            if (char.isdigit() or char == ".") and len(str(self.settings[key])) < 5:
                self.settings[key] = str(self.settings[key]) + char
        elif field == 5:
            # 背景是路径：可打印字符都能打
            if char.isprintable() and len(self.settings["background"]) < BACKGROUND_MAX_LENGTH:
                self.settings["background"] += char
        elif field == 6:
            # 跳高覆盖：数字和小数点，最多 4 位
            if (char.isdigit() or char == ".") and len(self.settings["jump_height"]) < 4:
                self.settings["jump_height"] += char
        elif field == 7:
            # 速度覆盖：数字和小数点，最多 5 位
            if (char.isdigit() or char == ".") and len(self.settings["move_speed"]) < 5:
                self.settings["move_speed"] += char
        elif field == 8:
            # 声音是库里的键：用左右键换，不直接敲字
            pass
        elif field in (10, 11):
            # 淡入淡出：数字和小数点，最多 5 位
            key = "fade_in" if field == 10 else "fade_out"
            if (char.isdigit() or char == ".") and len(str(self.settings[key])) < 5:
                self.settings[key] = str(self.settings[key]) + char

    def erase_settings_char(self) -> None:
        if self.settings is None:
            return
        if self.settings_cutscene_tab():
            self.erase_cutscene_char()
            return
        field = self.settings_field
        if field == 0:
            self.settings["name"] = self.settings["name"][:-1]
        elif field in (1, 2):
            key = {1: "width", 2: "height"}[field]
            self.settings[key] = str(self.settings[key])[:-1]
        elif field in (3, 4):
            key = "flip_up" if field == 3 else "flip_down"
            self.settings[key] = str(self.settings[key])[:-1]
        elif field == 5:
            self.settings["background"] = self.settings["background"][:-1]
        elif field == 6:
            self.settings["jump_height"] = self.settings["jump_height"][:-1]
        elif field == 7:
            self.settings["move_speed"] = self.settings["move_speed"][:-1]
        elif field == 8:
            pass                        # 声音是库里的键，退格不删它
        elif field in (10, 11):
            key = "fade_in" if field == 10 else "fade_out"
            self.settings[key] = str(self.settings[key])[:-1]


# ---- 绘制 -----------------------------------------------------------
