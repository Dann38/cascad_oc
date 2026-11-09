from __future__ import annotations
from typing import Callable, List, Optional

import numpy as np

from ..system.block import Block
from ..system.system import System
from ..mesh.mesh import CharacteristicMesh
from .ode_context import ODEContext, call_ode_fn


class ODESourceBlock(Block):
    """Решает ОДУ и пишет результат в ``NumericVariable``.

    Блок-источник для отложенных переменных: на каждом слое ``t`` решает
    ``dz/dt = ode_fn(z, t)`` и сохраняет ``z`` в ``source_var``.

    ``init_val`` — значение ``z`` на ``t = T0``.

    Поддерживаются обе формы правой части:

    * старая ``ode_fn(z, t)`` — как раньше;
    * новая ``ode_fn(z, t, ctx)`` — ``ctx`` (см. :class:`ODEContext`) даёт
      доступ к системе/точке слоя и к ``x`` на границе (``ctx.x('left')``,
      ``ctx.x('right')``), что нужно для ОДУ, связанного с ДУЧП.
    """

    def __init__(self, name: str, system: System, mesh: CharacteristicMesh,
                 source_var: str,
                 ode_fn: Callable[..., float],
                 init_val: float, side: str) -> None:
        super().__init__(name, system)
        self.mesh = mesh
        self.source_var = source_var
        self.ode_fn = ode_fn
        self.init_val = init_val
        self.side = side
        self.s_const = mesh.S0 if side == 'left' else mesh.S1

    @property
    def provides(self) -> str:
        return self.source_var

    def _boundary_nodes(self):
        return sorted(
            [n for n in self.mesh.nodes_center if n.point[0] == self.s_const],
            key=lambda n: n.point[1])

    def layer_times(self) -> List[float]:
        return sorted({n.point[1] for n in self._boundary_nodes()})

    def _find_node_at(self, t: float):
        for n in self._boundary_nodes():
            if abs(n.point[1] - t) < 1e-12:
                return n
        return None

    def solve_layer(self, t: float) -> None:
        times = self.layer_times()
        if t not in times:
            return
        node = self._find_node_at(t)
        if node is None:
            return

        idx = times.index(t)
        if idx == 0:
            node[self.source_var] = self.init_val
            return

        t_prev = times[idx - 1]
        prev_node = self._find_node_at(t_prev)
        if prev_node is None:
            return

        z_prev = prev_node[self.source_var]
        if z_prev is None:
            return
        dt = t - t_prev
        ctx_prev = ODEContext(self.system, prev_node.point)
        ctx = ODEContext(self.system, node.point)
        f_prev = call_ode_fn(self.ode_fn, z_prev, t_prev, ctx_prev)

        z_new = z_prev + dt * f_prev

        for _ in range(20):
            f_new = call_ode_fn(self.ode_fn, z_new, t, ctx)
            z_next = z_prev + 0.5 * dt * (f_prev + f_new)
            if abs(z_next - z_new) < 1e-14:
                z_new = z_next
                break
            z_new = z_next

        node[self.source_var] = z_new