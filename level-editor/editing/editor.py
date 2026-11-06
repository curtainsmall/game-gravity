"""Editor：编辑器状态与所有编辑操作。"""

import copy
import json
import os
from typing import TYPE_CHECKING

from core.constants import (
    BACKGROUND_MAX_LENGTH,
    BUTTON_SIZE,
    COLS,
    HANDLE_PIXELS,
    HEADER,
    JUMP_HEIGHT_DEFAULT,
    JUMP_HEIGHT_MIN,
    FACE_LABELS,
    FACE_ORDER,
    KIND_BLOCK,
    KIND_BUTTON,
    KIND_DESTINATION,
    KIND_HAS_NAME,
    KIND_ITEM,
    KIND_MOVABLE,
    KIND_NOZZLE,
    KIND_PLANK,
    KIND_PLAYER,
    KIND_PORTAL,
    KIND_TEXTURE,
    KIND_TITLES,
    LEVEL_HEIGHT_MAX,
    LEVEL_HEIGHT_MIN,
    LEVEL_SCENE_NAME,
    LEVEL_WIDTH_MAX,
    LEVEL_WIDTH_MIN,
    MARGIN,
    MIN_SIZE,
    MOVE_SPEED_DEFAULT,
    MOVE_SPEED_MAX,
    MOVE_SPEED_MIN,
    NAME_MAX_LENGTH,
    NOZZLE_DEFAULT_POWER,
    NUMBER_TEXT_MAX_LENGTH,
    PORTAL_SIZE,
    ROWS,
    TOOL_BLOCK,
    TOOL_BUTTON,
    TOOL_DEST,
    TOOL_ITEM,
    TOOL_NOZZLE,
    TOOL_PLANK,
    TOOL_PLAYER,
    TOOL_PORTAL,
    TOOL_SPECS,
    TOOL_TEXTURE,
)
from core.helpers import (
    clamp_float,
    clamp_int,
    display_path,
    folder_is_empty,
    folder_name_for,
    level_base_dir,
    normalize_rect,
    nozzle_box,
    nozzle_face_axis,
    nozzle_marker_box,
    nozzle_power_tip,
    number_text,
    object_box,
    relative_level_path,
    resolve_level_path,
    round_rect,
    snap,
)
from core.level import Level, dump_level
from editing.files import ask_image_path, ask_level_folder
from view.texture import image_size

if TYPE_CHECKING:
    from view.layout import Layout


