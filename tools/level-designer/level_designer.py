"""关卡编辑器：以「矩形」为最小单位编辑关卡。

运行：uv run python tools/level-designer/level_designer.py

编辑模型
  关卡数据里的方块与木板都是矩形（pos + size），编辑器同样按整体处理：
  光标停在某格时，会高亮它所属的整个矩形；修改、删除都作用于整个矩形。
  在空格上按住左键拖动可以画出一个新矩形，松开即按拖动范围生成。
  按钮、道具、玩家、终点是整格对象，单击放置。

  喷口不是格子而是「点」：pos 记的是三角形底边中点，三角朝 power 的方向
  占一格。它按自己的位置画、按画出来的三角命中，不吸附到格心，所以手写
  的坐标（比如 01.json 里的 [6, 0]）也能原样显示和选中。

操作
  工具栏     新建 / 打开 / 保存 / 撤销 / 工具下拉 / 关卡设置（都可点击）
  左键拖动   在空白处拖出新矩形（原地单击就是 1×1）
             光标下已经有对象时不会新建，只在状态栏提示
  右键       打开光标下对象的详细设置
  Delete     删除光标下的整个对象
  滚轮       缩放（以光标为锚）
  中键拖动   平移
  Ctrl-Z/S/O/N  撤销 / 保存 / 打开 / 新建
  Esc        关闭弹窗或退出

弹窗都可以用鼠标操作：工具下拉列表点击选择；详细设置里点行选中字段、
点左右小箭头改数值、点「删除对象」「关闭」；关卡设置里点字段选中、
点小箭头改跳高、点「退格」删名称末字、点「应用」「取消」；点面板外关闭。

保存不会自动写盘：没有文件时会弹出系统对话框让你选择位置。
"""

import copy
import json
import math
import os

import pygame

COLS = 120
ROWS = 8
HEADER = 88
FOOTER = 30
MARGIN = 12
DEFAULT_WINDOW = (1240, 360)
MIN_WINDOW = (620, 260)

ZOOM_STEP = 1.1
ZOOM_MAX_TILE = 48.0

BACKGROUND = (30, 30, 30)
PANEL = (45, 45, 45)
GRID = (70, 70, 70)
TEXT = (225, 225, 225)
DIM_TEXT = (160, 160, 160)
STATUS_TEXT = (160, 200, 160)
BLOCK_COLOR = (10, 10, 10)
PLANK_COLOR = (139, 69, 19)
MOVABLE_COLOR = (255, 105, 180)
BUTTON_COLOR = (220, 20, 60)
ITEM_COLOR = (220, 20, 60)
NOZZLE_COLOR = (220, 20, 60)
PLAYER_COLOR = (255, 140, 0)
DESTINATION_COLOR = (34, 139, 34)
GROUND_COLOR = (120, 120, 120)
DIALOG_BG = (55, 55, 60)
DIALOG_BORDER = (200, 200, 200)
HIGHLIGHT = (255, 230, 120)
BUTTON_BG = (70, 70, 78)
PREVIEW = (255, 230, 120, 90)

TOOL_BLOCK, TOOL_PLANK, TOOL_MOVABLE, TOOL_BUTTON, TOOL_ITEM, TOOL_NOZZLE, TOOL_PLAYER, TOOL_DEST = range(8)
TOOL_SPECS = {
    TOOL_BLOCK: ("方块", "rect"),
    TOOL_PLANK: ("木板", "rect"),
    TOOL_MOVABLE: ("可移动方块", "single"),
    TOOL_BUTTON: ("按钮", "single"),
    TOOL_ITEM: ("道具", "single"),
    TOOL_NOZZLE: ("喷口", "single"),
    TOOL_PLAYER: ("玩家", "single"),
    TOOL_DEST: ("终点", "single"),
}
TOOL_ORDER = [TOOL_BLOCK, TOOL_PLANK, TOOL_MOVABLE, TOOL_BUTTON, TOOL_ITEM, TOOL_NOZZLE, TOOL_PLAYER, TOOL_DEST]

NOZZLE_DEFAULT_POWER = 7
NOZZLE_DEFAULT_RANGE = 5
JUMP_HEIGHT_DEFAULT = 4
JUMP_HEIGHT_MIN, JUMP_HEIGHT_MAX = 0, 7

KIND_BLOCK = "block"
KIND_PLANK = "plank"
KIND_MOVABLE = "movable_block"
KIND_BUTTON = "button"
KIND_ITEM = "item"
KIND_NOZZLE = "nozzle"
KIND_PLAYER = "player"
KIND_DESTINATION = "destination"

KIND_TITLES = {
    KIND_BLOCK: "方块",
    KIND_PLANK: "木板",
    KIND_MOVABLE: "可移动方块",
    KIND_BUTTON: "按钮",
    KIND_ITEM: "道具",
    KIND_NOZZLE: "喷口",
    KIND_PLAYER: "玩家",
    KIND_DESTINATION: "终点",
}

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LEVELS_DIR = os.path.join(ROOT, "assets", "levels")
FILE_FILTERS = [("关卡 JSON", "*.json"), ("所有文件", "*.*")]
TOOLBAR_ITEMS = [
    ("新建", "new", 56),
    ("打开", "open", 56),
    ("保存", "save", 56),
    ("撤销", "undo", 56),
    ("工具", "tools", 132),
    ("关卡设置", "settings", 88),
]
TOOLBAR_HEIGHT = 24
ROW_HEIGHT = 22
BUTTON_HEIGHT = 22
COLUMN_GAP = 14


