"""TriggerSource：由若干触发者驱动的机关，位置被直接改写，不吃物理。"""

import math


class TriggerSource:
    """沿固定偏移前进；任一触发者被按下就去目标，全部松开就回原位。"""

    SPEED = 4.0  # 方块/秒

    def __init__(self, triggers=None, offset: tuple[float, float] = (0.0, 0.0)) -> None:
        self.triggers: list = list(triggers) if triggers else []
        self.offset: tuple[float, float] = (float(offset[0]), float(offset[1]))
        self.progress: float = 0.0            # 0 = 原点，1 = 走满
        self.origin: tuple[float, float] | None = None

    def advance(self, game_object, delta_seconds: float, input_state) -> None:
        body = game_object.body
        if self.origin is None:
            self.origin = (body.left, body.bottom)

        distance = math.hypot(*self.offset)
        step = self.SPEED * delta_seconds / distance if distance else 1.0
        target = 1.0 if self._is_triggered() else 0.0
        if self.progress < target:
            self.progress = min(target, self.progress + step)
        elif self.progress > target:
            self.progress = max(target, self.progress - step)

        body.left = self.origin[0] + self.offset[0] * self.progress
        body.bottom = self.origin[1] + self.offset[1] * self.progress

    def _is_triggered(self) -> bool:
        return any(getattr(trigger, "interaction_state", 0) != 0 for trigger in self.triggers)
