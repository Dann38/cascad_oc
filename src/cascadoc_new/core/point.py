from __future__ import annotations
from typing import Iterator, Tuple

import numpy as np


class Point:
    """Точка в пространстве произвольной размерности.

    Хранит кортеж координат и служит единым аргументом вместо списка
    отдельных чисел. Точки можно конкатенировать оператором ``|``:

        Point(s, t) | Point(s2, t2)        -> Point(s, t, s2, t2)
        Point(i, j) | Point(s, t)          -> Point(i, j, s, t)

    Для координат (s, t) доступны свойства ``s`` и ``t``.
    """

    __slots__ = ('_coords',)

    def __init__(self, *coords) -> None:
        if len(coords) == 1 and isinstance(coords[0], (tuple, list, np.ndarray)):
            coords = tuple(coords[0])
        self._coords: Tuple = tuple(coords)

    # ------------------------------------------------------------ конкатенация
    def __or__(self, other: 'Point') -> 'Point':
        if not isinstance(other, Point):
            return NotImplemented
        return Point(*(self._coords + other._coords))

    # -------------------------------------------------------------- контейнер
    def __getitem__(self, index) -> float:
        return self._coords[index]

    def __iter__(self) -> Iterator[float]:
        return iter(self._coords)

    def __len__(self) -> int:
        return len(self._coords)

    def __eq__(self, other) -> bool:
        return isinstance(other, Point) and self._coords == other._coords

    def __hash__(self) -> int:
        return hash(self._coords)

    def __repr__(self) -> str:
        return "Point(" + ", ".join(repr(c) for c in self._coords) + ")"

    # ------------------------------------------------------------------ данные
    @property
    def coords(self) -> Tuple:
        return self._coords

    @property
    def dim(self) -> int:
        return len(self._coords)

    @property
    def s(self) -> float:
        return self._coords[0]

    @property
    def t(self) -> float:
        return self._coords[1]

    def asarray(self) -> np.ndarray:
        return np.asarray(self._coords, dtype=float)

    def as_tuple(self) -> Tuple:
        return self._coords
