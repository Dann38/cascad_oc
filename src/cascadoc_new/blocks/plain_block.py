"""``PlainBoundaryBlock`` — шаг 1: граница задана напрямую, без ОДУ.

Это самый простой вид границы: недостающая компонента известна как функция
времени ``value_fn(t)`` (например, из начальных данных или извне), а вторая
компонента досчитывается по приходящей характеристике. Позже такой блок
заменяется на ``ODEBlock`` с той же ролью — отсюда единая композиция.
"""
from __future__ import annotations
from typing import Callable, List

from ..system.block import Block
from ..system.system import System
from ..mesh.mesh import CharacteristicMesh
from .boundary import boundary_plain_step


class PlainBoundaryBlock(Block):
    """Граница ``s = const`` со значением, заданным функцией времени."""

    def __init__(self, name: str, system: System, mesh: CharacteristicMesh,
                 side: str, value_fn: Callable[[float], float]) -> None:
        super().__init__(name, system)
        if side not in ('left', 'right'):
            raise ValueError(f"side должно быть 'left' или 'right', дано {side!r}")
        self.mesh = mesh
        self.side = side
        self.s_const = mesh.S0 if side == 'left' else mesh.S1
        self.value_fn = value_fn

    def _boundary_nodes(self):
        return [node for node in self.mesh.nodes_center if node.s == self.s_const]

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
            else:
                char = mesh.get_center_node_left(i, j)

            node['X'] = boundary_plain_step(
                self.system, node.point, char.point, char['X'],
                float(self.value_fn(node.t)), self.side)