class Editor:
    def __init__(self) -> None:
        self.level = Level()
        self.path: str | None = None
        self.dirty = False
        self.undo_stack: list = []
        self.tool = TOOL_BLOCK
        self.zoom: float | None = None
        self.pan_x = 0.0
        self.pan_y = 0.0
        self.hovered = None
        self.hovered_handle = None              # 光标下的角把手：(kind, entry, corner)
        self.selection: list = []               # 选中的对象：(kind, entry)
        self.marquee_start: tuple | None = None  # 左键拖出的框选，世界坐标
        self.marquee_current: tuple | None = None
        self.marquee_additive = False            # 框选开始时是否按着 Ctrl
        self.drag_start: tuple | None = None
        self.drag_current: tuple | None = None
        self.pan_drag: tuple | None = None
        self.dialog: dict | None = None
        self.dialog_field = 0
        self.dropdown_field: int | None = None   # 正在展开下拉列表的选择型字段
        self.name_focused = False
        self.number_buffer: str | None = None   # 正在键盘输入的数字字段，None 表示没在输入
        self.object_grab: dict | None = None    # 正在用鼠标拖对象：移动或缩放
        self.snapping = False                   # 按住 Shift：吸附到整格
        self.keep_ratio = False                 # 按住 Ctrl：贴图等比缩放
        self.click_through = False              # 按住 Alt：穿透最上层
        self.last_mouse = (0, 0)
        self.view_menu_open = False
        # 视图设置：只影响编辑器自己的显示，从不写进关卡数据、不落盘
        self.view_settings: dict = {"background": True, "debug": True}
        self.menu_open = False
        self.menu_origin = (MARGIN, HEADER)
        self.creating = False
        self.settings: dict | None = None
        self.settings_field = 0
        self.player_settings: dict | None = None   # 玩家设置浮层：跳高、速度
        self.player_settings_field = 0
        self.confirm_quit = False
        self.startup = True
        self.status = "新建关卡或打开一个已有关卡"

    # ---- 查询 -------------------------------------------------------
    def all_entries(self) -> list:
        """所有有矩形的对象，按绘制顺序（先画的在前）：(kind, entry)。"""
        pairs = []
        for entries, kind in (
            (self.level.blocks, KIND_BLOCK),
            (self.level.planks, KIND_PLANK),
            (self.level.movable_blocks, KIND_MOVABLE),
            (self.level.textures, KIND_TEXTURE),
            (self.level.buttons, KIND_BUTTON),
            (self.level.portals, KIND_PORTAL),
            (self.level.items, KIND_ITEM),
        ):
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
        stack = []
        if self.level.destination is not None and self._hit(
            position, layout, KIND_DESTINATION, self.level.destination
        ):
            stack.append((KIND_DESTINATION, self.level.destination))
        if self.level.player is not None and self._hit(
            position, layout, KIND_PLAYER, self.level.player
        ):
            stack.append((KIND_PLAYER, self.level.player))
        for entry in reversed(self.level.nozzles):
            if self._hit(position, layout, KIND_NOZZLE, entry):
                stack.append((KIND_NOZZLE, entry))
        for kind, entry in reversed(self.all_entries()):
            if self._hit(position, layout, kind, entry):
                stack.append((kind, entry))
        return stack

    @staticmethod
    def _hit(position: tuple, layout: Layout, kind: str, entry: dict) -> bool:
        return layout.entry_rect(object_box(kind, entry)).collidepoint(position)

    def object_at(self, position: tuple, layout: Layout):
        """最上层的那个对象；按住 Alt 时穿透一层。"""
        stack = self.object_stack_at(position, layout)
        if not stack:
            return None
        index = 1 if (self.click_through and len(stack) > 1) else 0
        return stack[index]

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
        """光标压在哪个手柄上：选中项优先，然后按绘制顺序从上往下找。"""
        candidates = []
        if self.dialog is not None:
            candidates.append((self.dialog["kind"], self.dialog["entry"]))
        candidates += [(kind, entry) for kind, entry in reversed(self.all_entries())]
        candidates += [(KIND_NOZZLE, entry) for entry in reversed(self.level.nozzles)]
        for kind, entry in candidates:
            name = self.handle_at(layout, kind, entry, position)
            if name is not None:
                return kind, entry, name
        return None

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
        """挑出光标下的对象：只认最上层那个（按住 Alt 时穿透一层）。"""
        self.last_mouse = (position[0], position[1])
        self.hovered = None
        self.hovered_handle = None
        # 画布铺满整个窗口：顶部信息栏、底部状态栏只是画字，不挡对象，
        # 所以整个窗口都算工作区，对象长到哪就点到哪
        if not (0 <= position[0] < layout.window[0] and 0 <= position[1] < layout.window[1]):
            return
        # 手柄优先：力度箭头末端、然后四角/四边，不然压在方块上的对象永远抓不到
        self.hovered_handle = self.power_handle_at(position, layout)
        if self.hovered_handle is None:
            self.hovered_handle = self.object_handle_at(position, layout)
        # 只选最上层那个：不隔着另一个对象去点它后面的东西
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
        else:
            self.level.movable_blocks.append(
                {
                    "name": "",
                    "pos": [x, y],
                    "size": [w, h],
                    "offset": [0, 0],
                    "sources": [],
                }
            )
        self.dirty = True
        self.status = f"新增{TOOL_SPECS[self.tool][0]} ({x}, {y}) {w}×{h}"

    def place_single(self, point: tuple) -> None:
        """按钮/道具/喷口/起点/终点：就地放下一个 1×1 的对象。"""
        x, y = point
        size = [1.0, 1.0]
        level = self.level
        self.push_undo()
        self.dirty = True
        # 新对象的数值/布尔/字符串一律给中性默认值，具体参数再在面板里调
        if self.tool == TOOL_BUTTON:
            # 按钮画出来的矩形就是触发区，所以缺省就是 1×0.3
            level.buttons.append(
                {"name": "", "pos": [x, y], "size": list(BUTTON_SIZE), "face": ""}
            )
        elif self.tool == TOOL_PORTAL:
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
        elif self.tool == TOOL_ITEM:
            level.items.append({"name": "", "pos": [x, y], "size": list(size), "heavy": False})
        elif self.tool == TOOL_NOZZLE:
            # 喷口的 size 就是风区（宽 × 长），face 是伸出的方向，power 是目标离底面多远
            level.nozzles.append(
                {
                    "pos": [x, y],
                    "face": FACE_ORDER[0],
                    "power": 0,
                    "size": list(NOZZLE_DEFAULT_SIZE),
                }
            )
        elif self.tool == TOOL_PLAYER:
            # 起点只有一份：再放一次就是把它挪过去
            level.player = {"pos": [x, y], "size": list(size)}
        elif self.tool == TOOL_DEST:
            # 终点也只有一份
            level.destination = {"pos": [x, y], "size": list(size)}
        self.status = f"新增{TOOL_SPECS[self.tool][0]} ({x}, {y})"

    def delete_entry(self, kind: str, entry: dict) -> None:
        self.push_undo()
        self.dirty = True
        self.remove_entry(kind, entry)
        self.dialog = None
        self.dropdown_field = None
        self.selection = []
        self.hovered = None
        self.number_buffer = None
        self.status = f"已删除{KIND_TITLES.get(kind, '对象')}"

    # ---- 撤销 -------------------------------------------------------
    def push_undo(self) -> None:
        self.undo_stack.append(copy.deepcopy(self.level.to_definition()))
        if len(self.undo_stack) > 200:
            self.undo_stack.pop(0)

    def undo(self) -> None:
        if not self.undo_stack:
            self.status = "没有可撤销的操作"
            return
        self.level = Level.from_definition(self.undo_stack.pop())
        self.dialog = None
        self.dropdown_field = None
        self.selection = []
        self.marquee_start = None
        self.marquee_current = None
        self.dirty = True
        self.status = "已撤销"

    # ---- 文件 -------------------------------------------------------
    def new_level(self) -> None:
        self.level = Level()
        self.path = None
        self.undo_stack.clear()
        self.dirty = False
        self.dialog = None
        self.dropdown_field = None
        self.selection = []
        self.marquee_start = None
        self.marquee_current = None
        self.name_focused = False
        self.number_buffer = None
        self.startup = False
        self.zoom = None
        self.pan_x = self.pan_y = 0.0
        self.drag_start = self.drag_current = None
        self.status = "新建关卡（尚未保存）"
        # 新建之后先把关卡设置摊开：名字、尺寸、跳高这些一上来就能填
        self.open_settings()

    def open_level(self) -> None:
        folder = ask_level_folder("打开关卡文件夹")
        if not folder:
            self.status = "打开已取消"
            return
        self.load(folder)

    def load(self, folder: str) -> None:
        """打开一个关卡文件夹：数据在里面的 scene.json。"""
        scene_path = os.path.join(folder, LEVEL_SCENE_NAME)
        try:
            with open(scene_path, encoding="utf-8") as file:
                definition = json.load(file)
        except (OSError, json.JSONDecodeError) as error:
            self.status = f"打开失败：{error}"
            return
        self.level = Level.from_definition(definition)
        if not self.level.name:
            self.level.name = os.path.basename(os.path.normpath(folder))
        self.path = folder
        self.undo_stack.clear()
        self.dirty = False
        self.dialog = None
        self.dropdown_field = None
        self.selection = []                 # 上一个关卡的选中项不能带过来
        self.marquee_start = None
        self.marquee_current = None
        self.name_focused = False
        self.number_buffer = None
        self.startup = False
        self.zoom = None
        self.pan_x = self.pan_y = 0.0
        self.drag_start = self.drag_current = None
        self.status = f"已打开 {display_path(folder)}"

    def save(self) -> None:
        """保存到关卡文件夹：scene.json 放数据，图片只记相对路径、一个都不复制。"""
        folder = self.path
        if folder is None:
            folder = ask_level_folder("保存到")
            if not folder:
                self.status = "保存已取消"
                return
            folder = self.folder_for_new_level(folder)
            if folder is None:
                return
        folder = os.path.normpath(folder)
        if not self.level.name:
            self.level.name = os.path.basename(folder)
        try:
            os.makedirs(folder, exist_ok=True)
            self.normalize_media_paths(folder)
            with open(
                os.path.join(folder, LEVEL_SCENE_NAME), "w", encoding="utf-8", newline="\n"
            ) as file:
                file.write(dump_level(self.level.to_definition()))
        except OSError as error:
            self.status = f"保存失败：{error}"
            return
        self.path = folder
        self.dirty = False
        self.status = f"已保存 {display_path(folder)}"

    def folder_for_new_level(self, chosen: str) -> str | None:
        """新关卡存哪儿：选中的是空文件夹就直接用它，否则在里面按关卡名新建一层。

        所以既可以先自己建个空文件夹再选它，也可以直接选 assets/levels，
        编辑器会自己建出 assets/levels/<关卡名>。
        """
        folder = os.path.normpath(chosen)
        if not folder_is_empty(folder):
            folder = os.path.join(folder, folder_name_for(self.level.name))
        try:
            os.makedirs(folder, exist_ok=True)
        except OSError as error:
            self.status = f"新建关卡文件夹失败：{error}"
            return None
        return folder

    def normalize_media_paths(self, folder: str) -> None:
        """背景和贴图都只记相对 scene.json 的路径，一个文件都不复制。

        图片要事先放进关卡文件夹（或者任意位置，只要相对路径写得出来）；
        找不到的路径原样留着，别把用户填的值抹掉。
        """
        if self.level.background:
            source = resolve_level_path(self.level.background, folder)
            if source is not None:
                self.level.background = relative_level_path(source, folder)
        for entry in self.level.textures:
            value = entry.get("image")
            if not value:
                continue
            source = resolve_level_path(value, folder)
            if source is None:
                continue
            entry["image"] = relative_level_path(source, folder)

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
        self.tool = tool
        self.creating = True
        self.menu_open = False
        action = "左键拖出矩形" if TOOL_SPECS[tool][1] == "rect" else "左键单击放置"
        self.status = f"新建：{TOOL_SPECS[tool][0]}（{action}，右键退出）"

    # ---- 贴图 -------------------------------------------------------
    def import_texture(self, layout: Layout) -> None:
        """直接导入一张贴图：不复制，只记一个相对 scene.json 的路径。

        图片按游戏比例（可玩行 400px）换算成世界格尺寸，位置和大小之后在详情里调。
        """
        path = ask_image_path("导入贴图", level_base_dir(self.path))
        if not path:
            self.status = "导入贴图已取消"
            return
        pixels = image_size(path)
        if pixels is None:
            self.status = f"图片读不出来：{os.path.basename(path)}"
            return
        tile = max(1.0, layout.game_tile)
        width = max(MIN_SIZE, round(pixels[0] / tile, 2))
        height = max(MIN_SIZE, round(pixels[1] / tile, 2))
        at = layout.world_point(self.menu_origin)
        image = relative_level_path(path, self.path)
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
        self.status = f"已导入贴图 {os.path.basename(path)}（{width}×{height} 格）"

    # ---- 鼠标拖动 / 缩放（所有对象） --------------------------------
    def begin_object_grab(self, position: tuple, layout: Layout) -> bool:
        """左键按下：先看是不是压在某个角把手上（缩放），再看是不是落在对象里（移动）。

        只动按下的那一个：多选只是列清单，不做整组编辑。
        """
        hit = self.hovered_handle
        if hit is None:
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
            # 拖力度箭头末端：末端到 pos 的距离（沿朝向）就是 power，不给负的
            step_x, step_y = nozzle_face_axis(entry)
            reach = (point[0] - x) * step_x + (point[1] - y) * step_y
            if self.snapping:
                reach = snap(reach)
            entry["power"] = round(clamp_float(reach, 0.0, 8.0, 0.0), 2)
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

        按钮、传送门和喷口的 pos 都是「底面」的中心、size 是没转过的宽高（左右朝向时
        屏幕上的宽高是反的），所以缩放后都要换算回这种写法。
        """
        if kind in (KIND_BUTTON, KIND_PORTAL, KIND_NOZZLE):
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
        text = f"{KIND_TITLES.get(kind, '对象')} ({entry['pos'][0]}, {entry['pos'][1]})"
        if size:
            text += f" {size[0]}×{size[1]}"
        self.status = text
        return True

    # ---- 选择 -------------------------------------------------------
    def select(self, kind: str, entry: dict) -> None:
        """单选：同时打开属性面板。"""
        self.selection = [(kind, entry)]
        self.dialog = {"kind": kind, "entry": entry}
        self.dialog_field = 0
        self.dropdown_field = None
        self.name_focused = False
        self.number_buffer = None
        self.status = f"已选中{KIND_TITLES.get(kind, '对象')}"

    def select_many(self, pairs: list) -> None:
        """多选：面板只列清单和数量，不给属性；正好一个时回到属性面板。"""
        self.selection = list(pairs)
        if len(self.selection) == 1:
            kind, entry = self.selection[0]
            self.dialog = {"kind": kind, "entry": entry}
            self.dialog_field = 0
        else:
            self.dialog = None
        self.dropdown_field = None
        self.name_focused = False
        self.number_buffer = None
        self.status = f"已选中 {len(self.selection)} 个对象" if self.selection else "已取消选中"

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
        pos = entry["pos"]
        name = entry.get("name") or KIND_TITLES.get(kind, "对象")
        return f"{name} ({pos[0]}, {pos[1]})"

    def delete_selection(self) -> None:
        """删掉所有选中的对象，算一步撤销。"""
        if not self.selection:
            self.status = "没有选中的对象"
            return
        self.push_undo()
        count = len(self.selection)
        for kind, entry in self.selection:
            self.remove_entry(kind, entry)
        self.select_many([])
        self.hovered = None
        self.dirty = True
        self.status = f"已删除 {count} 个对象"

    def remove_entry(self, kind: str, entry: dict) -> None:
        if kind == KIND_BLOCK:
            self.level.blocks = [e for e in self.level.blocks if e is not entry]
        elif kind == KIND_PLANK:
            self.level.planks = [e for e in self.level.planks if e is not entry]
        elif kind == KIND_MOVABLE:
            self.level.movable_blocks = [e for e in self.level.movable_blocks if e is not entry]
        elif kind == KIND_BUTTON:
            self.level.buttons = [e for e in self.level.buttons if e is not entry]
        elif kind == KIND_PORTAL:
            self.level.portals = [e for e in self.level.portals if e is not entry]
        elif kind == KIND_ITEM:
            self.level.items = [e for e in self.level.items if e is not entry]
        elif kind == KIND_NOZZLE:
            self.level.nozzles = [e for e in self.level.nozzles if e is not entry]
        elif kind == KIND_TEXTURE:
            self.level.textures = [e for e in self.level.textures if e is not entry]
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
            for kind, entry in self.all_entries()
            if self._in_marquee(kind, entry, x0, y0, x1, y1)
        ]
        for entry in self.level.nozzles:
            if self._in_marquee(KIND_NOZZLE, entry, x0, y0, x1, y1):
                picked.append((KIND_NOZZLE, entry))
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
        self.status = "已退出新建；左键 设置/框选，右键 新建"

    # ---- 退出确认 ---------------------------------------------------
    def request_quit(self) -> bool:
        """真能退出就返回 True；有未保存的改动就先弹确认。"""
        if self.dirty:
            self.confirm_quit = True
            return False
        return True

    def close_dialog(self) -> None:
        self.dialog = None
        self.dropdown_field = None
        self.name_focused = False
        self.number_buffer = None

    # ---- 名称输入 ---------------------------------------------------
    def focus_name(self) -> None:
        if self.dialog is None or self.dialog["kind"] not in KIND_HAS_NAME:
            return
        if not self.name_focused:
            self.push_undo()
        self.name_focused = True
        self.dialog_field = -1
        self.status = "输入名称；Enter 或点别处结束"

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
        pos = entry["pos"]
        rows = [("位置 x", number_text(pos[0])), ("位置 y", number_text(pos[1]))]
        size = entry.get("size", [1.0, 1.0])
        rows += [("宽度", number_text(size[0])), ("高度", number_text(size[1]))]
        if kind == KIND_MOVABLE:
            offset = entry.get("offset", [0, -3])
            sources = entry.get("sources", [])
            rows += [
                ("横向偏移", number_text(offset[0])),
                ("纵向偏移", number_text(offset[1])),
                ("触发按钮", "、".join(sources) if sources else "无"),
                ("一次触发", "是" if entry.get("once") else "否"),
            ]
        elif kind == KIND_BUTTON:
            rows.append(("朝向", FACE_LABELS.get(entry.get("face", ""), "（空）")))
        elif kind == KIND_PORTAL:
            rows += [
                ("朝向", FACE_LABELS.get(entry.get("face", ""), FACE_LABELS[FACE_ORDER[0]])),
                ("目标", entry.get("target") or "无"),
            ]
        elif kind == KIND_ITEM:
            rows.append(("变重", "是" if entry.get("heavy") else "否"))
        elif kind == KIND_NOZZLE:
            rows += [
                ("朝向", FACE_LABELS.get(entry.get("face", "up"), FACE_LABELS[FACE_ORDER[0]])),
                ("力度", number_text(entry.get("power", NOZZLE_DEFAULT_POWER))),
            ]
        elif kind == KIND_TEXTURE:
            rows.append(("图片", entry.get("image") or "（未选择）"))
        return rows

    def dialog_title(self) -> str:
        if self.dialog is None:
            return ""
        kind = self.dialog["kind"]
        name = self.dialog["entry"].get("name", "")
        return f"{KIND_TITLES.get(kind, '')} {name}".strip()

    def adjust_dialog(self, delta: int) -> None:
        """方向键与加减按钮：数字字段加 delta，其余字段循环切换。"""
        if self.dialog is None:
            return
        self.number_buffer = None          # 改用加减就把键盘输入状态收起来
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

        if kind == KIND_MOVABLE:
            if field == 6:                 # 触发按钮：在「无」和已有按钮名之间循环
                names = [
                    button.get("name", "") for button in self.level.buttons if button.get("name")
                ]
                options = [None, *names]
                current = (entry.get("sources") or [None])[0]
                chosen = (
                    options[(options.index(current) + delta) % len(options)]
                    if current in options
                    else names[0]
                    if names
                    else None
                )
                entry["sources"] = [chosen] if chosen else []
            else:                          # 一次触发：开关
                entry["once"] = not entry.get("once", False)
        elif kind == KIND_BUTTON:
            current_face = entry.get("face", FACE_ORDER[0])
            entry["face"] = (
                FACE_ORDER[(FACE_ORDER.index(current_face) + delta) % len(FACE_ORDER)]
                if current_face in FACE_ORDER
                else FACE_ORDER[0]
            )
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
        elif kind == KIND_ITEM:
            entry["heavy"] = not entry.get("heavy", False)

    # ---- 选择型字段的下拉列表 ---------------------------------------
    def dialog_options(self, field: int) -> list | None:
        """选择型字段的可选项 [(显示文字, 值)]；数字、开关字段返回 None。

        朝向、传送门的目标、可移动方块的触发按钮都从这里出下拉列表。
        """
        if self.dialog is None:
            return None
        kind = self.dialog["kind"]
        entry = self.dialog["entry"]
        if kind in (KIND_BUTTON, KIND_PORTAL, KIND_NOZZLE) and field == 4:
            return [(FACE_LABELS[face], face) for face in FACE_ORDER]
        if kind == KIND_PORTAL and field == 5:
            names = [
                portal.get("name", "")
                for portal in self.level.portals
                if portal.get("name") and portal is not entry
            ]
            return [("无", "")] + [(name, name) for name in names]
        if kind == KIND_MOVABLE and field == 6:
            names = [
                button.get("name", "") for button in self.level.buttons if button.get("name")
            ]
            return [("无", None)] + [(name, name) for name in names]
        return None

    def dialog_option_value(self, field: int):
        """选择型字段当前的值，用来在下拉列表里标出选中项。"""
        if self.dialog is None:
            return None
        kind = self.dialog["kind"]
        entry = self.dialog["entry"]
        if kind == KIND_MOVABLE and field == 6:
            return (entry.get("sources") or [None])[0]
        if kind == KIND_PORTAL and field == 5:
            return entry.get("target") or ""
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
        kind = self.dialog["kind"]
        entry = self.dialog["entry"]
        self.push_undo()
        if kind == KIND_MOVABLE and field == 6:
            entry["sources"] = [value] if value else []
        elif kind == KIND_PORTAL and field == 5:
            entry["target"] = value or ""
        else:
            entry["face"] = value
        self.dropdown_field = None
        self.number_buffer = None
        self.dirty = True

    # ---- 数字字段的键盘输入 -----------------------------------------
    def dialog_number_value(self, field: int):
        """字段是数字就返回当前值；朝向、触发按钮这类枚举返回 None。"""
        if self.dialog is None:
            return None
        kind = self.dialog["kind"]
        entry = self.dialog["entry"]
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
        return None

    def set_dialog_number(self, field: int, value: float) -> None:
        """把一个数字字段设成 value：位置、尺寸、偏移、力度都可以带小数。"""
        kind = self.dialog["kind"]
        entry = self.dialog["entry"]
        pos = entry["pos"]
        if field == 0:
            pos[0] = round(value, 2)
        elif field == 1:
            pos[1] = round(value, 2)
        elif field in (2, 3):
            size = list(entry.get("size", [1.0, 1.0]))
            size[field - 2] = max(MIN_SIZE, round(value, 2))
            entry["size"] = size
        elif kind == KIND_MOVABLE and field in (4, 5):
            offset = list(entry.get("offset", [0, -3]))
            offset[field - 4] = round(clamp_float(value, -8.0, 8.0, 0.0), 2)
            entry["offset"] = offset
        elif kind == KIND_NOZZLE and field == 5:
            # 力度是沿着朝向走出去多远，不给负的
            entry["power"] = round(clamp_float(value, 0.0, 8.0, 0.0), 2)

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
                self.push_undo()           # 一次完整输入只记一步撤销
            if len(self.number_buffer) < NUMBER_TEXT_MAX_LENGTH:
                self.number_buffer += char
        elif char == "-" and self.number_buffer is None:
            self.number_buffer = "-"       # 负号只允许打头（力度回头会被夹到 0）
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
        self.dirty = True

    def erase_dialog_number(self) -> None:
        if not self.number_buffer:
            return
        self.number_buffer = self.number_buffer[:-1]
        self.apply_number_buffer()

    def blur_number(self) -> None:
        self.number_buffer = None

    def move_dialog_field(self, delta: int) -> None:
        self.number_buffer = None
        count = len(self.dialog_rows())
        if count:
            self.dialog_field = (self.dialog_field + delta) % count

    # ---- 关卡设置 ---------------------------------------------------
    def open_settings(self) -> None:
        # 名称以外的数字项都按字符串编辑：可以直接敲数字，也可以点右边的加减
        flip_up, flip_down = self.level.flip_area_offsets
        self.settings = {
            "name": self.level.name,
            "width": str(self.level.width),
            "height": str(self.level.height),
            "flip_up": f"{flip_up:g}",
            "flip_down": f"{flip_down:g}",
            "background": self.level.background,
        }
        self.settings_field = 0
        self.push_undo()

    def close_settings(self, commit: bool) -> None:
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
            # 关卡变矮时跳高可能超了，顺手夹回来
            self.level.jump_height = clamp_int(
                self.level.jump_height,
                JUMP_HEIGHT_MIN,
                self._jump_height_limit(self.level.height),
                JUMP_HEIGHT_DEFAULT,
            )
            self.dirty = True
            background = self.level.background or "无"
            flip_up, flip_down = self.level.flip_area_offsets
            self.status = (
                f"关卡设置：名称 {self.level.name or '（空）'}，"
                f"尺寸 {self.level.width}×{self.level.height}，"
                f"翻转带 上 {flip_up:g} / 下 {flip_down:g}，背景 {background}"
            )
        self.settings = None

    def pick_background(self) -> None:
        """挑一张背景图：保存时才复制进关卡文件夹，复制后固定叫 background.png。"""
        if self.settings is None:
            return
        path = ask_image_path("选择背景图", level_base_dir(self.path))
        if not path:
            self.status = "选择背景已取消"
            return
        self.settings["background"] = relative_level_path(path, self.path)
        self.settings_field = 5
        self.status = "背景已选：只记相对 scene.json 的路径，不复制文件"

    def pick_texture_image(self) -> None:
        """给当前贴图换一张图：只记相对 scene.json 的路径，不复制文件。"""
        if self.dialog is None or self.dialog["kind"] != KIND_TEXTURE:
            return
        path = ask_image_path("选择贴图", level_base_dir(self.path))
        if not path:
            self.status = "选择贴图已取消"
            return
        self.push_undo()
        self.dirty = True
        self.dialog["entry"]["image"] = relative_level_path(path, self.path)
        self.number_buffer = None
        self.status = "贴图已换：路径相对 scene.json"

    def adjust_settings(self, delta: int) -> None:
        if self.settings is None:
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

    @staticmethod
    def _jump_height_limit(level_height: int) -> int:
        """初始跳高最多跳到关卡高度 - 1，别一蹦就穿过天花板。"""
        return max(JUMP_HEIGHT_MIN, level_height - 1)

    def _step_size(self, key: str, delta: int, low: int, high: int, fallback: int) -> None:
        """宽高在编辑期间是字符串：先夹回合法区间再加，空字符串按默认值算。"""
        current = clamp_int(self.settings[key], low, high, fallback)
        self.settings[key] = str(max(low, min(high, current + delta)))

    def type_settings(self, char: str) -> None:
        if self.settings is None:
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

    def erase_settings_char(self) -> None:
        if self.settings is None:
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

    # ---- 玩家设置 ---------------------------------------------------
    def open_player_settings(self) -> None:
        """玩家自己的几项：初始跳高、移动速度（以后还有动画）。"""
        self.player_settings = {
            "jump_height": str(self.level.jump_height),
            "move_speed": str(self.level.move_speed),
        }
        self.player_settings_field = 0
        self.push_undo()

    def close_player_settings(self, commit: bool) -> None:
        if self.player_settings is not None and commit:
            self.level.jump_height = clamp_int(
                self.player_settings["jump_height"],
                JUMP_HEIGHT_MIN,
                self._jump_height_limit(self.level.height),
                JUMP_HEIGHT_DEFAULT,
            )
            self.level.move_speed = clamp_float(
                self.player_settings["move_speed"],
                MOVE_SPEED_MIN,
                MOVE_SPEED_MAX,
                MOVE_SPEED_DEFAULT,
            )
            self.dirty = True
            self.status = (
                f"玩家设置：跳高 {self.level.jump_height}，速度 {self.level.move_speed}"
            )
        self.player_settings = None

    def adjust_player_settings(self, delta: int) -> None:
        if self.player_settings is None:
            return
        if self.player_settings_field == 0:
            # 跳高按 1 格加减，上限是关卡高度 - 1
            limit = self._jump_height_limit(self.level.height)
            current = clamp_int(
                self.player_settings["jump_height"], JUMP_HEIGHT_MIN, limit, JUMP_HEIGHT_DEFAULT
            )
            self.player_settings["jump_height"] = str(
                max(JUMP_HEIGHT_MIN, min(limit, current + delta))
            )
        else:
            # 移动速度按 0.5 一格加减
            current = clamp_float(
                self.player_settings["move_speed"], MOVE_SPEED_MIN, MOVE_SPEED_MAX, MOVE_SPEED_DEFAULT
            )
            stepped = max(MOVE_SPEED_MIN, min(MOVE_SPEED_MAX, current + 0.5 * delta))
            self.player_settings["move_speed"] = f"{stepped:g}"

    def type_player_settings(self, char: str) -> None:
        if self.player_settings is None:
            return
        if self.player_settings_field == 0:
            # 跳高是整数：只吃数字，最多 2 位
            current = str(self.player_settings["jump_height"])
            if char.isdigit() and len(current) < 2:
                self.player_settings["jump_height"] = current + char
        else:
            # 移动速度：数字和小数点，最多 5 位
            current = str(self.player_settings["move_speed"])
            if (char.isdigit() or char == ".") and len(current) < 5:
                self.player_settings["move_speed"] = current + char

    def erase_player_settings_char(self) -> None:
        if self.player_settings is None:
            return
        key = "jump_height" if self.player_settings_field == 0 else "move_speed"
        self.player_settings[key] = str(self.player_settings[key])[:-1]


# ---- 绘制 -----------------------------------------------------------
