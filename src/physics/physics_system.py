"""PhysicsSystem：一步之内先积分、再解算。积分结果单独存在时不构成有效状态。"""

from core.game_object import GameObject
from physics.body import Body
from world.world import World


class PhysicsSystem:
    def update(self, objects: list[GameObject], world: World, delta_seconds: float) -> None:
        for game_object in objects:
            body = game_object.body
            if body is None or body.is_sensor or body.is_static:
                continue
            self._integrate(body, world.gravity_acceleration_magnitude, delta_seconds)
            self._resolve(game_object, objects)

    def _integrate(self, body: Body, gravity: float, delta_seconds: float) -> None:
        """速度与位置：只做数学，不碰世界。"""
        body.velocity_y -= gravity * body.gravity_direction_sign * delta_seconds
        body.left += body.velocity_x * delta_seconds
        body.bottom += body.velocity_y * delta_seconds

    def _resolve(self, game_object: GameObject, objects: list[GameObject]) -> None:
        """约束：解除与其他 body 的重合，写 is_grounded 与穿透 flag。"""
        body = game_object.body
        for other in objects:
            other_body = other.body
            if other_body is None or other is game_object:
                continue
            if not self._is_solid_for(game_object, other):
                continue
            # 解算占位：求交并推出，写 is_grounded
        if game_object.controller is not None and body.is_grounded:
            game_object.controller.passes_through_planks = False

    def _is_solid_for(self, mover: GameObject, other: GameObject) -> bool:
        """对方是否挡住这个 mover：翻转穿透期间，可穿过的方块不挡。"""
        controller = mover.controller
        passes_through = controller is not None and controller.passes_through_planks
        if other.body.is_passable_during_flip and passes_through:
            return False
        return True
