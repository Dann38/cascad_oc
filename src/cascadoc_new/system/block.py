"""Базовый тип блока — единица композиции системы.

Система собирается из блоков (``System.blocks``). Каждый блок отвечает за
свою часть узлов и умеет решить их на заданном слое времени ``t``.
Блоки не хранят значения: узлы — это точки ``(s, t)``, а значения живут в
общих ``NumericVariable`` системы. Поэтому «интерфейс» между блоками — это
совпадающие точки: два блока, обращающиеся к ``Point(s, t)``, видят одну и
ту же ячейку хранилища. Отдельный объект ``Interface`` не нужен.
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List

from .system import System


class Block(ABC):
    """Часть системы, решаемая послойно по времени ``t``."""

    def __init__(self, name: str, system: System) -> None:
        self.name = name
        self.system = system
        self._depends_on: List[str] = []

    @property
    def depends_on(self) -> List[str]:
        """Имена блоков, которые должны быть решены раньше этого блока."""
        return list(self._depends_on)

    @depends_on.setter
    def depends_on(self, deps: List[str]) -> None:
        self._depends_on = list(deps)

    @property
    def provides(self) -> str:
        """Имя переменной, которую производит этот блок (или '')."""
        return ''

    @abstractmethod
    def layer_times(self) -> List[float]:
        """Времена слоёв, которые обрабатывает блок (порядок не важен)."""

    @abstractmethod
    def solve_layer(self, t: float) -> None:
        """Решить все свои узлы на слое ``t``."""

    def has_layer(self, t: float) -> bool:
        return any(layer == t for layer in self.layer_times())

    def finalize(self, t_last: float) -> None:
        """Пост-шаг после решения всех слоёв (по умолчанию не нужен).

        Нужен, когда сборка узлов последнего слоя должна произойти после того,
        как соседние блоки закончат свои узлы на этом же слое ``t_last``.
        """

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.name})"
