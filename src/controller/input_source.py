"""InputSource：玩家输入；InputState 是一帧的输入快照。"""

from controller.flip_rule import can_flip_gravity, flip_gravity


class InputState:
    def __init__(
        self, move_axis: int = 0, jump_pressed: bool = False, flip_pressed: bool = False
    ) -> None:
        self.move_axis: int = move_axis  # -1 左，0 停，+1 右
        self.jump_pressed: bool = jump_pressed
        self.flip_pressed: bool = flip_pressed


class InputSource:
    MOVE_SPEED = 8.0  # 方块/秒

    JUMP_LADDER_INDEX_DEFAULT = 4  # 默认 4 格

    # (目标跳高格数, 起跳速度)，重力 60、60 步/秒下按离散积分反解
    JUMP_LADDER: list[tuple[int, float]] = [
        (0, 0.000),  # 跳不起来
        (1, 11.500),
        (2, 16.059),
        (3, 19.500),
        (4, 22.435),
        (5, 25.038),
        (6, 27.357),
        (7, 29.500),
    ]
    jump_speed_index = JUMP_LADDER_INDEX_DEFAULT

    @classmethod
    def jump_height(cls) -> int:
        return cls.JUMP_LADDER[cls.jump_speed_index][0]

    @classmethod
    def jump_speed(cls) -> float:
        return cls.JUMP_LADDER[cls.jump_speed_index][1]

    @classmethod
    def decrease_jump_speed(cls) -> None:
        """变重：降一档，到底不再降。"""
        cls.jump_speed_index = max(0, cls.jump_speed_index - 1)

    @classmethod
    def reset_jump_speed(cls) -> None:
        """关卡重开时回到默认档位。"""
        cls.jump_speed_index = cls.JUMP_LADDER_INDEX_DEFAULT

    def advance(self, game_object, delta_seconds: float, input_state) -> None:
        body = game_object.body
        if body is None or input_state is None:
            return

        body.velocity_x = self.MOVE_SPEED * input_state.move_axis

        if input_state.flip_pressed and can_flip_gravity(body):
            flip_gravity(body, game_object.controller)

        if input_state.jump_pressed and body.is_grounded:
            # 起跳方向与重力方向相反
            body.velocity_y = InputSource.jump_speed() * body.gravity_direction_sign
