"""动画对象：预设 + 链接 + 跟随 + 播放。

动画对象是一个只显示、不碰撞的对象（和贴图同级）。它的位置尺寸是自己的；写了
follow 就记下加载时和目标对象的相对位置，之后一起平移（目标可以是玩家，写
"@player"）。显示哪一段剪辑看预设：

    general  只有一条剪辑，链接在 links.general.clip，不看任何状态
    player   四个动作（idle/run/jump/fall），动作来自玩家的物理状态；每个动作分左/右
             两个链接，空着的一侧用另一侧镜像

重力翻转时（目标就是玩家、且玩家倒挂）：先取相反方向的链接（朝右取左、朝左取右），
取不到再借本侧镜像，然后整体绕 z 轴旋转 180°；跟随玩家的通用预设也一起转。
这样朝右走、倒挂时显示的是另一侧的身体动画，并且仍然朝着运动方向。

链接里写的是动画库的键（见 animation.library）；键找不到、帧文件缺失都不画。
"""

from animation.clip import AnimationClip

PRESET_GENERAL = "general"
PRESET_PLAYER = "player"
GENERAL_CLIP = "clip"
PLAYER_ACTIONS = ("idle", "run", "jump", "fall")
SIDES = ("left", "right")
PLAYER_FOLLOW = ("@player", "player")


class AnimationSprite:
    """一个动画对象的播放状态：现在是什么动作、哪一侧、放到第几帧。"""

    def __init__(self, preset: str = PRESET_GENERAL, links: dict | None = None) -> None:
        self.preset: str = preset if preset in (PRESET_GENERAL, PRESET_PLAYER) else PRESET_GENERAL
        self.links: dict = links if isinstance(links, dict) else {}
        self.action: str = ""
        self.side: str = ""
        self.clip_key: str = ""
        self.frame_index: int = 0
        self.elapsed: float = 0.0

    def reset(self, action: str, side: str, clip_key: str) -> None:
        """换了动作、方向或剪辑：从第一帧重新放。"""
        if (action, side, clip_key) == (self.action, self.side, self.clip_key):
            return
        self.action, self.side, self.clip_key = action, side, clip_key
        self.frame_index = 0
        self.elapsed = 0.0


def state_of(body) -> str:
    """玩家当前的动作名：站住按有没有水平速度分；空中按速度相对重力方向分。

    翻转重力后起跳方向也反了，所以不能只看 velocity_y 的正负：
    「跳」是速度与重力同向（离开脚下那面），反过来就是下落。
    """
    if body.is_grounded:
        return "run" if body.velocity_x else "idle"
    if body.velocity_y * body.gravity_direction_sign > 0:
        return "jump"
    return "fall"


