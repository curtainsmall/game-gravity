"""ControllerSystem：读输入、改写水平速度、处理重力翻转。"""


class ControllerSystem:
    def update(self, objects, input_state, delta_seconds: float) -> None:
        for game_object in objects:
            controller = game_object.controller
            if controller is None:
                continue
            # 输入接入后：按 input_state 写 body.velocity_x，按 can_flip_gravity 翻转
