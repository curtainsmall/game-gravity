"""ItemSystem：道具的触发状态。

每帧看玩家和道具重叠没有（物理系统已经把 interaction_state 采样好）：
    once    第一次重叠就触发并禁用：triggered 一直为真，跳高加成一直保留
    persist 重叠期间算触发（加成生效），离开就撤销，再进来算一次新触发
加成是加在 InputSource 当前跳高上的：触发时加、撤销时减；多个道具同时在触发
状态时自然叠加，各自撤销时只减自己那一份。
"""

from controller.input_source import InputSource
from core.game_object import GameObject
from item.item import MODE_PERSIST


class ItemSystem:
    def update(self, objects: list[GameObject]) -> None:
        for game_object in objects:
            item = game_object.item
            if item is None:
                continue
            overlapping = game_object.interaction_state != 0
            if item.mode == MODE_PERSIST:
                if overlapping and not item.triggered:
                    self._set_triggered(item, True)
                elif not overlapping and item.triggered:
                    self._set_triggered(item, False)
            elif not item.disabled and overlapping:
                item.disabled = True
                self._set_triggered(item, True)

    @staticmethod
    def _set_triggered(item, triggered: bool) -> None:
        item.triggered = triggered
        InputSource.adjust_jump_height(item.jump_offset if triggered else -item.jump_offset)
