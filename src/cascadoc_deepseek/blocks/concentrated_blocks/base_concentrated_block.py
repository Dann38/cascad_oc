"""
Базовый класс для сосредоточенных блоков (ОДУ, алгебраические уравнения).
Сосредоточенные блоки не имеют пространственной переменной.
"""
from abc import abstractmethod
from typing import Any, Dict
from cascadoc_deepseek.blocks.base_block import BaseBlock

class BaseConcentratedBlock(BaseBlock):
    """Базовый класс для сосредоточенных систем"""
    
    def __init__(self, name: str):
        super().__init__(name)
        self.current_time = 0.0
        self.state = None
        self.mesh = None  # Сосредоточенные блоки не имеют пространственной сетки
    
    def build_mesh(self) -> None:
        """Сосредоточенные блоки не требуют построения пространственной сетки"""
        pass
    
    @abstractmethod
    def _compute_derivative(self, t: float, state: Any) -> Any:
        """Вычисление производной для ОДУ"""
        pass
    
    def initialize(self, initial_conditions: Dict[str, Any]) -> None:
        """Инициализация состояния блока"""
        if 'state' in initial_conditions:
            self.state = initial_conditions['state']
        if 't0' in initial_conditions:
            self.current_time = initial_conditions['t0']
        self.initialized = True
    
    def step(self, t: float, dt: float) -> Dict[str, Any]:
        """Шаг решения для сосредоточенного блока"""
        if not self.initialized:
            raise RuntimeError(f"Block {self.name} is not initialized")
        
        # Базовая реализация - метод Эйлера
        derivative = self._compute_derivative(t, self.state)
        self.state = self.state + derivative * dt
        self.current_time = t + dt
        
        return {'state': self.state, 't': self.current_time}