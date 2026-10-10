"""Решатели гиперболической системы каскадным методом характеристик.

Модуль содержит базовый интерфейс ``Solver`` и конкретные схемы дискретизации,
имя класса которых совпадает с названием схемы. Сейчас реализована
``TrapezoidalSolver`` — схема трапеций (Crank–Nicolson) вдоль характеристик
ds/dt = +C1, ds/dt = -C2.

Решатель работает поверх ``CharacteristicMesh`` и ``System``: коэффициенты
(B, F, G, C) читаются из аналитических переменных системы, а состояние (X),
сопряжённое состояние (PSI) и граничный прокси (p) пишутся в численные
переменные системы через узлы ``Node``. Координаты точек передаются как ``Point``.
"""
from __future__ import annotations
from abc import ABC, abstractmethod

import numpy as np

from ..system.system import System
from ..core.point import Point
from ..mesh.mesh import CharacteristicMesh


class Solver(ABC):
    """Базовый интерфейс решателя.

    Имя конкретного наследника = название схемы дискретизации.
    Прямой ход (X) считается от t=T0 к t=T1, сопряжённый (PSI) — обратно.
    """

    scheme: str = "base"

    def __init__(self, system: System) -> None:
        self.sys = system

    @abstractmethod
    def solve_forward(self, mesh: CharacteristicMesh) -> None:
        """Прямой ход: вычислить состояние X на всей сетке."""

    @abstractmethod
    def solve_adjoint(self, mesh: CharacteristicMesh) -> None:
        """Сопряжённый ход: вычислить PSI (и граничный прокси p)."""


