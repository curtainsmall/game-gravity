"""TriggerSystem：事件派发。

每帧把挂了 TriggerSheet 的对象求值一遍：哪张卡片正在生效（来源按着，或者是一次的卡片
已经按下过），就把那张卡片的行为名放进 game_object.events。它不知道行为名是什么意思，也不碰
任何组件——读 events 的系统各自认领。来源按名字解析一次就够了（场景建好时 attach）。
"""

from core.game_object import GameObject


class TriggerSystem:
    def __init__(self) -> None:
        self.sources: dict[str, GameObject] = {}   # 名字 → 来源对象
        self.sheets: list[GameObject] = []         # 挂了触发器的对象
        self.latched: set = set()                  # 已经按下过的「仅触发一次」卡片

    def attach(self, objects: list) -> None:
        """场景建好后调一次：解析来源名字，记住哪些对象有触发器。"""
        self.sources = {
            game_object.name: game_object for game_object in objects if game_object.name
        }
        self.sheets = [
            game_object for game_object in objects if game_object.triggers is not None
        ]
        self.latched = set()

    def update(self) -> None:
        """重算每个对象的生效事件集合；空集合表示一张卡片都没触发。"""
        for game_object in self.sheets:
            events: set[str] = set()
            for card in game_object.triggers.behaviors:
                source = self.sources.get(card.source)
                pressed = source is not None and source.interaction_state != 0
                if card.once and pressed:
                    self.latched.add(card)
                if pressed or card in self.latched:
                    events.add(card.behavior)
            game_object.events = events
