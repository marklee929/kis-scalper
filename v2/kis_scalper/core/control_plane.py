class ControlPlane:
    def __init__(self):
        self.halted = False

    def halt(self) -> None:
        self.halted = True

    def resume(self) -> None:
        self.halted = False