def _display_path(path: str | None) -> str:
    if not path:
        return "未命名（未保存）"
    try:
        return os.path.relpath(path, ROOT)
    except ValueError:
        return path


def ask_open_path() -> str | None:
    try:
        import tkinter as tk
        from tkinter import filedialog
    except ImportError:
        return None
    root = tk.Tk()
    root.withdraw()
    try:
        path = filedialog.askopenfilename(title="打开关卡", initialdir=LEVELS_DIR, filetypes=FILE_FILTERS)
    finally:
        root.destroy()
    return path or None


def ask_save_path() -> str | None:
    try:
        import tkinter as tk
        from tkinter import filedialog
    except ImportError:
        return None
    root = tk.Tk()
    root.withdraw()
    try:
        path = filedialog.asksaveasfilename(
            title="保存关卡",
            initialdir=LEVELS_DIR,
            defaultextension=".json",
            filetypes=FILE_FILTERS,
        )
    finally:
        root.destroy()
    return path or None


def entry_cells(entry: dict) -> set:
    x, y = entry["pos"]
    w, h = entry.get("size", [1, 1])
    return {(int(x) + i, int(y) + j) for i in range(int(w)) for j in range(int(h))}


def entry_contains(entry: dict, cell: tuple) -> bool:
    x, y = entry["pos"]
    w, h = entry.get("size", [1, 1])
    return x <= cell[0] < x + w and y <= cell[1] < y + h


def normalize_drag(a: tuple, b: tuple) -> tuple:
    x0, x1 = sorted((a[0], b[0]))
    y0, y1 = sorted((a[1], b[1]))
    return x0, y0, x1 - x0 + 1, y1 - y0 + 1


def nozzle_box(entry: dict) -> dict:
    """喷口是点（底边中点）；它画出来的 1×1 三角落在哪一格。

    向上的喷口坐在 y 之上，向下的挂在 y 之下，和游戏里风区的朝向一致。
    """
    x, y = entry["pos"]
    up = int(entry.get("power", NOZZLE_DEFAULT_POWER)) >= 0
    return {"pos": [x - 0.5, y if up else y - 1], "size": [1, 1]}


def _number(value) -> str:
    return f"{value:g}" if isinstance(value, float) else str(value)


