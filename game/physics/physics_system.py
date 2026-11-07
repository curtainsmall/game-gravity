"""PhysicsSystem：先积分速度、按最浅的一面推开已有的重叠，再按轴解算位移，
最后采样传感器并施加风力。"""

from core.game_object import GameObject
from physics.ballistics import launch_speed
from physics.body import Body
from world.world import World

OVERLAP_RESOLVE_PASSES = 4   # 重叠兜底最多推几轮，夹在两个物体中间时够用


class PhysicsSystem:
    def update(self, objects: list[GameObject], world: World, delta_seconds: float) -> None:
        gravity = world.gravity_acceleration_magnitude
        for game_object in objects:
            body = game_object.body
            if body is None or body.is_sensor or body.is_static:
                continue

            body.is_grounded = False
            body.velocity_y -= gravity * body.gravity_direction_sign * delta_seconds

            solids = self._solids_for(game_object, objects)
            # 先处理已经压在身体里的物体（比如被机关挤进来）：按最浅的一面推出去，
            # 再去走这一帧的位移；否则竖直解算会先按速度方向把人顶到别的面上。
            self._resolve_overlaps(body, solids)
            body.is_grounded = False          # 推出来之后重新由这一帧的位移判定站没站稳
            self._move_along_x(body, solids, body.velocity_x * delta_seconds)
            self._move_along_y(body, solids, body.velocity_y * delta_seconds)
            self._resolve_overlaps(body, solids)

            if body.is_grounded and not self._overlaps_passable(body, objects):
                body.is_flipping = False            # 落过地、也离开木板了：穿板许可用完

        self._sample_sensors(objects, gravity, delta_seconds)

    def _resolve_overlaps(self, body: Body, solids: list[Body]) -> None:
        """还和实心体重叠时，沿穿透最浅的那一面把身体推出去。

        正常移动时轴分离的解算已经贴面停住；这里兜底处理被移动方块挤进来、
        出生就重叠这类残留情况。多推几轮，夹在两个物体中间也能稳定下来。
        """
        for _ in range(OVERLAP_RESOLVE_PASSES):
            solid = next((other for other in solids if self._overlaps(body, other)), None)
            if solid is None:
                return
            self._push_out(body, solid)

    def _push_out(self, body: Body, solid: Body) -> None:
        """沿碰撞面法线推：每轴挑近的一侧，再挑穿透更浅的一轴。"""
        push_left = body.right - solid.left
        push_right = solid.right - body.left
        push_down = body.top - solid.bottom
        push_up = solid.top - body.bottom
        horizontal = min(push_left, push_right)
        vertical = min(push_down, push_up)
        if horizontal <= vertical:
            if push_left <= push_right:
                body.left = solid.left - body.width
            else:
                body.left = solid.right
            body.velocity_x = 0.0
            return
        if push_down <= push_up:
            body.bottom = solid.bottom - body.height
            if body.gravity_direction_sign < 0:
                body.is_grounded = True          # 重力向上：头顶着天花板即站立
        else:
            body.bottom = solid.top
            if body.gravity_direction_sign > 0:
                body.is_grounded = True          # 重力向下：脚下踩着东西即站立
        body.velocity_y = 0.0

    def _overlaps_passable(self, body: Body, objects: list[GameObject]) -> bool:
        """还压在某块可穿木板上没有：人卡在木板里时不能立刻恢复碰撞，否则会被挤得弹起来。"""
        return any(
            other.body is not None
            and other.body is not body
            and other.body.is_passable_during_flip
            and self._overlaps(body, other.body)
            for other in objects
        )

    def _sample_sensors(self, objects: list[GameObject], gravity: float, delta_seconds: float) -> None:
        """解算之后采样：传感器是否与运动物体重叠，风区给出飞向目标的初速度。"""
        movers = [
            (other, other.body)
            for other in objects
            if other.body is not None and not other.body.is_static and not other.body.is_sensor
        ]
        for game_object in objects:
            body = game_object.body
            if body is None or not body.is_sensor:
                continue

            overlapping = [(other, mover_body) for other, mover_body in movers if self._overlaps(body, mover_body)]
            if game_object.nozzle is not None:
                for mover_object, _ in overlapping:
                    self._apply_nozzle(game_object, mover_object, gravity, delta_seconds)
            game_object.interaction_state = 1 if overlapping else 0

    def _apply_nozzle(
        self,
        nozzle_object: GameObject,
        mover_object: GameObject,
        gravity: float,
        delta_seconds: float,
    ) -> None:
        """在风区内把速度设成「从当前位置正好飞到目标」的值。

        竖向风区推 velocity_y（起跳那种惯性会留着）；横向风区只能推 velocity_x，
        下一步控制来源会把它覆盖掉，所以效果是「待在风里就被往那个方向推」。
        """
        nozzle = nozzle_object.nozzle
        body = mover_object.body
        target_x, target_y = nozzle.target
        if nozzle.vertical:
            if target_y > body.bottom:
                body.velocity_y = launch_speed(target_y - body.bottom, gravity, delta_seconds)
            elif target_y < body.bottom:
                body.velocity_y = -launch_speed(body.bottom - target_y, gravity, delta_seconds)
            return
        if target_x > body.right:
            body.velocity_x = launch_speed(target_x - body.right, gravity, delta_seconds)
        elif target_x < body.left:
            body.velocity_x = -launch_speed(body.left - target_x, gravity, delta_seconds)

    def _solids_for(self, mover: GameObject, objects: list[GameObject]) -> list[Body]:
        solids: list[Body] = []
        for other in objects:
            other_body = other.body
            if other_body is None or other is mover or other_body.is_sensor:
                continue
            if not self._is_solid_for(mover, other):
                continue
            solids.append(other_body)
        return solids

    def _is_solid_for(self, mover: GameObject, other: GameObject) -> bool:
        """对方是否挡住这个 mover：刚翻过还没落地时，木板不挡路。"""
        if other.body.is_passable_during_flip and mover.body.is_flipping:
            return False
        return True

    def _move_along_x(self, body: Body, solids: list[Body], delta: float) -> None:
        if delta == 0.0:
            return
        body.left += delta
        for solid in solids:
            if not self._overlaps(body, solid):
                continue
            body.left = solid.left - body.width if delta > 0 else solid.right
            body.velocity_x = 0.0

    def _move_along_y(self, body: Body, solids: list[Body], delta: float) -> None:
        if delta == 0.0:
            return
        body.bottom += delta
        for solid in solids:
            if not self._overlaps(body, solid):
                continue
            if delta > 0:
                body.bottom = solid.bottom - body.height
                if body.gravity_direction_sign < 0:
                    body.is_grounded = True      # 重力向上：头顶着天花板即站立
            else:
                body.bottom = solid.top
                if body.gravity_direction_sign > 0:
                    body.is_grounded = True      # 重力向下：脚下踩着东西即站立
            body.velocity_y = 0.0

    @staticmethod
    def _overlaps(a: Body, b: Body) -> bool:
        return a.left < b.right and a.right > b.left and a.bottom < b.top and a.top > b.bottom
