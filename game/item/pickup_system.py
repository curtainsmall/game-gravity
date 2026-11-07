"""PickupSystem：道具被玩家重叠后施加效果，每个道具只生效一次。

效果是给玩家的跳高加一个偏移量（道具自己带 jump_offset），由 InputSource 夹到
[0, 关卡高度 - 1]，pickup 这一层不管范围。
"""

from controller.input_source import InputSource
from core.game_object import GameObject


class PickupSystem:
    def update(self, objects: list[GameObject]) -> None:
        for game_object in objects:
            item = game_object.item
            if item is None or item.consumed:
                continue
            if game_object.interaction_state == 0:
                continue
            item.consumed = True
            InputSource.adjust_jump_height(item.jump_offset)
