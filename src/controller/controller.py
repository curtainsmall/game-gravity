"""Controller：控制部件。来源对象决定这个 body 怎么动。"""


class Controller:
    def __init__(self, source=None) -> None:
        self.source = source                      # InputSource / TriggerSource
        self.passes_through_planks: bool = False
