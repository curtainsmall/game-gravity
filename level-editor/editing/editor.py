"""Editor：编辑器状态与所有编辑操作。"""

import copy
import json
import os
from typing import TYPE_CHECKING

from core.constants import (
    COLS,
    HEADER,
    JUMP_HEIGHT_MAX,
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
    KIND_TITLES,
    MARGIN,
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
)
from core.helpers import display_path, entry_contains, normalize_drag, nozzle_box, number_text
from core.level import Level
from editing.files import ask_open_path, ask_save_path

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
        self.hover: tuple | None = None
        self.hovered = None
        self.drag_start: tuple | None = None
        self.drag_current: tuple | None = None
        self.pan_drag: tuple | None = None
        self.dialog: dict | None = None
        self.dialog_field = 0
        self.picking_offset = False
        self.name_focused = False
        self.menu_open = False
        self.menu_origin = (MARGIN, HEADER)
        self.creating = False
        self.settings: dict | None = None
        self.settings_field = 0
        self.confirm_quit = False
        self.startup = True
        self.status = "新建关卡或打开一个已有关卡"

    # ---- 查询 -------------------------------------------------------
    def object_at(self, cell: tuple):
        for entry in self.level.blocks:
            if entry_contains(entry, cell):
                return KIND_BLOCK, entry
        for entry in self.level.planks:
            if entry_contains(entry, cell):
                return KIND_PLANK, entry
        for entry in self.level.movable_blocks:
            if entry_contains(entry, cell):
                return KIND_MOVABLE, entry
        for entry in self.level.buttons:
            if entry_contains(entry, cell):
                return KIND_BUTTON, entry
        for entry in self.level.items:
            if entry_contains(entry, cell):
                return KIND_ITEM, entry
        if self.level.player and entry_contains(self.level.player, cell):
            return KIND_PLAYER, self.level.player
        if self.level.destination and entry_contains(self.level.destination, cell):
            return KIND_DESTINATION, self.level.destination
        return None

    def nozzle_at(self, point: tuple):
        """喷口是一个点：命中按它画出来的那个 1×1 三角判定，不按格子。"""
        x, y = point
        for entry in self.level.nozzles:
            box = nozzle_box(entry)
            left, bottom = box["pos"]
            if left <= x <= left + 1 and bottom <= y <= bottom + 1:
                return entry
        return None

    def update_hover(self, position: tuple, layout: Layout) -> None:
        inside = (
            layout.left <= position[0] < layout.left + layout.width
            and layout.top <= position[1] < layout.top + layout.height
        )
        self.hover = layout.cell_at(position)
        self.hovered = None
        if not inside:
            return
        nozzle = self.nozzle_at(layout.level_point(position))
        if nozzle is not None:
            self.hovered = (KIND_NOZZLE, nozzle)
        elif self.hover is not None:
            self.hovered = self.object_at(self.hover)

    # ---- 创建 / 删除 -----------------------------------------------
    def begin_drag(self, cell: tuple) -> None:
        if self.tool != TOOL_NOZZLE and self.object_at(cell) is not None:
            self.status = "这一格已有对象；换个空位画"
            return
        self.drag_start = cell
        self.drag_current = cell

    def press_canvas(self, position: tuple, layout: Layout) -> None:
        """新建状态里的左键按下：光标下已有对象就只提示、不新建。

        喷口是点、不占格，所以喷口工具允许压在别的对象上放；其余工具遇到
        任何已有对象（包括喷口）都不新建，免得一次单击把该改的对象盖掉。
        """
        self.update_hover(position, layout)
        if self.hovered is not None:
            kind = self.hovered[0]
            if self.tool != TOOL_NOZZLE or kind == KIND_NOZZLE:
                self.status = f"这里是{KIND_TITLES.get(kind, '对象')}；换个空位画，右键退出新建"
                return
        cell = layout.cell_at(position)
        if cell is not None:
            self.begin_drag(cell)

    def finish_drag(self) -> None:
        if self.drag_start is None:
            return
        start = self.drag_start
        current = self.drag_current or start
        self.drag_start = None
        self.drag_current = None
        kind = TOOL_SPECS[self.tool][1]
        if kind == "rect":
            x, y, w, h = normalize_drag(start, current)
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
            self.status = f"新增{TOOL_SPECS[self.tool][0]} ({x},{y}) {w}×{h}"
        else:
            self.place_single(start)

    def place_single(self, cell: tuple) -> None:
        if self.tool != TOOL_NOZZLE and self.object_at(cell) is not None:
            return
        col, row = cell
        level = self.level
        if self.tool == TOOL_NOZZLE:
            point = [col + 0.5, row]
            if any(entry["pos"] == point for entry in level.nozzles):
                self.status = "这一格已经有喷口"
                return
        self.push_undo()
        self.dirty = True
        # 新对象的数值/布尔/字符串一律给中性默认值，具体参数再在面板里调
        if self.tool == TOOL_BUTTON:
            level.buttons.append({"name": "", "pos": [col, row], "face": ""})
        elif self.tool == TOOL_ITEM:
            level.items.append({"name": "", "pos": [col, row], "heavy": False})
        elif self.tool == TOOL_NOZZLE:
            level.nozzles.append({"pos": [col + 0.5, row], "power": 0, "range": 0})
        elif self.tool == TOOL_PLAYER:
            # 起点只有一份：再放一次就是把它挪过去
            level.player = {"pos": [col, row]}
        elif self.tool == TOOL_DEST:
            # 终点也只有一份
            level.destination = {"pos": [col, row]}

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
        elif kind == KIND_PLAYER:
            self.level.player = None
        elif kind == KIND_DESTINATION:
            self.level.destination = None
        self.dialog = None
        self.hovered = None
        self.picking_offset = False
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
        self.status = "新建关卡（尚未保存）"

    def open_level(self) -> None:
        path = ask_open_path()
        if not path:
            self.status = "打开已取消"
            return
        self.load(path)

    def load(self, path: str) -> None:
        try:
            with open(path, encoding="utf-8") as file:
                definition = json.load(file)
        except (OSError, json.JSONDecodeError) as error:
            self.status = f"打开失败：{error}"
            return
        self.level = Level.from_definition(definition)
        self.path = path
        self.undo_stack.clear()
        self.dirty = False
        self.dialog = None
        self.picking_offset = False
        self.startup = False
        self.zoom = None
        self.pan_x = self.pan_y = 0.0
        self.status = f"已打开 {display_path(path)}"

    def save(self) -> None:
        path = self.path
        if path is None:
            path = ask_save_path()
            if not path:
                self.status = "保存已取消"
                return
        if not self.level.name:
            self.level.name = os.path.splitext(os.path.basename(path))[0]
        try:
            with open(path, "w", encoding="utf-8", newline="\n") as file:
                json.dump(self.level.to_definition(), file, ensure_ascii=False, indent=2)
                file.write("\n")
        except OSError as error:
            self.status = f"保存失败：{error}"
            return
        self.path = path
        self.dirty = False
        self.status = f"已保存 {display_path(path)}"

    # ---- 新建状态 ---------------------------------------------------
    def open_create_menu(self, position: tuple) -> None:
        """右键弹出新建菜单，光标位置就是菜单的左上角。"""
        self.menu_open = True
        self.menu_origin = (position[0], position[1])

    def start_creating(self, tool: int) -> None:
        self.tool = tool
        self.creating = True
        self.menu_open = False
        action = "左键拖出矩形" if TOOL_SPECS[tool][1] == "rect" else "左键单击放置"
        self.status = f"新建：{TOOL_SPECS[tool][0]}（{action}，右键退出）"

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
            self.status = "这里没有可设置的对象"
            return
        kind, entry = self.hovered
        self.dialog = {"kind": kind, "entry": entry}
        self.dialog_field = 0
        self.picking_offset = False
        self.name_focused = False

    def close_dialog(self) -> None:
        self.dialog = None
        self.picking_offset = False
        self.name_focused = False

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

    def finish_pick_offset(self, cell: tuple) -> None:
        if not self.picking_offset or self.dialog is None:
            return
        entry = self.dialog["entry"]
        pos = entry["pos"]
        self.push_undo()
        entry["offset"] = [int(cell[0]) - int(pos[0]), int(cell[1]) - int(pos[1])]
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
        if kind in (KIND_BLOCK, KIND_PLANK, KIND_MOVABLE):
            size = entry.get("size", [1, 1])
            rows += [("宽度", str(size[0])), ("高度", str(size[1]))]
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
        return rows

    def dialog_title(self) -> str:
        if self.dialog is None:
            return ""
        kind = self.dialog["kind"]
        name = self.dialog["entry"].get("name", "")
        return f"{KIND_TITLES.get(kind, '')} {name}".strip()

    def adjust_dialog(self, delta: int) -> None:
        if self.dialog is None:
            return
        self.push_undo()
        kind = self.dialog["kind"]
        entry = self.dialog["entry"]
        field = self.dialog_field
        self.dirty = True
        pos = entry["pos"]
        if field == 0:
            if kind == KIND_NOZZLE:
                # 喷口是点：x 按半格移动，底边中点始终落在 0.5 的整数倍上。
                pos[0] = round(max(0.5, min(COLS - 0.5, float(pos[0]) + 0.5 * delta)), 1)
            else:
                pos[0] = max(0, min(COLS - 1, int(pos[0]) + delta))
        elif field == 1:
            pos[1] = max(0, min(ROWS - 1, int(pos[1]) + delta))
        elif kind in (KIND_BLOCK, KIND_PLANK, KIND_MOVABLE) and field in (2, 3):
            size = list(entry.get("size", [1, 1]))
            axis = field - 2
            limit = COLS - int(pos[0]) if axis == 0 else ROWS - int(pos[1])
            size[axis] = max(1, min(limit, int(size[axis]) + delta))
            entry["size"] = size
        elif kind == KIND_MOVABLE:
            index = field - 4
            if index == 0 or index == 1:
                offset = list(entry.get("offset", [0, -3]))
                offset[index] = max(-8, min(8, int(offset[index]) + delta))
                entry["offset"] = offset
            elif index == 2:
                names = [button.get("name", "") for button in self.level.buttons if button.get("name")]
                options = [None, *names]
                current = (entry.get("sources") or [None])[0]
                chosen = options[(options.index(current) + delta) % len(options)] if current in options else names[0] if names else None
                entry["sources"] = [chosen] if chosen else []
            else:
                entry["once"] = not entry.get("once", False)
        elif kind == KIND_BUTTON:
            faces = ["up", "right", "down", "left"]
            current = entry.get("face", "up")
            entry["face"] = faces[(faces.index(current) + delta) % len(faces)] if current in faces else "up"
        elif kind == KIND_ITEM:
            entry["heavy"] = not entry.get("heavy", False)
        elif kind == KIND_NOZZLE:
            if field == 2:
                entry["power"] = max(-8, min(8, int(entry.get("power", NOZZLE_DEFAULT_POWER)) + delta))
            else:
                entry["range"] = max(1, min(8, int(entry.get("range", NOZZLE_DEFAULT_RANGE)) + delta))

    def move_dialog_field(self, delta: int) -> None:
        count = len(self.dialog_rows())
        if count:
            self.dialog_field = (self.dialog_field + delta) % count

    # ---- 关卡设置 ---------------------------------------------------
    def open_settings(self) -> None:
        self.settings = {"name": self.level.name, "jump_height": self.level.jump_height}
        self.settings_field = 0
        self.push_undo()

    def close_settings(self, commit: bool) -> None:
        if self.settings is not None and commit:
            self.level.name = self.settings["name"]
            self.level.jump_height = int(self.settings["jump_height"])
            self.dirty = True
            self.status = f"关卡设置：名称 {self.level.name or '（空）'}，跳高 {self.level.jump_height}"
        self.settings = None

    def adjust_settings(self, delta: int) -> None:
        if self.settings is None:
            return
        if self.settings_field == 1:
            self.settings["jump_height"] = max(
                JUMP_HEIGHT_MIN, min(JUMP_HEIGHT_MAX, int(self.settings["jump_height"]) + delta)
            )

    def type_settings(self, char: str) -> None:
        if self.settings is None or self.settings_field != 0:
            return
        if char.isprintable() and len(self.settings["name"]) < 24:
            self.settings["name"] += char

    def erase_settings_char(self) -> None:
        if self.settings is not None and self.settings_field == 0:
            self.settings["name"] = self.settings["name"][:-1]


# ---- 绘制 -----------------------------------------------------------
