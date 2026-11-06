"""ControllerSystem：推进有 controller 的对象。

有 source 的按来源推进（玩家输入）；没有 source 的是可移动方块：系统内部记着原点和进度，
看 events 里有没有 "move"，有就沿 offset 走，没有就回原点。只触发一次的卡片由 TriggerSystem
一直把事件挂住，所以这里不用再管 once。
"""

import math

from core.game_object import GameObject

MOVE_EVENT = "move"      # 可移动方块认领的事件名
MOVE_SPEED = 4.0         # 格/秒


class ControllerSystem:
    def __init__(self) -> None:
        # 可移动方块的运行状态。对象在场景里一直活着，可以直接拿它当键
        self.origins: dict[GameObject, tuple[float, float]] = {}
        self.progresses: dict[GameObject, float] = {}

    def update(self, objects: list[GameObject], input_state, delta_seconds: float) -> None:
        for game_object in objects:
            controller = game_object.controller
            if controller is None:
                continue
            if controller.source is not None:
                controller.source.advance(game_object, delta_seconds, input_state)
            else:
                self._advance_move(game_object, controller, delta_seconds)

    def _advance_move(self, game_object, controller, delta_seconds: float) -> None:
        """沿 offset 推进：有 "move" 事件去目标点，没有就回原点。"""
        body = game_object.body
        if body is None:
            return
        origin = self.origins.setdefault(game_object, (body.left, body.bottom))

        distance = math.hypot(*controller.offset)
        step = MOVE_SPEED * delta_seconds / distance if distance else 1.0
        target = 1.0 if MOVE_EVENT in game_object.events else 0.0
        progress = self.progresses.get(game_object, 0.0)
        if progress < target:
            progress = min(target, progress + step)
        elif progress > target:
            progress = max(target, progress - step)
        self.progresses[game_object] = progress

        body.left = origin[0] + controller.offset[0] * progress
        body.bottom = origin[1] + controller.offset[1] * progress
