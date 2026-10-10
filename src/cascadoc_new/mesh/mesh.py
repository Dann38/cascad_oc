"""Характеристическая сетка для гиперболических систем.

Сетка строится из узлов (i, j) -> Node(Point(s, t)), лежащих вдоль характеристик
ds/dt = +C1 и ds/dt = -C2. Каждый узел — точка (Point), привязанная к System:
значения переменных хранит System (NumericVariable), а сетка отвечает только за
геометрию и топологию.

Классы узлов (входная граница — t = T0, выходная — t = T1):
    center   — узлы области (S0 <= s <= S1, T0 <= t <= T1);
    start_l  — узлы на входной границе t = T0 (семейство характеристик L);
    start_r  — узлы на входной границе t = T0 (семейство характеристик R);
    final_l  — узлы на выходной границе t = T1 (семейство характеристик L);
    final_r  — узлы на выходной границе t = T1 (семейство характеристик R).
"""
from __future__ import annotations
from typing import Dict, List, Optional, Tuple

import numpy as np

from ..system.system import System
from ..system.node import Node
from ..core.point import Point
from ..core.utils import normalize_float


_CENTER = 'center'
_START_L = 'start_l'
_START_R = 'start_r'
_FINAL_L = 'final_l'
_FINAL_R = 'final_r'

_GROUPS = (_CENTER, _START_L, _START_R, _FINAL_L, _FINAL_R)


