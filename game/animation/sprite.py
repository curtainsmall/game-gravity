"""动画对象：预设 + 链接 + 跟随 + 播放。

动画对象是一个只显示、不碰撞的对象（和贴图同级）。它的位置尺寸是自己的；写了
follow 就记下加载时和目标对象的相对位置，之后一起平移（目标可以是玩家，写
"@player"）。显示哪一段剪辑看预设：

    general  只有一条剪辑，链接在 links.general.clip，不看任何状态，播一遍就停
    player   六个动作，动作来自玩家（或跟随对象）的物理状态；每个动作分左/右两个
             链接，空着的一侧用另一侧镜像：
                 idle / run            站在地上（停 / 走）
                 takeoff               刚离开地面往上跳的一小段（一次）
                 raise                 还在上升（循环）
                 fall                  下落（循环）
                 landing               刚落地的一小段（一次）

循环由动作决定，不再写在链接上：idle / run / raise / fall 播完从头再来，
takeoff / landing 播一遍停在最后一帧，时长由 TAKEOFF_SECONDS / LANDING_SECONDS 管。

重力翻转时（目标就是玩家、且玩家倒挂）：先取相反方向的链接（朝右取左、朝左取右），
取不到再借本侧镜像，然后整体绕 z 轴旋转 180°；跟随玩家的通用预设也一起转。
这样朝右走、倒挂时显示的是另一侧的身体动画，并且仍然朝着运动方向。

链接里写的是动画库的键（见 animation.library）；老数据把上升写在 jump 里，
读链接时当作 raise 的兜底，链接还可以是直接写键的字符串。键找不到、帧文件缺失都不画。
"""

from animation.clip import AnimationClip

PRESET_GENERAL = "general"
PRESET_PLAYER = "player"
PLAYER_ACTIONS = ("idle", "run", "takeoff", "raise", "fall", "landing")
# 持续动作：剪辑播完从头再来；不在表里的（takeoff / landing）只播一次
LOOP_ACTIONS = frozenset({"idle", "run", "raise", "fall"})
SIDES = ("left", "right")
PLAYER_FOLLOW = ("@player", "player")
TAKEOFF_SECONDS = 0.10      # 起跳动作占多久
LANDING_SECONDS = 0.15      # 落地动作占多久


def loop_for(action: str) -> bool:
    """这个动作要不要循环。"""
    return action in LOOP_ACTIONS


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


class PlayerMotion:
    """玩家的动作状态机：把物理状态翻译成六个动作之一。

    只看三样东西：站在地上没有、水平速度、垂直速度相对重力的方向（上升还是下落）。
    起跳在「刚离开地面并且还在上升」的那一帧开始，落地在「刚碰到地面」的那一帧开始；
    两个都是短计时，计完回到 idle / run。重力翻转后上升/下落按新的重力方向算。
    """

    def __init__(self) -> None:
        self.grounded: bool = True       # 上一帧站没站在地上
        self.takeoff_left: float = 0.0
        self.landing_left: float = 0.0
        self.action: str = "idle"

    def update(self, body, delta_seconds: float) -> str:
        if body is None:
            return self.action
        step = max(0.0, delta_seconds)
        grounded = bool(body.is_grounded)
        rising = body.velocity_y * body.gravity_direction_sign > 0.0
        if grounded:
            self.takeoff_left = 0.0
            if not self.grounded:
                self.landing_left = LANDING_SECONDS      # 刚落地，从头计时
            self.landing_left = max(0.0, self.landing_left - step)
            if self.landing_left > 0.0:
                self.action = "landing"
            else:
                self.action = "run" if body.velocity_x else "idle"
        else:
            self.landing_left = 0.0
            if self.grounded and rising:
                self.takeoff_left = TAKEOFF_SECONDS      # 刚起跳
            self.takeoff_left = max(0.0, self.takeoff_left - step)
            if self.takeoff_left > 0.0 and rising:
                self.action = "takeoff"
            else:
                self.takeoff_left = 0.0
                self.action = "raise" if rising else "fall"
        self.grounded = grounded
        return self.action


