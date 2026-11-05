"""InputSource：玩家输入；InputState 是一帧的输入快照。

跳高按格数记（关卡设的初始值，变重道具会再降），起跳速度不查表：
用和物理同一套离散积分现算，重力与步长固定，反解一次就够。
"""

from controller.flip_rule import FLIP_AREA_OFFSETS_DEFAULT, can_flip_gravity, flip_gravity
from physics.ballistics import launch_speed
from world.world import GRAVITY_ACCELERATION


class InputState:
    def __init__(
        self, move_axis: int = 0, jump_pressed: bool = False, flip_pressed: bool = False
    ) -> None:
        self.move_axis: int = move_axis  # -1 左，0 停，+1 右
        self.jump_pressed: bool = jump_pressed
        self.flip_pressed: bool = flip_pressed


class InputSource:
    MOVE_SPEED_DEFAULT = 8.0  # 方块/秒

    JUMP_HEIGHT_DEFAULT = 2  # 默认跳 2 格
    JUMP_HEIGHT_MIN = 0      # 0 = 跳不起来

    move_speed = MOVE_SPEED_DEFAULT   # 关卡可以覆盖
    jump_height_blocks = JUMP_HEIGHT_DEFAULT

    # 翻转区：离关卡顶多少格才能翻（第一个向上、第二个向下），要配合关卡高度用
    flip_area_offsets = FLIP_AREA_OFFSETS_DEFAULT
    level_height_blocks = 0.0

    @classmethod
    def set_move_speed(cls, speed: float) -> None:
        """关卡给定的水平移动速度（方块/秒）。"""
        cls.move_speed = float(speed)

    @classmethod
    def set_flip_area(cls, offsets, level_height: float) -> None:
        """关卡给定的翻转区起点（离关卡顶的格数）和关卡高度（格）。"""
        cls.flip_area_offsets = (float(offsets[0]), float(offsets[1]))
        cls.level_height_blocks = float(level_height)

    @classmethod
    def jump_height(cls) -> int:
        return cls.jump_height_blocks

    @classmethod
    def jump_speed(cls, delta_seconds: float) -> float:
        """按当前跳高反解起跳速度：离散积分下要正好升到这么多格。"""
        return launch_speed(cls.jump_height_blocks, GRAVITY_ACCELERATION, delta_seconds)

    @classmethod
    def decrease_jump_height(cls) -> None:
        """变重：跳高降一格，到 0 不再降。"""
        cls.jump_height_blocks = max(cls.JUMP_HEIGHT_MIN, cls.jump_height_blocks - 1)

    @classmethod
    def set_jump_height(cls, height: int) -> None:
        """关卡给定的初始跳高（格）。"""
        cls.jump_height_blocks = max(cls.JUMP_HEIGHT_MIN, int(height))

    def advance(self, game_object, delta_seconds: float, input_state) -> None:
        body = game_object.body
        if body is None or input_state is None:
            return

        body.velocity_x = InputSource.move_speed * input_state.move_axis

        if input_state.flip_pressed and can_flip_gravity(
            body, InputSource.level_height_blocks, InputSource.flip_area_offsets
        ):
            flip_gravity(body, game_object.controller)

        if input_state.jump_pressed and body.is_grounded:
            # 起跳方向与重力方向相反
            body.velocity_y = InputSource.jump_speed(delta_seconds) * body.gravity_direction_sign
