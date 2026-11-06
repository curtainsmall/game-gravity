"""PlayerAnimator：玩家的帧动画。

状态词汇固定，和编辑器里那一页的行一一对应：
    idle 站立 / run 移动 / jump 上升 / fall 下落 / flip 翻转（重力朝上）
按物理状态挑剪辑（状态对应的剪辑没有就退回 idle），左右朝向用水平翻转；
每次 update 把当前帧的路径写进 RenderSpec，渲染那边只管画图。
"""

PLAYER_STATES = ("idle", "run", "jump", "fall", "flip")


class PlayerAnimator:
    def __init__(self, player, clips: dict | None = None) -> None:
        self.player = player
        self.clips: dict = clips or {}
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

        clip = self.clips.get(state) or self.clips.get("idle")
        render = self.player.render
        if render is None or clip is None or not clip.frames:
            if render is not None:
                render.texture_path = None
            return

        if body.velocity_x > 0.0:
            self.facing = 1
        elif body.velocity_x < 0.0:
            self.facing = -1
        self._advance(clip, delta_seconds)
        render.texture_path = clip.frames[self.frame_index]
        render.texture_face = "up"
        render.texture_flip = self.facing < 0

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
        seconds = clip.frame_seconds
        self.elapsed += delta_seconds
        while self.elapsed >= seconds:
            self.elapsed -= seconds
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