class AnimationSystem:
    """每步推进所有动画对象：先跟随摆位，再挑动作和剪辑，最后写渲染。"""

    def __init__(self, clips: dict[str, AnimationClip]) -> None:
        self.clips = clips
        self.objects: list = []
        self.targets: dict[int, object] = {}      # 动画对象 id → 跟随目标（None = 没跟到）
        self.followers: list = []                # (动画对象, 目标, 相对 x, 相对 y)
        self.player = None
        self.facing = 1                          # 玩家朝向：+1 右，-1 左；停下来保持

    def attach(self, objects: list, player) -> None:
        """场景建好后调一次：解析跟随目标，记下相对位置。"""
        self.player = player
        self.facing = 1
        self.objects = [
            game_object
            for game_object in objects
            if getattr(game_object, "sprite", None) is not None
        ]
        named = {}
        for game_object in objects:
            if game_object.name and game_object.body is not None:
                named.setdefault(game_object.name, game_object)
        self.followers = []
        self.targets = {}
        for game_object in self.objects:
            target = None
            follow = str(game_object.follow or "")
            if follow in PLAYER_FOLLOW:
                target = player
            elif follow:
                target = named.get(follow)
            self.targets[id(game_object)] = target
            body = game_object.body
            if target is not None and target.body is not None and body is not None:
                self.followers.append(
                    (
                        game_object,
                        target,
                        body.left - target.body.left,
                        body.bottom - target.body.bottom,
                    )
                )

    def update(self, delta_seconds: float) -> None:
        self._update_facing()
        self._follow()
        for game_object in self.objects:
            self._update_sprite(game_object, delta_seconds)

    def _update_facing(self) -> None:
        body = getattr(self.player, "body", None) if self.player is not None else None
        if body is None:
            return
        if body.velocity_x > 0.0:
            self.facing = 1
        elif body.velocity_x < 0.0:
            self.facing = -1

    def _follow(self) -> None:
        for game_object, target, offset_x, offset_y in self.followers:
            body = game_object.body
            if body is None or target.body is None:
                continue
            body.left = target.body.left + offset_x
            body.bottom = target.body.bottom + offset_y

    def _update_sprite(self, game_object, delta_seconds: float) -> None:
        sprite: AnimationSprite = game_object.sprite
        render = game_object.render
        if render is None:
            return
        target = self.targets.get(id(game_object))
        flipped = (
            target is self.player
            and self.player is not None
            and self.player.body is not None
            and self.player.body.gravity_direction_sign < 0
        )
        clip, mirror = self._resolve(game_object, sprite, flipped)
        if clip is None:
            render.texture_path = None
            return
        self._advance(sprite, clip, delta_seconds)
        render.texture_path = clip.frames[sprite.frame_index]
        # 倒挂时绕 z 轴转 180°；再按需水平镜像，合起来就是“先镜像再转”或“转后再镜像”
        render.texture_face = "down" if flipped else "up"
        render.texture_flip = mirror

    def _resolve(
        self, game_object, sprite: AnimationSprite, gravity_flipped: bool
    ) -> tuple:
        """这一帧要播的剪辑和要不要水平镜像；没有就 (None, False)。"""
        if sprite.preset == PRESET_GENERAL:
            key = _link_value(sprite.links.get("general"), GENERAL_CLIP)
            return self.clips.get(key) if key else None, False
        target = self.targets.get(id(game_object))
        if target is not None and target is self.player and self.player is not None:
            body = self.player.body
            action = state_of(body) if body is not None else "idle"
            side = "right" if self.facing > 0 else "left"
            if gravity_flipped:
                # 倒挂时看到的是身体另一侧：朝右取左、朝左取右
                side = "left" if side == "right" else "right"
        else:
            # 目标不是玩家：没有玩家那四个状态，退到站立；方向用右侧
            action, side = "idle", "right"
        pairs = sprite.links.get("player")
        pairs = pairs if isinstance(pairs, dict) else {}
        for candidate in (action, "idle", *PLAYER_ACTIONS):
            pair = pairs.get(candidate)
            if not isinstance(pair, dict):
                continue
            key = str(pair.get(side) or "")
            mirror = False
            if not key:
                other = "left" if side == "right" else "right"
                key = str(pair.get(other) or "")
                mirror = bool(key)
            if not key:
                continue
            clip = self.clips.get(key)
            if clip is not None:
                sprite.reset(candidate, side, key)
                return clip, mirror
        sprite.reset(action, side, "")
        return None, False

    @staticmethod
    def _advance(sprite: AnimationSprite, clip: AnimationClip, delta_seconds: float) -> None:
        count = len(clip.frames)
        if count <= 1:
            sprite.frame_index = 0
            return
        sprite.elapsed += max(0.0, delta_seconds)
        index = max(0, min(sprite.frame_index, count - 1))
        # 加一点余量：正好落在边界上算进下一帧，又不被浮点误差卡住
        while sprite.elapsed >= clip.hold(index) - 1e-9:
            sprite.elapsed = max(0.0, sprite.elapsed - clip.hold(index))
            if index + 1 < count:
                index += 1
            elif clip.loop:
                index = 0
            else:
                index = count - 1
                sprite.elapsed = 0.0
                break
        sprite.frame_index = index


def _link_value(pair, key: str) -> str:
    if not isinstance(pair, dict):
        return ""
    return str(pair.get(key) or "")
