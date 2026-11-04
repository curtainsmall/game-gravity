"""Entity：物件。位于空位格的交互对象，状态由自身推进。"""

from core.spec import RenderSpec


class Entity:
    def __init__(
        self,
        cell_position=(0, 0),
        interaction_state=0,
        reports_player_overlap=False,
        render_spec: RenderSpec | None = None,
    ):
        self.cell_position = cell_position                  # 所在空位格
        self.interaction_state = interaction_state          # 少量可枚举状态
        self.reports_player_overlap = reports_player_overlap  # 是否做与玩家的重叠判定
        self.collision_body = None                          # 参与碰撞时才有
        self.render_spec = render_spec if render_spec is not None else RenderSpec()

    def advance(self, delta_seconds: float) -> None:
        """本帧状态推进。"""

    def sample_overlap(self, player) -> None:
        """解算之后采样与玩家的重叠，更新 interaction_state。"""
