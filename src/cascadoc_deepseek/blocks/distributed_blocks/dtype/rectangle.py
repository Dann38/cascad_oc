"""
Прямоугольная область для ограничения расчетной области.
Определяет границы в координатах (S, T).
"""
from dataclasses import dataclass
from typing import Tuple

@dataclass
class Rectangle:
    """Прямоугольная область в координатах (S, T)"""
    S0: float
    S1: float  
    T0: float
    T1: float

    @property
    def center(self) -> Tuple[float, float]:
        """Центр прямоугольника"""
        return (self.S0 + self.S1) / 2, (self.T0 + self.T1) / 2

    def contains(self, s: float, t: float) -> bool:
        """Проверяет, содержится ли точка в области"""
        return (self.S0 <= s <= self.S1 and 
                self.T0 <= t <= self.T1)