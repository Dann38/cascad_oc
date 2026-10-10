from abc import ABC, abstractmethod
from typing import Callable, Dict, Tuple, Optional, Union
import numpy as np
from .point import Point
from .utils import normalize_float


class Variable(ABC):
    name: str
    dim: int

    def __init__(self, name: str, dim: int = 1):
        self.name = name
        self.dim = dim

    @abstractmethod
    def at(self, point: Point) -> Optional[Union[float, np.ndarray]]:
        ...


class AnalyticVariable(Variable):
    """f(point) = expression(point). Вычисляется на лету.

    Можно передать либо функцию ``fn(point)``, либо константу (число/массив) —
    тогда она будет возвращаться в любой точке.

    dim=1 → fn возвращает float
    dim=2 → fn возвращает np.ndarray shape (2,)  (напр. вектор F)
    """

    def __init__(self, name: str, fn: Union[Callable, float, int, np.ndarray],
                 dim: Union[int, Tuple[int, ...]] = 1):
        super().__init__(name, dim if isinstance(dim, int) else dim[0])
        if callable(fn):
            self.fn = fn
        else:
            value = fn
            self.fn = lambda point, _value=value: _value

    def at(self, point: Point) -> Union[float, np.ndarray]:
        return self.fn(point)


class NumericVariable(Variable):
    """Численная: хранит значения в узлах сетки.

    dim — размерность вектора на узле. Ключ — координаты точки.
    """

    def __init__(self, name: str, dim: int = 1):
        super().__init__(name, dim)
        self._data: Dict[Tuple[float, ...], np.ndarray] = {}

    @staticmethod
    def _key(point: Point) -> Tuple[float, ...]:
        return tuple(normalize_float(list(point.coords)))

    def at(self, point: Point) -> Optional[np.ndarray]:
        return self._data.get(self._key(point))

    def store(self, point: Point, value: Union[np.ndarray, list, float]) -> None:
        arr = np.asarray(value, dtype=float)
        if arr.ndim == 0:
            arr = arr.reshape(self.dim)
        self._data[self._key(point)] = arr

    @property
    def storage(self) -> Dict[Tuple[float, ...], np.ndarray]:
        return self._data


def is_analytic(var: Variable) -> bool:
    return isinstance(var, AnalyticVariable)


def is_numeric(var: Variable) -> bool:
    return isinstance(var, NumericVariable)
