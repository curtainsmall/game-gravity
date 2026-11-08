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
TRIGGER_SOURCE_COLOR = (220, 20, 60)   # 触发源：整块矩形就是触发区，红色
NOZZLE_COLOR = (220, 20, 60)
PORTAL_COLOR = (130, 80, 200)
PLAYER_COLOR = (255, 140, 0)
DESTINATION_COLOR = (34, 139, 34)
PIVOT_COLOR = (255, 70, 70)
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
ANIMATION_COLOR = (110, 190, 220)
SOUND_COLOR = (150, 225, 150)
HANDLE_COLOR = (255, 255, 255)
VIEW_MENU_WIDTH = 170          # 视图设置菜单宽度
LEVEL_SELECT_WIDTH = 420       # 关卡列表浮层宽度

# ---- 新建菜单里的对象种类 ----
(
    TOOL_BLOCK,
    TOOL_PLANK,
    TOOL_MOVABLE,
    TOOL_TRIGGER_SOURCE,
    TOOL_NOZZLE,
    TOOL_PLAYER,
    TOOL_DEST,
    TOOL_TEXTURE,
    TOOL_PORTAL,
    TOOL_ANIMATION,
    TOOL_SOUND,
) = range(11)

TOOL_SPECS = {
    TOOL_BLOCK: ("方块", "rect"),
    TOOL_PLANK: ("木板", "rect"),
    TOOL_MOVABLE: ("可移动方块", "rect"),
    TOOL_TRIGGER_SOURCE: ("触发源", "rect"),
    TOOL_NOZZLE: ("喷口", "single"),
    TOOL_PLAYER: ("起点", "single"),
    TOOL_DEST: ("终点", "single"),
    TOOL_TEXTURE: ("贴图", "import"),   # import：选图直接导入，不进创建模式
    TOOL_PORTAL: ("传送门", "single"),
    TOOL_ANIMATION: ("动画", "single"),
    TOOL_SOUND: ("声音", "single"),
}

TOOL_ORDER = [
    TOOL_BLOCK,
    TOOL_PLANK,
    TOOL_MOVABLE,
    TOOL_TRIGGER_SOURCE,
    TOOL_PORTAL,
    TOOL_NOZZLE,
    TOOL_PLAYER,
    TOOL_DEST,
    TOOL_TEXTURE,
    TOOL_ANIMATION,
    TOOL_SOUND,
]

# 新建时预览框用的颜色：和画布里这种对象本身的颜色一致
TOOL_COLORS = {
    TOOL_BLOCK: BLOCK_COLOR,
    TOOL_PLANK: PLANK_COLOR,
    TOOL_MOVABLE: MOVABLE_COLOR,
    TOOL_TRIGGER_SOURCE: TRIGGER_SOURCE_COLOR,
    TOOL_PORTAL: PORTAL_COLOR,
    TOOL_NOZZLE: NOZZLE_COLOR,
    TOOL_PLAYER: PLAYER_COLOR,
    TOOL_DEST: DESTINATION_COLOR,
    TOOL_TEXTURE: TEXTURE_COLOR,
    TOOL_ANIMATION: ANIMATION_COLOR,
    TOOL_SOUND: SOUND_COLOR,
}

# ---- 默认值 ----
NOZZLE_DEFAULT_POWER = 7
NOZZLE_DEFAULT_SIZE = (1.0, 5.0)   # 风区尺寸：宽 1 格、长 5 格（老数据里的 range 读进来换成它）
# 力度（目标离底面多远）至少要比风区沿朝向的长度多 0.5 格：目标点必须在风区外面，
# 不然风区末端那一段会把物体往回推。风区可以随意改，力度只跟着往上顶，不设上限。
NOZZLE_POWER_MARGIN = 0.5
# 传送门画出来的那块门：1 格宽、0.3 格高。门本身既是外观也是触发区，没有额外范围
PORTAL_SIZE = (1.0, 0.3)
# 老数据里的按钮：棱台，pos 是底面中点，缺省 1 格宽、0.3 格高；读进来按实际矩形换算
LEGACY_BUTTON_SIZE = (1.0, 0.3)
FACE_ORDER = ("up", "right", "down", "left")   # 传送门和喷口的朝向循环顺序
FACE_LABELS = {"up": "上", "right": "右", "down": "下", "left": "左"}  # 界面上显示的中文
FACE_DIRECTIONS = {
    "up": (0.0, 1.0),
    "right": (1.0, 0.0),
    "down": (0.0, -1.0),
    "left": (-1.0, 0.0),
}
# 跳高（格）：可以是小数，加减按半格一步；输入上限还要看关卡高度
JUMP_HEIGHT_DEFAULT = 2.0
JUMP_HEIGHT_MIN, JUMP_HEIGHT_MAX = 0.0, 99.0
JUMP_HEIGHT_STEP = 0.5

