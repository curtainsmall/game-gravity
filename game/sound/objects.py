"""声音对象：关卡里的音效。

声音对象只出声、不碰撞、不画东西。预设决定什么时候放：

    general  关卡加载时放一次（播一遍就停）
    player   按「跟随」那个对象的状态切，和动画对象同一套动作：
                 idle / run / takeoff / raise / fall / landing
             持续动作（idle / run / raise / fall）循环，takeoff / landing 播一遍；
             换了动作就把旧的声音短淡出、放新的

跟随写 "@player" 就是玩家，写关卡里别的对象的名字就跟着那个对象（没有位置和大小，
声音也不分远近）。链接里写 game.json 声音库的键和要不要循环——循环由动作决定，
链接只写键；老数据把上升写在 jump 里，读的时候当作 raise 的兜底。键找不到、文件不在
都只是没有声音。所有音效走普通 channel，音量是总音量 × 音效音量。
"""

from animation.sprite import PlayerMotion, loop_for
from sound.sound_system import SoundSystem

PRESET_GENERAL = "general"
PRESET_PLAYER = "player"
PLAYER_ACTIONS = ("idle", "run", "takeoff", "raise", "fall", "landing")
PLAYER_FOLLOW = ("@player", "player")
SHORT_FADE = 0.08         # 换动作、离开关卡时旧声音淡出多久


class SoundSprite:
    """一个声音对象的播放状态：预设、链接、跟随目标、动作和现在占着的 channel。"""

    def __init__(self, preset: str = PRESET_GENERAL, links: dict | None = None) -> None:
        self.preset: str = (
            preset if preset in (PRESET_GENERAL, PRESET_PLAYER) else PRESET_GENERAL
        )
        self.links: dict = links if isinstance(links, dict) else {}
        self.target = None       # 跟随的那个 GameObject；None 表示没跟到
        self.motion = PlayerMotion()
        self.action: str = ""    # player 预设现在按哪个动作在放
        self.channel = None

    def stop(self, system: SoundSystem | None) -> None:
        if self.channel is None or system is None:
            return
        system.stop_channel(self.channel, SHORT_FADE)
        self.channel = None


class SoundObjects:
    """一关里所有声音对象的运行时：进关卡放 general，每步盯跟随对象的动作。"""

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
            sprite.motion = PlayerMotion()
            sprite.action = ""

    def start(self, system: SoundSystem) -> None:
        """进这一关：先把 general 预设的那一条放出来（播一遍）。"""
        self.system = system
        for game_object in self.objects:
            sprite: SoundSprite = game_object.sound
            if sprite.preset != PRESET_GENERAL:
                continue
            key = _link_key(sprite.links.get(PRESET_GENERAL))
            self._play(sprite, key, False)

    def update(self, delta_seconds: float) -> None:
        """每步推进跟随对象的动作；变了就换 player 预设的那一条。"""
        if self.system is None:
            return
        for game_object in self.objects:
            sprite: SoundSprite = game_object.sound
            if sprite.preset != PRESET_PLAYER:
                continue
            body = getattr(sprite.target, "body", None) if sprite.target is not None else None
            action = sprite.motion.update(body, delta_seconds)
            if action == sprite.action:
                continue
            sprite.action = action
            pair = sprite.links.get(PRESET_PLAYER)
            pair = pair if isinstance(pair, dict) else {}
            key = _action_key(pair, action)
            self._play(sprite, key, loop_for(action))

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


def _action_key(pair: dict, action: str) -> str:
    """动作 → 声音键：老数据把上升写在 jump 里，raise 找不到时去那儿借。"""
    key = _link_key(pair.get(action))
    if not key and action == "raise":
        return _link_key(pair.get("jump"))
    return key


def _link_key(value) -> str:
    """一条链接 → 声音键：新写法是 {"sound": 键}，老数据直接写键。"""
    if isinstance(value, dict):
        return str(value.get("sound") or "")
    return str(value or "")
