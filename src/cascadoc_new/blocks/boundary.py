"""Переиспользуемые шаги для граничных узлов гиперболической системы.

Оба шага решают одну и ту же задачу — «досчитать узел на границе области,
зная приходящую характеристику», — но граничное условие задаётся по-разному:

* ``boundary_plain_step`` — граница задана напрямую значением (шаг 1);
* ``boundary_ode_step``   — граница задана ОДУ, сцепленным с ДУЧП (шаги 2–3).

Одна и та же логика используется и на ``s = S0`` (``side='left'``), и на
``s = S1`` (``side='right'``): меняются лишь роли компонент.

Схема дискретизации — трапеции (Crank–Nicolson) вдоль характеристик.
"""
from __future__ import annotations
from typing import Tuple

import numpy as np

from ..system.system import System
from ..core.point import Point

State = np.ndarray


def _coef(system: System, name: str, point: Point) -> float:
    return float(system.variables[name].at(point))


def boundary_ode_step(
    system: System,
    point: Point,
    prev_point: Point, prev_state: State,
    char_point: Point, char_state: State,
    side: str,
) -> State:
    """Один шаг граничного ОДУ, сцепленного с характеристикой.

    ``side='left'``  (s = S0): ОДУ задаёт компоненту 1 (y) через ``G21, G22``,
    компонента 0 (x) приходит по характеристике справа.

    ``side='right'`` (s = S1): ОДУ задаёт компоненту 0 (x) через ``G11, G12``,
    компонента 1 (y) приходит по характеристике слева.

    ``prev_*`` — тот же граничный узел на предыдущем слое (шаг ОДУ),
    ``char_*`` — приходящая характеристика (шаг ДУЧП).
    """
    if side == 'left':
        dt_ode = point.t - prev_point.t
        dt_char = point.t - char_point.t

        B11, B12 = _coef(system, 'B11', point), _coef(system, 'B12', point)
        B11c, B12c = _coef(system, 'B11', char_point), _coef(system, 'B12', char_point)
        F1, F1c = _coef(system, 'F1', point), _coef(system, 'F1', char_point)
        G21, G22 = _coef(system, 'G21', point), _coef(system, 'G22', point)
        G21p, G22p = _coef(system, 'G21', prev_point), _coef(system, 'G22', prev_point)

        A = [[1 - dt_char / 2 * B11, -dt_char / 2 * B12],
             [-dt_ode / 2 * G21, 1 - dt_ode / 2 * G22]]
        b = [char_state[0] + dt_char / 2 *
             (B11c * char_state[0] + B12c * char_state[1] + F1 + F1c),
             prev_state[1] + dt_ode / 2 *
             (G21p * prev_state[0] + G22p * prev_state[1])]
        return np.linalg.solve(A, b)

    if side == 'right':
        dt_char = point.t - char_point.t
        dt_ode = point.t - prev_point.t

        B21, B22 = _coef(system, 'B21', point), _coef(system, 'B22', point)
        B21c, B22c = _coef(system, 'B21', char_point), _coef(system, 'B22', char_point)
        F2, F2c = _coef(system, 'F2', point), _coef(system, 'F2', char_point)
        G11, G12 = _coef(system, 'G11', point), _coef(system, 'G12', point)
        G11p, G12p = _coef(system, 'G11', prev_point), _coef(system, 'G12', prev_point)

        A = [[1 - dt_ode / 2 * G11, -dt_ode / 2 * G12],
             [-dt_char / 2 * B21, 1 - dt_char / 2 * B22]]
        b = [prev_state[0] + dt_ode / 2 *
             (G11p * prev_state[0] + G12p * prev_state[1]),
             char_state[1] + dt_char / 2 *
             (B21c * char_state[0] + B22c * char_state[1] + F2 + F2c)]
        return np.linalg.solve(A, b)

    raise ValueError(f"Неизвестная граница: {side!r} (ожидается 'left' или 'right')")


def boundary_plain_step(
    system: System,
    point: Point,
    char_point: Point, char_state: State,
    value: float,
    side: str,
) -> State:
    """Шаг границы, заданной напрямую значением (без ОДУ).

    ``side='left'``:  известна компонента 1 (y) = ``value``, компонента 0 (x)
    считается из приходящей характеристики.

    ``side='right'``: известна компонента 0 (x) = ``value``, компонента 1 (y)
    считается из приходящей характеристики.
    """
    if side == 'left':
        dt_char = point.t - char_point.t
        B11, B12 = _coef(system, 'B11', point), _coef(system, 'B12', point)
        B11c, B12c = _coef(system, 'B11', char_point), _coef(system, 'B12', char_point)
        F1, F1c = _coef(system, 'F1', point), _coef(system, 'F1', char_point)

        a00 = 1 - dt_char / 2 * B11
        rhs = (char_state[0] + dt_char / 2 *
               (B11c * char_state[0] + B12c * char_state[1] + F1 + F1c))
        x = (rhs + dt_char / 2 * B12 * value) / a00
        return np.array([x, value])

    if side == 'right':
        dt_char = point.t - char_point.t
        B21, B22 = _coef(system, 'B21', point), _coef(system, 'B22', point)
        B21c, B22c = _coef(system, 'B21', char_point), _coef(system, 'B22', char_point)
        F2, F2c = _coef(system, 'F2', point), _coef(system, 'F2', char_point)

        a11 = 1 - dt_char / 2 * B22
        rhs = (char_state[1] + dt_char / 2 *
               (B21c * char_state[0] + B22c * char_state[1] + F2 + F2c))
        y = (rhs + dt_char / 2 * B21 * value) / a11
        return np.array([value, y])

    raise ValueError(f"Неизвестная граница: {side!r} (ожидается 'left' или 'right')")