class TrapezoidalSolver(Solver):
    """Схема трапеций (Crank–Nicolson) на характеристической сетке."""

    scheme = "trapezoidal"

    def __init__(self, system: System) -> None:
        super().__init__(system)
        self.C1 = self._const('C1')
        self.C2 = self._const('C2')
        self.S0 = self._const('S0')
        self.S1 = self._const('S1')

    # ----------------------------------------------------------- coefficients
    def _const(self, name: str) -> float:
        return float(self.sys.variables[name].at(Point(0.0, 0.0)))

    def _coef(self, name: str, point: Point) -> float:
        return float(self.sys.variables[name].at(point))

    # ------------------------------------------------------------ оркестрация
    def solve_forward(self, mesh: CharacteristicMesh) -> None:
        self.solve_initial(mesh)
        self.solve_center(mesh)
        self.solve_final(mesh)

    def solve_adjoint(self, mesh: CharacteristicMesh) -> None:
        self.solve_initial_adjoint(mesh)
        self.solve_center_adjoint(mesh)
        self.solve_final_adjoint(mesh)

    # ================================================================= ПРЯМОЙ
    def solve_initial(self, mesh: CharacteristicMesh) -> None:
        for group in ('start_l', 'start_r'):
            for i, j in getattr(mesh, 'order_' + group):
                node = getattr(mesh, group)[(i, j)]
                node['X'] = [node['x0'], node['y0']]

    def solve_center(self, mesh: CharacteristicMesh) -> None:
        for i, j in mesh.order_center:
            node = mesh.center[(i, j)]
            left, right = self._center_neighbours(mesh, i, j, node.point.s)
            if node.point.s == self.S0:
                node['X'] = self.left_solve(node.point, left.point, right.point, left['X'], right['X'])
            elif node.point.s == self.S1:
                node['X'] = self.right_solve(node.point, left.point, right.point, left['X'], right['X'])
            else:
                node['X'] = self.center_solve(node.point, left.point, right.point, left['X'], right['X'])

    @staticmethod
    def _center_neighbours(mesh, i, j, s):
        if s == mesh.S0:
            return mesh.get_s0_node_left(i, j), mesh.get_center_node_right(i, j)
        if s == mesh.S1:
            return mesh.get_center_node_left(i, j), mesh.get_s1_node_right(i, j)
        return mesh.get_center_node_left(i, j), mesh.get_center_node_right(i, j)

    def solve_final(self, mesh: CharacteristicMesh) -> None:
        deferred = []
        for i, j in mesh.order_final_r:
            node = mesh.final_r[(i, j)]
            point = node.point

            if point.s == self.S1:
                center = mesh.get_center_node(i, j)
                if mesh.is_from_center(i - 1, j):
                    c2 = mesh.get_center_node(i - 1, j)
                    point_l, st_l = mesh.get_stxy_c_3node(
                        center.point, center['X'], c2.point, c2['X'], point, self.C2)
                    node['X'] = self.right_solve(point, point_l, center.point, st_l, center['X'])
                else:
                    deferred.append((i, j, center.point, center['X']))
                continue

            c0 = mesh.get_center_node(i, j)
            c1 = mesh.get_center_node(i + 1, j)
            c2 = mesh.get_center_node(i + 1, j + 1) if mesh.is_from_center(i + 1, j + 1) \
                else mesh.get_right_node(i + 1, j)
            point_r, st_r = mesh.get_stxy_c_3node(
                c1.point, c1['X'], c2.point, c2['X'], point, -self.C1)
            node['X'] = self.center_solve(point, c0.point, point_r, c0['X'], st_r)

        for i, j in mesh.order_final_l:
            node = mesh.final_l[(i, j)]
            point = node.point

            if point.s == self.S0:
                c0 = mesh.get_center_node(i, j)
                c2 = mesh.get_center_node(i, j + 1) if mesh.is_from_center(i, j + 1) \
                    else mesh.get_right_node(i, j)
                point_r, st_r = mesh.get_stxy_c_3node(
                    c0.point, c0['X'], c2.point, c2['X'], point, -self.C1)
                node['X'] = self.left_solve(point, c0.point, point_r, c0['X'], st_r)
                continue

            c0 = mesh.get_center_node(i, j)
            c1 = mesh.get_center_node(i, j - 1)
            c2 = mesh.get_center_node(i - 1, j - 1) if mesh.is_from_center(i - 1, j - 1) \
                else mesh.get_left_node(i, j - 1)
            point_l, st_l = mesh.get_stxy_c_3node(
                c1.point, c1['X'], c2.point, c2['X'], point, self.C2)
            node['X'] = self.center_solve(point, point_l, c0.point, st_l, c0['X'])

        for i, j, point_r, st_r in deferred:
            node = mesh.final_r[(i, j)]
            left = mesh.get_left_node(i, j)
            point_l, st_l = mesh.get_stxy_c_3node(
                point_r, st_r, left.point, left['X'], node.point, self.C2)
            node['X'] = self.right_solve(node.point, point_l, point_r, st_l, st_r)

    # ============================================================= СОПРЯЖЁННЫЙ
    def solve_initial_adjoint(self, mesh: CharacteristicMesh) -> None:
        phi_dx = self.sys.get_callable('phi_dx')
        phi_dy = self.sys.get_callable('phi_dy')

        for group in ('final_r', 'final_l'):
            for i, j in getattr(mesh, 'order_' + group):
                node = getattr(mesh, group)[(i, j)]
                x, y = node['X']
                node['PSI'] = [phi_dx(node.point, x, y), phi_dy(node.point, x, y)]
                if node.point.s == self.S0 or node.point.s == self.S1:
                    node['p'] = 0.0

    def solve_center_adjoint(self, mesh: CharacteristicMesh) -> None:
        for i, j in reversed(mesh.order_center):
            node = mesh.center[(i, j)]
            point = node.point

            if point.s == self.S0:
                left = mesh.get_s0_node_conj_left(i, j)
                right = mesh.get_center_node_conj_right(i, j)
                psi, p = self.left_conj_solve(
                    point, left.point, right.point, left['PSI'], right['PSI'], left['p'])
                node['PSI'] = psi
                node['p'] = p
            elif point.s == self.S1:
                left = mesh.get_center_node_conj_left(i, j)
                right = mesh.get_s1_node_conj_right(i, j)
                psi, p = self.right_conj_solve(
                    point, left.point, right.point, left['PSI'], right['PSI'], right['p'])
                node['PSI'] = psi
                node['p'] = p
            else:
                left = mesh.get_center_node_conj_left(i, j)
                right = mesh.get_center_node_conj_right(i, j)
                node['PSI'] = self.center_conj_solve(
                    point, left.point, right.point, left['PSI'], right['PSI'])

    def solve_final_adjoint(self, mesh: CharacteristicMesh) -> None:
        left_p = right_p = None
        deferred = []

        for i, j in reversed(mesh.order_start_l):
            node = mesh.start_l[(i, j)]
            point = node.point

            if point.s == self.S0:
                c0 = mesh.get_center_conj_node(i, j)
                if mesh.is_from_center(i + 1, j):
                    c2 = mesh.get_center_conj_node(i + 1, j)
                    point_r, st_r = mesh.get_stxy_c_3node(
                        c2.point, c2['PSI'], c0.point, c0['PSI'], point, self.C2)
                    psi, p = self.left_conj_solve(
                        point, c0.point, point_r, c0['PSI'], st_r, c0['p'])
                    node['PSI'] = psi
                    node['p'] = p
                    left_p = p
                else:
                    deferred.append((i, j, c0))
                continue

            c0 = mesh.get_center_conj_node(i, j)
            c1 = mesh.get_center_conj_node(i - 1, j)
            c2 = mesh.get_center_conj_node(i - 1, j - 1) if mesh.is_from_center(i - 1, j - 1) \
                else mesh.get_left_conj_node(i - 1, j)
            point_l, st_l = mesh.get_stxy_c_3node(
                c2.point, c2['PSI'], c1.point, c1['PSI'], point, -self.C1)
            node['PSI'] = self.center_conj_solve(point, point_l, c0.point, st_l, c0['PSI'])

        for i, j in reversed(mesh.order_start_r):
            node = mesh.start_r[(i, j)]
            point = node.point

            if point.s == self.S1:
                c0 = mesh.get_center_conj_node(i, j)
                c2 = mesh.get_center_conj_node(i, j - 1) if mesh.is_from_center(i, j - 1) \
                    else mesh.get_left_conj_node(i, j)
                point_l, st_l = mesh.get_stxy_c_3node(
                    c2.point, c2['PSI'], c0.point, c0['PSI'], point, -self.C1)
                psi, p = self.right_conj_solve(
                    point, point_l, c0.point, st_l, c0['PSI'], c0['p'])
                node['PSI'] = psi
                node['p'] = p
                right_p = p
                continue

            c0 = mesh.get_center_conj_node(i, j)
            c1 = mesh.get_center_conj_node(i, j + 1)
            c2 = mesh.get_center_conj_node(i + 1, j + 1) if mesh.is_from_center(i + 1, j + 1) \
                else mesh.get_right_conj_node(i, j + 1)
            point_r, st_r = mesh.get_stxy_c_3node(
                c2.point, c2['PSI'], c1.point, c1['PSI'], point, self.C2)
            node['PSI'] = self.center_conj_solve(point, c0.point, point_r, c0['PSI'], st_r)

        for i, j, c0 in deferred:
            node = mesh.start_l[(i, j)]
            right = mesh.get_right_conj_node(i, j)
            point_r, st_r = mesh.get_stxy_c_3node(
                right.point, right['PSI'], c0.point, c0['PSI'], node.point, self.C2)
            psi, p = self.left_conj_solve(
                node.point, c0.point, point_r, c0['PSI'], st_r, c0['p'])
            node['PSI'] = psi
            node['p'] = p
            left_p = p

        # Прокси управления p постоянно вдоль граничной характеристики.
        if left_p is not None or right_p is not None:
            for group in ('start_l', 'start_r'):
                for i, j in getattr(mesh, 'order_' + group):
                    node = getattr(mesh, group)[(i, j)]
                    if node.point.s == self.S0 and left_p is not None:
                        node['p'] = left_p
                    elif node.point.s == self.S1 and right_p is not None:
                        node['p'] = right_p

    # ================================================== схема: прямой ход
    def center_solve(self, point, point_l, point_r, st_l, st_r):
        B11, B12 = self._coef('B11', point), self._coef('B12', point)
        B21, B22 = self._coef('B21', point), self._coef('B22', point)
        B11r, B12r = self._coef('B11', point_r), self._coef('B12', point_r)
        B21l, B22l = self._coef('B21', point_l), self._coef('B22', point_l)
        F1, F2 = self._coef('F1', point), self._coef('F2', point)
        F1r, F2l = self._coef('F1', point_r), self._coef('F2', point_l)

        hl, hr = point.t - point_l.t, point.t - point_r.t
        A = [[1 - hr / 2 * B11, -hr / 2 * B12],
             [-hl / 2 * B21, 1 - hl / 2 * B22]]
        b = [st_r[0] + hr / 2 * (B11r * st_r[0] + B12r * st_r[1] + F1 + F1r),
             st_l[1] + hl / 2 * (B21l * st_l[0] + B22l * st_l[1] + F2 + F2l)]
        return np.linalg.solve(A, b)

    def left_solve(self, point, point_l, point_r, st_l, st_r):
        B11, B12 = self._coef('B11', point), self._coef('B12', point)
        B11r, B12r = self._coef('B11', point_r), self._coef('B12', point_r)
        F1, F1r = self._coef('F1', point), self._coef('F1', point_r)
        G21_t, G22_t = self._coef('G21', point), self._coef('G22', point)
        G21_tl, G22_tl = self._coef('G21', point_l), self._coef('G22', point_l)

        hl, hr = point.t - point_l.t, point.t - point_r.t
        A = [[1 - hr / 2 * B11, -hr / 2 * B12],
             [-hl / 2 * G21_t, 1 - hl / 2 * G22_t]]
        b = [st_r[0] + hr / 2 * (B11r * st_r[0] + B12r * st_r[1] + F1 + F1r),
             st_l[1] + hl / 2 * (G21_tl * st_l[0] + G22_tl * st_l[1])]
        return np.linalg.solve(A, b)

    def right_solve(self, point, point_l, point_r, st_l, st_r):
        B21, B22 = self._coef('B21', point), self._coef('B22', point)
        B21l, B22l = self._coef('B21', point_l), self._coef('B22', point_l)
        F2, F2l = self._coef('F2', point), self._coef('F2', point_l)
        G11_t, G12_t = self._coef('G11', point), self._coef('G12', point)
        G11_tr, G12_tr = self._coef('G11', point_r), self._coef('G12', point_r)

        hl, hr = point.t - point_l.t, point.t - point_r.t
        A = [[1 - hr / 2 * G11_t, -hr / 2 * G12_t],
             [-hl / 2 * B21, 1 - hl / 2 * B22]]
        b = [st_r[0] + hr / 2 * (G11_tr * st_r[0] + G12_tr * st_r[1]),
             st_l[1] + hl / 2 * (B21l * st_l[0] + B22l * st_l[1] + F2 + F2l)]
        return np.linalg.solve(A, b)

    # ================================================== схема: сопряжённый ход
    def center_conj_solve(self, point, point_l, point_r, st_l, st_r):
        B11, B12 = self._coef('B11', point), self._coef('B12', point)
        B21, B22 = self._coef('B21', point), self._coef('B22', point)
        B11l, B21l = self._coef('B11', point_l), self._coef('B21', point_l)
        B12r, B22r = self._coef('B12', point_r), self._coef('B22', point_r)
        F1, F2 = self._coef('F1', point), self._coef('F2', point)
        F1l, F2r = self._coef('F1', point_l), self._coef('F2', point_r)

        hl, hr = point.t - point_l.t, point.t - point_r.t
        A = [[1 + hl / 2 * B11, hl / 2 * B21],
             [hr / 2 * B12, 1 + hr / 2 * B22]]
        b = [st_l[0] + hl / 2 * (-B11l * st_l[0] - B21l * st_l[1] + F1 + F1l),
             st_r[1] + hr / 2 * (-B12r * st_r[0] - B22r * st_r[1] + F2 + F2r)]
        return np.linalg.solve(A, b)

    def left_conj_solve(self, point, point_l, point_r, st_l, st_r, p_l):
        B12, B22 = self._coef('B12', point), self._coef('B22', point)
        B12r, B22r = self._coef('B12', point_r), self._coef('B22', point_r)
        G22_t = self._coef('G22', point)
        G22_tl = self._coef('G22', point_l)
        C2 = self._coef('C2', point)
        psi_to_P = 1 / self.C1 * G22_t

        hl, hr = point.t - point_l.t, point.t - point_r.t
        A = [[1 + hl / 2 * G22_t, hl / 2 * C2],
             [hr / 2 * B12 * psi_to_P, 1 + hr / 2 * B22]]
        b = [p_l + hl / 2 * (-G22_tl * p_l - C2 * st_l[1]),
             st_r[1] + hr / 2 * (-B12r * st_r[0] - B22r * st_r[1])]
        p2, psi2 = np.linalg.solve(A, b)
        psi1 = psi_to_P * p2
        return np.array([psi1, psi2]), p2

    def right_conj_solve(self, point, point_l, point_r, st_l, st_r, p_r):
        B11, B21 = self._coef('B11', point), self._coef('B21', point)
        B11l, B21l = self._coef('B11', point_l), self._coef('B21', point_l)
        G11_t = self._coef('G11', point)
        G11_tr = self._coef('G11', point_r)
        C1 = self._coef('C1', point)
        psi_to_P = 1 / self.C2 * G11_t

        hl, hr = point.t - point_l.t, point.t - point_r.t
        A = [[1 + hl / 2 * B11, hl / 2 * B21 * psi_to_P],
             [hr / 2 * C1, 1 + hr / 2 * G11_t]]
        b = [st_l[0] + hl / 2 * (-B11l * st_l[0] - B21l * st_l[1]),
             p_r + hr / 2 * (-G11_tr * p_r - C1 * st_r[0])]
        psi1, p1 = np.linalg.solve(A, b)
        psi2 = psi_to_P * p1
        return np.array([psi1, psi2]), p1
