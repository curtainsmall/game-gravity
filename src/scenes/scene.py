"""Scene：流程单元，持有对象与世界，按固定顺序驱动系统。"""

from controller.controller_system import ControllerSystem
from mover.mover_system import MoverSystem
from physics.physics_system import PhysicsSystem
from renderer.render_system import RenderSystem
from world.world import World


class Scene:
    def __init__(self, world: World | None = None, shared_context=None):
        self.world = world
        self.shared_context = shared_context
        self.objects: list = []
        self.input_state = None

        self.mover_system = MoverSystem()
        self.controller_system = ControllerSystem()
        self.physics_system = PhysicsSystem()
        self.render_system = RenderSystem()

        self.requested_next_scene = None
        self.elapsed_seconds = 0.0

    def enter(self):
        """进入场景。"""

    def exit(self):
        """离开场景。"""

    def handle_event(self, pygame_event):
        """处理一个 pygame 事件。"""

    def update(self, delta_seconds: float):
        """一步：机关先就位 → 控制器读输入 → 物理积分与解算。"""
        self.elapsed_seconds += delta_seconds
        if self.world is None:
            return
        self.mover_system.update(self.objects, delta_seconds)
        self.controller_system.update(self.objects, self.input_state, delta_seconds)
        self.physics_system.update(self.objects, self.world, delta_seconds)

    def draw(self, surface):
        """每帧一次：绘制。与 update 分开，因为一步可能在一帧内执行多次。"""
        self.render_system.update(self.objects, surface)
