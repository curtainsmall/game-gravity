"""AnimationClip：一段帧动画。

帧是一串已经解析成绝对路径的 PNG；fps 是每秒几帧；loop 决定播完最后一张之后是回到第一张
还是停住。剪辑本身不记播放进度，进度在播出它的那个 animator 里。
"""

DEFAULT_FPS = 8.0
MIN_FPS = 0.1
MAX_FPS = 60.0


class AnimationClip:
    def __init__(self, frames: list, fps=DEFAULT_FPS, loop: bool = True) -> None:
        self.frames: list[str] = list(frames)
        try:
            value = float(fps)
        except (TypeError, ValueError):
            value = DEFAULT_FPS
        self.fps: float = max(MIN_FPS, min(MAX_FPS, value))
        self.loop: bool = bool(loop)

    @property
    def frame_seconds(self) -> float:
        """一帧放多久（秒）。"""
        return 1.0 / self.fps

    def __len__(self) -> int:
        return len(self.frames)

    def __repr__(self) -> str:
        return f"AnimationClip({len(self.frames)} 帧, {self.fps:g}fps, loop={self.loop})"
