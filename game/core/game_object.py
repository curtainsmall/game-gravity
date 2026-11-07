"""GameObject：身份 + 部件容器。纯数据，行为在系统里。"""

from enum import StrEnum

from controller.controller import Controller
from nozzle.nozzle import Nozzle
from physics.body import Body
from portal.portal import Portal
from renderer.render_spec import RenderSpec
from trigger.trigger import TriggerSheet
from trigger_source.trigger_source import TriggerSource


class GameObjectKind(StrEnum):
    """对象的用途标签。新增一类对象时在此加成员。"""

    UNKNOWN = "unknown"
    BLOCK = "block"
    PLANK = "plank"
    GROUND = "ground"
    CEILING = "ceiling"
    WALL = "wall"
    PLAYER = "player"
    NOZZLE = "nozzle"
    MOVABLE_BLOCK = "movable_block"
    TRIGGER_SOURCE = "trigger_source"  # 按钮和道具合并后的触发源（静态传感器）
    PORTAL = "portal"
    DESTINATION = "destination"
    TEXTURE = "texture"    # 只显示美术图，不参与碰撞
    ANIMATION = "animation"  # 只显示一段动画，不参与碰撞；预设和链接在 sprite 部件里
    SOUND = "sound"        # 只出声，不画不碰撞；预设和链接在 sound 部件里


class GameObject:
    def __init__(
        self,
        kind: GameObjectKind = GameObjectKind.UNKNOWN,
        body: Body | None = None,
        controller: Controller | None = None,
        render: RenderSpec | None = None,
        nozzle: Nozzle | None = None,
        trigger_source: TriggerSource | None = None,
        portal: Portal | None = None,
        triggers: TriggerSheet | None = None,
        interaction_state: int = 0,
        name: str = "",
        follow: str = "",
    ) -> None:
        self.kind: GameObjectKind = kind
        self.name: str = name                             # 关卡里的名字，供引用
        self.follow: str = follow                         # 跟哪个可移动方块一起动（名字），空表示不动
        self.body: Body | None = body                     # 物理部件
        self.controller: Controller | None = controller   # 运动部件
        self.render: RenderSpec | None = render           # 显示部件
        self.nozzle: Nozzle | None = nozzle                        # 风区参数
        self.trigger_source: TriggerSource | None = trigger_source  # 触发源参数
        self.portal: Portal | None = portal               # 传送门参数
        self.triggers: TriggerSheet | None = triggers     # 触发行为卡片，空表示不接触发器
        self.sprite = None                                # 动画对象的预设与链接（animation.sprite）
        self.sound = None                                 # 声音对象的预设与链接（sound.objects）
        self.interaction_state: int = interaction_state   # 交互状态，由系统写入
        self.events: set[str] = set()                     # 当前生效的事件名，由 TriggerSystem 写入

    def describe(self) -> str:
        parts = [
            name
            for name in ("body", "controller", "render", "nozzle", "trigger_source", "portal", "triggers")
            if getattr(self, name) is not None
        ]
        label = self.name or str(self.kind)
        return f"{label}({', '.join(parts) or 'data'})"

    def __repr__(self) -> str:
        return self.describe()