class Layout:
    def __init__(
        self,
        window_size: tuple,
        zoom: float | None = None,
        pan_x: float = 0.0,
        pan_y: float = 0.0,
    ) -> None:
        width, height = window_size
        self.window = (width, height)
        self.usable_width = max(1, width - 2 * MARGIN)
        self.usable_height = max(1, height - HEADER - FOOTER)
        self.min_tile = min(self.usable_width / COLS, self.usable_height / (ROWS + 2))
        self.max_tile = max(ZOOM_MAX_TILE, self.min_tile)
        self.tile = self.min_tile if zoom is None else min(max(zoom, self.min_tile), self.max_tile)
        self.zoom = zoom
        self.width = self.tile * COLS
        self.height = self.tile * (ROWS + 2)
        self.max_pan_x = max(0.0, self.width - self.usable_width)
        self.max_pan_y = max(0.0, self.height - self.usable_height)
        self.pan_x = min(max(0.0, pan_x), self.max_pan_x)
        self.pan_y = min(max(0.0, pan_y), self.max_pan_y)
        self.left = MARGIN - self.pan_x
        self.top = HEADER - self.pan_y + max(0.0, (self.usable_height - self.height) / 2.0)

    def cell_at(self, position: tuple) -> tuple | None:
        x, y = position
        if not (0 <= x < self.window[0] and HEADER <= y < self.window[1] - FOOTER):
            return None
        if not (self.left <= x < self.left + self.width and self.top <= y < self.top + self.height):
            return None
        col = int((x - self.left) // self.tile)
        screen_row = int((y - self.top) // self.tile)
        level_y = ROWS - screen_row
        if not (0 <= col < COLS) or not (0 <= level_y < ROWS):
            return None
        return col, level_y

    def level_point(self, position: tuple) -> tuple:
        """屏幕坐标 → 关卡连续坐标（喷口这类「点」对象用它定位）。"""
        return (
            (position[0] - self.left) / self.tile,
            ROWS + 1 - (position[1] - self.top) / self.tile,
        )

    def cell_rect(self, x: float, y: float, size: tuple = (1, 1)) -> pygame.Rect:
        left = self.left + (x - 0.5 if size[0] < 1 else x) * self.tile
        top = self.top + (ROWS - y - (size[1] - 1)) * self.tile
        return pygame.Rect(
            round(left),
            round(top),
            max(1, round(size[0] * self.tile)),
            max(1, round(size[1] * self.tile)),
        )

    def entry_rect(self, entry: dict) -> pygame.Rect:
        return self.cell_rect(entry["pos"][0], entry["pos"][1], tuple(entry.get("size", [1, 1])))


class Level:
    def __init__(self) -> None:
        self.name = ""
        self.jump_height = JUMP_HEIGHT_DEFAULT
        self.blocks: list = []
        self.planks: list = []
        self.movable_blocks: list = []
        self.buttons: list = []
        self.items: list = []
        self.nozzles: list = []
        self.player: dict | None = None
        self.destination: dict | None = None

    def to_definition(self) -> dict:
        definition = {
            "name": self.name,
            "width": COLS,
            "height": ROWS,
            "jump_height": self.jump_height,
            "player": copy.deepcopy(self.player) or {"pos": [0, 0]},
            "blocks": copy.deepcopy(self.blocks),
            "planks": copy.deepcopy(self.planks),
            "movable_blocks": copy.deepcopy(self.movable_blocks),
            "buttons": copy.deepcopy(self.buttons),
            "items": copy.deepcopy(self.items),
            "nozzles": copy.deepcopy(self.nozzles),
        }
        if self.destination is not None:
            definition["destination"] = copy.deepcopy(self.destination)
        return definition

    @classmethod
    def from_definition(cls, definition: dict) -> "Level":
        level = cls()
        level.name = str(definition.get("name", ""))
        level.jump_height = int(definition.get("jump_height", JUMP_HEIGHT_DEFAULT))
        level.player = copy.deepcopy(definition.get("player"))
        level.destination = copy.deepcopy(definition.get("destination"))
        level.blocks = copy.deepcopy(list(definition.get("blocks", [])))
        level.planks = copy.deepcopy(list(definition.get("planks", [])))
        level.movable_blocks = copy.deepcopy(list(definition.get("movable_blocks", [])))
        level.buttons = copy.deepcopy(list(definition.get("buttons", [])))
        level.items = copy.deepcopy(list(definition.get("items", [])))
        level.nozzles = copy.deepcopy(list(definition.get("nozzles", [])))
        return level


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
        self.menu_open = False
        self.settings: dict | None = None
        self.settings_field = 0
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
            self.status = "这一格已有对象；右键可修改，Delete 可删除"
            return
        self.drag_start = cell
        self.drag_current = cell

    def press_canvas(self, position: tuple, layout: Layout) -> None:
        """画布上的左键按下：光标下已有对象就只提示、不新建。

        喷口是点、不占格，所以喷口工具允许压在别的对象上放；其余工具遇到
        任何已有对象（包括喷口）都不新建，免得一次单击把该改的对象盖掉。
        """
        self.update_hover(position, layout)
        if self.hovered is not None:
            kind = self.hovered[0]
            if self.tool != TOOL_NOZZLE or kind == KIND_NOZZLE:
                self.status = f"这里是{KIND_TITLES.get(kind, '对象')}；右键可修改，Delete 可删除"
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
            target = self.level.blocks if self.tool == TOOL_BLOCK else self.level.planks
            target.append({"pos": [x, y], "size": [w, h]})
            self.dirty = True
            self.status = f"新增矩形 ({x},{y}) {w}×{h}"
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
        if self.tool == TOOL_MOVABLE:
            level.movable_blocks.append(
                {
                    "name": f"g{len(level.movable_blocks) + 1}",
                    "pos": [col, row],
                    "size": [1, 1],
                    "offset": [0, -3],
                    "sources": [],
                }
            )
        elif self.tool == TOOL_BUTTON:
            level.buttons.append({"name": f"b{len(level.buttons) + 1}", "pos": [col, row], "face": "up"})
        elif self.tool == TOOL_ITEM:
            level.items.append({"name": f"i{len(level.items) + 1}", "pos": [col, row], "heavy": False})
        elif self.tool == TOOL_NOZZLE:
            level.nozzles.append(
                {
                    "pos": [col + 0.5, row],
                    "power": NOZZLE_DEFAULT_POWER,
                    "range": NOZZLE_DEFAULT_RANGE,
                }
            )
        elif self.tool == TOOL_PLAYER:
            level.player = {"pos": [col, row]}
        elif self.tool == TOOL_DEST:
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
        self.dirty = True
        self.status = "已撤销"

    # ---- 文件 -------------------------------------------------------
    def new_level(self) -> None:
        self.level = Level()
        self.path = None
        self.undo_stack.clear()
        self.dirty = False
        self.dialog = None
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
        self.startup = False
        self.zoom = None
        self.pan_x = self.pan_y = 0.0
        self.status = f"已打开 {_display_path(path)}"

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
        self.status = f"已保存 {_display_path(path)}"

    # ---- 详细设置 ---------------------------------------------------
    def open_dialog(self) -> None:
        if self.hovered is None:
            self.status = "这里没有可设置的对象"
            return
        kind, entry = self.hovered
        self.dialog = {"kind": kind, "entry": entry}
        self.dialog_field = 0

    def close_dialog(self) -> None:
        self.dialog = None

    def dialog_rows(self) -> list:
        if self.dialog is None:
            return []
        kind = self.dialog["kind"]
        entry = self.dialog["entry"]
        pos = entry["pos"]
        rows = [("位置 x", _number(pos[0])), ("位置 y", _number(pos[1]))]
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
            rows.append(("朝向", entry.get("face", "up")))
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
def toolbar_rects() -> list:
    rects = []
    x = MARGIN
    for label, action, width in TOOLBAR_ITEMS:
        rects.append((pygame.Rect(x, HEADER - 34, width, TOOLBAR_HEIGHT), label, action))
        x += width + 8
    return rects


def menu_rects() -> list:
    rects = []
    button = next(rect for rect, _, action in toolbar_rects() if action == "tools")
    x, y = button.left, button.bottom + 2
    for tool in TOOL_ORDER:
        rects.append((pygame.Rect(x, y, button.width, 22), tool))
        y += 22
    return rects


def startup_rects(surface: pygame.Surface) -> list:
    panel = pygame.Rect(0, 0, 320, 140)
    panel.center = (surface.get_width() // 2, surface.get_height() // 2)
    return [
        (pygame.Rect(panel.left + 24, panel.top + 70, 120, 32), "new"),
        (pygame.Rect(panel.right - 144, panel.top + 70, 120, 32), "open"),
    ]


def draw_canvas(surface: pygame.Surface, editor: Editor, layout: Layout) -> None:
    level = editor.level
    tile = layout.tile
    pygame.draw.rect(surface, PANEL, (layout.left, layout.top, layout.width, layout.height))

    for row in range(ROWS + 2):
        top = layout.top + row * tile
        if row in (0, ROWS + 1):
            pygame.draw.rect(surface, GROUND_COLOR, (layout.left, top, layout.width, tile))

    for entry in level.blocks:
        pygame.draw.rect(surface, BLOCK_COLOR, layout.entry_rect(entry))
    for entry in level.planks:
        pygame.draw.rect(surface, PLANK_COLOR, layout.entry_rect(entry))

    for col in range(COLS + 1):
        x = layout.left + col * tile
        if -tile <= x <= layout.window[0] + tile:
            pygame.draw.line(surface, GRID, (x, layout.top), (x, layout.top + layout.height))
    for row in range(ROWS + 3):
        y = layout.top + row * tile
        pygame.draw.line(surface, GRID, (layout.left, y), (layout.left + layout.width, y))

    for entry in level.movable_blocks:
        pygame.draw.rect(surface, MOVABLE_COLOR, layout.entry_rect(entry))

    for entry in level.buttons:
        rect = layout.entry_rect(entry)
        inset = rect.width * 0.2
        pygame.draw.polygon(
            surface,
            BUTTON_COLOR,
            [
                (rect.left, rect.bottom),
                (rect.right, rect.bottom),
                (rect.right - inset, rect.top),
                (rect.left + inset, rect.top),
            ],
        )

    for entry in level.items:
        rect = layout.entry_rect(entry)
        center = rect.center
        radius = rect.width / 2.0
        pygame.draw.polygon(
            surface,
            ITEM_COLOR,
            [
                (
                    center[0] + radius * math.cos(math.radians(-90 + 72 * i)),
                    center[1] + radius * math.sin(math.radians(-90 + 72 * i)),
                )
                for i in range(5)
            ],
        )

    for entry in level.nozzles:
        # pos 是底边中点：三角形底边中点就画在这个点上，底边落在 y 这道平面上。
        center_x = layout.left + entry["pos"][0] * tile
        base_y = layout.top + (ROWS + 1 - entry["pos"][1]) * tile
        up = int(entry.get("power", NOZZLE_DEFAULT_POWER)) >= 0
        apex_y = base_y - tile if up else base_y + tile
        pygame.draw.polygon(
            surface,
            NOZZLE_COLOR,
            [(center_x - tile / 2, base_y), (center_x + tile / 2, base_y), (center_x, apex_y)],
        )

    if level.player:
        pygame.draw.rect(surface, PLAYER_COLOR, layout.entry_rect(level.player).inflate(0, -2))
    if level.destination:
        pygame.draw.rect(surface, DESTINATION_COLOR, layout.entry_rect(level.destination))

    # 拖动预览
    if editor.drag_start is not None and editor.drag_current is not None:
        x, y, w, h = normalize_drag(editor.drag_start, editor.drag_current)
        preview = pygame.Surface((max(1, round(w * tile)), max(1, round(h * tile))), pygame.SRCALPHA)
        preview.fill(PREVIEW)
        surface.blit(preview, layout.cell_rect(x, y, (w, h)).topleft)

    # 高亮整个对象
    if editor.hovered is not None and not editor.startup:
        kind, entry = editor.hovered
        box = nozzle_box(entry) if kind == KIND_NOZZLE else entry
        pygame.draw.rect(surface, HIGHLIGHT, layout.entry_rect(box), 2)


def draw_header(surface: pygame.Surface, editor: Editor, layout: Layout, font: pygame.font.Font) -> None:
    marker = " *" if editor.dirty else ""
    zoom_text = "自适应" if layout.zoom is None else f"{layout.tile:.1f}px/格"
    head = (
        f"{_display_path(editor.path)}{marker}   缩放: {zoom_text}   "
        f"跳高: {editor.level.jump_height}   撤销 {len(editor.undo_stack)} 步"
    )
    surface.blit(font.render(head, True, TEXT), (MARGIN, 8))

    tool_name = TOOL_SPECS[editor.tool][0]
    hint = (
        f"左键拖出新矩形  右键 设置  Delete 删除  滚轮缩放  中键平移  "
        "Ctrl-Z/S/O/N 撤销/保存/打开/新建"
    )
    surface.blit(font.render(hint, True, DIM_TEXT), (MARGIN, 30))

    for rect, label, action in toolbar_rects():
        pygame.draw.rect(surface, BUTTON_BG, rect)
        pygame.draw.rect(surface, DIALOG_BORDER, rect, 1)
        text_label = f"工具: {tool_name}" if action == "tools" else label
        text = font.render(text_label, True, TEXT)
        surface.blit(text, (rect.centerx - text.get_width() // 2, rect.centery - text.get_height() // 2))
        if action == "tools":
            ax = rect.right - 12
            ay = rect.centery - 2
            pygame.draw.polygon(surface, TEXT, [(ax, ay), (ax + 8, ay), (ax + 4, ay + 5)])


def draw_menu(surface: pygame.Surface, editor: Editor, font: pygame.font.Font) -> None:
    mouse = pygame.mouse.get_pos()
    for rect, tool in menu_rects():
        active = tool == editor.tool
        hovered = rect.collidepoint(mouse)
        if active:
            fill = HIGHLIGHT
        elif hovered:
            fill = (100, 100, 110)
        else:
            fill = BUTTON_BG
        pygame.draw.rect(surface, fill, rect)
        pygame.draw.rect(surface, DIALOG_BORDER, rect, 1)
        color = (20, 20, 20) if active else TEXT
        surface.blit(font.render(TOOL_SPECS[tool][0], True, color), (rect.left + 8, rect.top + 3))


def place_panel(surface: pygame.Surface, panel: pygame.Rect) -> pygame.Rect:
    """居中摆放，并夹在信息栏与状态栏之间。"""
    panel.center = (surface.get_width() // 2, surface.get_height() // 2)
    panel.top = max(HEADER + 4, min(panel.top, surface.get_height() - FOOTER - panel.height - 4))
    panel.left = max(MARGIN, min(panel.left, surface.get_width() - MARGIN - panel.width))
    return panel


def draw_panel(surface: pygame.Surface, panel: pygame.Rect) -> None:
    shade = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    shade.fill((0, 0, 0, 130))
    surface.blit(shade, (0, 0))
    pygame.draw.rect(surface, DIALOG_BG, panel)
    pygame.draw.rect(surface, DIALOG_BORDER, panel, 1)


def _draw_arrow(surface: pygame.Surface, rect: pygame.Rect, direction: int) -> None:
    inset = 6
    if direction < 0:
        points = [
            (rect.right - inset, rect.top + 5),
            (rect.right - inset, rect.bottom - 5),
            (rect.left + inset, rect.centery),
        ]
    else:
        points = [
            (rect.left + inset, rect.top + 5),
            (rect.left + inset, rect.bottom - 5),
            (rect.right - inset, rect.centery),
        ]
    pygame.draw.polygon(surface, TEXT, points)


def _draw_stepper(surface: pygame.Surface, rect: pygame.Rect, direction: int) -> None:
    hovered = rect.collidepoint(pygame.mouse.get_pos())
    pygame.draw.rect(surface, (100, 100, 110) if hovered else BUTTON_BG, rect)
    pygame.draw.rect(surface, DIALOG_BORDER, rect, 1)
    _draw_arrow(surface, rect, direction)


def _draw_button(
    surface: pygame.Surface, font: pygame.font.Font, rect: pygame.Rect, caption: str
) -> None:
    hovered = rect.collidepoint(pygame.mouse.get_pos())
    pygame.draw.rect(surface, (100, 100, 110) if hovered else BUTTON_BG, rect)
    pygame.draw.rect(surface, DIALOG_BORDER, rect, 1)
    text = font.render(caption, True, TEXT)
    surface.blit(text, (rect.centerx - text.get_width() // 2, rect.centery - text.get_height() // 2))


def stepper_rects(cell: pygame.Rect) -> tuple:
    """字段右侧的「减 / 加」两个小方块。"""
    step = 18
    right = pygame.Rect(cell.right - step - 2, cell.top + 1, step, cell.height - 2)
    left = pygame.Rect(right.left - step - 2, cell.top + 1, step, cell.height - 2)
    return left, right


def dialog_geometry(surface: pygame.Surface, editor: Editor) -> tuple:
    """绘制与点击共用同一套几何：面板、字段格、两个按钮。"""
    count = len(editor.dialog_rows())
    columns = 1 if count <= 6 else 2
    per_column = count if columns == 1 else max(1, math.ceil(count / 2))
    width = 380 if columns == 1 else 486
    height = 34 + per_column * ROW_HEIGHT + 8 + BUTTON_HEIGHT + 6
    panel = place_panel(surface, pygame.Rect(0, 0, width, height))

    inner = panel.width - 24
    column_width = (inner - (columns - 1) * COLUMN_GAP) // columns
    cells = []
    for index in range(count):
        column = index // per_column if per_column else 0
        row = index % per_column if per_column else 0
        cells.append(
            (
                pygame.Rect(
                    panel.left + 12 + column * (column_width + COLUMN_GAP),
                    panel.top + 34 + row * ROW_HEIGHT,
                    column_width,
                    ROW_HEIGHT - 2,
                ),
                index,
            )
        )

    button_y = panel.bottom - BUTTON_HEIGHT - 6
    delete_rect = pygame.Rect(panel.left + 12, button_y, 96, BUTTON_HEIGHT)
    close_rect = pygame.Rect(panel.right - 12 - 76, button_y, 76, BUTTON_HEIGHT)
    return panel, cells, delete_rect, close_rect


def draw_dialog(surface: pygame.Surface, editor: Editor, font: pygame.font.Font) -> None:
    panel, cells, delete_rect, close_rect = dialog_geometry(surface, editor)
    draw_panel(surface, panel)

    surface.blit(font.render(editor.dialog_title(), True, TEXT), (panel.left + 12, panel.top + 8))
    hint = font.render("点击面板外关闭", True, DIM_TEXT)
    surface.blit(hint, (panel.right - 12 - hint.get_width(), panel.top + 8))

    rows = editor.dialog_rows()
    for rect, index in cells:
        label, value = rows[index]
        selected = index == editor.dialog_field
        pygame.draw.rect(surface, (62, 62, 72) if selected else (48, 48, 54), rect)
        pygame.draw.rect(surface, HIGHLIGHT if selected else (86, 86, 94), rect, 1)
        left, right = stepper_rects(rect)
        text = font.render(f"{label}: {value}", True, HIGHLIGHT if selected else TEXT)
        clip = max(1, left.left - rect.left - 8)
        surface.blit(
            text,
            (rect.left + 6, rect.centery - text.get_height() // 2),
            (0, 0, min(text.get_width(), clip), text.get_height()),
        )
        _draw_stepper(surface, left, -1)
        _draw_stepper(surface, right, 1)

    _draw_button(surface, font, delete_rect, "删除对象")
    _draw_button(surface, font, close_rect, "关闭")


def settings_geometry(surface: pygame.Surface) -> tuple:
    panel = place_panel(surface, pygame.Rect(0, 0, 440, 172))
    name_rect = pygame.Rect(panel.left + 12, panel.top + 38, panel.width - 24, ROW_HEIGHT + 2)
    erase_rect = pygame.Rect(name_rect.right - 60, name_rect.top + 1, 58, name_rect.height - 2)
    jump_rect = pygame.Rect(panel.left + 12, panel.top + 72, panel.width - 24, ROW_HEIGHT + 2)
    button_y = panel.bottom - BUTTON_HEIGHT - 8
    apply_rect = pygame.Rect(panel.right - 12 - 140, button_y, 68, BUTTON_HEIGHT)
    cancel_rect = pygame.Rect(panel.right - 12 - 68, button_y, 68, BUTTON_HEIGHT)
    return panel, name_rect, erase_rect, jump_rect, apply_rect, cancel_rect


def draw_settings(surface: pygame.Surface, editor: Editor, font: pygame.font.Font) -> None:
    panel, name_rect, erase_rect, jump_rect, apply_rect, cancel_rect = settings_geometry(surface)
    draw_panel(surface, panel)

    surface.blit(font.render("关卡设置", True, TEXT), (panel.left + 12, panel.top + 8))
    hint = font.render("点击面板外取消", True, DIM_TEXT)
    surface.blit(hint, (panel.right - 12 - hint.get_width(), panel.top + 8))

    name = editor.settings["name"]
    name_selected = editor.settings_field == 0
    pygame.draw.rect(surface, (62, 62, 72) if name_selected else (48, 48, 54), name_rect)
    pygame.draw.rect(surface, HIGHLIGHT if name_selected else (86, 86, 94), name_rect, 1)
    caret = "|" if name_selected else ""
    text = font.render(f"名称: {name if name else '（空）'}{caret}", True, HIGHLIGHT if name_selected else TEXT)
    clip = max(1, erase_rect.left - name_rect.left - 10)
    surface.blit(
        text,
        (name_rect.left + 6, name_rect.centery - text.get_height() // 2),
        (0, 0, min(text.get_width(), clip), text.get_height()),
    )
    _draw_button(surface, font, erase_rect, "退格")

    jump_selected = editor.settings_field == 1
    pygame.draw.rect(surface, (62, 62, 72) if jump_selected else (48, 48, 54), jump_rect)
    pygame.draw.rect(surface, HIGHLIGHT if jump_selected else (86, 86, 94), jump_rect, 1)
    left, right = stepper_rects(jump_rect)
    value = font.render(
        f"初始跳高: {editor.settings['jump_height']}", True, HIGHLIGHT if jump_selected else TEXT
    )
    surface.blit(value, (jump_rect.left + 6, jump_rect.centery - value.get_height() // 2))
    _draw_stepper(surface, left, -1)
    _draw_stepper(surface, right, 1)

    _draw_button(surface, font, apply_rect, "应用")
    _draw_button(surface, font, cancel_rect, "取消")


def draw_startup(surface: pygame.Surface, font: pygame.font.Font) -> None:
    panel = place_panel(surface, pygame.Rect(0, 0, 320, 140))
    draw_panel(surface, panel)
    title = font.render("关卡编辑器", True, TEXT)
    surface.blit(title, (panel.centerx - title.get_width() // 2, panel.top + 16))
    sub = font.render("新建一个关卡，或打开已有关卡文件", True, DIM_TEXT)
    surface.blit(sub, (panel.centerx - sub.get_width() // 2, panel.top + 42))
    for rect, action in startup_rects(surface):
        pygame.draw.rect(surface, BUTTON_BG, rect)
        pygame.draw.rect(surface, DIALOG_BORDER, rect, 1)
        label = "新建关卡" if action == "new" else "打开关卡"
        text = font.render(label, True, TEXT)
        surface.blit(text, (rect.centerx - text.get_width() // 2, rect.centery - text.get_height() // 2))


def draw(surface: pygame.Surface, editor: Editor, font: pygame.font.Font, layout: Layout) -> None:
    surface.fill(BACKGROUND)
    draw_canvas(surface, editor, layout)
    draw_header(surface, editor, layout, font)
    surface.blit(font.render(editor.status, True, STATUS_TEXT), (MARGIN, surface.get_height() - FOOTER + 6))

    if editor.menu_open:
        draw_menu(surface, editor, font)
    if editor.dialog is not None:
        draw_dialog(surface, editor, font)
    if editor.settings is not None:
        draw_settings(surface, editor, font)
    if editor.startup:
        draw_startup(surface, font)


def handle_toolbar(editor: Editor, position: tuple) -> str | None:
    for rect, _, action in toolbar_rects():
        if not rect.collidepoint(position):
            continue
        if action == "new":
            editor.new_level()
        elif action == "open":
            editor.open_level()
        elif action == "save":
            editor.save()
        elif action == "undo":
            editor.undo()
        elif action == "tools":
            editor.menu_open = not editor.menu_open
        elif action == "settings":
            editor.open_settings()
        return action
    return None


def tools_button_hit(position: tuple) -> bool:
    return any(
        rect.collidepoint(position) for rect, _, action in toolbar_rects() if action == "tools"
    )


def handle_menu(editor: Editor, position: tuple) -> bool:
    for rect, tool in menu_rects():
        if rect.collidepoint(position):
            editor.tool = tool
            editor.menu_open = False
            return True
    return False


def handle_dialog_click(surface: pygame.Surface, editor: Editor, position: tuple) -> None:
    panel, cells, delete_rect, close_rect = dialog_geometry(surface, editor)
    if delete_rect.collidepoint(position):
        kind, entry = editor.dialog["kind"], editor.dialog["entry"]
        editor.delete_entry(kind, entry)
        return
    if close_rect.collidepoint(position):
        editor.close_dialog()
        return
    for rect, index in cells:
        if not rect.collidepoint(position):
            continue
        editor.dialog_field = index
        left, right = stepper_rects(rect)
        if left.collidepoint(position):
            editor.adjust_dialog(-1)
        elif right.collidepoint(position):
            editor.adjust_dialog(1)
        return
    if not panel.collidepoint(position):
        editor.close_dialog()


def handle_settings_click(surface: pygame.Surface, editor: Editor, position: tuple) -> None:
    panel, name_rect, erase_rect, jump_rect, apply_rect, cancel_rect = settings_geometry(surface)
    if apply_rect.collidepoint(position):
        editor.close_settings(True)
        return
    if cancel_rect.collidepoint(position):
        editor.close_settings(False)
        return
    if erase_rect.collidepoint(position):
        editor.settings_field = 0
        editor.erase_settings_char()
        return
    if name_rect.collidepoint(position):
        editor.settings_field = 0
        return
    if jump_rect.collidepoint(position):
        editor.settings_field = 1
        left, right = stepper_rects(jump_rect)
        if left.collidepoint(position):
            editor.adjust_settings(-1)
        elif right.collidepoint(position):
            editor.adjust_settings(1)
        return
    if not panel.collidepoint(position):
        editor.close_settings(False)


def main() -> None:
    pygame.init()
    pygame.display.set_caption("level designer")
    screen = pygame.display.set_mode(DEFAULT_WINDOW, pygame.RESIZABLE)
    font = pygame.font.SysFont("microsoftyahei", 14)
    clock = pygame.time.Clock()
    editor = Editor()

    running = True
    while running:
        layout = Layout(screen.get_size(), editor.zoom, editor.pan_x, editor.pan_y)
        editor.pan_x, editor.pan_y = layout.pan_x, layout.pan_y

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.VIDEORESIZE:
                size = (max(MIN_WINDOW[0], event.w), max(MIN_WINDOW[1], event.h))
                screen = pygame.display.set_mode(size, pygame.RESIZABLE)
                layout = Layout(size, editor.zoom, editor.pan_x, editor.pan_y)
                editor.pan_x, editor.pan_y = layout.pan_x, layout.pan_y
            elif editor.startup:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key in (pygame.K_RETURN, pygame.K_n):
                        editor.new_level()
                    elif event.key == pygame.K_o:
                        editor.open_level()
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for rect, action in startup_rects(screen):
                        if rect.collidepoint(event.pos):
                            editor.new_level() if action == "new" else editor.open_level()
                            break
            elif editor.settings is not None:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        editor.close_settings(False)
                    elif event.key == pygame.K_RETURN:
                        editor.close_settings(True)
                    elif event.key == pygame.K_UP:
                        editor.settings_field = (editor.settings_field - 1) % 2
                    elif event.key == pygame.K_DOWN:
                        editor.settings_field = (editor.settings_field + 1) % 2
                    elif event.key == pygame.K_LEFT:
                        editor.adjust_settings(-1)
                    elif event.key == pygame.K_RIGHT:
                        editor.adjust_settings(1)
                    elif event.key == pygame.K_BACKSPACE:
                        editor.erase_settings_char()
                    else:
                        editor.type_settings(event.unicode)
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    handle_settings_click(screen, editor, event.pos)
            elif editor.dialog is not None:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        editor.close_dialog()
                    elif event.key == pygame.K_DELETE:
                        kind, entry = editor.dialog["kind"], editor.dialog["entry"]
                        editor.delete_entry(kind, entry)
                    elif event.key == pygame.K_UP:
                        editor.move_dialog_field(-1)
                    elif event.key == pygame.K_DOWN:
                        editor.move_dialog_field(1)
                    elif event.key == pygame.K_LEFT:
                        editor.adjust_dialog(-1)
                    elif event.key == pygame.K_RIGHT:
                        editor.adjust_dialog(1)
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    handle_dialog_click(screen, editor, event.pos)
            elif editor.menu_open:
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    editor.menu_open = False
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button in (1, 3):
                    if event.button == 1 and handle_menu(editor, event.pos):
                        continue
                    editor.menu_open = False
                    if event.button == 1 and not tools_button_hit(event.pos):
                        handle_toolbar(editor, event.pos)
            elif event.type == pygame.MOUSEMOTION:
                cell = layout.cell_at(event.pos)
                editor.update_hover(event.pos, layout)
                if editor.pan_drag is not None:
                    start_x, start_y, start_pan_x, start_pan_y = editor.pan_drag
                    editor.pan_x = start_pan_x - (event.pos[0] - start_x)
                    editor.pan_y = start_pan_y - (event.pos[1] - start_y)
                elif editor.drag_start is not None and cell is not None:
                    editor.drag_current = cell
            elif event.type == pygame.MOUSEWHEEL:
                if event.y:
                    factor = ZOOM_STEP if event.y > 0 else 1.0 / ZOOM_STEP
                    new_tile = min(max(layout.tile * factor, layout.min_tile), layout.max_tile)
                    anchor_x, anchor_y = pygame.mouse.get_pos()
                    canvas_x = (anchor_x - layout.left) / layout.tile
                    canvas_y = (anchor_y - layout.top) / layout.tile
                    editor.zoom = new_tile
                    editor.pan_x = MARGIN - anchor_x + canvas_x * new_tile
                    editor.pan_y = HEADER - anchor_y + canvas_y * new_tile
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button in (4, 5):
                    continue
                if event.button == 1 and handle_toolbar(editor, event.pos):
                    continue
                if event.button == 2:
                    editor.pan_drag = (event.pos[0], event.pos[1], editor.pan_x, editor.pan_y)
                    continue
                cell = layout.cell_at(event.pos)
                if event.button == 1 and cell is not None:
                    editor.press_canvas(event.pos, layout)
                elif event.button == 3:
                    editor.update_hover(event.pos, layout)
                    editor.open_dialog()
            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 2:
                    editor.pan_drag = None
                elif event.button == 1 and editor.drag_start is not None:
                    editor.finish_drag()
            elif event.type == pygame.KEYDOWN:
                ctrl = bool(event.mod & pygame.KMOD_CTRL)
                if ctrl and event.key == pygame.K_z:
                    editor.undo()
                elif ctrl and event.key == pygame.K_s:
                    editor.save()
                elif ctrl and event.key == pygame.K_o:
                    editor.open_level()
                elif ctrl and event.key == pygame.K_n:
                    editor.new_level()
                elif event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_DELETE and editor.hovered is not None:
                    kind, entry = editor.hovered
                    editor.delete_entry(kind, entry)

        draw(screen, editor, font, layout)
        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    main()
