"""声音对象：关卡里的音效。

声音对象只出声、不碰撞、不画东西。预设决定什么时候放：

    general  关卡加载时放一次；链接写了循环就一直放到离开这一关
    player   按「跟随」那个对象的状态切（idle / run / jump / fall，和动画对象同一套），
             换了状态就把旧的声音短淡出、放新的

跟随写 "@player" 就是玩家，写关卡里别的对象的名字就跟着那个对象（没有位置和大小，
声音也不分远近）。链接里写 game.json 声音库的键和要不要循环；键找不到、文件不在
都只是没有声音。所有音效走普通 channel，音量是总音量 × 音效音量。
"""

from animation.sprite import state_of
from sound.sound_system import SoundSystem

PRESET_GENERAL = "general"
PRESET_PLAYER = "player"
PLAYER_ACTIONS = ("idle", "run", "jump", "fall")
PLAYER_FOLLOW = ("@player", "player")
SHORT_FADE = 0.08         # 换状态、离开关卡时旧声音淡出多久


class SoundSprite:
    """一个声音对象的播放状态：预设、链接、跟随目标和现在占着的 channel。"""

    def __init__(self, preset: str = PRESET_GENERAL, links: dict | None = None) -> None:
        self.preset: str = (
            preset if preset in (PRESET_GENERAL, PRESET_PLAYER) else PRESET_GENERAL
        )
        self.links: dict = links if isinstance(links, dict) else {}
        self.target = None       # 跟随的那个 GameObject；None 表示没跟到
        self.action: str = ""    # player 预设现在按哪个动作在放
        self.channel = None

    def stop(self, system: SoundSystem | None) -> None:
        if self.channel is None or system is None:
            return
        system.stop_channel(self.channel, SHORT_FADE)
        self.channel = None


class SoundObjects:
    """一关里所有声音对象的运行时：进关卡放 general，每步盯跟随对象的状态。"""

    def __init__(self, sounds: dict[str, str]) -> None:
        self.sounds = sounds          # 声音键 → 绝对路径
        self.objects: list = []       # 带 sound 的那几个 GameObject
        self.system: SoundSystem | None = None

    def attach(self, objects: list, targets: list | None = None, player=None) -> None:
        """解析跟随：玩家写 "@player"，其余按名字找；找不到就没有状态来源。"""
        self.objects = [
            game_object
            for game_object in objects
            if getattr(game_object, "sound", None) is not None
        ]
        named = {}
        for game_object in targets or []:
            if game_object.name and game_object.body is not None:
                named.setdefault(game_object.name, game_object)
        for game_object in self.objects:
            sprite: SoundSprite = game_object.sound
            follow = str(getattr(game_object, "follow", "") or "")
            if follow in PLAYER_FOLLOW:
                sprite.target = player
            elif follow:
                sprite.target = named.get(follow)
            else:
                sprite.target = None
            sprite.action = ""

    def start(self, system: SoundSystem) -> None:
        """进这一关：先把 general 预设的那一条放出来。"""
        self.system = system
        for game_object in self.objects:
            sprite: SoundSprite = game_object.sound
            if sprite.preset != PRESET_GENERAL:
                continue
            key, loop = _link_parts(sprite.links.get(PRESET_GENERAL))
            self._play(sprite, key, loop)

    def update(self) -> None:
        """每步看一眼跟随对象的状态；变了就换 player 预设的那几条。"""
        if self.system is None:
            return
        for game_object in self.objects:
            sprite: SoundSprite = game_object.sound
            if sprite.preset != PRESET_PLAYER:
                continue
            body = getattr(sprite.target, "body", None) if sprite.target is not None else None
            state = state_of(body) if body is not None else ""
            if state == sprite.action:
                continue
            sprite.action = state
            pair = sprite.links.get(PRESET_PLAYER)
            pair = pair if isinstance(pair, dict) else {}
            key, loop = _link_parts(pair.get(state)) if state else ("", False)
            self._play(sprite, key, loop)

    def stop(self) -> None:
        """离开这一关：所有声音对象收声。"""
        for game_object in self.objects:
            game_object.sound.stop(self.system)

    def _play(self, sprite: SoundSprite, key: str, loop: bool) -> None:
        sprite.stop(self.system)
        path = self.sounds.get(key)
        if not path or self.system is None:
            return
        sprite.channel = self.system.play_sound(path, loop)


def _link_parts(value) -> tuple:
    """一条链接 → (声音键, 是否循环)；老数据直接写键、不循环。"""
    if isinstance(value, dict):
        return str(value.get("sound") or ""), bool(value.get("loop", False))
    return str(value or ""), False
