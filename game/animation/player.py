"""PlayerAnimator：玩家的帧动画。

状态词汇固定，和编辑器里那几页一一对应：
    idle 站立 / run 移动 / jump 上升 / fall 下落 / flip 翻转（重力朝上）
每个状态分左右两套（朝向）：当前朝向那一套有帧就用它；空着就用另一侧的帧镜像；
两边都没有就退到 idle（同样先本侧、再另一侧镜像）；idle 也没有就不画贴图。
每帧的停留时间来自剪辑自己的 holds。每次 update 把当前帧路径和镜像标记写进 RenderSpec。
"""

PLAYER_STATES = ("idle", "run", "jump", "fall", "flip")
PLAYER_SIDES = ("right", "left")


class PlayerAnimator:
    def __init__(self, player, clips: dict | None = None) -> None:
        self.player = player
        self.clips: dict = clips or {}     # 状态名 → {"right": AnimationClip, "left": AnimationClip}
        self.state: str = ""
        self.frame_index: int = 0
        self.elapsed: float = 0.0
        self.facing: int = 1      # +1 朝右，-1 朝左

    def update(self, delta_seconds: float) -> None:
        body = self.player.body if self.player is not None else None
        if body is None:
            return
        state = self.state_of(body)
        if state != self.state:
            self.state = state
            self.frame_index = 0
            self.elapsed = 0.0
        if body.velocity_x > 0.0:
            self.facing = 1
        elif body.velocity_x < 0.0:
            self.facing = -1

        side = "right" if self.facing > 0 else "left"
        clip, mirror = self._resolve(state, side)
        render = self.player.render
        if render is None or clip is None:
            if render is not None:
                render.texture_path = None
            return

        self._advance(clip, delta_seconds)
        render.texture_path = clip.frames[self.frame_index]
        render.texture_face = "up"
        render.texture_flip = mirror

    def _resolve(self, state: str, side: str):
        """(剪辑, 要不要镜像)：本侧有就用本侧；空着用另一侧并镜像；再退到 idle。"""
        other = "left" if side == "right" else "right"
        for name in (state, "idle"):
            sides = self.clips.get(name) or {}
            clip = sides.get(side)
            if clip is not None and clip.frames:
                return clip, False
            clip = sides.get(other)
            if clip is not None and clip.frames:
                return clip, True
        return None, False

    @staticmethod
    def state_of(body) -> str:
        """当前状态名：翻转优先，然后按站没站住、上下速度分。"""
        if body.gravity_direction_sign < 0:
            return "flip"
        if body.is_grounded:
            return "run" if body.velocity_x else "idle"
        return "jump" if body.velocity_y > 0 else "fall"

    def _advance(self, clip, delta_seconds: float) -> None:
        count = len(clip.frames)
        if count <= 1:
            self.frame_index = 0
            return
        self.elapsed += delta_seconds
        # 加一点点余量：正好停在边界上时算进下一帧，又不被浮点误差多推一帧
        while self.elapsed >= clip.hold(self.frame_index) - 1e-9:
            self.elapsed -= clip.hold(self.frame_index)
            if self.frame_index + 1 < count:
                self.frame_index += 1
            elif clip.loop:
                self.frame_index = 0
            else:
                # 不循环：停在最后一帧
                self.frame_index = count - 1
                self.elapsed = 0.0
                return
        self.frame_index = min(self.frame_index, count - 1)
