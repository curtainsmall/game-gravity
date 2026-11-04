"""TriggerSource：由触发者状态驱动的机关，位置被直接改写，不吃物理。"""

from core.game_object import GameObject


class TriggerSource:
    """沿一个单位轴前进固定距离；触发者状态决定目标是走满还是归零。"""

    def __init__(
        self,
        triggered_by: GameObject | None = None,
        axis: tuple[float, float] = (0.0, 1.0),
        distance: float = 3.0,
        speed: float = 4.0,
    ) -> None:
        self.triggered_by: GameObject | None = triggered_by
        self.axis: tuple[float, float] = axis      # 单位向量
        self.distance: float = distance            # 方块
        self.speed: float = speed                  # 方块/秒
        self.progress: float = 0.0                 # 0 = 起点，1 = 走满
        self.origin: tuple[float, float] | None = None

    def advance(self, game_object: GameObject, delta_seconds: float, input_state: object | None) -> None:
        body = game_object.body
        if self.origin is None:
            self.origin = (body.left, body.bottom)

        target = 1.0 if self._is_triggered() else 0.0
        step = self.speed * delta_seconds / self.distance if self.distance else 1.0
        if self.progress < target:
            self.progress = min(target, self.progress + step)
        elif self.progress > target:
            self.progress = max(target, self.progress - step)

        travel = self.progress * self.distance
        body.left = self.origin[0] + self.axis[0] * travel
        body.bottom = self.origin[1] + self.axis[1] * travel

    def _is_triggered(self) -> bool:
        return self.triggered_by is not None and self.triggered_by.interaction_state != 0
