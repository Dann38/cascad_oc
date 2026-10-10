from __future__ import annotations
from typing import TYPE_CHECKING, Optional, Union
import numpy as np
from ..core.point import Point
from ..core.variable import AnalyticVariable
from ..core.utils import normalize_float

if TYPE_CHECKING:
    from .system import System


class Node:
    """Точка на сетке с доступом к векторным переменным.

    Узел хранит только координаты (Point) и ссылку на System.

    node['X']     → np.ndarray(dim,) — вектор состояния
    node['B11']   → float            — скаляр (dim=1)
    node['X'][k]  → float            — k-я компонента вектора
    node['X'] = np.array([x, y])
    """

    __slots__ = ('point', '_system')

    def __init__(self, point: Union[Point, float], system: Optional[System] = None,
                 t: Optional[float] = None):
        if isinstance(point, Point):
            self.point = point
        elif t is not None:
            self.point = Point(point, t)  # совместимость: Node(s, t)
        else:
            self.point = Point(point)
        self._system = system

    @property
    def s(self) -> float:
        return self.point.s

    @property
    def t(self) -> float:
        return self.point.t

    def __getitem__(self, name: str) -> Optional[Union[float, np.ndarray]]:
        if self._system is None:
            raise RuntimeError(f"{self!r}: no system attached")
        var = self._system.variables[name]
        val = var.at(self.point)
        if val is None:
            return None
        if var.dim == 1 and isinstance(val, np.ndarray) and val.ndim == 1:
            return val[0]
        return val

    def __setitem__(self, name: str, value: Union[float, np.ndarray, list]):
        if self._system is None:
            raise RuntimeError(f"{self!r}: no system attached")
        var = self._system.variables[name]
        if isinstance(var, AnalyticVariable):
            raise TypeError(f"Cannot store analytic variable '{name}'")
        var.store(self.point, value)

    def __contains__(self, name: str) -> bool:
        if self._system is None:
            return False
        return name in self._system.variables

    def is_computed(self, name: str) -> bool:
        var = self._system.variables[name]
        if isinstance(var, AnalyticVariable):
            return True
        key = tuple(normalize_float(list(self.point.coords)))
        return key in var._data

    def __repr__(self):
        return f"Node({self.point!r})"
