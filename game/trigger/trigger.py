"""TriggerBehavior / TriggerSheet：触发行为卡片。

一张卡片是「来源 + 行为 + 模式」：来源是按钮的名字，行为是一个事件名，模式决定事件什么时候挂着。
    once    触发一次就一直生效（按下去就不再撤销）
    hold    按着才生效，松开就撤销
    switch  触发一下切换：生效和撤销之间来回翻
TriggerSystem 只负责看来源按没按下，把生效的行为名写进 GameObject.events；这个事件名是什么
意思、该由谁去做，各系统自己读 events 认领（ControllerSystem 认 "move"，RenderSystem 认
"hide" / "show"），这里不解释，也不碰组件。
"""

MODE_ONCE = "once"
MODE_HOLD = "hold"
MODE_SWITCH = "switch"
TRIGGER_MODES = (MODE_ONCE, MODE_HOLD, MODE_SWITCH)
MODE_LABELS = {MODE_ONCE: "一次", MODE_HOLD: "按住", MODE_SWITCH: "切换"}


def normalize_mode(value, fallback: str = MODE_HOLD) -> str:
    """把数据里的模式整理成三个值之一；写坏了就退回 fallback。"""
    mode = str(value or "").strip()
    return mode if mode in TRIGGER_MODES else fallback


class TriggerBehavior:
    def __init__(self, source: str = "", behavior: str = "", mode: str = MODE_HOLD) -> None:
        self.source: str = source        # 触发来源：按钮的名字
        self.behavior: str = behavior    # 行为名（事件名），由读 events 的系统认领
        self.mode: str = normalize_mode(mode)   # once / hold / switch

    def __repr__(self) -> str:
        suffix = f"（{MODE_LABELS[self.mode]}）"
        return f"{self.source or '(无)'} → {self.behavior or '(无)'}{suffix}"


class TriggerSheet:
    def __init__(self, behaviors: list | None = None) -> None:
        self.behaviors: list[TriggerBehavior] = list(behaviors) if behaviors else []

    def __len__(self) -> int:
        return len(self.behaviors)
