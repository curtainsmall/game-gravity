"""Follower：贴图挂在可移动方块上，跟着它一起动。

关卡的 textures 条目可以写 follow: 可移动方块的名字。加载场景时把两者当时的相对位置
记下来；之后每帧控制器写完方块的新位置，再把贴图摆回那个相对位置，图和方块就不会走散。
名字没写、找不到或者方块没名字的，就当普通贴图，留在原地。
"""

from core.game_object import GameObject, GameObjectKind


class Follower:
    """一张贴图跟着一个可移动方块：位置 = 方块位置 + 加载时的相对偏移。"""

    def __init__(self, texture: GameObject, block: GameObject) -> None:
        self.texture = texture
        self.block = block
        self.offset_x = texture.body.left - block.body.left
        self.offset_y = texture.body.bottom - block.body.bottom

    def update(self) -> None:
        self.texture.body.left = self.block.body.left + self.offset_x
        self.texture.body.bottom = self.block.body.bottom + self.offset_y


class FollowSystem:
    def __init__(self) -> None:
        self.followers: list[Follower] = []

    def attach(self, objects: list) -> None:
        """按名字把贴图挂到可移动方块上；场景建好之后调一次。"""
        blocks: dict[str, GameObject] = {}
        for game_object in objects:
            if game_object.kind != GameObjectKind.MOVABLE_BLOCK or not game_object.name:
                continue
            blocks.setdefault(game_object.name, game_object)
        self.followers = []
        for game_object in objects:
            if game_object.kind != GameObjectKind.TEXTURE:
                continue
            block = blocks.get(game_object.follow)
            if block is None or game_object.body is None or block.body is None:
                continue
            self.followers.append(Follower(game_object, block))

    def update(self) -> None:
        """控制器写完方块位置之后调：贴图跟着摆过去。"""
        for follower in self.followers:
            follower.update()
