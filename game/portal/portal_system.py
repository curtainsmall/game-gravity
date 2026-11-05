"""PortalSystem：玩家踩到传送门本身就被送到目标门。

触发区就是门那块矩形，没有额外的范围。刚从某个门出来时，那个门（以及玩家落点压着
的门）在玩家离开它之前都不触发，所以走过去不会立刻被弹回来，得先走出去再进来。
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
        """门的矩形和玩家是否相交：门的 body 就是触发区。"""
        door = portal.body
        return (
            body.left < door.right
            and body.right > door.left
            and body.bottom < door.top
            and body.top > door.bottom
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
