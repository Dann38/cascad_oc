from abc import ABC, abstractmethod

class BaseBlock(ABC):
    def __init__(self, config:dict):
        self.config = config

    @property
    def size(self):
        return 0, 0

    @abstractmethod
    def one_time_step(self, dt):
        pass