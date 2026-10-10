"""CascadOC — новая архитектура решения каскадных систем ДУЧП + ОДУ.

Пакет разбит на подпакеты:

* :mod:`cascadoc_new.core`    — базовые типы (``Point``, ``Variable``, ``utils``);
* :mod:`cascadoc_new.system`  — реестр переменных и узлы (``System``, ``Node``);
* :mod:`cascadoc_new.mesh`    — характеристическая сетка (``CharacteristicMesh``);
* :mod:`cascadoc_new.solvers` — решатели (``Solver``, ``TrapezoidalSolver``);
* :mod:`cascadoc_new.problem` — сборка задачи (``build_hyp_system``);
* :mod:`cascadoc_new.viz`     — визуализация (``Plotter`` и функции-обёртки).

Публичный API остаётся плоским: всё перечисленное доступно прямо из
``cascadoc_new``.
"""
from .core import Point, Variable, AnalyticVariable, NumericVariable, normalize_float, PRECISION
from .system import Node, System, Block
from .mesh import CharacteristicMesh
from .solvers import Solver, TrapezoidalSolver
from .blocks import (boundary_ode_step, boundary_plain_step,
                     HypBlock, ODEBlock, PlainBoundaryBlock)
from .problem import build_hyp_system, build_hyp_blocks
from .viz import Plotter, plot_mesh, plot_field, plot_slice, plot_surface

__all__ = [
    'Point',
    'Variable', 'AnalyticVariable', 'NumericVariable',
    'Node',
    'System',
    'Block',
    'CharacteristicMesh',
    'Solver', 'TrapezoidalSolver',
    'HypBlock', 'ODEBlock', 'PlainBoundaryBlock',
    'boundary_ode_step', 'boundary_plain_step',
    'build_hyp_system', 'build_hyp_blocks',
    'Plotter', 'plot_mesh', 'plot_field', 'plot_slice', 'plot_surface',
    'normalize_float', 'PRECISION',
]
