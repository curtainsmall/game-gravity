"""MoverSystem：按触发者状态推进机关位置。"""


class MoverSystem:
    def update(self, objects, delta_seconds: float) -> None:
        for game_object in objects:
            if game_object.mover is None:
                continue
            # 读 mover.triggered_by.interaction_state，推进 body 位置
