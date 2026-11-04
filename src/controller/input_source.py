"""InputSource：玩家输入；InputState 是一帧的输入快照。"""

from controller.flip_rule import can_flip_gravity, flip_gravity


class InputState:
    def __init__(self, move_axis: int = 0, jump_pressed: bool = False, flip_pressed: bool = False) -> None:
        self.move_axis: int = move_axis          # -1 左，0 停，+1 右
        self.jump_pressed: bool = jump_pressed
        self.flip_pressed: bool = flip_pressed


class InputSource:
    MOVE_SPEED = 8.0      # 方块/秒
    JUMP_SPEED = 19.0     # 起跳速度，跳高由它与重力共同决定

    def advance(self, game_object, delta_seconds: float, input_state) -> None:
        body = game_object.body
        if body is None or input_state is None:
            return

        body.velocity_x = self.MOVE_SPEED * input_state.move_axis

        if input_state.flip_pressed and can_flip_gravity(body):
            flip_gravity(body, game_object.controller)

        if input_state.jump_pressed and body.is_grounded:
            # 起跳方向与重力方向相反
            body.velocity_y = self.JUMP_SPEED * body.gravity_direction_sign
