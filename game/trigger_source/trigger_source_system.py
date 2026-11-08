"""TriggerSourceSystem：每帧更新所有触发源的「按下」状态和跳高效果。

物理系统已经把 interaction_state 采样好（玩家压在上面就是 1）。这里按模式处理：
    hold  压着就按下，松开撤销；跳高加成跟着加、跟着减
    once  第一次压到就一直是按下；跳高加成只加一次，之后不再撤
触发源上挂了物品时，第一次按下会把这个物品 id 交给调用方（Scene 再交给背包）；
之后松开也不会收回。TriggerSystem 只读 pressed，不关心模式；它对玩家没有任何直接影响。
"""

from controller.input_source import InputSource
from core.game_object import GameObject
from trigger_source.trigger_source import MODE_ONCE


class TriggerSourceSystem:
    def update(self, objects: list[GameObject]) -> list[str]:
        """更新状态，返回这一帧新解锁的物品 id（可能一次多个）。"""
        unlocked: list[str] = []
        for game_object in objects:
            source = game_object.trigger_source
            if source is None:
                continue
            overlapping = game_object.interaction_state != 0
            if source.mode == MODE_ONCE:
                if not source.pressed and overlapping:
                    source.pressed = True
                    self._engage(source, True)
                    self._unlock(source, unlocked)
                continue
            if overlapping != source.pressed:
                source.pressed = overlapping
                self._engage(source, overlapping)
                if overlapping:
                    self._unlock(source, unlocked)
        return unlocked

    @staticmethod
    def _unlock(source, unlocked: list[str]) -> None:
        """第一次按下时把物品交出去；同一个触发源只交一次。"""
        if source.item and not source.item_unlocked:
            source.item_unlocked = True
            unlocked.append(source.item)

    @staticmethod
    def _engage(source, on: bool) -> None:
        """跳高加成的加减：0 也要把 engaged 记对，方便以后调试。"""
        if source.jump_offset != 0.0:
            InputSource.adjust_jump_height(
                source.jump_offset if on else -source.jump_offset
            )
        source.engaged = on
