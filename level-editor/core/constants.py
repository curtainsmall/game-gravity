"""常量：尺寸、配色、对象种类、工具栏项。"""

import os

# ---- 画布与窗口 ----
COLS = 120
ROWS = 8
HEADER = 88
FOOTER = 30
MARGIN = 12
DEFAULT_WINDOW = (1280, 720)
MIN_WINDOW = (620, 260)

ZOOM_STEP = 1.1
ZOOM_MAX_TILE = 48.0

# ---- 配色 ----
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
PIVOT_COLOR = (255, 70, 70)
RANGE_COLOR = (200, 120, 130)
GROUND_COLOR = (120, 120, 120)
DIALOG_BG = (55, 55, 60)
DIALOG_BORDER = (200, 200, 200)
HIGHLIGHT = (255, 230, 120)
BUTTON_BG = (70, 70, 78)
PREVIEW = (255, 230, 120, 90)

# ---- 新建菜单里的对象种类 ----
(
    TOOL_BLOCK,
    TOOL_PLANK,
    TOOL_MOVABLE,
    TOOL_BUTTON,
    TOOL_ITEM,
    TOOL_NOZZLE,
    TOOL_PLAYER,
    TOOL_DEST,
) = range(8)

TOOL_SPECS = {
    TOOL_BLOCK: ("方块", "rect"),
    TOOL_PLANK: ("木板", "rect"),
    TOOL_MOVABLE: ("可移动方块", "rect"),
    TOOL_BUTTON: ("按钮", "single"),
    TOOL_ITEM: ("道具", "single"),
    TOOL_NOZZLE: ("喷口", "single"),
    TOOL_PLAYER: ("起点", "single"),
    TOOL_DEST: ("终点", "single"),
}

TOOL_ORDER = [
    TOOL_BLOCK,
    TOOL_PLANK,
    TOOL_MOVABLE,
    TOOL_BUTTON,
    TOOL_ITEM,
    TOOL_NOZZLE,
    TOOL_PLAYER,
    TOOL_DEST,
]

# 新建时预览框用的颜色：和画布里这种对象本身的颜色一致
TOOL_COLORS = {
    TOOL_BLOCK: BLOCK_COLOR,
    TOOL_PLANK: PLANK_COLOR,
    TOOL_MOVABLE: MOVABLE_COLOR,
    TOOL_BUTTON: BUTTON_COLOR,
    TOOL_ITEM: ITEM_COLOR,
    TOOL_NOZZLE: NOZZLE_COLOR,
    TOOL_PLAYER: PLAYER_COLOR,
    TOOL_DEST: DESTINATION_COLOR,
}

# ---- 默认值 ----
NOZZLE_DEFAULT_POWER = 7
NOZZLE_DEFAULT_RANGE = 5
JUMP_HEIGHT_DEFAULT = 4
JUMP_HEIGHT_MIN, JUMP_HEIGHT_MAX = 0, 7

# 关卡设置里的字段数：名称、初始跳高
SETTINGS_FIELD_COUNT = 2

# ---- 对象种类 ----
KIND_BLOCK = "block"
KIND_PLANK = "plank"
KIND_MOVABLE = "movable_block"
KIND_BUTTON = "button"
KIND_ITEM = "item"
KIND_NOZZLE = "nozzle"
KIND_PLAYER = "player"
KIND_DESTINATION = "destination"

# 关卡数据里带 name 字段、会被别的对象引用的种类
KIND_HAS_NAME = (KIND_MOVABLE, KIND_BUTTON, KIND_ITEM)
NAME_MAX_LENGTH = 24

KIND_TITLES = {
    KIND_BLOCK: "方块",
    KIND_PLANK: "木板",
    KIND_MOVABLE: "可移动方块",
    KIND_BUTTON: "按钮",
    KIND_ITEM: "道具",
    KIND_NOZZLE: "喷口",
    KIND_PLAYER: "起点",
    KIND_DESTINATION: "终点",
}

# ---- 路径 ----
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LEVELS_DIR = os.path.join(ROOT, "assets", "levels")
FILE_FILTERS = [("关卡 JSON", "*.json"), ("所有文件", "*.*")]

# ---- 界面尺寸 ----
TOOLBAR_ITEMS = [
    ("新建", "new", 56),
    ("打开", "open", 56),
    ("保存", "save", 56),
    ("撤销", "undo", 56),
    ("关卡设置", "settings", 88),
]

TOOLBAR_HEIGHT = 24
ROW_HEIGHT = 22
BUTTON_HEIGHT = 22
DETAIL_PANEL_WIDTH = 250
CREATE_MENU_WIDTH = 150
RULER_HEIGHT = 24
RULER_STEP = 10

# 按钮朝向 -> 棱台旋转角度，和 renderer 里 PlaceholderFace.rotation 一致
FACE_ROTATIONS = {"up": 0, "right": 90, "down": 180, "left": 270}
