"""``ODEBlock`` — граница, заданная ОДУ, сцепленным с гиперболическим блоком.

В отличие от ``HypBlock``, блок знает только про границу ``s = const`` и про
ОДУ на ней (коэффициенты ``G``). Значения приходящей характеристики он берёт
из узлов, уже посчитанных ``HypBlock``; недостающую компоненту считает шагом
``boundary_ode_step`` (шаг 3 — переиспользуемая логика граничного ОДУ).

Композиция собирается в ``System``: ``HypBlock`` решает внутренность, два
``ODEBlock`` (слева и справа) — границы. Обмен идёт через общее хранилище
``NumericVariable``: узел ``Point(s, t)`` один и тот же для обоих блоков.
"""
from __future__ import annotations
from typing import List

from ..system.block import Block
from ..system.system import System
from ..mesh.mesh import CharacteristicMesh
from .boundary import boundary_ode_step


class ODEBlock(Block):
    """Граничный ОДУ-блок на ``s = S0`` (left) или ``s = S1`` (right)."""

    def __init__(self, name: str, system: System, mesh: CharacteristicMesh,
                 side: str) -> None:
        super().__init__(name, system)
        if side not in ('left', 'right'):
            raise ValueError(f"side должно быть 'left' или 'right', дано {side!r}")
        self.mesh = mesh
        self.side = side
        self.s_const = mesh.S0 if side == 'left' else mesh.S1

    # ------------------------------------------------------------------ слои
    def _boundary_nodes(self):
        return [node for node in self.mesh.nodes_center
                if node.s == self.s_const]

    def layer_times(self) -> List[float]:
        return sorted({node.t for node in self._boundary_nodes()})

    def solve_layer(self, t: float) -> None:
        mesh = self.mesh
        for i, j in mesh.order_center:
            node = mesh.center[(i, j)]
            if node.t != t or node.s != self.s_const:
                continue

            if self.side == 'left':
                char = mesh.get_center_node_right(i, j)
                prev = mesh.get_s0_node_left(i, j)
            else:
                char = mesh.get_center_node_left(i, j)
                prev = mesh.get_s1_node_right(i, j)

            node['X'] = boundary_ode_step(
                self.system, node.point,
                prev.point, prev['X'], char.point, char['X'], self.side)
