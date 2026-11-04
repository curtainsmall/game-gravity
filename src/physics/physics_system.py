"""PhysicsSystem：一步之内先积分、再解算。积分结果单独存在时不构成有效状态。"""


class PhysicsSystem:
    def update(self, objects, world, delta_seconds: float) -> None:
        for game_object in objects:
            body = game_object.body
            if body is None or body.is_sensor or body.is_static:
                continue
            self._integrate(body, world.gravity_acceleration_magnitude, delta_seconds)
            self._resolve(game_object, world)

    def _integrate(self, body, gravity: float, delta_seconds: float) -> None:
        """速度与位置：只做数学，不碰世界。"""
        body.velocity_y -= gravity * body.gravity_direction_sign * delta_seconds
        body.left += body.velocity_x * delta_seconds
        body.bottom += body.velocity_y * delta_seconds

    def _resolve(self, game_object, world) -> None:
        """约束：解除与其他 body 的重合，写 is_grounded 与穿透 flag。"""
        body = game_object.body
        # 解算占位：与静态 body、可移动方块求交并推出
        if game_object.controller is not None and body.is_grounded:
            game_object.controller.passes_through_planks = False
