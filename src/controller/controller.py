"""Controller：控制部件。来源对象决定这个 body 怎么动。"""


class Controller:
    def __init__(self, source=None) -> None:
        self.source = source                      # InputSource / TriggerSource
        self.passes_through_planks: bool = False
        self.fan_boost_used: bool = False         # 一次滞空只借一次风力，落地复位