class CharacteristicMesh:
    def __init__(self, system: System, m: int = None, h: float = None) -> None:
        self.system = system

        # Геометрические параметры берём из системы (единый источник правды).
        self.C1 = self._const('C1')
        self.C2 = self._const('C2')
        self.S0 = self._const('S0')
        self.S1 = self._const('S1')
        self.T0 = self._const('T0')
        self.T1 = self._const('T1')

        self._setup_discretization(m, h)
        self._setup_bounds()
        self._build()

    # ------------------------------------------------------------------ setup
    def _const(self, name: str) -> float:
        return float(self.system.variables[name].at(Point(0.0, 0.0)))

    def _setup_discretization(self, m: Optional[int], h: Optional[float]) -> None:
        self.Sc = (self.S1 + self.S0) / 2
        self.Tc = (self.T1 + self.T0) / 2

        if m:
            M = m * 2
            DeltaS = (self.S1 - self.S0) / M
            Delta1T = DeltaS / self.C1
            Delta2T = DeltaS / self.C2
            DeltaT = Delta1T + Delta2T
        elif h:
            DeltaT = h
            DeltaS = DeltaT * self.C1 * self.C2 / (self.C1 + self.C2)
            Delta1T = DeltaS / self.C1
            Delta2T = DeltaS / self.C2
        else:
            raise ValueError("Укажите либо m (число точек), либо h (шаг по t)")

        self.dS, self.d1T, self.d2T = DeltaS, Delta1T, Delta2T
        self.dT = DeltaT

    def _setup_bounds(self) -> None:
        """Границы области в индексном пространстве (i, j)."""
        self.__T_min_ij = (2 * self.T0 - (self.T1 - self.T0)) / (2 * self.dS)
        self.__T_max_ij = (2 * self.T1 - (self.T1 - self.T0)) / (2 * self.dS)
        self.__S_min_ij = (self.S0 - self.Sc) / self.dS
        self.__S_max_ij = (self.S1 - self.Sc) / self.dS

        self.__L = np.array([[self.dS, self.dS],
                             [-self.d1T, self.d2T]])
        self.__v = np.array([self.Sc, self.Tc])

        self.min_j = int((self.__S_max_ij * self.C1 + self.__T_max_ij) /
                         (1 / self.C1 + 1 / self.C2))
        self.min_i = int(self.__S_max_ij + self.min_j)

    # ------------------------------------------------------------------ build
    def is_from_center(self, i: int, j: int) -> bool:
        t_ind = 1 / self.C2 * j - 1 / self.C1 * i
        s_ind = i + j
        return (self.__T_min_ij <= t_ind) and (self.__T_max_ij >= t_ind) and \
               (self.__S_min_ij <= s_ind) and (self.__S_max_ij >= s_ind)

    def _build(self) -> None:
        raw: Dict[str, List[Tuple[int, int, Point]]] = {g: [] for g in _GROUPS}

        for i in range(-self.min_i, self.min_i + 1):
            for j in range(-self.min_j, self.min_j + 1):
                if not self.is_from_center(i, j):
                    continue

                s, t = (float(x) for x in normalize_float(self.__L @ np.array([i, j]) + self.__v))
                raw[_CENTER].append((i, j, Point(s, t)))

                if s == self.S0:
                    if not self.is_from_center(i + 1, j - 1):
                        raw[_START_L].append((i, j, Point(self.S0, self.T0)))
                    if not self.is_from_center(i + 1, j):
                        raw[_START_R].append((i, j, Point(s + (t - self.T0) * self.C1, self.T0)))
                    if not self.is_from_center(i, j + 1):
                        raw[_FINAL_R].append((i, j, Point(s + (self.T1 - t) * self.C2, self.T1)))
                    if not self.is_from_center(i - 1, j + 1):
                        raw[_FINAL_L].append((i, j, Point(self.S0, self.T1)))
                elif s == self.S1:
                    if not self.is_from_center(i, j - 1):
                        raw[_START_L].append((i, j, Point(s - (t - self.T0) * self.C2, self.T0)))
                    if not self.is_from_center(i + 1, j - 1):
                        raw[_START_R].append((i, j, Point(self.S1, self.T0)))
                    if not self.is_from_center(i - 1, j + 1):
                        raw[_FINAL_R].append((i, j, Point(self.S1, self.T1)))
                    if not self.is_from_center(i - 1, j):
                        raw[_FINAL_L].append((i, j, Point(s - (self.T1 - t) * self.C1, self.T1)))
                else:
                    if not self.is_from_center(i, j - 1):
                        raw[_START_L].append((i, j, Point(s - (t - self.T0) * self.C2, self.T0)))
                    if not self.is_from_center(i + 1, j):
                        raw[_START_R].append((i, j, Point(s + (t - self.T0) * self.C1, self.T0)))
                    if not self.is_from_center(i, j + 1):
                        raw[_FINAL_R].append((i, j, Point(s + (self.T1 - t) * self.C2, self.T1)))
                    if not self.is_from_center(i - 1, j):
                        raw[_FINAL_L].append((i, j, Point(s - (self.T1 - t) * self.C1, self.T1)))

        for group in _GROUPS:
            items = sorted(raw[group], key=lambda e: e[2].t)  # сортировка по t
            order: List[Tuple[int, int]] = []
            mapping: Dict[Tuple[int, int], Node] = {}
            nodes: List[Node] = []
            for i, j, point in items:
                node = self.system.node(point)
                order.append((i, j))
                mapping[(i, j)] = node
                nodes.append(node)

            setattr(self, group, mapping)
            setattr(self, 'order_' + group, order)
            setattr(self, 'nodes_' + group, nodes)

    # ------------------------------------------------------------- accessors
    def get_center_node(self, i: int, j: int) -> Node:
        return self.center[(int(i), int(j))]

    def get_left_node(self, i: int, j: int) -> Node:
        return self.final_l[(int(i), int(j))]

    def get_right_node(self, i: int, j: int) -> Node:
        return self.final_r[(int(i), int(j))]

    def get_center_node_left(self, i: int, j: int) -> Node:
        if self.is_from_center(i, j - 1):
            return self.center[(int(i), int(j - 1))]
        return self.start_l[(int(i), int(j))]

    def get_center_node_right(self, i: int, j: int) -> Node:
        if self.is_from_center(i + 1, j):
            return self.center[(int(i + 1), int(j))]
        return self.start_r[(int(i), int(j))]

    def get_s0_node_left(self, i: int, j: int) -> Node:
        if self.is_from_center(i + 1, j - 1):
            return self.center[(int(i + 1), int(j - 1))]
        return self.start_l[(int(i), int(j))]

    def get_s1_node_right(self, i: int, j: int) -> Node:
        if self.is_from_center(i + 1, j - 1):
            return self.center[(int(i + 1), int(j - 1))]
        return self.start_r[(int(i), int(j))]

    # ------------------------------------------------- конъюгатные (обратные)
    def get_center_conj_node(self, i: int, j: int) -> Node:
        return self.center[(int(i), int(j))]

    def get_final_l_conj_node(self, i: int, j: int) -> Node:
        return self.final_l[(int(i), int(j))]

    def get_final_r_conj_node(self, i: int, j: int) -> Node:
        return self.final_r[(int(i), int(j))]

    def get_left_conj_node(self, i: int, j: int) -> Node:
        return self.start_l[(int(i), int(j))]

    def get_right_conj_node(self, i: int, j: int) -> Node:
        return self.start_r[(int(i), int(j))]

    def get_center_node_conj_left(self, i: int, j: int) -> Node:
        if self.is_from_center(i - 1, j):
            return self.center[(int(i - 1), int(j))]
        return self.final_l[(int(i), int(j))]

    def get_center_node_conj_right(self, i: int, j: int) -> Node:
        if self.is_from_center(i, j + 1):
            return self.center[(int(i), int(j + 1))]
        return self.final_r[(int(i), int(j))]

    def get_s0_node_conj_left(self, i: int, j: int) -> Node:
        if self.is_from_center(i - 1, j + 1):
            return self.center[(int(i - 1), int(j + 1))]
        return self.final_l[(int(i), int(j))]

    def get_s1_node_conj_right(self, i: int, j: int) -> Node:
        if self.is_from_center(i - 1, j + 1):
            return self.center[(int(i - 1), int(j + 1))]
        return self.final_r[(int(i), int(j))]

    # -------------------------------------------------------------- geometry
    def get_stxy_c_3node(self, p1: Point, st1, p2: Point, st2, p3: Point, c: float):
        """Точка выхода характеристики (наклон c) из p3 на прямую p1-p2.

        Возвращает (Point, state) — координату и линейно проинтерполированное
        состояние (np.ndarray произвольной размерности или float).
        """
        if p1.t == p2.t:
            if p3.t == p2.t:
                return p1, np.asarray(st1, dtype=float)
            raise ValueError("Невозможно интерполировать: p1.t == p2.t != p3.t")
        if p1.t > p2.t:
            raise ValueError("Ожидается p1.t <= p2.t")

        c12 = (p1.s - p2.s) / (p1.t - p2.t)
        t = 1 / (c12 - c) * (c12 * p1.t - c * p3.t + p3.s - p1.s)
        alpha = (t - p1.t) / (p2.t - p1.t)
        s = p1.s + alpha * (p2.s - p1.s)

        a1 = np.asarray(st1, dtype=float)
        a2 = np.asarray(st2, dtype=float)
        return Point(s, t), a1 + alpha * (a2 - a1)

    # ------------------------------------------------------------- borders
    def get_border(self, type_border: str = 'start', sort_t: bool = False,
                   sort_s: bool = False) -> List[Node]:
        if type_border in ('left', 'right'):
            target = self.S0 if type_border == 'left' else self.S1
            nodes = [node for group in _GROUPS for node in getattr(self, 'nodes_' + group)
                     if node.s == target]
        elif type_border == 'final':
            nodes = list(self.nodes_final_l) + list(self.nodes_final_r)
        elif type_border == 'start':
            nodes = list(self.nodes_start_l) + list(self.nodes_start_r)
        else:
            raise ValueError(f"Неизвестная граница: {type_border}")

        if sort_s:
            nodes = [nodes[k] for k in np.argsort([n.s for n in nodes])]
        if sort_t:
            nodes = [nodes[k] for k in np.argsort([n.t for n in nodes])]
        return nodes
