"""
Базовый класс для распределенных блоков (гиперболические, параболические уравнения).
Распределенные блоки имеют пространственную переменную.
"""
from abc import abstractmethod
from cascadoc_deepseek.blocks.base_block import BaseBlock
from typing import Dict, Any

class BaseDistributedBlock(BaseBlock):
    """Базовый класс для распределенных систем"""
    
    def __init__(self, name: str):
        super().__init__(name)
        self.mesh = None
        self.solution = None
        self.boundary_conditions = {}
        self.initial_condition = None
    
    @abstractmethod
    def _apply_boundary_conditions(self, t: float) -> None:
        """Применение граничных условий"""
        pass
    
    @abstractmethod
    def _solve_step(self, t: float, dt: float) -> Any:
        """Решение на одном шаге по времени"""
        pass
    
    def initialize(self, initial_conditions: Dict[str, Any]) -> None:
        """Инициализация распределенного блока"""
        if 'initial_condition' in initial_conditions:
            self.initial_condition = initial_conditions['initial_condition']
        if 'boundary_conditions' in initial_conditions:
            self.boundary_conditions = initial_conditions['boundary_conditions']
        
        self.build_mesh()
        self._initialize_solution()
        self.initialized = True
    
    def _initialize_solution(self) -> None:
        """Инициализация решения на сетке"""
        if self.mesh and self.initial_condition:
            self.solution = {}
            # Заполняем начальными условиями
            for (i, j), node in self.mesh.nodes.items():
                s, t_val = node
                self.solution[(i, j)] = self.initial_condition(s)
    
    def step(self, t: float, dt: float) -> Dict[str, Any]:
        """Шаг решения для распределенного блока"""
        if not self.initialized:
            raise RuntimeError(f"Block {self.name} is not initialized")
        
        self._apply_boundary_conditions(t)
        new_solution = self._solve_step(t, dt)
        
        if new_solution:
            self.solution = new_solution
        
        return {'solution': self.solution, 'mesh': self.mesh}