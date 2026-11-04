"""InputSource：玩家输入。"""

from core.game_object import GameObject


class InputSource:
    """读输入，改写水平速度；按下翻转键且位置允许时翻转重力。"""

    def advance(self, game_object: GameObject, delta_seconds: float, input_state: object | None) -> None:
        """接入输入后：按 input_state 写 body.velocity_x，按翻转键调用 flip_gravity。"""
