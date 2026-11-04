"""ControllerSystem：按来源对象推进有 controller 的对象。"""

from core.game_object import GameObject


class ControllerSystem:
    def update(self, objects: list[GameObject], input_state, delta_seconds: float) -> None:
        for game_object in objects:
            controller = game_object.controller
            if controller is None or controller.source is None:
                continue
            controller.source.advance(game_object, delta_seconds, input_state)
