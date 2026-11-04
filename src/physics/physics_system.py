"""PhysicsSystem：先积分、再解算。积分结果单独存在时不构成有效状态。"""

from core.game_object import GameObject
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
