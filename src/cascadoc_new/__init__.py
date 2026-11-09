"""CascadOC — новая архитектура решения каскадных систем ДУЧП + ОДУ.

Пакет разбит на подпакеты:

* :mod:`cascadoc_new.core`    — базовые типы (``Point``, ``Variable``, ``utils``);
* :mod:`cascadoc_new.system`  — реестр переменных и узлы (``System``, ``Node``);
* :mod:`cascadoc_new.mesh`    — характеристическая сетка (``CharacteristicMesh``);
* :mod:`cascadoc_new.solvers` — решатели (``Solver``, ``TrapezoidalSolver``);
* :mod:`cascadoc_new.problem` — сборка задачи (``build_hyp_blocks``);
* :mod:`cascadoc_new.viz`     — визуализация (``Plotter`` и функции-обёртки).

Публичный API остаётся плоским: всё перечисленное доступно прямо из
``cascadoc_new``.

============================================================================
АРХИТЕКТУРНАЯ ЗАМЕТКА: кейс ``cases/case1/case1.md`` (роль: архитектор)
============================================================================

ВНИМАНИЕ: постановка кейса ИЗМЕНИЛАСЬ. Прежние выводы («прямой DAG»,
«``x(s1,t)=N(t)`` задано → ``ODESourceBlock`` с ``N(t)`` явно», «петли нет»)
УСТАРЕЛИ и здесь исправлены.

ПОСТАНОВКА (актуальная). Независимые ``s in [s0, s1]``, ``t in [t0, t1]``;
заданы ``c1, c2, B11..B22(s,t), F1, F2(s,t), N(t), f(z, t), x0, y0``.
ДУЧП 2x2: ``x_t - c1 x_s = B11 x + B12 y + F1``,
``y_t + c2 y_s = B21 x + B22 y + F2``; НУ ``x(s,t0)=x0(s), y(s,t0)=y0(s)``;
ГУ ``x(s1,t)=N(t)``, ``y(s0,t)=z(t)``;
ОДУ ``dz/dt = f(t, z, x(s0,t))``, ``z(t0)=y0(s0)``.
(Было ``x(s1,t)`` в правой части ОДУ — теперь ``x(s0,t)``.)
Неизвестные ``x, y, z``; ``z`` — фиктивная, ``z ≡ y(s0,t)``.

ГЛАВНОЕ СЛЕДСТВИЕ. ``x(s0,t)`` — СТОК левой характеристики (не задано).
Левое ГУ требует ``y(s0,t)=z(t)``, а ``x(s0,t)`` считается изнутри
(``boundary_plain_step(side='left')``) И подаётся в ``f``. Возникает ЗАМКНУТАЯ
связка на каждом слое:
    ``x(s0,t) ↔ z(t) ↔ y(s0,t)=z ↔ ДУЧП``.
Это уже НЕ DAG: топосортировки блоков недостаточно, нужен ИТЕРАТИВНЫЙ решатель
связки ВНУТРИ слоя.

Связка слоя ``t_k`` (вывод из кода ``boundary_plain_step``, ``boundary.py:101-111``):
    (a) ``x_k = α·z_k + ρ_k``,  ``α = (d1T/2)·B12 / (1-(d1T/2)·B11)``,
        ``d1T = dS/c1``; ``ρ_k`` — из приходящей справа характеристики;
    (b) ``z_k = z_{k-1} + (dT/2)[ f(t_k,z_k,x_k) + f(t_{k-1},z_{k-1},x_{k-1}) ]``,
        ``dT = d1T+d2T``.
Свести к скаляру: ``z_k = G(z_k)``; ``q = (dT/2)(L_z + α·L_w) = O(dT) < 1`` при
малом шаге → простое сжатие (обоснование: ``math/04_petlya_svyazannaya_sistema.md``
§4.3). Даёт порядок 2; «явный» проход с ``x(s0,t_{k-1})`` — лишь порядок 1
(``math/04`` §4.4, численно подтверждено).

ГОТОВОГО МЕХАНИЗМА ИТЕРАЦИЙ В КОДЕ НЕТ. Есть только математика (``math/04``),
демо ``math/numerics/loop_demo.py`` и диагностика ``_audit_diag_*.py``. В
``src/`` нет ни SCC, ни послойной итерации, ни ``peek``, ни Ньютона.

ЭСКИЗ СБОРКИ (минимальный путь: новый блок связки; см. §6 плана):

    sys, mesh, _ = build_hyp_system(
        S=(s0, s1), T=(t0, t1), C=(c1, c2),
        B=(B11, B12, B21, B22), F=(F1, F2),
        G=((lambda t: 0.0, lambda t: 0.0),
           (lambda t: 0.0, lambda t: 0.0)),       # для прямого кейса не нужно
        x0=x0, y0=y0,
        phi_dx=lambda s, x, y: 0.0, phi_dy=lambda s, x, y: 0.0,
        m=40)

    sys.var_numeric('Z_numeric', dim=1)            # хранилище z (z ≡ y(s0,·))

    sys.add_block(HypBlock('hyp', sys, mesh))
    sys.add_block(PlainBoundaryBlock('right_plain', sys, mesh,      # x(s1,t)=N(t)
                                     'right', value_fn=N))

    coupled = CoupledBoundaryBlock(                # блок связки (реализован, M2)
        'left_coupled', sys, mesh, side='left',
        source_var='Z_numeric',
        ode_fn=lambda z, t, ctx: f(t, z, ctx.x('left')),  # x(s0,t) ТОГО ЖЕ слоя
        init_val=y0(s0),
        method='fixed_point', tol=1e-12, max_iter=50)
    coupled.depends_on = ['hyp']                   # входной слой start_l/start_r
    sys.add_block(coupled)

    sys.solve()

``CoupledBoundaryBlock`` владеет и границей (``y(s0,t)=z`` + ``x`` по
характеристике), и шагом ОДУ, и гоняет итерации по слою до сходимости. Поэтому
``System.solve`` менять не обязательно (минимальный путь). Общий путь —
SCC-группа ``[z_source, left_deferred]`` + послойная итерация в ``System.solve``
+ ``Block.residual`` + ``DeferredVariable.peek`` (см. §6.2 плана).

ЗАВИСИМОСТИ/ПОРЯДОК. Входной слой ``start_l/start_r`` заполняет только
``HypBlock.solve_layer(T0)``; поэтому граничным/связующим блокам нужен ЯВНЫЙ
``depends_on=['hyp']``. Правая граница независима. Внутренность и выходной слой
слоя в связку НЕ входят.

ПРОБЕЛЫ (блокирующие для O(dt^2)): M1 контекстный ``ode_fn``
(``blocks/ode_source.py:21``); M3 SCC + послойная итерация
(``system/system.py:104-105`` и ``:118-121``); M5 ``DeferredVariable.peek``
(``core/variable.py:100-107``). Детали и весь список M1–M8 — в
``.kilo/plans/1794223868393-case1-architecture.md`` и в заметках подпакетов
``problem/``, ``blocks/``, ``core/``, ``system/``.

ЧТО ЗАКРЫВАЕТ ТРЕБОВАНИЕ «ОТРИСОВАТЬ НЕИЗВЕСТНУЮ И ЕЁ СРЕЗ». Любая
неизвестная: ``X`` (вектор ``[x, y]``) и ``Z_numeric`` (``z``). Срез
``x(s, t1)``: ``Plotter.plot_slice([('X', 0)], t=mesh.T1)``. Поля:
``Plotter.plot_field('X', component=0)``. См. ``viz/__init__.py``.
"""
from .core import (Point, Variable, AnalyticVariable, NumericVariable,
                    DeferredVariable, normalize_float, PRECISION)
