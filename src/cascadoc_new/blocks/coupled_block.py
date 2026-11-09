"""``CoupledBoundaryBlock`` — граница, сцепленная с ОДУ через ДУЧП (M2).

Блок реализует **замкнутую связку** исправленной постановки кейса
``cases/case1``: на левой границе ``s = s0``

    ``y(s0, t) = z(t)``                       (граничное условие),
    ``dz/dt = f(t, z(t), x(s0, t))``,          ``z(t0) = y0(s0)``,

где ``x(s0, t)`` — **сток** левой характеристики, который не задан, а
вычисляется переносом изнутри области (:func:`boundary_plain_step`,
``side='left'``) и сам зависит от ``z(t)``.  Возникает цикл
``x(s0,t) ↔ z(t) ↔ ДУЧП``, которого нет в обычном DAG-порядке блоков.

На каждом слое ``t_k`` связка сводится к **одному скалярному уравнению**
(см. ``math/07_case1_kaskad_pde_ode.md``):

    ``x_k = p_k + q_k · z_k``,   ``q_k = (d1T/2)·B12(s0,t_k) / a``,
                                 ``a = 1 − (d1T/2)·B11(s0,t_k)``,
    ``R(z_k) = z_k − z_{k-1}
               − (dT/2)·[ f(t_k, z_k, p_k + q_k z_k) + f(t_{k-1}, z_{k-1}, x_{k-1}) ] = 0``.

Здесь ``p_k`` собирается из узла ``r`` приходящей характеристики ``x``
(``boundary_plain_step`` при ``value=0``), ``d1T`` — шаг времени вдоль
характеристики ``x`` (``mesh.d1T``), ``dT = d1T + d2T`` — шаг слоя.

Методы решения (``method``):

* ``'auto'``    — для **аффинной** по ``(z, w)`` правой части ``f`` решает
  уравнение прямой подстановкой (без итераций); иначе — Ньютон;
* ``'fixed_point'`` — простая итерация ``z ← G(z)`` (условие сжатия ``q<1``);
* ``'newton'``  — Ньютон по скалярному ``z`` (численная производная ``R``);
* ``'explicit'``— диагностический «лаг»-проход: ``x`` берётся с предыдущего
  слоя (``x_{k-1}``), итерации связки нет; даёт схему порядка ``O(dT)`` вместо
  ``O(dT²)`` (используется в ноутбуке для демонстрации необходимости итераций).

Контроль вырождения и сходимости
--------------------------------

* Коэффициент ``a = 1 − (d1T/2)·B11(s0,t_k)`` — знаменатель уравнения переноса
  ``x = p + q·z``.  При ``|a| < _A_EPS`` связка вырождена (``x`` не выражается
  через ``z``); выбрасывается ``ValueError`` с параметрами ``a``, ``B11``,
  ``d1T`` (см. также :data:`_A_EPS`).
* ``method='fixed_point'`` — перед итерацией оценивается константа сжатия
  ``q = (dT/2)(|f_z| + |β|·|f_w|)`` (``β=q_k``).  Если ``q ≥ 1`` или итерация
  не сошлась за ``max_iter`` (``|R| > tol``), выдаётся :class:`RuntimeWarning`.
  При ``fallback=True`` (по умолчанию) метод автоматически **переключается на
  Ньютон** и решает слой им (см. :attr:`last_fallback`).  При ``fallback=False``
  и нестрогом ``strict=False`` слой остаётся с невязкой, но о ней сообщено;
  при ``strict=True`` выбрасывается ``RuntimeError``.
* ``method='newton'`` / ``'explicit'`` — при исчерпании ``max_iter`` без
  достижения ``tol`` выставляется :attr:`last_converged = False`, и выдаётся
  ``RuntimeWarning`` (или ``RuntimeError`` при ``strict=True``).

Блок пишет ``Z_numeric(s0, t) = z`` и ``X(s0, t) = [x, y=z]``. Число итераций
и невязка ``|R(z_k)|`` доступны в :attr:`history`, :attr:`last_iters`,
:attr:`last_residual`, а также в :attr:`max_iters`, :attr:`max_residual`;
признаки сходимости и фолбэка — в :attr:`last_converged`, :attr:`last_fallback`.
"""
from __future__ import annotations
import warnings
from typing import Callable, Dict, List, Optional, Tuple

