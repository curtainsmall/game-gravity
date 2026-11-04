"""GameObject：身份 + 部件容器。纯数据，行为在系统里。"""

from enum import StrEnum

from controller.controller import Controller
from physics.body import Body
from renderer.render_spec import RenderSpec


class GameObjectKind(StrEnum):
    """对象的用途标签。新增一类对象时在此加成员。"""

    UNKNOWN = "unknown"
    BLOCK = "block"
    PLANK = "plank"
    GROUND = "ground"
    CEILING = "ceiling"
    PLAYER = "player"


class GameObject:
    def __init__(
        self,
        kind: GameObjectKind = GameObjectKind.UNKNOWN,
        body: Body | None = None,
        controller: Controller | None = None,
        render: RenderSpec | None = None,
        interaction_state: int = 0,
    ) -> None:
        self.kind: GameObjectKind = kind
        self.body: Body | None = body                    # 物理部件
        self.controller: Controller | None = controller  # 运动来源
        self.render: RenderSpec | None = render          # 显示部件
        self.interaction_state: int = interaction_state  # 交互状态，由系统写入

    def describe(self) -> str:
        parts = [
            name
            for name in ("body", "controller", "render")
            if getattr(self, name) is not None
        ]
        return f"{self.kind}({', '.join(parts) or 'data'})"

    def __repr__(self) -> str:
        return self.describe()