from .system import Node, System, Block
from .mesh import CharacteristicMesh
from .solvers import Solver, TrapezoidalSolver
from .blocks import (boundary_ode_step, boundary_plain_step,
                     HypBlock, ODEBlock, PlainBoundaryBlock,
                     ODESourceBlock, DeferredBoundaryBlock,
                     CoupledBoundaryBlock, ODEContext, call_ode_fn)
from .problem import build_hyp_system, build_hyp_blocks
from .viz import Plotter, plot_mesh, plot_field, plot_slice, plot_surface

__all__ = [
    'Point',
    'Variable', 'AnalyticVariable', 'NumericVariable', 'DeferredVariable',
    'Node',
    'System',
    'Block',
    'CharacteristicMesh',
    'Solver', 'TrapezoidalSolver',
    'HypBlock', 'ODEBlock', 'PlainBoundaryBlock',
    'ODESourceBlock', 'DeferredBoundaryBlock',
    'CoupledBoundaryBlock', 'ODEContext', 'call_ode_fn',
    'boundary_ode_step', 'boundary_plain_step',
    'build_hyp_system', 'build_hyp_blocks',
    'Plotter', 'plot_mesh', 'plot_field', 'plot_slice', 'plot_surface',
    'normalize_float', 'PRECISION',
]