import numpy as np

from ..system.block import Block
from ..system.system import System
from ..mesh.mesh import CharacteristicMesh
from ..core.point import Point
from .boundary import boundary_plain_step
from .ode_context import ODEContext, call_ode_fn


class CoupledBoundaryBlock(Block):
    """Левая граница ``y(s0,t)=z``, сцепленная с ОДУ ``dz/dt=f(t,z,x(s0,t))``."""

    # Порог вырождения коэффициента ``a = 1 − (d1T/2)·B11`` из уравнения
    # переноса ``x = p + q·z``.  ``a`` безразмерно и имеет естественный
    # масштаб O(1) (диагональ неявного шага, равная 1), поэтому абсолютный
    # порог ``1e-12`` масштабно-инвариантен и согласован с ``tol`` по умолчанию.
    _A_EPS: float = 1e-12

    def __init__(self, name: str, system: System, mesh: CharacteristicMesh,
                 side: str = 'left',
                 source_var: str = 'Z_numeric',
                 ode_fn: Optional[Callable[..., float]] = None,
                 init_val: Optional[float] = None,
                 method: str = 'auto',
                 tol: float = 1e-12,
                 max_iter: int = 50,
                 x_component: int = 0,
                 y_component: int = 1,
                 fallback: bool = True,
                 strict: bool = False) -> None:
        super().__init__(name, system)
        if side != 'left':
            raise NotImplementedError(
                "CoupledBoundaryBlock реализован для side='left' "
                "(связка x(s0,t) ↔ z через левую границу).")
        if ode_fn is None:
            raise ValueError("CoupledBoundaryBlock требует ode_fn")
        if method not in ('auto', 'fixed_point', 'newton', 'explicit'):
            raise ValueError(
                f"method должно быть 'auto'/'fixed_point'/'newton'/'explicit', "
                f"дано {method!r}")
        self.mesh = mesh
        self.side = side
        self.s_const = mesh.S0 if side == 'left' else mesh.S1
        self.source_var = source_var
        self.ode_fn = ode_fn
        self.init_val = init_val
        self.method = method
        self.tol = tol
        self.max_iter = max_iter
        self.x_component = x_component
        self.y_component = y_component
        # fallback=True  — при несходимости fixed_point автоматически перейти
        #                  на Ньютон (с предупреждением);
        # strict=True    — вместо предупреждения выбрасывать RuntimeError.
        self.fallback = fallback
        self.strict = strict

        self.d1T = mesh.d1T
        self.dT = mesh.dT

        # Диагностика связки.
        self.history: Dict[float, Tuple[int, float]] = {}
        self.last_iters: int = 0
        self.last_residual: float = 0.0
        self.max_iters: int = 0
        self.max_residual: float = 0.0
        # Признаки для последнего решённого слоя.
        self.last_converged: bool = True
        self.last_fallback: bool = False
        # Дедупликация сигналов (предупреждение один раз на блок).
        self._warned: Dict[str, bool] = {}

    # ------------------------------------------------------------------ слои
    @property
    def provides(self) -> str:
        return self.source_var

    def _boundary_nodes(self) -> List:
        return sorted(
            [n for n in self.mesh.nodes_center if n.point[0] == self.s_const],
            key=lambda n: n.point[1])

    def layer_times(self) -> List[float]:
        return sorted({n.point[1] for n in self._boundary_nodes()})

    def _node_ij(self, node) -> Tuple[int, int]:
        for ij, n in self.mesh.center.items():
            if n is node:
                return ij
        raise KeyError("Узел не найден в mesh.center")

    def _coef(self, name: str, point: Point) -> float:
        return float(self.system.variables[name].at(point))

    # --------------------------------------------------------- вспомогательное
    def _ctx(self, point: Point, w: Optional[float] = None) -> ODEContext:
        overrides = {self.side: w} if w is not None else None
        return ODEContext(self.system, point, overrides)

    def _f(self, t: float, z: float, w: float, point: Point) -> float:
        return float(call_ode_fn(self.ode_fn, z, t, self._ctx(point, w)))

    def _affine_coeffs(self, t: float, point: Point
                       ) -> Optional[Tuple[float, float, float]]:
        """Если ``f`` аффинна по ``(z, w)`` — вернуть ``(alpha, gamma, delta)``.

        ``f(t, z, w) = alpha·z + gamma·w + delta``. Иначе ``None``.
        """
        try:
            f00 = self._f(t, 0.0, 0.0, point)
            f10 = self._f(t, 1.0, 0.0, point) - f00
            f01 = self._f(t, 0.0, 1.0, point) - f00
            probes = [
                (2.0, 0.0, f00 + 2 * f10),
                (0.0, 2.0, f00 + 2 * f01),
                (1.0, 1.0, f00 + f10 + f01),
                (0.5, 0.3, f00 + 0.5 * f10 + 0.3 * f01),
            ]
            scale = max(1.0, abs(f00), abs(f10), abs(f01))
            # Порог согласован с tol: если проба отклоняется от аффинной модели
            # сильнее, чем ``tol·scale``, прямая подстановка внесла бы в решение
            # систематическую ошибку, сравнимую с допуском сходимости.  В этом
            # случае f считаем НЕаффинной и (в режиме 'auto') решаем Ньютоном —
            # безопаснее, чем молча принять слабо-нелинейную f за аффинную.
            tol_aff = max(self.tol, 1e-12)
            for z, w, expected in probes:
                if abs(self._f(t, z, w, point) - expected) > tol_aff * scale:
                    return None
            return f10, f01, f00
        except RuntimeError:
            # ctx.x недоступен (напр. 2-арг. ode_fn читается иначе) — не аффинно.
            return None

    # ------------------------------------------------------------------- шаг
    def solve_layer(self, t: float) -> Optional[Tuple[int, float]]:
        nodes = [n for n in self._boundary_nodes()
                 if abs(n.point[1] - t) < 1e-12]
        if not nodes:
            return None
        node = nodes[0]

        if abs(t - self.mesh.T0) < 1e-12:
            self._solve_initial(node)
            self.last_converged = True
            self.last_fallback = False
            return 0, 0.0

        iters, res = self._solve_coupled(node, t)
        self.history[t] = (iters, res)
        self.last_iters, self.last_residual = iters, res
        self.max_iters = max(self.max_iters, iters)
        self.max_residual = max(self.max_residual, res)
        return iters, res

    def _solve_initial(self, node) -> None:
        """Слой ``t0``: ``z = y0(s0)``, ``x = x0(s0)`` (данные задачи)."""
        xval = node['X']
        if xval is not None:
            x = float(np.asarray(xval).reshape(-1)[self.x_component])
        else:
            x = float(self.system.variables['x0'].at(node.point))
        if self.init_val is not None:
            z = float(self.init_val)
        else:
            yval = node['X']
            z = (float(np.asarray(yval).reshape(-1)[self.y_component])
                 if yval is not None
                 else float(self.system.variables['y0'].at(node.point)))
        node['X'] = [x, z] if self.x_component == 0 else [z, x]
        node[self.source_var] = z

    def _solve_coupled(self, node, t: float) -> Tuple[int, float]:
        i, j = self._node_ij(node)
        prev = self.mesh.get_s0_node_left(i, j)
        char = self.mesh.get_center_node_right(i, j)

        z_prev = float(prev[self.source_var])
        x_prev = float(np.asarray(prev['X']).reshape(-1)[self.x_component])

        B11p = self._coef('B11', node.point)
        B12p = self._coef('B12', node.point)
        a = 1.0 - self.d1T / 2.0 * B11p
        if abs(a) < self._A_EPS:
            # a=1−(d1T/2)·B11 — знаменатель уравнения переноса x=p+q·z;
            # вырождение при B11 ≈ 2/d1T (a→0).  Громко и информативно.
            raise ValueError(
                "CoupledBoundaryBlock "
                f"{self.name!r}: вырождение связки: коэффициент a = "
                "1 − (d1T/2)·B11(s0,t_k) ≈ 0 "
                f"(a={a:.3e}, порог |a|={self._A_EPS:.0e}) в точке "
                f"{tuple(node.point)}; B11={B11p:.6e}, d1T={self.d1T:.6e} "
                f"(вырождение при B11 ≈ 2/d1T = {2.0 / self.d1T:.6e}). "
                "Уравнение переноса x = p + q·z не разрешимо относительно x. "
                "Уменьшите шаг dT (мельче сетка) или |B11| так, чтобы "
                "|1 − (d1T/2)·B11| ≥ 1e-12.")
        q = (self.d1T / 2.0) * B12p / a

        # p: перенос x при value=0 (свободный член XZ).
        Xp0 = boundary_plain_step(
            self.system, node.point, char.point, char['X'], 0.0, 'left')
        p = float(Xp0[0])

        def x_of(z: float) -> float:
            return p + q * z

        f_prev = self._f(t - self.dT, z_prev, x_prev, prev.point)
        half = 0.5 * self.dT

        def resid(z: float) -> float:
            return z - z_prev - half * (self._f(t, z, x_of(z), node.point)
                                        + f_prev)

        if self.method == 'explicit':
            # Диагностический «лаг»: x берётся с предыдущего слоя.
            x_lag = x_prev

            def resid_lag(z: float) -> float:
                return z - z_prev - half * (self._f(t, z, x_lag, node.point)
                                            + f_prev)

            z, iters, converged = self._newton(resid_lag, z_prev)
            res = abs(resid_lag(z))
            self.last_fallback = False
            self.last_converged = converged
            if not converged:
                self._report_nonconvergence('explicit', res, t)
        else:
            method = self.method
            if method == 'auto':
                coeffs = self._affine_coeffs(t, node.point)
                if coeffs is not None:
                    z = self._solve_affine(coeffs, z_prev, p, q, f_prev)
                    iters = 0
                    res = abs(resid(z))
                    self.last_fallback = False
                    self.last_converged = True
                    return self._store(node, x_of(z), z, iters, res)
                method = 'newton'
            if method == 'fixed_point':
                z, iters, converged = self._solve_fixed_point(
                    resid, z_prev, t, x_of, node.point, q)
            else:  # newton
                z, iters, converged = self._newton(resid, z_prev)
                self.last_fallback = False
                if not converged:
                    self._report_nonconvergence('newton', abs(resid(z)), t)
            res = abs(resid(z))
            self.last_converged = converged

        return self._store(node, x_of(z), z, iters, res)

    def _solve_affine(self, coeffs, z_prev, p, q, f_prev) -> float:
        alpha, gamma, delta = coeffs
        half = 0.5 * self.dT
        denom = 1.0 - half * (alpha + gamma * q)
        num = z_prev + half * (gamma * p + delta + f_prev)
        return num / denom

    def _contraction_estimate(self, t: float, z: float, w: float,
                              point: Point, q_k: float) -> float:
        """Оценка константы сжатия ``q = (dT/2)(|f_z| + |β|·|f_w|)`` (``07`` §2).

        ``β = q_k`` — коэффициент связи ``x = p + q_k·z``; производные ``f``
        берутся центральной разностью в точке ``(t, z, w)``.
        """
        h = 1e-7 * max(1.0, abs(z))
        fz = (self._f(t, z + h, w, point) - self._f(t, z - h, w, point)) / (2.0 * h)
        fw = (self._f(t, z, w + h, point) - self._f(t, z, w - h, point)) / (2.0 * h)
        return 0.5 * self.dT * (abs(fz) + abs(q_k) * abs(fw))

    def _solve_fixed_point(self, resid, z0: float, t: float, x_of,
                           point: Point, q_k: float) -> Tuple[float, int, bool]:
        """Простая итерация с контролем сжатия и фолбэком на Ньютон.

        Возвращает ``(z, iters, converged)``.  При ``q ≥ 1`` или несходимости
        за ``max_iter`` выдаёт :class:`RuntimeWarning`; если ``self.fallback``,
        переключается на Ньютон (см. :attr:`last_fallback`).
        """
        q_est = self._contraction_estimate(t, z0, x_of(z0), point, q_k)
        if q_est >= 1.0:
            msg = (f"CoupledBoundaryBlock {self.name!r}: оценка константы сжатия "
                   f"q=(dT/2)(|f_z|+|β||f_w|)={q_est:.3f} ≥ 1 на слое t={t}; "
                   "простая итерация не гарантированно сходится "
                   "(условие сжатия q<1 нарушено).")
            if self.strict:
                raise RuntimeError(msg)
            self._warn_once('contraction', msg)
        z, iters, converged = self._fixed_point(resid, z0)
        if converged:
            self.last_fallback = False
            return z, iters, True
        # Не сошлось за max_iter.
        if self.fallback:
            self._warn_once(
                'fallback',
                f"CoupledBoundaryBlock {self.name!r}: method='fixed_point' "
                f"не сошёлся за max_iter={self.max_iter} на слое t={t} "
                f"(q≈{q_est:.3f}, |R|={abs(resid(z)):.3e} > tol={self.tol:.1e}); "
                "автоматический фолбэк на Ньютон.")
            z2, iters2, converged2 = self._newton(resid, z0)
            self.last_fallback = True
            if not converged2:
                self._report_nonconvergence(
                    'fixed_point→newton', abs(resid(z2)), t)
            return z2, iters2, converged2
        self.last_fallback = False
        self._report_nonconvergence('fixed_point', abs(resid(z)), t)
        return z, iters, False

    def _warn_once(self, key: str, msg: str) -> None:
        """Выдать ``RuntimeWarning`` не более одного раза на блок (по ``key``)."""
        if not self._warned.get(key):
            self._warned[key] = True
            warnings.warn(msg, RuntimeWarning)

    def _report_nonconvergence(self, method: str, res: float, t: float) -> None:
        """Сигнал о несходимости: ``RuntimeError`` при ``strict``, иначе warn."""
        msg = (f"CoupledBoundaryBlock {self.name!r}: метод {method!r} не сошёлся "
               f"на слое t={t}: невязка |R|={res:.3e} > tol={self.tol:.1e} "
               f"после max_iter={self.max_iter}.")
        if self.strict:
            raise RuntimeError(msg)
        self._warn_once(f'nonconverged:{method}', msg)

    def _fixed_point(self, resid, z0: float) -> Tuple[float, int, bool]:
        # Работаем в форме z ← z − R(z) (эквивалент G(z) для трапеций ОДУ).
        z = z0
        for it in range(1, self.max_iter + 1):
            z_new = z - resid(z)
            if abs(z_new - z) < self.tol:
                return z_new, it, True
            z = z_new
        return z, self.max_iter, False

    def _newton(self, resid, z0: float) -> Tuple[float, int, bool]:
        z = z0
        for it in range(1, self.max_iter + 1):
            r = resid(z)
            if abs(r) < self.tol:
                return z, it - 1, True
            h = 1e-7 * max(1.0, abs(z))
            dr = (resid(z + h) - resid(z - h)) / (2.0 * h)
            if dr == 0.0:
                break
            z = z - r / dr
        return z, self.max_iter, False

    def _store(self, node, x: float, z: float, iters: int,
               res: float) -> Tuple[int, float]:
        node['X'] = [x, z] if self.x_component == 0 else [z, x]
        node[self.source_var] = z
        return iters, res
