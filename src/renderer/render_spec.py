"""RenderSpec：占位图形的描述。纯数据，本阶段不做绘制。"""

from enum import StrEnum


class PlaceholderShape(StrEnum):
    RECT = "rect"
    CIRCLE = "circle"
    POLY = "poly"


class RenderSpec:
    def __init__(
        self,
        placeholder_shape: PlaceholderShape = PlaceholderShape.RECT,
        placeholder_size_in_blocks: tuple[float, float] = (1.0, 1.0),
        placeholder_color: tuple[int, int, int] = (180, 180, 180),
        placeholder_label_text: str = "",
    ) -> None:
        self.placeholder_shape: PlaceholderShape = placeholder_shape
        self.placeholder_size_in_blocks: tuple[float, float] = placeholder_size_in_blocks
        self.placeholder_color: tuple[int, int, int] = placeholder_color
        self.placeholder_label_text: str = placeholder_label_text  # 占位期用于辨认
