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
HEADER_BG = (26, 26, 30, 205)      # 顶部信息栏 + 工具栏的半透明底板
HEADER_LINE = (90, 90, 100)        # 底板下沿的分隔线
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
PORTAL_COLOR = (130, 80, 200)
PLAYER_COLOR = (255, 140, 0)
DESTINATION_COLOR = (34, 139, 34)
PIVOT_COLOR = (255, 70, 70)
RANGE_COLOR = (200, 120, 130)
# 翻转带：向上翻贴顶画红、向下翻贴底画蓝（和游戏里的调试显示同一套颜色）
FLIP_UP_COLOR = (235, 70, 70, 70)
FLIP_DOWN_COLOR = (70, 120, 235, 70)
GROUND_COLOR = (120, 120, 120)
DIALOG_BG = (55, 55, 60)
DIALOG_BORDER = (200, 200, 200)
HIGHLIGHT = (255, 230, 120)
BUTTON_BG = (70, 70, 78)
PREVIEW = (255, 230, 120, 90)
TEXTURE_COLOR = (150, 150, 170)
HANDLE_COLOR = (255, 255, 255)
VIEW_MENU_WIDTH = 170          # 视图设置菜单宽度
LEVEL_SELECT_WIDTH = 420       # 关卡列表浮层宽度

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
    TOOL_PORTAL,
) = range(10)

TOOL_SPECS = {
    TOOL_BLOCK: ("方块", "rect"),
    TOOL_PLANK: ("木板", "rect"),
    TOOL_MOVABLE: ("可移动方块", "rect"),
    TOOL_BUTTON: ("按钮", "single"),
    TOOL_PORTAL: ("传送门", "single"),
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
    TOOL_PORTAL,
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
    TOOL_PORTAL: PORTAL_COLOR,
    TOOL_ITEM: ITEM_COLOR,
    TOOL_NOZZLE: NOZZLE_COLOR,
    TOOL_PLAYER: PLAYER_COLOR,
    TOOL_DEST: DESTINATION_COLOR,
    TOOL_TEXTURE: TEXTURE_COLOR,
}

# ---- 默认值 ----
NOZZLE_DEFAULT_POWER = 7
NOZZLE_DEFAULT_SIZE = (1.0, 5.0)   # 风区尺寸：宽 1 格、长 5 格（老数据里的 range 读进来换成它）
# 传送门画出来的那块门：1 格宽、0.3 格高。门本身既是外观也是触发区，没有额外范围
PORTAL_SIZE = (1.0, 0.3)
# 按钮同理：画出来的矩形就是触发区，缺省 1 格宽、0.3 格高
BUTTON_SIZE = (1.0, 0.3)
FACE_ORDER = ("up", "right", "down", "left")   # 按钮、传送门和喷口的朝向循环顺序
FACE_LABELS = {"up": "上", "right": "右", "down": "下", "left": "左"}  # 界面上显示的中文
FACE_DIRECTIONS = {
    "up": (0.0, 1.0),
    "right": (1.0, 0.0),
    "down": (0.0, -1.0),
    "left": (-1.0, 0.0),
}
JUMP_HEIGHT_DEFAULT = 2
JUMP_HEIGHT_MIN, JUMP_HEIGHT_MAX = 0, 99   # 输入上限；实际还要看关卡高度

# 水平移动速度（方块/秒）
MOVE_SPEED_DEFAULT = 8.0
MOVE_SPEED_MIN, MOVE_SPEED_MAX = 0.5, 40.0

# 翻转带高度：第一个贴着关卡顶（向上翻），第二个贴着关卡底（向下翻）；0 表示翻不了
FLIP_AREA_OFFSETS_DEFAULT = (0.0, 0.0)

# 关卡设置里的字段数：名称、宽度、高度、翻转带上下、背景、跳高与速度的覆盖
SETTINGS_FIELD_COUNT = 8
BACKGROUND_MAX_LENGTH = 120

