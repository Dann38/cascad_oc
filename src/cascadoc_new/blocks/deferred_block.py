from __future__ import annotations
from typing import Callable, List, Optional, Union

import numpy as np

from ..system.block import Block
from ..system.system import System
from ..mesh.mesh import CharacteristicMesh
from .boundary import boundary_plain_step


class DeferredBoundaryBlock(Block):
    """Граничный блок, читающий значение из отложенной переменной.

    На ``side='right'``: читает ``x`` из ``deferred_var``, ``y`` считает
    из приходящей характеристики.
    На ``side='left'``: читает ``y`` из ``deferred_var``, ``x`` считает
    из приходящей характеристики.

    Блок зависит от блока, который производит ``deferred_var``
    (указывается в ``source_block``).
    """

    def __init__(self, name: str, system: System, mesh: CharacteristicMesh,
                 side: str, deferred_var: str,
                 source_block: Optional[str] = None) -> None:
        super().__init__(name, system)
        if side not in ('left', 'right'):
            raise ValueError(f"side должно быть 'left' или 'right', дано {side!r}")
        self.mesh = mesh
        self.side = side
        self.s_const = mesh.S0 if side == 'left' else mesh.S1
        self.deferred_var = deferred_var
        if source_block:
            self.depends_on = [source_block]

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

            val = node[self.deferred_var]

            if self.side == 'left':
                char = mesh.get_center_node_right(i, j)
                node['X'] = boundary_plain_step(
                    self.system, node.point, char.point, char['X'],
                    float(val), 'left')
            else:
                char = mesh.get_center_node_left(i, j)
                node['X'] = boundary_plain_step(
                    self.system, node.point, char.point, char['X'],
                    float(val), 'right')