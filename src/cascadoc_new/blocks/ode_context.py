"""Контекст правой части ОДУ для ``ode_fn`` (M1).

Исторически ``ode_fn`` имел жёсткую сигнатуру ``f(z, t)``: правую часть можно
было вычислить только из ``(z, t)``. В исправленной постановке кейса
``cases/case1`` правая часть зависит ещё и от ``x(s0, t)`` — значения
ДУЧП на границе **того же** слоя, которое не задано, а вычисляется решением.
Поэтому вводится контекстная форма ``f(z, t, ctx)``, где ``ctx`` даёт доступ к
системе, точке слоя и значению ``x`` на границе.

Обе формы поддерживаются: арность ``ode_fn`` определяется автоматически
(:func:`call_ode_fn`), старые вызовы ``f(z, t)`` продолжают работать без
изменений.
"""
from __future__ import annotations

import inspect
from typing import Callable, Dict, Optional

import numpy as np

from ..core.point import Point


class ODEContext:
    """Контекст вычисления правой части ОДУ на слое ``t``.

    Параметры
    ---------
    system : System
        Система, из которой читаются переменные.
    point : Point
        Точка слоя ``(s, t)``; для граничного ОДУ ``s`` — это ``S0``/``S1``,
        а ``t`` — время текущего слоя.
    x_overrides : dict, optional
        Явные значения ``x`` по сторонам (``{'left': 0.3}``). Нужны для
        пробных вычислений ``f`` вне итерации (например, при проверке
        аффинности). Если сторона не переопределена, значение читается из
        переменной ``X`` системы в точке ``(S0 или S1, t)``.
    """

    __slots__ = ('system', 'point', '_x_overrides')

    def __init__(self, system, point: Point,
                 x_overrides: Optional[Dict[str, float]] = None) -> None:
        self.system = system
        self.point = point
        self._x_overrides = dict(x_overrides or {})

    def _s_const(self, side: str) -> float:
        if side == 'left':
            return float(self.system.variables['S0'].at(self.point))
        if side == 'right':
            return float(self.system.variables['S1'].at(self.point))
        raise ValueError(f"side должно быть 'left' или 'right', дано {side!r}")

    def x(self, side: str = 'left', component: int = 0) -> float:
        """Значение компоненты ``x`` на границе ``side`` в точке слоя ``t``.

        ``side='left'`` → ``x(s0, t)``, ``side='right'`` → ``x(s1, t)``.
        """
        if side in self._x_overrides:
            return float(self._x_overrides[side])
        s = self._s_const(side)
        val = self.system.variables['X'].at(Point(s, self.point[1]))
        if val is None:
            raise RuntimeError(
                f"ODEContext.x({side!r}): значение X({s}, {self.point[1]}) "
                f"ещё не вычислено на слое t={self.point[1]} "
                f"(проверьте зависимости блоков).")
        arr = np.asarray(val, dtype=float)
        if arr.ndim == 0 or arr.size == 1:
            return float(arr.reshape(-1)[0])
        return float(arr.reshape(-1)[component])


def ode_fn_arity(ode_fn: Callable) -> int:
    """Число позиционных аргументов ``ode_fn`` (2 — старая форма, 3 — новая)."""
    try:
        sig = inspect.signature(ode_fn)
    except (TypeError, ValueError):
        return 2
    return sum(
        1 for p in sig.parameters.values()
        if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD))


def call_ode_fn(ode_fn: Callable, z: float, t: float,
                ctx: Optional[ODEContext] = None) -> float:
    """Вызвать ``ode_fn`` в старой (``z, t``) или новой (``z, t, ctx``) форме."""
    if ode_fn_arity(ode_fn) >= 3:
        return ode_fn(z, t, ctx)
    return ode_fn(z, t)
