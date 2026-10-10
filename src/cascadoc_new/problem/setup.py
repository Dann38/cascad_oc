from typing import Callable, Tuple, Optional

from ..system.system import System
from ..mesh.mesh import CharacteristicMesh
from ..solvers.solver import TrapezoidalSolver
from ..blocks import HypBlock, ODEBlock, PlainBoundaryBlock


def _register_variables(
    sys: System,
    S: Tuple[float, float],
    T: Tuple[float, float],
    C: Tuple[float, float],
    B: Tuple[Callable, Callable, Callable, Callable],
    F: Tuple[Callable, Callable],
    G: Tuple[Tuple[Callable, Callable], Tuple[Callable, Callable]],
    x0: Callable[[float], float],
    y0: Callable[[float], float],
    phi_dx: Callable[[float, float, float], float],
    phi_dy: Callable[[float, float, float], float],
) -> System:
    """Зарегистрировать переменные гиперболической задачи в системе."""
    # ---- аналитические константы области (функции от Point) ----
    sys.var_analytic('C1', lambda point: C[0])
    sys.var_analytic('C2', lambda point: C[1])
    sys.var_analytic('S0', lambda point: S[0])
    sys.var_analytic('S1', lambda point: S[1])
    sys.var_analytic('T0', lambda point: T[0])
    sys.var_analytic('T1', lambda point: T[1])

    # ---- аналитические коэффициенты уравнений (пользовательские f(s, t)) ----
    sys.var_analytic('B11', lambda point: B[0](point.s, point.t))
    sys.var_analytic('B12', lambda point: B[1](point.s, point.t))
    sys.var_analytic('B21', lambda point: B[2](point.s, point.t))
    sys.var_analytic('B22', lambda point: B[3](point.s, point.t))
    sys.var_analytic('F1', lambda point: F[0](point.s, point.t))
    sys.var_analytic('F2', lambda point: F[1](point.s, point.t))

    sys.var_analytic('G11', lambda point: G[0][0](point.t))
    sys.var_analytic('G12', lambda point: G[0][1](point.t))
    sys.var_analytic('G21', lambda point: G[1][0](point.t))
    sys.var_analytic('G22', lambda point: G[1][1](point.t))

    # ---- начальные данные прямого хода (аналитически по s) ----
    sys.var_analytic('x0', lambda point: x0(point.s))
    sys.var_analytic('y0', lambda point: y0(point.s))

    # ---- терминальные условия сопряжённого хода (зависят от состояния) ----
    sys.var_callable('phi_dx', lambda point, x, y: phi_dx(point.s, x, y))
    sys.var_callable('phi_dy', lambda point, x, y: phi_dy(point.s, x, y))

    # ---- численные (векторные) переменные ----
    sys.var_numeric('X', dim=2)      # [x, y] — вектор состояния
    sys.var_numeric('PSI', dim=2)    # [psi1, psi2] — сопряжённый вектор
    sys.var_numeric('p', dim=1)      # граничный прокси управления (скаляр)

    return sys


def build_hyp_system(
    S: Tuple[float, float],
    T: Tuple[float, float],
    C: Tuple[float, float],
    B: Tuple[Callable, Callable, Callable, Callable],
    F: Tuple[Callable, Callable],
    G: Tuple[Tuple[Callable, Callable], Tuple[Callable, Callable]],
    x0: Callable[[float], float],
    y0: Callable[[float], float],
    phi_dx: Callable[[float, float, float], float],
    phi_dy: Callable[[float, float, float], float],
    m: Optional[int] = None,
    h: Optional[float] = None,
) -> Tuple[System, CharacteristicMesh, TrapezoidalSolver]:
    sys = _register_variables(System(), S, T, C, B, F, G, x0, y0, phi_dx, phi_dy)

    mesh = CharacteristicMesh(sys, m=m, h=h)
    solver = TrapezoidalSolver(sys)

    return sys, mesh, solver


def build_hyp_blocks(
    S: Tuple[float, float],
    T: Tuple[float, float],
    C: Tuple[float, float],
    B: Tuple[Callable, Callable, Callable, Callable],
    F: Tuple[Callable, Callable],
    G: Tuple[Tuple[Callable, Callable], Tuple[Callable, Callable]],
    x0: Callable[[float], float],
    y0: Callable[[float], float],
    phi_dx: Callable[[float, float, float], float],
    phi_dy: Callable[[float, float, float], float],
    m: Optional[int] = None,
    h: Optional[float] = None,
    boundaries: str = 'ode',
    bc_left: Optional[Callable[[float], float]] = None,
    bc_right: Optional[Callable[[float], float]] = None,
) -> Tuple[System, CharacteristicMesh, HypBlock]:
    """Собрать гиперболическую систему как композицию блоков.

    ``boundaries='ode'``   — границы заданы ОДУ (``ODEBlock``);
    ``boundaries='plain'`` — границы заданы напрямую (``PlainBoundaryBlock``),
    значения берутся из ``bc_left(t)`` / ``bc_right(t)``.

    После сборки решение запускается через ``sys.solve()`` (послойно по ``t``).
    """
    sys = _register_variables(System(), S, T, C, B, F, G, x0, y0, phi_dx, phi_dy)
    mesh = CharacteristicMesh(sys, m=m, h=h)

    hyp = HypBlock('hyp', sys, mesh)
    sys.add_block(hyp)

    if boundaries == 'ode':
        sys.add_block(ODEBlock('ode_left', sys, mesh, side='left'))
        sys.add_block(ODEBlock('ode_right', sys, mesh, side='right'))
    elif boundaries == 'plain':
        if bc_left is None or bc_right is None:
            raise ValueError("Для boundaries='plain' нужны bc_left и bc_right")
        sys.add_block(PlainBoundaryBlock('plain_left', sys, mesh, 'left', bc_left))
        sys.add_block(PlainBoundaryBlock('plain_right', sys, mesh, 'right', bc_right))
    else:
        raise ValueError(f"Неизвестный режим границ: {boundaries!r}")

    return sys, mesh, hyp
