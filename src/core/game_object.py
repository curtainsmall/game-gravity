"""GameObject：身份 + 部件容器。纯数据，行为在系统里。"""


class GameObject:
    def __init__(
        self,
        kind: str = "",
        body=None,
        controller=None,
        mover=None,
        render=None,
        interaction_state: int = 0,
    ):
        self.kind = kind                        # 用于调试与关卡数据
        self.body = body                        # 物理部件
        self.controller = controller            # 控制部件
        self.mover = mover                      # 机关部件
        self.render = render                    # 显示部件
        self.interaction_state = interaction_state  # 交互状态，由系统写入

    def describe(self) -> str:
        parts = [
            name
            for name in ("body", "controller", "mover", "render")
            if getattr(self, name) is not None
        ]
        return f"{self.kind or 'object'}({', '.join(parts) or 'data'})"

    def __repr__(self) -> str:
        return self.describe()
