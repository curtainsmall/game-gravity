"""BGM 播放：一台机器上只有一条音乐流，切一幕就是淡出旧的、淡入新的。

pygame 只有一个 mixer.music，做不了交叉淡入淡出：换曲时先让旧的淡出，等它淡完
（每帧在 update 里等，这期间是静音）再换文件开始新的，所以 fade_out 别写太长。
音量 = 总音量 × 音乐音量，都在 .game/setting.json 里，曲子本身不再单独调。

音效是另一条路：走普通 channel，音量 = 总音量 × 音效音量。声音对象（sound.objects）
拿到的 channel 由它自己管；这里只负责载入、缓存、停和调音量。
没有声卡、曲子读不出来，都只是没有声音，游戏照常跑。
"""

import pygame

from sound.bgm import Bgm

DEFAULT_VOLUME = {"master": 1.0, "music": 1.0, "sfx": 1.0}


class SoundSystem:
    def __init__(self, volume: dict | None = None) -> None:
        self.volume = dict(volume or DEFAULT_VOLUME)
        self.ready = False
        self.current: Bgm | None = None      # 本该放着的那一首（可能还在等旧曲子淡出）
        self.paused = False
        self._wait_seconds = 0.0             # 旧曲子还要淡出多久，淡完再开始新的
        self._cache: dict[str, pygame.mixer.Sound] = {}   # 音效：路径 → 载入好的声音
        self._channels: list = []            # 正在放音效的 channel，暂停和统一停止用

    # ---- 初始化 -----------------------------------------------------
    def start(self) -> None:
        """开混音器。没有声卡就整个关掉，之后所有调用都是空操作。"""
        try:
            if pygame.mixer.get_init() is None:
                pygame.mixer.init()
        except pygame.error:
            self.ready = False
            return
        self.ready = True
        self.apply_volume()

    def shutdown(self) -> None:
        """退出前收尾：直接把音乐停掉，不等淡出。"""
        if not self.ready:
            return
        try:
            pygame.mixer.music.stop()
        except pygame.error:
            pass

    # ---- 播放 -------------------------------------------------------
    def play(self, bgm: Bgm | None) -> None:
        """换到这一幕：同一首就接着放，`None` 表示这一幕没有音乐。

        同一首不重新开头，这样暂停菜单里的「重新开始」不会把曲子打断重放。
        """
        if not self.ready:
            return
        if self.paused:
            self.resume()
        if bgm is not None and bgm == self.current:
            # 不循环的曲子放完了，再进这一幕就重新开头；还在淡出交接时就等着
            if self._wait_seconds <= 0.0 and not pygame.mixer.music.get_busy():
                self._start(bgm)
            return
        previous, self.current = self.current, bgm
        self._wait_seconds = 0.0
        if bgm is None:
            self._fade_out(previous)
            return
        if previous is not None and previous.fade_out > 0.0 and pygame.mixer.music.get_busy():
            # 旧曲子先淡出，淡完由 update 接手开始新的
            pygame.mixer.music.fadeout(self._milliseconds(previous.fade_out))
            self._wait_seconds = previous.fade_out
            return
        self._start(bgm)

    def update(self, elapsed_seconds: float) -> None:
        """每帧一次：旧曲子的淡出还没走完就等着，走完了开始新的。"""
        if not self.ready or self._wait_seconds <= 0.0:
            return
        self._wait_seconds = max(0.0, self._wait_seconds - elapsed_seconds)
        if self._wait_seconds > 0.0:
            return
        if self.current is not None:
            self._start(self.current)
            if self.paused:
                # 交接期间被暂停了：新的这首也就位，但仍然是停住的
                pygame.mixer.music.pause()
        else:
            self._stop()

    def pause(self) -> None:
        """暂停游戏时音乐也停在那儿，回来接着放。"""
        if not self.ready or self.paused or not pygame.mixer.music.get_busy():
            return
        pygame.mixer.music.pause()
        self.paused = True

    def resume(self) -> None:
        if not self.ready or not self.paused:
            return
        pygame.mixer.music.unpause()
        self.paused = False

    # ---- 音效 -------------------------------------------------------
    def play_sound(self, path: str, loop: bool = False):
        """放一段音效：走普通 channel，返回那个 channel（拿来停、淡出）。"""
        if not self.ready:
            return None
        sound = self._load(path)
        if sound is None:
            return None
        try:
            channel = sound.play(-1 if loop else 0)
        except pygame.error:
            return None
        if channel is None:
            return None
        channel.set_volume(self.sound_volume)
        self._channels.append(channel)
        return channel

    def stop_channel(self, channel, fade_out: float = 0.0) -> None:
        """停掉一个音效 channel：fade_out 秒淡出，0 就直接停。"""
        if channel is None:
            return
        try:
            if fade_out > 0.0:
                channel.fadeout(self._milliseconds(fade_out))
            else:
                channel.stop()
        except pygame.error:
            pass
        self._channels = [item for item in self._channels if item is not channel]

    def stop_sounds(self, fade_out: float = 0.0) -> None:
        """把所有音效停掉（离开关卡、进过场、回标题时用）。"""
        for channel in list(self._channels):
            self.stop_channel(channel, fade_out)
        self._channels = []

    def pause_sounds(self) -> None:
        for channel in list(self._channels):
            try:
                channel.pause()
            except pygame.error:
                pass

    def resume_sounds(self) -> None:
        for channel in list(self._channels):
            try:
                channel.unpause()
            except pygame.error:
                pass

    def _load(self, path: str) -> pygame.mixer.Sound | None:
        sound = self._cache.get(path)
        if sound is not None:
            return sound
        try:
            sound = pygame.mixer.Sound(path)
        except (pygame.error, OSError):
            return None
        self._cache[path] = sound
        return sound

    # ---- 音量 -------------------------------------------------------
    @property
    def music_volume(self) -> float:
        return _clamp(self.volume.get("master", 1.0) * self.volume.get("music", 1.0))

    @property
    def sound_volume(self) -> float:
        """音效的音量：以后放音效时乘到每个 Sound.set_volume 上。"""
        return _clamp(self.volume.get("master", 1.0) * self.volume.get("sfx", 1.0))

    def set_volume(self, volume: dict) -> None:
        """设置里改了音量：立刻对正在放的曲子生效。"""
        self.volume = dict(volume)
        self.apply_volume()

    def apply_volume(self) -> None:
        if not self.ready:
            return
        try:
            pygame.mixer.music.set_volume(self.music_volume)
        except pygame.error:
            pass
        for channel in list(self._channels):
            try:
                channel.set_volume(self.sound_volume)
            except pygame.error:
                pass

    # ---- 内部 -------------------------------------------------------
    def _start(self, bgm: Bgm) -> None:
        """真的开始一首：读文件按 loop、fade_in 放；读不出来就当没音乐。"""
        try:
            pygame.mixer.music.load(bgm.path)
            pygame.mixer.music.set_volume(self.music_volume)
            pygame.mixer.music.play(
                -1 if bgm.loop else 0, fade_ms=self._milliseconds(bgm.fade_in)
            )
        except (pygame.error, OSError):
            return

    def _fade_out(self, previous: Bgm | None) -> None:
        """把正在放的那首淡出（没有 fade_out 就直接停）。"""
        if not self.ready or not pygame.mixer.music.get_busy():
            return
        fade_out = previous.fade_out if previous is not None else 0.0
        if fade_out > 0.0:
            pygame.mixer.music.fadeout(self._milliseconds(fade_out))
        else:
            self._stop()

    def _stop(self) -> None:
        try:
            pygame.mixer.music.stop()
        except pygame.error:
            pass

    @staticmethod
    def _milliseconds(seconds: float) -> int:
        return max(0, int(round(seconds * 1000.0)))


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))
