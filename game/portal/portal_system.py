"""PortalSystem：玩家踩进传送门的触发区就被送到目标门。

刚从某个门出来时，那个门（以及玩家落点压着的门）在玩家离开触发区之前都不触发，
所以走过去不会立刻被弹回来，得先走出去再进来。
"""

from core.game_object import GameObject
from portal.portal import exit_offset


class PortalSystem:
    def __init__(self) -> None:
        self.blocked: set[int] = set()   # 刚出来的门（按对象 id），离开触发区才解锁

    def update(self, objects: list[GameObject], player: GameObject | None) -> None:
        if player is None or player.body is None:
            return
        portals = [game_object for game_object in objects if game_object.portal is not None]
        if not portals:
            return
        portals_by_name = {portal.name: portal for portal in portals if portal.name}

        # 玩家已经走出这些门的触发区：解锁
        for portal in portals:
            if id(portal) in self.blocked and not self._overlaps(portal, player.body):
                self.blocked.discard(id(portal))

        for portal in portals:
            if id(portal) in self.blocked:
                continue
            target = portals_by_name.get(portal.portal.target)
            if target is None or target is portal:
                continue                      # 没设目标、目标不存在或指向自己：不传送
            if not self._overlaps(portal, player.body):
                continue
            self._teleport(player.body, target)
            # 落地时压着的门全都先锁上：不然会立刻被再传送一次
            for other in portals:
                if self._overlaps(other, player.body):
                    self.blocked.add(id(other))
            return                            # 一步最多穿一次门

    @staticmethod
    def _overlaps(portal: GameObject, body) -> bool:
        left, bottom, right, top = portal.portal.trigger_bounds(portal.body)
        return (
            body.left < right
            and body.right > left
            and body.bottom < top
            and body.top > bottom
        )

    @staticmethod
    def _teleport(body, target: GameObject) -> None:
        """把玩家放到目标门中心，再沿门的朝向挪出去一点。"""
        target_body = target.body
        offset_x, offset_y = exit_offset(target.portal.face)
        center_x = target_body.left + target_body.width / 2.0 + offset_x
        center_y = target_body.bottom + target_body.height / 2.0 + offset_y
        body.left = center_x - body.width / 2.0
        body.bottom = center_y - body.height / 2.0
