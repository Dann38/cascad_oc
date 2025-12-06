"""
Базовый класс для всех блоков каскадной системы.
Определяет общий интерфейс для сосредоточенных и распределенных блоков.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from ..core.connection import BoundaryConnection

class BaseBlock(ABC):
    """Абстрактный базовый класс для всех блоков системы"""
    
    def __init__(self, name: str):
        self.name = name
        self.connections: List[BoundaryConnection] = []
        self.initialized = False
        self.solution_data = None
    
    @abstractmethod
    def initialize(self, initial_conditions: Dict[str, Any]) -> None:
        """Инициализация блока с начальными условиями"""
        pass
    
    @abstractmethod
    def build_mesh(self) -> None:
        """Построение сетки для блока"""
        pass
    
    @abstractmethod
    def step(self, t: float, dt: float) -> Dict[str, Any]:
        """Выполнение одного шага решения"""
        pass
    
    def connect(self, connection: BoundaryConnection) -> None:
        """Добавление соединения с другим блоком"""
        self.connections.append(connection)
    
    def get_boundary_value(self, boundary_name: str, t: float) -> Any:
        """Получение значения на границе от соединенного блока"""
        for connection in self.connections:
            if connection.source_boundary == boundary_name:
                return connection.get_value(t)
        return None
    
    def is_ready(self, t: float) -> bool:
        """Проверка готовности блока к шагу в момент времени t"""
        return all(conn.is_ready(t) for conn in self.connections)