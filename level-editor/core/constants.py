"""常量：尺寸、配色、对象种类、工具栏项。"""

import os
import sys

# ---- 画布与窗口 ----
COLS = 120          # 新建关卡的默认宽度（格）
ROWS = 8            # 新建关卡的默认高度（格）

# 关卡尺寸的取值范围（宽、高，以格计）。宽度上限防手滑打成几万格把画布拖死。
LEVEL_WIDTH_MIN, LEVEL_WIDTH_MAX = 8, 1000
LEVEL_HEIGHT_MIN, LEVEL_HEIGHT_MAX = 2, 40

# 和游戏同一套像素规则：可玩行在屏幕上固定 400px 高，背景图按这个高度画，
# 且只铺可玩区（地面行与天花板行在背景之外）。编辑器默认就按这个比例显示。
BAND_PIXEL_HEIGHT = 400.0

HEADER = 88
FOOTER = 30
MARGIN = 12
DEFAULT_WINDOW = (1280, 720)
MIN_WINDOW = (620, 260)

ZOOM_STEP = 1.1
ZOOM_MAX_TILE = 100.0   # px/格上限；游戏比例比它大时以游戏比例为准，保证默认可达

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
TEXTURE_COLOR = (150, 150, 170)
HANDLE_COLOR = (255, 255, 255)
TEXTURE_HANDLE_PIXELS = 14     # 贴图四角的缩放热区半径（像素）
VIEW_MENU_WIDTH = 170          # 视图设置菜单宽度

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
    TOOL_TEXTURE,
) = range(9)

TOOL_SPECS = {
    TOOL_BLOCK: ("方块", "rect"),
    TOOL_PLANK: ("木板", "rect"),
    TOOL_MOVABLE: ("可移动方块", "rect"),
    TOOL_BUTTON: ("按钮", "single"),
    TOOL_ITEM: ("道具", "single"),
    TOOL_NOZZLE: ("喷口", "single"),
    TOOL_PLAYER: ("起点", "single"),
    TOOL_DEST: ("终点", "single"),
    TOOL_TEXTURE: ("贴图", "import"),   # import：选图直接导入，不进创建模式
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
    TOOL_TEXTURE,
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
    TOOL_TEXTURE: TEXTURE_COLOR,
}

# ---- 默认值 ----
NOZZLE_DEFAULT_POWER = 7
NOZZLE_DEFAULT_RANGE = 5
JUMP_HEIGHT_DEFAULT = 4
JUMP_HEIGHT_MIN = 0   # 上限不是常数：最多到「关卡高度 - 1」，见 Editor._jump_height_limit

# 关卡设置里的字段数：名称、宽度、高度、初始跳高、背景
SETTINGS_FIELD_COUNT = 5
BACKGROUND_MAX_LENGTH = 120

# ---- 对象种类 ----
KIND_BLOCK = "block"
KIND_PLANK = "plank"
KIND_MOVABLE = "movable_block"
KIND_BUTTON = "button"
KIND_ITEM = "item"
KIND_NOZZLE = "nozzle"
KIND_PLAYER = "player"
KIND_DESTINATION = "destination"
KIND_TEXTURE = "texture"
TEXTURE_MIN_SIZE = 0.05   # 贴图最小宽高（格），防止拖成一条看不见的线

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
    KIND_TEXTURE: "贴图",
}

# ---- 路径 ----
# 打包成 exe 后，关卡放在 exe 旁边的 assets/ 里；直接跑源码时在仓库根目录
if getattr(sys, "frozen", False):
    ROOT = os.path.dirname(os.path.abspath(sys.executable))
else:
    ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

LEVELS_DIR = os.path.join(ROOT, "assets", "levels")
# 一个关卡 = 一个文件夹，文件夹名就是关卡名
LEVEL_SCENE_NAME = "scene.json"            # 关卡数据
LEVEL_BACKGROUND_NAME = "background.png"   # 背景图进来后固定叫这个名字
# 贴图没有专门的目录：image 只要求是相对 scene.json 的路径，放哪儿都行
BACKGROUND_FILTERS = [("图片", "*.png *.jpg *.jpeg *.bmp *.gif"), ("所有文件", "*.*")]

# ---- 界面尺寸 ----
TOOLBAR_ITEMS = [
    ("新建", "new", 56),
    ("打开", "open", 56),
    ("保存", "save", 56),
    ("撤销", "undo", 56),
    ("关卡设置", "settings", 88),
    ("视图", "view", 56),
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
