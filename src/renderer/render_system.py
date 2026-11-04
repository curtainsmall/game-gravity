"""RenderSystem：按部件绘制对象与静态方块。本阶段不做绘制。"""


class RenderSystem:
    def update(self, objects, surface) -> None:
        """绘制目标接入后：遍历有 render 的对象，再遍历静态网格的可见列。"""
