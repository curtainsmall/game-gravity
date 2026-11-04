"""PhysicsSystem：先积分、再解算，最后采样传感器并施加风力。"""

from core.game_object import GameObject
from fan.fan import launch_speed
from physics.body import Body
from world.world import World


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
            self._move_along_x(body, solids, body.velocity_x * delta_seconds)
            self._move_along_y(body, solids, body.velocity_y * delta_seconds)

            if game_object.controller is not None and body.is_grounded:
                game_object.controller.passes_through_planks = False
                game_object.controller.fan_boost_used = False

        self._sample_sensors(objects, gravity, delta_seconds)

    def _sample_sensors(self, objects: list[GameObject], gravity: float, delta_seconds: float) -> None:
        """解算之后采样：传感器是否与运动物体重叠，风扇在进入时施加初速度。"""
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
            entered = game_object.interaction_state == 0 and bool(overlapping)
            if entered and game_object.fan is not None:
                for mover_object, _ in overlapping:
                    self._apply_fan(game_object, mover_object, gravity, delta_seconds)
            game_object.interaction_state = 1 if overlapping else 0

    def _apply_fan(self, fan_object: GameObject, mover_object: GameObject, gravity: float, delta_seconds: float) -> None:
        """进入风区时给一次初速度，使其抛物线正好到达风区远端；一次滞空只给一次。"""
        fan = fan_object.fan
        body = mover_object.body
        controller = mover_object.controller
        if controller is not None and controller.fan_boost_used:
            return
        target_y = fan.target_y
        if fan.power > 0 and body.bottom < target_y:
            body.velocity_y = launch_speed(target_y - body.bottom, gravity, delta_seconds)
        elif fan.power < 0 and body.bottom > target_y:
            body.velocity_y = -launch_speed(body.bottom - target_y, gravity, delta_seconds)
        else:
            return
        body.is_grounded = False
        if controller is not None:
            controller.fan_boost_used = True

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
        """对方是否挡住这个 mover：翻转穿透期间，可穿过的方块不挡。"""
        controller = mover.controller
        passes_through = controller is not None and controller.passes_through_planks
        if other.body.is_passable_during_flip and passes_through:
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