# ---- 对象种类 ----
KIND_BLOCK = "block"
KIND_PLANK = "plank"
KIND_MOVABLE = "movable_block"
KIND_BUTTON = "button"
KIND_PORTAL = "portal"
KIND_ITEM = "item"
KIND_NOZZLE = "nozzle"
KIND_PLAYER = "player"
KIND_DESTINATION = "destination"
KIND_TEXTURE = "texture"
MIN_SIZE = 0.05   # 对象最小宽高（格），防止拖成一条看不见的线
HANDLE_PIXELS = 7  # 缩放手柄的热区半径（像素）：比画出来的把手大一点点
NUMBER_TEXT_MAX_LENGTH = 8  # 属性面板里数字字段最多敲几个字符（含负号和小数点）

# 关卡数据里带 name 字段、会被别的对象引用的种类
KIND_HAS_NAME = (KIND_MOVABLE, KIND_BUTTON, KIND_PORTAL, KIND_ITEM)
NAME_MAX_LENGTH = 24

KIND_TITLES = {
    KIND_BLOCK: "方块",
    KIND_PLANK: "木板",
    KIND_MOVABLE: "可移动方块",
    KIND_BUTTON: "按钮",
    KIND_PORTAL: "传送门",
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

# 游戏根：一个文件夹，里面是 game.json 和 levels/。编辑器启动时让用户挑一个 game.json
# （或者新建一个），之后关卡都从它旁边的 levels/ 里找。下面只是选择框的默认位置。
DEFAULT_GAME_DIR = os.path.join(ROOT, "assets", "game")
GAME_FILE_NAME = "game.json"
LEVELS_DIR_NAME = "levels"
# 一个关卡 = 一个文件夹，文件夹名就是关卡名
LEVEL_SCENE_NAME = "scene.json"            # 关卡数据
LEVEL_BACKGROUND_NAME = "background.png"   # 背景图进来后固定叫这个名字
# 贴图没有专门的目录：image 只要求是相对 scene.json 的路径，放哪儿都行
BACKGROUND_FILTERS = [("图片文件", "*.png *.jpg *.jpeg *.bmp *.gif"), ("所有文件", "*.*")]
GAME_FILTERS = [("游戏配置文件", "*.json"), ("所有文件", "*.*")]

# ---- 界面尺寸 ----
# (文字, 动作, 宽度, 什么时候显示, 靠哪边)：
#   always 一直在；game 打开了游戏就在；level 只改当前这一关，视图里没有关卡时整个不画。
#   left 从左边排，right 贴着右边排（right 组里靠后的更靠右：游戏配置在最右，
#   这样关卡设置收起来时它不会动）。
TOOLBAR_ITEMS = [
    ("文件", "files", 56, "always", "left"),      # 下拉：打开游戏配置 / 选择关卡
    ("视图", "view", 56, "always", "left"),
    ("保存", "save", 56, "level", "left"),
    ("撤销", "undo", 56, "level", "left"),
    ("关卡设置", "settings", 88, "level", "right"),
    ("游戏配置", "game_settings", 88, "game", "right"),
]

# 「文件」菜单里的项：(文字, 动作, 什么时候能点)
FILE_MENU_ITEMS = [
    ("打开游戏配置", "open_game", "always"),
    ("选择关卡", "levels", "game"),
]
FILE_MENU_WIDTH = 150

TOOLBAR_HEIGHT = 24
ROW_HEIGHT = 22
BUTTON_HEIGHT = 22
DETAIL_PANEL_WIDTH = 250
CREATE_MENU_WIDTH = 150
RULER_HEIGHT = 24
RULER_STEP = 10

# 按钮朝向 -> 棱台旋转角度，和 renderer 里 PlaceholderFace.rotation 一致
FACE_ROTATIONS = {"up": 0, "right": 90, "down": 180, "left": 270}