# 触发源对跳高的变化量（格）：正数跳更高、负数跳更低、0 只是开关
TRIGGER_JUMP_OFFSET_MIN, TRIGGER_JUMP_OFFSET_MAX = -99.0, 99.0

# 触发源的模式：(显示文字, json 里的值)。hold = 压着才算，once = 第一次压到后一直算
TRIGGER_SOURCE_MODES = (("按住", "hold"), ("一次", "once"))
TRIGGER_SOURCE_MODE_VALUES = tuple(value for _, value in TRIGGER_SOURCE_MODES)
TRIGGER_SOURCE_MODE_LABELS = {value: label for label, value in TRIGGER_SOURCE_MODES}
TRIGGER_SOURCE_MODE_DEFAULT = "hold"

# 水平移动速度（方块/秒）
MOVE_SPEED_DEFAULT = 8.0
MOVE_SPEED_MIN, MOVE_SPEED_MAX = 0.5, 40.0

# 翻转带高度：第一个贴着关卡顶（向上翻），第二个贴着关卡底（向下翻）；0 表示翻不了
FLIP_AREA_OFFSETS_DEFAULT = (0.0, 0.0)

# 关卡设置分四页：(页签标题, 这一页有哪几个字段)。字段下标对应编辑器 settings 里的格子：
# 0 名称、1 宽度、2 高度、3 上翻带、4 下翻带、5 背景、6 跳高、7 速度、
# 8 声音（声音库的键）、9 循环、10 淡入、11 淡出。过场页是卡片列表，不用这套字段。
SETTINGS_TABS = (
    ("常规", (0, 1, 2, 3, 4, 5)),
    ("玩家", (6, 7)),
    ("声音", (8, 9, 10, 11)),
    ("过场", ()),
)
SETTINGS_CUTSCENE_TAB = 3
# 游戏配置分七页：常规、动画集、制作名单、声音、声音库、过场、玩家表现。每页有哪些格子由
# editor.game_cells 按页给；玩家表现页只负责跳到属性面板里的全局项。
GAME_SETTINGS_TABS = ("常规", "动画集", "制作名单", "声音", "声音库", "过场", "玩家表现")
GAME_ANIMATION_TAB = 1
GAME_SOUND_LIBRARY_TAB = 4
GAME_CUTSCENE_TAB = 5
GAME_PLAYER_VIEW_TAB = 6
BACKGROUND_MAX_LENGTH = 120

# 编辑器里可滚的页面：滚轮一格滚多少像素
SCROLL_STEP = 48

# ---- 对象种类 ----
KIND_BLOCK = "block"
KIND_PLANK = "plank"
KIND_MOVABLE = "movable_block"
KIND_TRIGGER_SOURCE = "trigger_source"
KIND_PORTAL = "portal"
KIND_NOZZLE = "nozzle"
KIND_PLAYER = "player"
KIND_DESTINATION = "destination"
KIND_TEXTURE = "texture"
KIND_ANIMATION = "animation"
KIND_SOUND = "sound"
# 全局项：只属于游戏配置，不写进关卡；在对象列表里固定排在最上面
KIND_GLOBAL_HEADER = "global_header"
KIND_GLOBAL_ANIMATION = "global_animation"
KIND_GLOBAL_SOUND = "global_sound"
GLOBAL_KINDS = (KIND_GLOBAL_ANIMATION, KIND_GLOBAL_SOUND)
MIN_SIZE = 0.05   # 对象最小宽高（格），防止拖成一条看不见的线
HANDLE_PIXELS = 7  # 缩放手柄的热区半径（像素）：比画出来的把手大一点点
NUMBER_TEXT_MAX_LENGTH = 8  # 属性面板里数字字段最多敲几个字符（含负号和小数点）

