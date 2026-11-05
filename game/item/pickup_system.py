"""PickupSystem：道具被玩家重叠后施加效果，每个道具只生效一次。"""

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
            if item.heavy:
                InputSource.decrease_jump_height()
