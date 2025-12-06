from abc import ABC

class BaseMesh(ABC):
    def __init__(self, config):
        self.config = config