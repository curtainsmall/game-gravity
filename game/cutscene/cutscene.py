"""过场：一关之前或结尾的一段图片，带淡入淡出。

数据写在 game.json 或关卡 json 的 cutscene 里：
    pictures  [{"path", "fade_in", "hold", "fade_out"}, ...]，path 相对 game.json
    cascade   下一张的淡入是否和上一张的淡出重叠，缺省 false
    sound     false（缺省，静音）/ true（用这一幕自己的音乐）/ 一段 sound 对象
缺省一律取零值：没写的字段当 0、""、false、[]；fade_in + hold + fade_out 为 0 的图
不占时间，直接跳过；没有图、或者所有图都找不到，就当没有过场。
"""

from dataclasses import dataclass
from pathlib import Path

from sound.bgm import Bgm, bgm_value

CUTSCENE_KEY = "cutscene"
PICTURES_KEY = "pictures"
MAX_SECONDS = 3600.0


@dataclass(frozen=True)
class Picture:
    """一张过场图：路径 + 淡入、停留、淡出的秒数。"""

    path: str
    fade_in: float = 0.0
    hold: float = 0.0
    fade_out: float = 0.0

    @property
    def length(self) -> float:
        return self.fade_in + self.hold + self.fade_out


class Cutscene:
    """一段过场：图片按顺序排；cascade 时下一张在上一张淡出开始时进场。"""

    def __init__(
        self,
        pictures: list[Picture],
        cascade: bool = False,
        sound: Bgm | None = None,
        keep_scene_music: bool = False,
    ) -> None:
        self.pictures = tuple(pictures)
        self.cascade = bool(cascade)
        self.sound = sound
        self.keep_scene_music = bool(keep_scene_music)
        # 每张图的开始时间与整段时长；cascade 时不算上一张的淡出
        self.starts: list[float] = []
        self.duration = 0.0
        time = 0.0
        for picture in self.pictures:
            self.starts.append(time)
            self.duration = time + picture.length
            time += picture.fade_in + picture.hold
            if not self.cascade:
                time += picture.fade_out

    def alpha_at(self, index: int, elapsed: float) -> float:
        """第 index 张图在 elapsed 秒时的透明度（0~1）。"""
        picture = self.pictures[index]
        offset = elapsed - self.starts[index]
        if offset < 0.0:
            return 0.0
        if picture.fade_in > 0.0 and offset < picture.fade_in:
            return offset / picture.fade_in
        offset -= picture.fade_in
        if offset < picture.hold:
            return 1.0
        offset -= picture.hold
        if picture.fade_out > 0.0 and offset < picture.fade_out:
            return 1.0 - offset / picture.fade_out
        return 0.0


def cutscene_of(container, base_dir: str | Path | None) -> Cutscene | None:
    """读一份 json 里的 cutscene；没有、没图或图都找不到时返回 None。"""
    value = container.get(CUTSCENE_KEY) if isinstance(container, dict) else None
    if not isinstance(value, dict):
        return None
    pictures = []
    entries = value.get(PICTURES_KEY)
    for entry in entries if isinstance(entries, list) else []:
        if not isinstance(entry, dict):
            continue
        path = _resolve(entry.get("path"), base_dir)
        if path is None:
            continue
        fade_in = _seconds(entry.get("fade_in"))
        hold = _seconds(entry.get("hold"))
        fade_out = _seconds(entry.get("fade_out"))
        if fade_in + hold + fade_out <= 0.0:
            continue
        pictures.append(Picture(path, fade_in, hold, fade_out))
    if not pictures:
        return None
    sound_value = value.get("sound")
    if sound_value is True:
        return Cutscene(pictures, bool(value.get("cascade")), None, keep_scene_music=True)
    if isinstance(sound_value, dict):
        return Cutscene(pictures, bool(value.get("cascade")), bgm_value(sound_value, base_dir))
    return Cutscene(pictures, bool(value.get("cascade")))


def _seconds(value) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(MAX_SECONDS, number))


def _resolve(value, base_dir: str | Path | None) -> str | None:
    """图片路径：相对 game.json；不是现成的文件就跳过这张。"""
    if not value:
        return None
    path = Path(str(value))
    if not path.is_absolute():
        if base_dir is None:
            return None
        path = Path(base_dir) / path
    path = path.resolve()
    return str(path) if path.is_file() else None
