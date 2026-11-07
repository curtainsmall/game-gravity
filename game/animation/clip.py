"""AnimationClip：一段帧动画。

frames 是已经解析成绝对路径的图片，holds 是每帧停留的秒数（和 frames 一一对应）；
loop 决定播完最后一张之后是回到第一张还是停住，不过真正播的时候以动画对象那条
链接上的 loop 为准，这里的只是老数据的默认值。老数据只有统一 fps，没有 holds 时按 1/fps 算。
剪辑本身不记播放进度，进度在播出它的那个 animator 里。
"""

DEFAULT_FPS = 8.0        # 老数据没写 fps 时的默认值
DEFAULT_HOLD = 0.1       # 一帧停留多久的兜底值
MIN_HOLD = 0.01
MAX_HOLD = 10.0


class AnimationClip:
    def __init__(
        self,
        frames: list | None = None,
        holds: list | None = None,
        loop: bool = True,
        fps: float | None = None,
    ) -> None:
        self.frames: list[str] = list(frames) if frames else []
        fallback = _clamp_hold(1.0 / float(fps), DEFAULT_HOLD) if fps else DEFAULT_HOLD
        given = list(holds) if isinstance(holds, (list, tuple)) else []
        self.holds: list[float] = []
        for index in range(len(self.frames)):
            value = given[index] if index < len(given) else fallback
            self.holds.append(_clamp_hold(value, fallback))
        self.loop: bool = bool(loop)

    def __len__(self) -> int:
        return len(self.frames)

    def hold(self, index: int) -> float:
        """第 index 帧停留多少秒。"""
        index = max(0, min(index, len(self.holds) - 1))
        return self.holds[index] if self.holds else DEFAULT_HOLD

    @property
    def frame_seconds(self) -> float:
        """第一帧的时长（老代码兼容用）。"""
        return self.hold(0)

    def __repr__(self) -> str:
        return f"AnimationClip({len(self.frames)} 帧, loop={self.loop})"


def _clamp_hold(value, fallback: float) -> float:
    try:
        seconds = float(value)
    except (TypeError, ValueError):
        seconds = fallback
    return max(MIN_HOLD, min(MAX_HOLD, seconds))
