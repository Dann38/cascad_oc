from __future__ import annotations
from typing import Callable, Dict, List, Optional, Union, Tuple
from ..core.variable import Variable, AnalyticVariable, NumericVariable
from .node import Node
from ..core.point import Point


class System:
    def __init__(self):
        self.variables: Dict[str, Variable] = {}
        self.functions: Dict[str, Callable] = {}
        self.blocks: List = []

    def var_callable(self, name: str, fn: Callable) -> Callable:
        """Произвольная функция, не привязанная к точке сетки.

        Например, терминальное условие сопряжённой задачи phi_dx(point, x, y),
        зависящее от состояния x, y, а не только от координаты point.
        """
        self.functions[name] = fn
        return fn

    def get_callable(self, name: str) -> Callable:
        return self.functions[name]

    def var_analytic(self, name: str, fn: Callable,
                     dim: Union[int, Tuple[int, ...]] = 1) -> AnalyticVariable:
        """Аналитическая переменная fn(point) → скаляр/вектор.

        Вместо функции можно передать константу: ``sys.var_analytic('C1', 1)``.
        """
        if name in self.variables:
            raise ValueError(f"Variable '{name}' already registered")
        v = AnalyticVariable(name, fn, dim=dim)
        self.variables[name] = v
        return v

    def var_const(self, name: str, value,
                  dim: Union[int, Tuple[int, ...]] = 1) -> AnalyticVariable:
        """Сахар для константы: ``sys.var_const('C1', 1)``."""
        return self.var_analytic(name, value, dim=dim)

    def var_numeric(self, name: str, dim: int = 1) -> NumericVariable:
        if name in self.variables:
            raise ValueError(f"Variable '{name}' already registered")
        v = NumericVariable(name, dim)
        self.variables[name] = v
        return v

    def get_var(self, name: str) -> Variable:
        return self.variables[name]

    def node(self, point: Point, t: Optional[float] = None) -> Node:
        if t is not None:
            point = Point(point, t)  # совместимость: node(s, t)
        return Node(point, system=self)

    # ------------------------------------------------------------- композиция
    def add_block(self, block):
        """Зарегистрировать блок в композиции системы."""
        block.system = self
        self.blocks.append(block)
        return block

    def solve(self) -> None:
        """Решить композицию блоков послойно по времени ``t``.

        Слои берутся у всех блоков и обрабатываются по возрастанию ``t``.
        На каждом слое блоки решают свои узлы независимо: зависимости любого
        узла лежат строго на более ранних слоях, поэтому порядок блоков внутри
        слоя не важен.
        """
        if not self.blocks:
            return
        times = sorted({t for block in self.blocks for t in block.layer_times()})
        for t in times:
            for block in self.blocks:
                if block.has_layer(t):
                    block.solve_layer(t)
        for block in self.blocks:
            block.finalize(times[-1])

    def list_variables(self) -> List[str]:
        return list(self.variables.keys())

    def list_analytic(self) -> List[str]:
        return [n for n, v in self.variables.items()
                if isinstance(v, AnalyticVariable)]

    def list_numeric(self) -> List[str]:
        return [n for n, v in self.variables.items()
                if isinstance(v, NumericVariable)]

    def dim(self, name: str) -> int:
        return self.variables[name].dim

    def __repr__(self):
        a = len(self.list_analytic())
        n = len(self.list_numeric())
        b = len(self.blocks)
        return f"System(vars={a+n}:{a}anal+{n}num, blocks={b})"