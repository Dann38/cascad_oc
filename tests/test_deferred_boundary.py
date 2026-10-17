"""Тесты отложенных переменных и блоков-источников.

Проверяет:
1. ``DeferredVariable`` — чтение значения из NumericVariable, заполненного
   блоком-производителем.
2. ``ODESourceBlock`` — решение ОДУ и запись в NumericVariable.
3. ``DeferredBoundaryBlock`` — граница, читающая значение из отложенной
   переменной.
4. Топологическая сортировка блоков в ``System.solve()``.
5. Сверка с аналитическим решением.
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import unittest
import numpy as np

from cascadoc_new import (
    Point, System, CharacteristicMesh,
    HypBlock, ODEBlock, PlainBoundaryBlock,
    ODESourceBlock, DeferredBoundaryBlock,
    DeferredVariable, AnalyticVariable, NumericVariable,
)


# ---------------------------------------------------------------------------
# Аналитическое решение
# ---------------------------------------------------------------------------
C1, C2 = 1.0, 1.0
S0, S1 = 0.0, 1.0
T0, T1 = 0.0, 0.5

x_an = lambda s, t: np.exp(s + C1 * t)
y_an = lambda s, t: np.exp(-s + C2 * t)
x0_fn = lambda s: x_an(s, T0)
y0_fn = lambda s: y_an(s, T0)


def _register_common(sys: System, m: int = 40):
    """Зарегистрировать общие переменные в системе."""
    sys.var_analytic('C1', C1)
    sys.var_analytic('C2', C2)
    sys.var_analytic('S0', S0)
    sys.var_analytic('S1', S1)
    sys.var_analytic('T0', T0)
    sys.var_analytic('T1', T1)

    sys.var_analytic('B11', lambda point: 0.0)
    sys.var_analytic('B12', lambda point: 0.0)
    sys.var_analytic('B21', lambda point: 0.0)
    sys.var_analytic('B22', lambda point: 0.0)
    sys.var_analytic('F1', lambda point: 0.0)
    sys.var_analytic('F2', lambda point: 0.0)

    sys.var_analytic('x0', lambda point: x0_fn(point.s))
    sys.var_analytic('y0', lambda point: y0_fn(point.s))

    sys.var_numeric('X', dim=2)


def _register_g(sys: System):
    """Зарегистрировать G-коэффициенты для ODEBlock."""
    sys.var_analytic('G11', lambda point: C1)
    sys.var_analytic('G12', lambda point: 0.0)
    sys.var_analytic('G21', lambda point: 0.0)
    sys.var_analytic('G22', lambda point: C2)


def _make_mesh(sys: System, m: int = 40):
    return CharacteristicMesh(sys, m=m)


class TestDeferredBoundary(unittest.TestCase):
    """Граница через отложенную переменную + ODE-источник."""

    @classmethod
    def setUpClass(cls):
        cls.m = 40

    # --------------------------------------------------------- эталон (ODEBlock)
    def _build_reference(self):
        """Система с ODEBlock на обеих границах (как в существующем коде)."""
        sys = System()
        _register_common(sys, self.m)
        _register_g(sys)
        mesh = _make_mesh(sys, self.m)

        hyp = HypBlock('hyp', sys, mesh)
        sys.add_block(hyp)
        sys.add_block(ODEBlock('ode_left', sys, mesh, 'left'))
        sys.add_block(ODEBlock('ode_right', sys, mesh, 'right'))

        return sys, mesh

    # ----------------------------------------------------- система с отложенной
    def _build_deferred(self):
        """Система с DeferredBoundaryBlock + ODESourceBlock на правой границе.

        Левая граница — ODEBlock (как в эталоне), правая — отложенная
        переменная ``Z``, заполняемая ``ODESourceBlock``, решающим
        ``dz/dt = C1 * z``.
        """
        sys = System()
        _register_common(sys, self.m)
        _register_g(sys)
        mesh = _make_mesh(sys, self.m)

        # NumericVariable — хранилище для результата ОДУ
        sys.var_numeric('Z_numeric', dim=1)

        # Отложенная переменная — читает из Z_numeric
        sys.var_deferred('Z', source='Z_numeric')

        # Блоки
        hyp = HypBlock('hyp', sys, mesh)
        sys.add_block(hyp)

        # Левая граница — ODEBlock (как в эталоне)
        sys.add_block(ODEBlock('ode_left', sys, mesh, 'left'))

        # Источник ОДУ для правой границы: dz/dt = C1 * z
        # z(T0) = x0(S1) = exp(S1 + C1*T0)
        z_init = x0_fn(S1)
        ode_src = ODESourceBlock(
            'z_source', sys, mesh,
            source_var='Z_numeric',
            ode_fn=lambda z, t: C1 * z,
            init_val=z_init,
            side='right',
        )
        sys.add_block(ode_src)

        # Правая граница — читает Z из отложенной переменной
        right = DeferredBoundaryBlock(
            'deferred_right', sys, mesh, 'right',
            deferred_var='Z', source_block='z_source',
        )
        sys.add_block(right)

        return sys, mesh

    # ---------------------------------------------------------------- тесты
    def test_reference_matches_analytic(self):
        """Эталон (ODEBlock) совпадает с аналитикой в пределах схемы."""
        sys, mesh = self._build_reference()
        sys.solve()

        err_x, err_y = [], []
        for node in mesh.nodes_center:
            x_num, y_num = node['X']
            x_a, y_a = x_an(node.s, node.t), y_an(node.s, node.t)
            err_x.append(abs(x_num - x_a))
            err_y.append(abs(y_num - y_a))

        max_err_x = max(err_x)
        max_err_y = max(err_y)
        self.assertLess(max_err_x, 0.002,
                        f"Reference max|x-x_an| = {max_err_x:.6f}")
        self.assertLess(max_err_y, 0.002,
                        f"Reference max|y-y_an| = {max_err_y:.6f}")

    def test_deferred_matches_reference(self):
        """Deferred-система совпадает с эталоном (ODEBlock) в пределах
        машинной точности."""
        sys_ref, _ = self._build_reference()
        sys_ref.solve()

        sys_def, mesh_def = self._build_deferred()
        sys_def.solve()

        diff_x, diff_y = [], []
        for node in mesh_def.nodes_center:
            x_def, y_def = node['X']

            ref_node = sys_ref.node(node.point)
            x_ref, y_ref = ref_node['X']

            diff_x.append(abs(x_def - x_ref))
            diff_y.append(abs(y_def - y_ref))

        max_dx = max(diff_x)
        max_dy = max(diff_y)
        self.assertLess(max_dx, 1e-12,
                        f"max|x_def - x_ref| = {max_dx:.2e}")
        self.assertLess(max_dy, 1e-12,
                        f"max|y_def - y_ref| = {max_dy:.2e}")

    def test_deferred_matches_analytic(self):
        """Deferred-система совпадает с аналитикой в пределах схемы."""
        sys, mesh = self._build_deferred()
        sys.solve()

        err_x, err_y = [], []
        for node in mesh.nodes_center:
            x_num, y_num = node['X']
            x_a, y_a = x_an(node.s, node.t), y_an(node.s, node.t)
            err_x.append(abs(x_num - x_a))
            err_y.append(abs(y_num - y_a))

        max_err_x = max(err_x)
        max_err_y = max(err_y)
        self.assertLess(max_err_x, 0.002,
                        f"Deferred max|x-x_an| = {max_err_x:.6f}")
        self.assertLess(max_err_y, 0.002,
                        f"Deferred max|y-y_an| = {max_err_y:.6f}")

    def test_right_boundary_z_matches_analytic(self):
        """На правой границе x = Z совпадает с аналитическим x(S1, t)
        в пределах погрешности схемы (O(dt^2) для трапеций)."""
        sys, mesh = self._build_deferred()
        sys.solve()

        diffs = []
        for node in mesh.nodes_center:
            if node.s != S1:
                continue
            x_num = node['X'][0]
            x_a = x_an(S1, node.t)
            diffs.append(abs(x_num - x_a))

        max_diff = max(diffs) if diffs else 0.0
        self.assertLess(max_diff, 0.002,
                        f"max|x_num - x_an| at right boundary = {max_diff:.6f}")

    def test_z_source_matches_odeblock_on_boundary(self):
        """Z(t) от ODESourceBlock совпадает с x(t) от ODEBlock на s=S1
        в пределах машинной точности (оба — трапеции для dz/dt = c1·z)."""
        sys_def, mesh_def = self._build_deferred()
        sys_def.solve()

        sys_ref, _ = self._build_reference()
        sys_ref.solve()

        diffs = []
        for node in mesh_def.nodes_center:
            if node.s != S1:
                continue
            x_def = node['X'][0]
            p = node.point
            ref_node = sys_ref.node(p)
            x_ref = ref_node['X'][0]
            diffs.append(abs(x_def - x_ref))

        max_diff = max(diffs) if diffs else 0.0
        self.assertLess(max_diff, 1e-12,
                        f"max|x_def - x_ref| at right boundary = {max_diff:.2e}")


class TestDeferredVariable(unittest.TestCase):
    """Unit-тесты DeferredVariable."""

    def test_bind_and_read(self):
        sys = System()
        src = sys.var_numeric('src', dim=1)
        dv = sys.var_deferred('z', source='src')

        self.assertIsInstance(dv, DeferredVariable)
        self.assertEqual(dv.name, 'z')
        self.assertEqual(dv.source_name, 'src')

        p = Point(0.5, 0.1)
        src.store(p, 42.0)
        self.assertEqual(dv.at(p), 42.0)

    def test_unbound_raises(self):
        dv = DeferredVariable('z', 'src')
        with self.assertRaises(RuntimeError):
            dv.at(Point(0.0, 0.0))

    def test_missing_source_raises(self):
        sys = System()
        sys.var_numeric('src', dim=1)
        dv = DeferredVariable('z', 'nonexistent')
        dv.bind(sys)
        with self.assertRaises(RuntimeError):
            dv.at(Point(0.0, 0.0))

    def test_not_computed_raises(self):
        sys = System()
        sys.var_numeric('src', dim=1)
        dv = sys.var_deferred('z', source='src')
        with self.assertRaises(RuntimeError):
            dv.at(Point(0.5, 0.1))


class TestBlockDependencies(unittest.TestCase):
    """Unit-тесты топологической сортировки блоков."""

    def test_no_deps_preserves_order(self):
        sys = System()
        _register_common(sys, 10)
        mesh = _make_mesh(sys, 10)
        b1 = HypBlock('first', sys, mesh)
        b2 = HypBlock('second', sys, mesh)
        sys.add_block(b1)
        sys.add_block(b2)
        sorted_blocks = sys._sort_blocks()
        self.assertEqual([b.name for b in sorted_blocks], ['first', 'second'])

    def test_deps_ordering(self):
        sys = System()
        _register_common(sys, 10)
        mesh = _make_mesh(sys, 10)
        a = ODEBlock('A', sys, mesh, 'left')
        b = ODEBlock('B', sys, mesh, 'right')
        c = ODEBlock('C', sys, mesh, 'left')
        b.depends_on = ['A']
        c.depends_on = ['B']
        sys.add_block(a)
        sys.add_block(b)
        sys.add_block(c)
        sorted_blocks = sys._sort_blocks()
        a_idx = [b.name for b in sorted_blocks].index('A')
        b_idx = [b.name for b in sorted_blocks].index('B')
        c_idx = [b.name for b in sorted_blocks].index('C')
        self.assertLess(a_idx, b_idx)
        self.assertLess(b_idx, c_idx)


if __name__ == '__main__':
    unittest.main()