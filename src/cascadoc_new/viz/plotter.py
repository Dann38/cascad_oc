"""Отрисовка результатов для cascadoc_new.

Весь код, связанный с визуализацией, вынесен сюда из ``mesh``/``system``:
ни сетка, ни решатель больше не знают о matplotlib. Визуализация работает
поверх готовых ``System`` и ``CharacteristicMesh``.

Основные возможности (2D-задачи, область (s, t)):

* ``plot_mesh``     — геометрия характеристической сетки;
* ``plot_field``    — псевдоцветное поле любой функции на (s, t);
* ``plot_slice``    — разрез при фиксированном ``s`` или ``t``; можно вывести
                      сразу несколько функций на одном графике;
* ``plot_surface``  — 3D-поверхность z = f(s, t).

Функция для отрисовки задаётся одним из способов:

* ``'X'``                 — имя переменной System (численной или аналитической);
* ``('X', 1)``            — компонента векторной переменной;
* ``lambda point: ...``   — ``f(Point) -> float``;
* ``lambda s, t: ...``    — ``f(s, t) -> float``;
* число                   — константа.

Численные переменные рисуются по узлам сетки (это фактические данные решения),
аналитические и callable — по непрерывной линии (``samples`` точек), поэтому
численное решение и аналитический эталон удобно сравнивать на одном графике.
"""
from __future__ import annotations

import inspect
from typing import Callable, Dict, List, Optional, Sequence, Tuple, Union

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.tri as mtri
from matplotlib.collections import LineCollection

from ..core.point import Point
from ..system.system import System
from ..mesh.mesh import CharacteristicMesh
from ..core.variable import NumericVariable
from ..core.utils import PRECISION

#: Выражение, которое можно отрисовать.
Expr = Union[str, Tuple[str, int], Callable, float, int]

_GROUPS = ('center', 'start_l', 'start_r', 'final_l', 'final_r')


