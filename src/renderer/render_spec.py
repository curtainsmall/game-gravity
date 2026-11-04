"""RenderSpec：占位图形的描述。纯数据，本阶段不做绘制。"""

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
    ) -> None:
        self.placeholder_shape: PlaceholderShape = placeholder_shape
        self.placeholder_size_in_blocks: tuple[float, float] = placeholder_size_in_blocks
        self.placeholder_color: tuple[int, int, int, int] = placeholder_color
        self.placeholder_label_text: str = placeholder_label_text  # 占位期用于辨认
        self.placeholder_direction: int = placeholder_direction    # 三角形朝向：+1 上，-1 下
        self.placeholder_face: PlaceholderFace = placeholder_face  # 棱台窄端朝向
        self.placeholder_has_axis: bool = placeholder_has_axis      # 沿 body 中轴画虚线
