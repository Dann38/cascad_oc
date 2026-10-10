"""``HypBlock`` — гиперболический блок (ДУЧП) без знания о граничных ОДУ.

Блок решает только «свою» часть узлов:

* начальный слой ``t = T0`` (данные ``x0, y0``);
* внутренние узлы ``S0 < s < S1`` на каждом слое;
* выходной слой ``t = T1``.

Узлы на границах ``s = S0`` и ``s = S1`` (шаг 1 — «граница просто задана»,
шаг 2 — «граница как ОДУ») решаются соседними блоками (``ODEBlock`` /
``PlainBoundaryBlock``), которые пишут значения в те же точки хранилища.
Именно поэтому ``HypBlock`` не содержит коэффициентов ``G`` и не различает,
чем задана граница.
"""
from __future__ import annotations
from typing import List

from ..system.block import Block
from ..system.system import System
from ..mesh.mesh import CharacteristicMesh
from ..solvers.solver import TrapezoidalSolver


class HypBlock(Block):
    """Гиперболический ДУЧП-блок на характеристической сетке."""

    def __init__(self, name: str, system: System, mesh: CharacteristicMesh) -> None:
        super().__init__(name, system)
        self.mesh = mesh
        self.solver = TrapezoidalSolver(system)

    # ------------------------------------------------------------------ слои
    def layer_times(self) -> List[float]:
        times = {self.mesh.T0, self.mesh.T1}
        times.update(node.t for node in self.mesh.nodes_center)
        return sorted(times)

    def solve_layer(self, t: float) -> None:
        if t == self.mesh.T0:
            self.solver.solve_initial(self.mesh)
        self._solve_center_interior(t)

    def finalize(self, t_last: float) -> None:
        """Собрать узлы выходной границы ``t = T1``.

        Выполняется после того, как граничные блоки закончили свои узлы на
        этом слое (они нужны как соседи при сборке выходной границы).
        """
        self.solver.solve_final(self.mesh)

    # --------------------------------------------------------------- внутренние
    def _solve_center_interior(self, t: float) -> None:
        """Решить внутренние узлы ``S0 < s < S1`` на слое ``t``.

        Граничные узлы (``s == S0`` / ``s == S1``) пропускаются — их ведут
        соседние блоки границы.
        """
        mesh, S0, S1 = self.mesh, self.mesh.S0, self.mesh.S1
        for i, j in mesh.order_center:
            node = mesh.center[(i, j)]
            if node.t != t:
                continue
            s = node.s
            if s == S0 or s == S1:
                continue
            left = mesh.get_center_node_left(i, j)
            right = mesh.get_center_node_right(i, j)
            node['X'] = self.solver.center_solve(
                node.point, left.point, right.point, left['X'], right['X'])
