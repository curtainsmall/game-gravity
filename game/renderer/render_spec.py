"""RenderSpec：占位图形与贴图的描述。纯数据，行为在渲染系统里。"""

from enum import StrEnum


class PlaceholderShape(StrEnum):
    RECT = "rect"
    CIRCLE = "circle"
    TRIANGLE = "triangle"
    FRUSTUM = "frustum"
    PENTAGON = "pentagon"
    POLY = "poly"


class PlaceholderFace(StrEnum):
    """占位图形的朝向：窄端指向这一侧。"""

    UP = "up"
    DOWN = "down"
    LEFT = "left"
    RIGHT = "right"

    @property
    def rotation(self) -> int:
        return {"up": 0, "right": 90, "down": 180, "left": 270}[str(self)]


class RenderSpec:
    def __init__(
        self,
        placeholder_shape: PlaceholderShape = PlaceholderShape.RECT,
        placeholder_size_in_blocks: tuple[float, float] = (1.0, 1.0),
        placeholder_color: tuple[int, int, int, int] = (180, 180, 180, 255),
        placeholder_label_text: str = "",
        placeholder_direction: int = 1,
        placeholder_face: PlaceholderFace = PlaceholderFace.UP,
        placeholder_has_axis: bool = False,
        texture_path: str | None = None,
        texture_smooth: bool = False,
        texture_face: str = "up",
        texture_flip: bool = False,
        hidden: bool = False,
    ) -> None:
        self.placeholder_shape: PlaceholderShape = placeholder_shape
        self.placeholder_size_in_blocks: tuple[float, float] = placeholder_size_in_blocks
        self.placeholder_color: tuple[int, int, int, int] = placeholder_color
        self.placeholder_label_text: str = placeholder_label_text  # 占位期用于辨认
        self.placeholder_direction: int = placeholder_direction    # 三角形朝向：+1 上，-1 下
        self.placeholder_face: PlaceholderFace = placeholder_face  # 棱台窄端朝向
        self.placeholder_has_axis: bool = placeholder_has_axis      # 沿 body 中轴画虚线
        self.texture_path: str | None = texture_path                # 有图就画图，占位形状退到兜底
        self.texture_smooth: bool = texture_smooth                  # 平滑缩放（像素画应关掉）
        self.texture_face: str = texture_face                       # 图先顺时针转：up/right/down/left
        self.texture_flip: bool = texture_flip                      # 转完再水平镜像
        self.hidden: bool = hidden                                  # 初始隐藏；触发器事件会再改可见性