# 关卡数据里带 name 字段、会被别的对象引用的种类
KIND_HAS_NAME = (KIND_MOVABLE, KIND_TRIGGER_SOURCE, KIND_PORTAL)
NAME_MAX_LENGTH = 24

KIND_TITLES = {
    KIND_BLOCK: "方块",
    KIND_PLANK: "木板",
    KIND_MOVABLE: "可移动方块",
    KIND_TRIGGER_SOURCE: "触发源",
    KIND_PORTAL: "传送门",
    KIND_NOZZLE: "喷口",
    KIND_PLAYER: "起点",
    KIND_DESTINATION: "终点",
    KIND_TEXTURE: "贴图",
    KIND_ANIMATION: "动画",
    KIND_SOUND: "声音",
    KIND_GLOBAL_HEADER: "全局",
    KIND_GLOBAL_ANIMATION: "玩家动画",
    KIND_GLOBAL_SOUND: "玩家音效",
}

# 左侧对象列表里的种类顺序（筛选菜单也按这个顺序列）
KIND_ORDER = (
    KIND_BLOCK,
    KIND_PLANK,
    KIND_MOVABLE,
    KIND_TRIGGER_SOURCE,
    KIND_PORTAL,
    KIND_NOZZLE,
    KIND_PLAYER,
    KIND_DESTINATION,
    KIND_TEXTURE,
    KIND_ANIMATION,
    KIND_SOUND,
)

# ---- 触发行为 ----
# 每种对象能接的触发行为：(显示文字, json 里的行为名)。TriggerSystem 只派发事件名，这些名字
# 由游戏里各自读 events 的系统认领（move 由 ControllerSystem，hide/show 由渲染）；编辑器这边
# 只负责列出每种对象能填哪些。终点比较特殊：它不看行为名，所有卡片都生效才能通关。
KIND_BEHAVIORS = {
    KIND_TEXTURE: (("隐藏", "hide"), ("显示", "show")),
    KIND_ANIMATION: (("隐藏", "hide"), ("显示", "show")),
    KIND_MOVABLE: (("移动", "move"),),
    KIND_DESTINATION: (("解锁", "unlock"),),
}

# 触发卡片的模式：(显示文字, json 里的值)。once = 触发一次就一直生效；hold = 按着才生效、
# 松开就撤销；switch = 每触发一次在生效和撤销之间切换。新卡片的默认模式沿用以前的「不勾」；
# 终点的条件是「触发过就算」，所以默认一次，免得按住类触发源永远解不开。
TRIGGER_MODES = (("一次", "once"), ("按住", "hold"), ("切换", "switch"))
TRIGGER_MODE_VALUES = tuple(value for _, value in TRIGGER_MODES)
TRIGGER_DEFAULT_MODE = "hold"
DESTINATION_TRIGGER_DEFAULT_MODE = "once"

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
# 一个关卡 = levels/ 下的一个 <关卡名>.json；图片放哪儿都行，路径相对 game.json
LEVEL_FILE_SUFFIX = ".json"
LEVEL_BACKGROUND_NAME = "background.png"   # 没写 background 时在游戏根里找它兜底
# 贴图没有专门的目录：image 只要求是相对 game.json 的路径，放哪儿都行
BACKGROUND_FILTERS = [("图片文件", "*.png *.jpg *.jpeg *.bmp *.gif"), ("所有文件", "*.*")]
AUDIO_FILTERS = [("音频文件", "*.ogg *.mp3 *.wav *.flac"), ("所有文件", "*.*")]
GAME_FILTERS = [("游戏配置文件", "*.json"), ("所有文件", "*.*")]

# 玩家自己的设置（音量）：和游戏共用 exe 旁边的 .game/setting.json，编辑器只读它
SETTING_DIR_NAME = ".game"
SETTING_FILE_NAME = "setting.json"

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
DOCK_TAB_HEIGHT = 26          # 右侧面板顶上「属性 / 对象列表」两个标签占多高
CREATE_MENU_WIDTH = 150
RULER_HEIGHT = 24
RULER_STEP = 10

# 按钮朝向 -> 棱台旋转角度，和 renderer 里 PlaceholderFace.rotation 一致
FACE_ROTATIONS = {"up": 0, "right": 90, "down": 180, "left": 270}
