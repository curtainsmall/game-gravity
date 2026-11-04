"""Scene：流程单元，也是唯一的调度者。"""

from world.solve import solve_collisions
from world.world import World


class Scene:
    def __init__(self, shared_context=None, level_world: World | None = None, player=None):
        self.shared_context = shared_context              # 输入、资源、视图、音频的访问点
        self.level_world = level_world                    # 关卡场景持有，其余场景为空
        self.player = player
        self.requested_next_scene = None                  # 流程出口
        self.elapsed_seconds = 0.0

    def enter(self):
        """进入场景。"""

    def exit(self):
        """离开场景。"""

    def handle_event(self, pygame_event):
        """处理一个 pygame 事件。"""

    def update(self, delta_seconds: float):
        """一帧：机关 → 玩家 → 解算 → 采样 → 收尾。"""
        self.elapsed_seconds += delta_seconds

        world = self.level_world
        if world is None:
            return

        for movable_block in world.moving_blocks:      # 机关先于玩家
            movable_block.advance(delta_seconds)

        self.player.advance(delta_seconds, world)

        solve_collisions(self.player, world)           # 解算先于采样

        for entity in world.interactive_objects:
            entity.sample_overlap(self.player)

        self.player.settle()