class Plotter:
    """Набор функций отрисовки для пары ``System`` + ``CharacteristicMesh``.

    Все методы принимают необязательный ``ax`` (``matplotlib.axes.Axes``) и
    возвращают его же, чтобы графики можно было компоновать в подграфики::

        viz = Plotter(sys, mesh)
        fig, axes = plt.subplots(1, 2)
        viz.plot_slice([('X', 0), x_an], t=mesh.T1, ax=axes[0])
        viz.plot_field('PSI', component=0, ax=axes[1])
    """

    def __init__(self, system: System, mesh: CharacteristicMesh) -> None:
        self.sys = system
        self.mesh = mesh
        self._nodes_cache: Optional[List] = None

    # ============================================================ внутреннее
    @staticmethod
    def _num_params(fn: Callable) -> int:
        try:
            sig = inspect.signature(fn)
        except (TypeError, ValueError):
            return 1
        return sum(
            1 for p in sig.parameters.values()
            if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)
        )

    def _all_nodes(self) -> List:
        """Все уникальные узлы сетки (по координате), кэшируется."""
        if self._nodes_cache is None:
            seen: Dict[Tuple[float, float], object] = {}
            for group in _GROUPS:
                for node in getattr(self.mesh, 'nodes_' + group):
                    key = (round(node.s, PRECISION), round(node.t, PRECISION))
                    seen.setdefault(key, node)
            self._nodes_cache = list(seen.values())
        return self._nodes_cache

    def _make_getter(self, expr: Expr, component: int = 0):
        """Вернуть ``(get(node) -> float, label, is_numeric)`` для выражения."""
        name = None
        comp = component
        if isinstance(expr, str):
            name = expr
        elif isinstance(expr, tuple) and len(expr) == 2 and isinstance(expr[0], str):
            name, comp = expr

        if name is not None:
            var = self.sys.variables[name]
            is_numeric = isinstance(var, NumericVariable)
            dim = var.dim

            def get(node, _name=name, _comp=comp):
                val = node[_name]
                if val is None:
                    return np.nan
                arr = np.asarray(val, dtype=float)
                if arr.ndim == 0:
                    return float(arr)
                if arr.size == 1:
                    return float(arr.reshape(-1)[0])
                return float(arr[_comp])

            label = name if dim == 1 else f"{name}[{comp}]"
            return get, label, is_numeric

        if callable(expr):
            if self._num_params(expr) >= 2:
                get = lambda node, _f=expr: float(_f(node.s, node.t))
            else:
                get = lambda node, _f=expr: float(_f(node.point))
            return get, getattr(expr, '__name__', 'fn'), False

        const = float(expr)
        return (lambda node, _v=const: _v), str(const), False

    @staticmethod
    def _as_list(exprs) -> List[Expr]:
        if isinstance(exprs, list):
            return exprs
        return [exprs]

    def _slice_level(self, coord: str, value: float) -> Tuple[float, float]:
        """Ближайший к ``value`` уровень координаты ``coord`` среди узлов сетки."""
        levels: Dict[float, float] = {}
        for node in self._all_nodes():
            levels.setdefault(round(getattr(node, coord), PRECISION), getattr(node, coord))
        keys = np.array(list(levels.keys()))
        key = float(keys[int(np.argmin(np.abs(keys - value)))])
        return key, levels[key]

    def _free_range(self, free: str) -> Tuple[float, float]:
        if free == 's':
            return float(self.mesh.S0), float(self.mesh.S1)
        return float(self.mesh.T0), float(self.mesh.T1)

    # ================================================================ сетка
    def plot_mesh(self, ax=None, node_color: str = 'b', edge_color: str = 'g',
                  boundary_color: str = 'r', figsize=None):
        """Нарисовать характеристическую сетку и границу области."""
        mesh = self.mesh
        if ax is None:
            _, ax = plt.subplots(figsize=figsize)

        segments: List = []
        center_s: List[float] = []
        center_t: List[float] = []
        boundary_s: List[float] = []
        boundary_t: List[float] = []

        for i, j in mesh.order_center:
            node = mesh.center[(i, j)]
            if mesh.is_from_center(i, j - 1):
                other = mesh.center[(i, j - 1)]
                segments.append([(node.s, node.t), (other.s, other.t)])
            if mesh.is_from_center(i + 1, j):
                other = mesh.center[(i + 1, j)]
                segments.append([(node.s, node.t), (other.s, other.t)])
            center_s.append(node.s)
            center_t.append(node.t)

        for group in ('final_l', 'final_r', 'start_l', 'start_r'):
            for i, j in getattr(mesh, 'order_' + group):
                node = getattr(mesh, group)[(i, j)]
                center = mesh.get_center_node(i, j)
                segments.append([(node.s, node.t), (center.s, center.t)])
                boundary_s.append(node.s)
                boundary_t.append(node.t)

        ax.add_collection(LineCollection(segments, colors=edge_color))
        ax.scatter(center_s, center_t, color=node_color)
        ax.scatter(boundary_s, boundary_t, color=boundary_color, marker='.')

        ax.plot([mesh.S0, mesh.S1], [mesh.T0, mesh.T0], boundary_color)
        ax.plot([mesh.S0, mesh.S1], [mesh.T1, mesh.T1], boundary_color)
        ax.plot([mesh.S0, mesh.S0], [mesh.T0, mesh.T1], boundary_color)
        ax.plot([mesh.S1, mesh.S1], [mesh.T0, mesh.T1], boundary_color)

        ax.set_xlabel('s')
        ax.set_ylabel('t')
        ax.set_aspect('equal')
        return ax

    # ================================================================ поле 2D
    def plot_field(self, expr: Expr, ax=None, component: int = 0,
                   cmap: str = 'viridis', levels: Optional[int] = None,
                   shading: str = 'gouraud', colorbar: bool = True,
                   region: str = 'all', title: Optional[str] = None,
                   grid: bool = False, figsize=None, **kwargs):
        """Псевдоцветное поле ``expr`` на области (s, t).

        ``levels=None`` — непрерывная заливка (``tripcolor``), иначе
        изолинии (``tricontourf`` с заданным числом уровней).
        """
        getter, label, _ = self._make_getter(expr, component)

        if region == 'center':
            nodes = list(self.mesh.nodes_center)
        else:
            nodes = self._all_nodes()

        s = np.array([n.s for n in nodes], dtype=float)
        t = np.array([n.t for n in nodes], dtype=float)
        v = np.array([getter(n) for n in nodes], dtype=float)

        good = np.isfinite(v)
        s, t, v = s[good], t[good], v[good]

        if ax is None:
            _, ax = plt.subplots(figsize=figsize)

        tri = mtri.Triangulation(s, t)
        if levels is None:
            mappable = ax.tripcolor(tri, v, shading=shading, cmap=cmap, **kwargs)
        else:
            mappable = ax.tricontourf(tri, v, levels=levels, cmap=cmap, **kwargs)

        if colorbar:
            plt.colorbar(mappable, ax=ax)

        ax.set_xlabel('s')
        ax.set_ylabel('t')
        ax.set_aspect('equal')
        ax.grid(grid)
        ax.set_title(title if title is not None else label)
        return ax

    # ============================================================== разрез 1D
    def plot_slice(self, exprs, s: Optional[float] = None, t: Optional[float] = None,
                   ax=None, component: int = 0, labels: Optional[Sequence[str]] = None,
                   styles: Optional[Sequence[str]] = None, samples: int = 200,
                   x_range: Optional[Tuple[float, float]] = None,
                   grid: bool = True, legend: bool = True,
                   title: Optional[str] = None, xlabel: Optional[str] = None,
                   ylabel: Optional[str] = None, figsize=None, **kwargs):
        """Разрез при фиксированном ``s`` или ``t``.

        Ровно один из ``s`` / ``t`` должен быть задан. Координата фиксируется
        на ближайшем уровне сетки, вторая — свободная ось.

        Для численных переменных точки берутся из узлов сетки (маркеры),
        аналитические и callable считаются по непрерывной линии (``samples``
        точек). На одном графике можно вывести несколько функций::

            viz.plot_slice([('X', 0), ('X', 1), x_an], t=mesh.T1)
            viz.plot_slice([('PSI', 0), ('PSI', 1)], s=mesh.S0)
        """
        if (s is None) == (t is None):
            raise ValueError("Задайте ровно один параметр: s или t")

        fixed, value = ('s', s) if s is not None else ('t', t)
        free = 't' if fixed == 's' else 's'
        key, level = self._slice_level(fixed, value)

        exprs = self._as_list(exprs)
        if ax is None:
            _, ax = plt.subplots(figsize=figsize)

        slice_nodes = [n for n in self._all_nodes()
                       if round(getattr(n, fixed), PRECISION) == key]
        slice_nodes.sort(key=lambda n: getattr(n, free))

        lo, hi = x_range if x_range is not None else self._free_range(free)
        dense = np.linspace(lo, hi, samples)

        for k, expr in enumerate(exprs):
            getter, label, is_numeric = self._make_getter(expr, component)
            if labels is not None:
                label = labels[k]
            style = styles[k] if styles is not None else None

            if is_numeric:
                xs = np.array([getattr(n, free) for n in slice_nodes])
                ys = np.array([getter(n) for n in slice_nodes])
                ax.plot(xs, ys, style or 'o-', label=label, **kwargs)
            else:
                pts = [Point(val, x) if fixed == 's' else Point(x, val)
                       for x, val in zip(dense, [level] * samples)]
                ys = np.array([getter(self.sys.node(p)) for p in pts])
                ax.plot(dense, ys, style or '-', label=label, **kwargs)

        ax.set_xlabel(xlabel if xlabel is not None else free)
        if ylabel is not None:
            ax.set_ylabel(ylabel)
        ax.grid(grid)
        if legend:
            ax.legend()
        ax.set_title(title if title is not None else f"{fixed} = {level:g}")
        return ax

    # ============================================================ поверхность
    def plot_surface(self, expr: Expr, ax=None, component: int = 0,
                     cmap: str = 'viridis', region: str = 'all',
                     figsize=None, **kwargs):
        """3D-поверхность ``z = expr(s, t)``."""
        getter, label, _ = self._make_getter(expr, component)

        if region == 'center':
            nodes = list(self.mesh.nodes_center)
        else:
            nodes = self._all_nodes()

        s = np.array([n.s for n in nodes], dtype=float)
        t = np.array([n.t for n in nodes], dtype=float)
        v = np.array([getter(n) for n in nodes], dtype=float)
        good = np.isfinite(v)
        s, t, v = s[good], t[good], v[good]

        if ax is None:
            fig = plt.figure(figsize=figsize)
            ax = fig.add_subplot(111, projection='3d')

        tri = mtri.Triangulation(s, t)
        ax.plot_trisurf(tri, v, cmap=cmap, **kwargs)

        ax.set_xlabel('s')
        ax.set_ylabel('t')
        ax.set_zlabel(label)
        ax.set_title(label)
        return ax


# ===================================================== функции-обёртки (API)
def plot_mesh(mesh: CharacteristicMesh, **kwargs):
    return Plotter(mesh.system, mesh).plot_mesh(**kwargs)


def plot_field(mesh: CharacteristicMesh, expr: Expr, **kwargs):
    return Plotter(mesh.system, mesh).plot_field(expr, **kwargs)


def plot_slice(mesh: CharacteristicMesh, exprs, **kwargs):
    return Plotter(mesh.system, mesh).plot_slice(exprs, **kwargs)


def plot_surface(mesh: CharacteristicMesh, expr: Expr, **kwargs):
    return Plotter(mesh.system, mesh).plot_surface(expr, **kwargs)
