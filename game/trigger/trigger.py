"""TriggerBehavior / TriggerSheet：触发行为卡片。

一条卡片就是「来源 + 行为 + 仅触发一次」：来源是按钮的名字，行为是一个事件名，
once 表示按下过一次就一直算生效。TriggerSystem 只负责看来源按没按下，把生效的行为名写进
GameObject.events；这个事件名是什么意思、该由谁去做，各系统自己读 events 认领
（ControllerSystem 认 "move"，RenderSystem 认 "hide" / "show"），这里不解释，也不碰组件。
"""


class TriggerBehavior:
    def __init__(self, source: str = "", behavior: str = "", once: bool = False) -> None:
        self.source: str = source        # 触发来源：按钮的名字
        self.behavior: str = behavior    # 行为名（事件名），由读 events 的系统认领
        self.once: bool = once           # 只触发一次：按下过一次就一直生效

    def __repr__(self) -> str:
        suffix = "（一次）" if self.once else ""
        return f"{self.source or '(无)'} → {self.behavior or '(无)'}{suffix}"


class TriggerSheet:
    def __init__(self, behaviors: list | None = None) -> None:
        self.behaviors: list[TriggerBehavior] = list(behaviors) if behaviors else []

    def __len__(self) -> int:
        return len(self.behaviors)