class AnimationSystem:
    """每步推进所有动画对象：先跟随摆位，再挑动作和剪辑，最后写渲染。"""

    def __init__(self, clips: dict[str, AnimationClip]) -> None:
        self.clips = clips
        self.objects: list = []
        self.targets: dict[int, object] = {}      # 动画对象 id → 跟随目标（None = 没跟到）
        self.followers: list = []                # (动画对象, 目标, 相对 x, 相对 y)
        self.player = None
        self.facing = 1                          # 玩家朝向：+1 右，-1 左；停下来保持
        self.motion = PlayerMotion()

    def attach(self, objects: list, player) -> None:
        """场景建好后调一次：解析跟随目标，记下相对位置。"""
        self.player = player
        self.facing = 1
        self.motion = PlayerMotion()
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
        action = self._player_action(delta_seconds)
        for game_object in self.objects:
            self._update_sprite(game_object, delta_seconds, action)

    def _player_action(self, delta_seconds: float) -> str:
        body = getattr(self.player, "body", None) if self.player is not None else None
        if body is None:
            return "idle"
        return self.motion.update(body, delta_seconds)

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

    def _update_sprite(
        self, game_object, delta_seconds: float, player_action: str
    ) -> None:
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
        clip, mirror, loop = self._resolve(game_object, sprite, player_action, flipped)
        if clip is None:
            render.texture_path = None
            return
        self._advance(sprite, clip, delta_seconds, loop)
        render.texture_path = clip.frames[sprite.frame_index]
        # 倒挂时绕 z 轴转 180°；再按需水平镜像，合起来就是“先镜像再转”或“转后再镜像”
        render.texture_face = "down" if flipped else "up"
        render.texture_flip = mirror

    def _resolve(
        self,
        game_object,
        sprite: AnimationSprite,
        player_action: str,
        gravity_flipped: bool,
    ) -> tuple:
        """这一帧要播的剪辑、要不要水平镜像、要不要循环；没有就 (None, False, True)。"""
        if sprite.preset == PRESET_GENERAL:
            key = _link_key(sprite.links.get("general"))
            clip = self.clips.get(key) if key else None
            if clip is None:
                return None, False, True
            return clip, False, False          # 通用预设播一遍就停
        target = self.targets.get(id(game_object))
        if target is not None and target is self.player and self.player is not None:
            action = player_action
            side = "right" if self.facing > 0 else "left"
            if gravity_flipped:
                # 倒挂时看到的是身体另一侧：朝右取左、朝左取右
                side = "left" if side == "right" else "right"
        else:
            # 目标不是玩家：没有动作状态，退到站立；方向用右侧
            action, side = "idle", "right"
        pairs = sprite.links.get("player")
        pairs = pairs if isinstance(pairs, dict) else {}
        for candidate in _candidates(action):
            pair = pairs.get(candidate)
            if not isinstance(pair, dict):
                continue
            key = _link_key(pair.get(side))
            mirror = False
            if not key:
                other = "left" if side == "right" else "right"
                key = _link_key(pair.get(other))
                mirror = bool(key)
            if not key:
                continue
            clip = self.clips.get(key)
            if clip is not None:
                sprite.reset(candidate, side, key)
                return clip, mirror, loop_for(action)
        sprite.reset(action, side, "")
        return None, False, True

    @staticmethod
    def _advance(
        sprite: AnimationSprite, clip: AnimationClip, delta_seconds: float, loop: bool
    ) -> None:
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
            elif loop:
                index = 0
            else:
                index = count - 1
                sprite.elapsed = 0.0
                break
        sprite.frame_index = index


def _candidates(action: str) -> tuple:
    """挑链接的顺序：先要的动作，再兜底到站立，最后所有动作都试一遍。

    老数据把上升写在 jump 里，raise 找不到时也去那儿借。
    """
    if action == "raise":
        return ("raise", "jump", "idle", *PLAYER_ACTIONS)
    return (action, "idle", *PLAYER_ACTIONS)


def _link_key(value) -> str:
    """一条链接 → 剪辑键：新写法是 {"clip": 键}，老数据直接写字符串。"""
    if isinstance(value, dict):
        return str(value.get("clip") or "")
    return str(value or "")
