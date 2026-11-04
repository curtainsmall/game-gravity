"""GameObject：身份 + 部件容器。纯数据，行为在系统里。"""

from enum import StrEnum

from controller.controller import Controller
from fan.fan import Fan
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
    FAN = "fan"
    ITEM = "item"
    MOVABLE_BLOCK = "movable_block"
    BUTTON = "button"
    DESTINATION = "destination"


class GameObject:
    def __init__(
        self,
        kind: GameObjectKind = GameObjectKind.UNKNOWN,
        body: Body | None = None,
        controller: Controller | None = None,
        render: RenderSpec | None = None,
        fan: Fan | None = None,
        interaction_state: int = 0,
        name: str = "",
    ) -> None:
        self.kind: GameObjectKind = kind
        self.name: str = name                             # 关卡里的名字，供引用
        self.body: Body | None = body                     # 物理部件
        self.controller: Controller | None = controller   # 运动来源
        self.render: RenderSpec | None = render           # 显示部件
        self.fan: Fan | None = fan                        # 风区参数
        self.interaction_state: int = interaction_state   # 交互状态，由系统写入

    def describe(self) -> str:
        parts = [
            name
            for name in ("body", "controller", "render", "fan")
            if getattr(self, name) is not None
        ]
        label = self.name or str(self.kind)
        return f"{label}({', '.join(parts) or 'data'})"

    def __repr__(self) -> str:
        return self.describe()
