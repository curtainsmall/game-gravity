"""RenderSpec：占位图形的描述。纯数据，本阶段不做绘制。"""


class RenderSpec:
    def __init__(
        self,
        placeholder_shape: str = "rect",
        placeholder_size_in_blocks: tuple[float, float] = (1.0, 1.0),
        placeholder_color: tuple[int, int, int] = (180, 180, 180),
        placeholder_label_text: str = "",
    ):
        self.placeholder_shape = placeholder_shape                        # rect / circle / poly
        self.placeholder_size_in_blocks = placeholder_size_in_blocks
        self.placeholder_color = placeholder_color
        self.placeholder_label_text = placeholder_label_text              # 占位期用于辨认
