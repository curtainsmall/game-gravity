"""Editor：编辑器状态与所有编辑操作。"""

import copy
import json
import os
from typing import TYPE_CHECKING

from core.constants import (
    BACKGROUND_MAX_LENGTH,
    COLS,
    FOOTER,
    HANDLE_PIXELS,
    HEADER,
    JUMP_HEIGHT_DEFAULT,
    JUMP_HEIGHT_MIN,
    KIND_BLOCK,
    KIND_BUTTON,
    KIND_DESTINATION,
    KIND_HAS_NAME,
    KIND_ITEM,
    KIND_MOVABLE,
    KIND_NOZZLE,
    KIND_PLANK,
    KIND_PLAYER,
    KIND_TEXTURE,
    KIND_TITLES,
    LEVEL_HEIGHT_MAX,
    LEVEL_HEIGHT_MIN,
    LEVEL_SCENE_NAME,
    LEVEL_WIDTH_MAX,
    LEVEL_WIDTH_MIN,
    MARGIN,
    MIN_SIZE,
    NAME_MAX_LENGTH,
    NOZZLE_DEFAULT_POWER,
    NOZZLE_DEFAULT_RANGE,
    ROWS,
    TOOL_BLOCK,
    TOOL_BUTTON,
    TOOL_DEST,
    TOOL_ITEM,
    TOOL_NOZZLE,
    TOOL_PLANK,
    TOOL_PLAYER,
    TOOL_SPECS,
    TOOL_TEXTURE,
)
from core.helpers import (
    clamp_int,
    display_path,
    entry_contains,
    level_base_dir,
    normalize_rect,
    nozzle_box,
    number_text,
    relative_level_path,
    resolve_level_path,
    round_rect,
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
        self.drag_start: tuple | None = None
        self.drag_current: tuple | None = None
        self.pan_drag: tuple | None = None
        self.dialog: dict | None = None
        self.dialog_field = 0
        self.picking_offset = False
        self.name_focused = False
        self.number_buffer: str | None = None   # 正在键盘输入的数字字段，None 表示没在输入
        self.object_grab: dict | None = None    # 正在用鼠标拖对象：移动或缩放
        self.snapping = False                   # 按住 Shift：吸附到整格
        self.view_menu_open = False
        # 视图设置：只影响编辑器自己的显示，从不写进关卡数据、不落盘
        self.view_settings: dict = {"background": True}
        self.menu_open = False
        self.menu_origin = (MARGIN, HEADER)
        self.creating = False
        self.settings: dict | None = None
        self.settings_field = 0
        self.confirm_quit = False
        self.startup = True
        self.status = "新建关卡或打开一个已有关卡"

    # ---- 查询 -------------------------------------------------------
    def all_entries(self) -> list:
        """所有有矩形的对象，按绘制顺序：(kind, entry)。"""
        pairs = []
        for entries, kind in (
            (self.level.blocks, KIND_BLOCK),
            (self.level.planks, KIND_PLANK),
            (self.level.movable_blocks, KIND_MOVABLE),
            (self.level.buttons, KIND_BUTTON),
            (self.level.items, KIND_ITEM),
        ):
            pairs += [(kind, entry) for entry in entries]
        if self.level.player is not None:
            pairs.append((KIND_PLAYER, self.level.player))
        if self.level.destination is not None:
            pairs.append((KIND_DESTINATION, self.level.destination))
        return pairs

    def object_at(self, point: tuple):
        """世界坐标点下的对象：小的机关排在大的方块之前，后加的先命中。"""
        for entries, kind in (
            (self.level.buttons, KIND_BUTTON),
            (self.level.items, KIND_ITEM),
            (self.level.movable_blocks, KIND_MOVABLE),
            (self.level.blocks, KIND_BLOCK),
            (self.level.planks, KIND_PLANK),
        ):
            for entry in reversed(entries):
                if entry_contains(entry, point):
                    return kind, entry
        if self.level.player is not None and entry_contains(self.level.player, point):
            return KIND_PLAYER, self.level.player
        if self.level.destination is not None and entry_contains(self.level.destination, point):
            return KIND_DESTINATION, self.level.destination
        return None

    def nozzle_at(self, point: tuple):
        """喷口是一个点：命中按它画出来的那个 1×1 三角判定（世界坐标）。"""
        x, y = point
        for entry in reversed(self.level.nozzles):
            box = nozzle_box(entry)
            left, bottom = box["pos"]
            if left <= x <= left + 1 and bottom <= y <= bottom + 1:
                return entry
        return None

    def texture_at(self, point: tuple):
        """贴图是自由矩形：按世界坐标判定。后加的盖住先加的，所以倒序找。"""
        for entry in reversed(self.level.textures):
            if entry_contains(entry, point):
                return entry
        return None

    def corner_at(self, layout: Layout, entry: dict, position: tuple):
        """光标离对象哪个角够近：返回角名，都不够近返回 None。"""
        rect = layout.entry_rect(entry)
        for name, point in (
            ("bl", rect.bottomleft),
            ("br", rect.bottomright),
            ("tl", rect.topleft),
            ("tr", rect.topright),
        ):
            if (
                abs(position[0] - point[0]) <= HANDLE_PIXELS
                and abs(position[1] - point[1]) <= HANDLE_PIXELS
            ):
                return name
        return None

    def object_handle_at(self, position: tuple, layout: Layout):
        """光标压在哪个角把手上：选中项优先，然后贴图，然后其它对象。

        贴图排在其它对象之前，是因为贴图通常盖在方块上，角也落在方块上，
        不这样排就永远抓不到贴图的角。
        """
        candidates = []
        if self.dialog is not None:
            candidates.append((self.dialog["kind"], self.dialog["entry"]))
        candidates += [(KIND_TEXTURE, entry) for entry in reversed(self.level.textures)]
        candidates += [(kind, entry) for kind, entry in reversed(self.all_entries())]
        for kind, entry in candidates:
            corner = self.corner_at(layout, entry, position)
            if corner is not None:
                return kind, entry, corner
        return None

    def update_hover(self, position: tuple, layout: Layout) -> None:
        """挑出光标下的对象。

        所有对象都是浮点自由矩形，按世界坐标命中；贴图是背景皮，排在最后选。
        """
        self.hovered = None
        self.hovered_handle = None
        in_work_area = (
            HEADER <= position[1] < layout.window[1] - FOOTER
            and 0 <= position[0] < layout.window[0]
        )
        if not in_work_area:
            return
        point = layout.world_point(position)
        # 角把手优先：不然压在方块上的贴图（或选中的方块）永远抓不到
        self.hovered_handle = self.object_handle_at(position, layout)
        nozzle = self.nozzle_at(point)
        if nozzle is not None:
            self.hovered = (KIND_NOZZLE, nozzle)
            return
        hit = self.object_at(point)
        if hit is not None:
            self.hovered = hit
            return
        texture = self.texture_at(point)
        if texture is not None:
            self.hovered = (KIND_TEXTURE, texture)

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
            level.buttons.append({"name": "", "pos": [x, y], "size": list(size), "face": ""})
        elif self.tool == TOOL_ITEM:
            level.items.append({"name": "", "pos": [x, y], "size": list(size), "heavy": False})
        elif self.tool == TOOL_NOZZLE:
            level.nozzles.append({"pos": [x, y], "power": 0, "range": 0})
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
        if kind == KIND_BLOCK:
            self.level.blocks = [e for e in self.level.blocks if e is not entry]
        elif kind == KIND_PLANK:
            self.level.planks = [e for e in self.level.planks if e is not entry]
        elif kind == KIND_MOVABLE:
            self.level.movable_blocks = [e for e in self.level.movable_blocks if e is not entry]
        elif kind == KIND_BUTTON:
            self.level.buttons = [e for e in self.level.buttons if e is not entry]
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
        self.dialog = None
        self.hovered = None
        self.picking_offset = False
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
        self.picking_offset = False
        self.dirty = True
        self.status = "已撤销"

    # ---- 文件 -------------------------------------------------------
    def new_level(self) -> None:
        self.level = Level()
        self.path = None
        self.undo_stack.clear()
        self.dirty = False
        self.dialog = None
        self.picking_offset = False
        self.startup = False
        self.zoom = None
        self.pan_x = self.pan_y = 0.0
        self.drag_start = self.drag_current = None
        self.status = "新建关卡（尚未保存）"

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
        self.picking_offset = False
        self.startup = False
        self.zoom = None
        self.pan_x = self.pan_y = 0.0
        self.drag_start = self.drag_current = None
        self.status = f"已打开 {display_path(folder)}"

    def save(self) -> None:
        """保存到关卡文件夹：scene.json 放数据，背景与贴图复制进文件夹。"""
        folder = self.path
        if folder is None:
            folder = ask_level_folder("选择关卡文件夹（文件夹名就是关卡名）")
            if not folder:
                self.status = "保存已取消"
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
        """左键按下：先看是不是压在某个角把手上（缩放），再看是不是落在对象里（移动）。"""
        hit = self.hovered_handle
        if hit is None:
            hit = self.object_handle_at(position, layout)
        if hit is not None:
            kind, entry, corner = hit
        elif self.hovered is not None:
            kind, entry = self.hovered
            corner = None                  # 喷口没有矩形，只能整体挪
        else:
            return False
        self.push_undo()                   # 先记下拖动前的状态，没动过就弹掉
        self.object_grab = {
            "kind": kind,
            "entry": entry,
            "corner": corner,
            "start": layout.world_point(position),
            "pos": list(entry["pos"]),
            "size": list(entry.get("size", [1.0, 1.0])),
            "moved": False,
        }
        return True

    def update_object_grab(self, position: tuple, layout: Layout) -> None:
        grab = self.object_grab
        if grab is None:
            return
        point = layout.world_point(position)
        dx = point[0] - grab["start"][0]
        dy = point[1] - grab["start"][1]
        if not grab["moved"] and abs(dx) * layout.tile < 1 and abs(dy) * layout.tile < 1:
            return                          # 还不到 1 像素，当作抖动
        grab["moved"] = True
        self.dirty = True
        entry = grab["entry"]
        x, y = grab["pos"]
        width, height = grab["size"]
        corner = grab["corner"]
        if corner is None or "size" not in entry:
            entry["pos"] = [round(x + dx, 2), round(y + dy, 2)]
            if self.snapping:
                entry["pos"] = [round(value) for value in entry["pos"]]
            return
        left, right, bottom, top = x, x + width, y, y + height
        if "l" in corner:
            left = point[0]
        if "r" in corner:
            right = point[0]
        if "b" in corner:
            bottom = point[1]
        if "t" in corner:
            top = point[1]
        if self.snapping:
            left, right, bottom, top = round(left), round(right), round(bottom), round(top)
        entry["pos"] = [round(min(left, right), 2), round(min(bottom, top), 2)]
        entry["size"] = [
            max(MIN_SIZE, round(abs(right - left), 2)),
            max(MIN_SIZE, round(abs(top - bottom), 2)),
        ]

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
            self.select(kind, entry)       # 点角也是点这个对象，别去选下面的
            return True
        size = entry.get("size")
        text = f"{KIND_TITLES.get(kind, '对象')} ({entry['pos'][0]}, {entry['pos'][1]})"
        if size:
            text += f" {size[0]}×{size[1]}"
        self.status = text
        return True

    def select(self, kind: str, entry: dict) -> None:
        self.dialog = {"kind": kind, "entry": entry}
        self.dialog_field = 0
        self.picking_offset = False
        self.name_focused = False
        self.number_buffer = None
        self.status = f"已选中{KIND_TITLES.get(kind, '对象')}"

    def stop_creating(self) -> None:
        self.creating = False
        self.status = "已退出新建；左键设置对象，右键新建"

    # ---- 退出确认 ---------------------------------------------------
    def request_quit(self) -> bool:
        """真能退出就返回 True；有未保存的改动就先弹确认。"""
        if self.dirty:
            self.confirm_quit = True
            return False
        return True

    # ---- 详细设置 ---------------------------------------------------
    def open_dialog(self) -> None:
        if self.hovered is None:
            # 点空地：取消选中，高亮跟着消失
            if self.dialog is not None:
                self.close_dialog()
                self.status = "已取消选中"
            else:
                self.status = "这里没有可设置的对象"
            return
        kind, entry = self.hovered
        self.dialog = {"kind": kind, "entry": entry}
        self.dialog_field = 0
        self.picking_offset = False
        self.name_focused = False
        self.number_buffer = None

    def close_dialog(self) -> None:
        self.dialog = None
        self.picking_offset = False
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

    # ---- 拾取偏移 ---------------------------------------------------
    def begin_pick_offset(self) -> None:
        """等用户在关卡里点一下，用那一点和 pos 的差算出 offset。"""
        if self.dialog is None or self.dialog["kind"] != KIND_MOVABLE:
            return
        self.picking_offset = True
        self.status = "在关卡里左键点一下目标位置；右键或 Esc 取消"

    def cancel_pick_offset(self) -> None:
        self.picking_offset = False
        self.status = "已取消拾取偏移"

    def finish_pick_offset(self, point: tuple) -> None:
        if not self.picking_offset or self.dialog is None:
            return
        entry = self.dialog["entry"]
        pos = entry["pos"]
        self.push_undo()
        # 偏移按整格记，取点到对象左下角的差
        entry["offset"] = [int(round(point[0] - pos[0])), int(round(point[1] - pos[1]))]
        self.picking_offset = False
        self.dirty = True
        self.status = f"偏移设为 {entry['offset'][0]}, {entry['offset'][1]}"

    def dialog_rows(self) -> list:
        if self.dialog is None:
            return []
        kind = self.dialog["kind"]
        entry = self.dialog["entry"]
        pos = entry["pos"]
        rows = [("位置 x", number_text(pos[0])), ("位置 y", number_text(pos[1]))]
        if kind != KIND_NOZZLE:
            size = entry.get("size", [1.0, 1.0])
            rows += [("宽度", number_text(size[0])), ("高度", number_text(size[1]))]
        if kind == KIND_MOVABLE:
            offset = entry.get("offset", [0, -3])
            sources = entry.get("sources", [])
            rows += [
                ("横向偏移", str(offset[0])),
                ("纵向偏移", str(offset[1])),
                ("触发按钮", "、".join(sources) if sources else "无"),
                ("一次触发", "是" if entry.get("once") else "否"),
            ]
        elif kind == KIND_BUTTON:
            rows.append(("朝向", entry.get("face") or "（空）"))
        elif kind == KIND_ITEM:
            rows.append(("变重", "是" if entry.get("heavy") else "否"))
        elif kind == KIND_NOZZLE:
            rows += [
                ("力度", str(entry.get("power", NOZZLE_DEFAULT_POWER))),
                ("长度", str(entry.get("range", NOZZLE_DEFAULT_RANGE))),
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
            self.set_dialog_number(field, current_number + delta)
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
            faces = ["up", "right", "down", "left"]
            current_face = entry.get("face", "up")
            entry["face"] = (
                faces[(faces.index(current_face) + delta) % len(faces)]
                if current_face in faces
                else "up"
            )
        elif kind == KIND_ITEM:
            entry["heavy"] = not entry.get("heavy", False)

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
        if kind != KIND_NOZZLE and field in (2, 3):
            return entry.get("size", [1.0, 1.0])[field - 2]
        if kind == KIND_MOVABLE and field in (4, 5):
            return entry.get("offset", [0, -3])[field - 4]
        if kind == KIND_NOZZLE and field == 2:
            return entry.get("power", NOZZLE_DEFAULT_POWER)
        if kind == KIND_NOZZLE and field == 3:
            return entry.get("range", NOZZLE_DEFAULT_RANGE)
        return None

    def set_dialog_number(self, field: int, value: float) -> None:
        """把一个数字字段设成 value：位置和尺寸都是浮点，不再夹到网格。"""
        kind = self.dialog["kind"]
        entry = self.dialog["entry"]
        pos = entry["pos"]
        if field == 0:
            pos[0] = round(value, 2)
        elif field == 1:
            pos[1] = round(value, 2)
        elif kind != KIND_NOZZLE and field in (2, 3):
            size = list(entry.get("size", [1.0, 1.0]))
            size[field - 2] = max(MIN_SIZE, round(value, 2))
            entry["size"] = size
        elif kind == KIND_MOVABLE and field in (4, 5):
            index = field - 4
            offset = list(entry.get("offset", [0, -3]))
            offset[index] = int(max(-8, min(8, round(value))))
            entry["offset"] = offset
        elif kind == KIND_NOZZLE and field == 2:
            entry["power"] = int(max(-8, min(8, round(value))))
        elif kind == KIND_NOZZLE and field == 3:
            entry["range"] = int(max(1, min(8, round(value))))

    def type_dialog_number(self, char: str) -> bool:
        """数字字段键盘输入：第一次敲键起一个新值，之后追加。返回是否吃掉了字符。"""
        if self.dialog is None or self.name_focused:
            return False
        if self.dialog_number_value(self.dialog_field) is None:
            return False
        if char.isdigit():
            if self.number_buffer is None:
                self.number_buffer = ""
                self.push_undo()           # 一次完整输入只记一步撤销
            if len(self.number_buffer) < 6:
                self.number_buffer += char
        elif char == "-" and self.number_buffer is None:
            self.number_buffer = "-"       # 负号只允许打头（偏移、力度可为负）
            self.push_undo()
        else:
            return False
        self.apply_number_buffer()
        return True

    def apply_number_buffer(self) -> None:
        """把输入框里的文本写回字段；只有「-」或空串时先不动。"""
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
        self.settings = {
            "name": self.level.name,
            "width": str(self.level.width),
            "height": str(self.level.height),
            "jump_height": str(self.level.jump_height),
            "background": self.level.background,
        }
        self.settings_field = 0
        self.push_undo()

    def close_settings(self, commit: bool) -> None:
        if self.settings is not None and commit:
            self.level.name = self.settings["name"]
            self.level.width = clamp_int(
                self.settings["width"], LEVEL_WIDTH_MIN, LEVEL_WIDTH_MAX, COLS
            )
            self.level.height = clamp_int(
                self.settings["height"], LEVEL_HEIGHT_MIN, LEVEL_HEIGHT_MAX, ROWS
            )
            self.level.jump_height = clamp_int(
                self.settings["jump_height"],
                JUMP_HEIGHT_MIN,
                self._jump_height_limit(self.level.height),
                JUMP_HEIGHT_DEFAULT,
            )
            self.level.background = self.settings["background"]
            self.dirty = True
            background = self.level.background or "无"
            self.status = (
                f"关卡设置：名称 {self.level.name or '（空）'}，"
                f"尺寸 {self.level.width}×{self.level.height}，"
                f"跳高 {self.level.jump_height}，背景 {background}"
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
        self.settings_field = 4
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
        elif field == 3:
            # 跳高上限跟着设置里的高度走：不能高过关卡高度 - 1
            height = clamp_int(
                self.settings["height"], LEVEL_HEIGHT_MIN, LEVEL_HEIGHT_MAX, self.level.height
            )
            limit = self._jump_height_limit(height)
            current = clamp_int(self.settings["jump_height"], JUMP_HEIGHT_MIN, limit, JUMP_HEIGHT_DEFAULT)
            self.settings["jump_height"] = str(max(JUMP_HEIGHT_MIN, min(limit, current + delta)))

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
        elif field in (1, 2, 3):
            # 数字项只吃数字：宽度最多 4 位（1000 格上限），高度和跳高 2 位够用
            key = {1: "width", 2: "height", 3: "jump_height"}[field]
            if char.isdigit() and len(str(self.settings[key])) < (4 if field == 1 else 2):
                self.settings[key] = str(self.settings[key]) + char
        elif field == 4:
            # 背景是路径：可打印字符都能打
            if char.isprintable() and len(self.settings["background"]) < BACKGROUND_MAX_LENGTH:
                self.settings["background"] += char

    def erase_settings_char(self) -> None:
        if self.settings is None:
            return
        field = self.settings_field
        if field == 0:
            self.settings["name"] = self.settings["name"][:-1]
        elif field in (1, 2, 3):
            key = {1: "width", 2: "height", 3: "jump_height"}[field]
            self.settings[key] = str(self.settings[key])[:-1]
        elif field == 4:
            self.settings["background"] = self.settings["background"][:-1]


# ---- 绘制 -----------------------------------------------------------
