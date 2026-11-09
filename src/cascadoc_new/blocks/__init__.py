"""Композиция блоков: ДУЧП + граничные условия + источники.

АРХИТЕКТУРНАЯ ЗАМЕТКА: кейс ``cases/case1`` (роль: архитектор).
ПОСТАНОВКА ИЗМЕНИЛАСЬ: ОДУ теперь ``dz/dt = f(t, z, x(s0,t))`` (было
``x(s1,t)``). Ранее вывод «прямой цикл отсутствует, ``f`` замкнута явной
``N(t)``» УСТАРЕЛ. См. план ``.kilo/plans/1794223868393-case1-architecture.md``.

СУТЬ НОВОЙ СВЯЗКИ. ``x(s0,t)`` — сток левой характеристики; он НЕ задан, а
считается изнутри (``boundary_plain_step(side='left')``) и подаётся в ``f``.
Левое ГУ ``y(s0,t)=z(t)``. На слое ``t_k`` имеем замкнутую связку:
    ``x(s0,t) ↔ z(t) ↔ y(s0,t)=z ↔ ДУЧП``  →  НЕ DAG, нужна ИТЕРАЦИЯ слоя.

Формулы связки (из ``boundary.py:101-111`` и трапеций ОДУ):
    ``x_k = α·z_k + ρ_k``, ``α = (d1T/2)B12/(1-(d1T/2)B11)``;
    ``z_k = z_{k-1} + (dT/2)[f(t_k,z_k,x_k)+f(t_{k-1},z_{k-1},x_{k-1})]``;
    ``q = (dT/2)(L_z+α·L_w) = O(dT) < 1`` → фикс-точка сходится (порядок 2).

Роли блоков при минимальной сборке (реализовано: M1 + M2):
  * ``HypBlock``                    — внутренность ДУЧП 2x2 и начальный слой;
  * ``PlainBoundaryBlock('right')`` — заданное ГУ ``x(s1,t)=N(t)``;
  * ``CoupledBoundaryBlock('left')`` — владеет и ГУ ``y(s0,t)=z``
    (``boundary_plain_step``), и шагом ОДУ ``dz/dt=f(t,z,x(s0,t))``, и
    ИТЕРАЦИЯМИ по слою до сходимости. Пишет ``Z_numeric(s0,t)=z`` и
    ``X(s0,t)=[x,z]``. ``depends_on=['hyp']``.

Альтернатива (общий путь): ``ODESourceBlock('left')`` +
``DeferredBoundaryBlock('left')`` в одной SCC-группе, итерируемой в
``System.solve`` (см. ``system/__init__.py``).

--- ПРОБЕЛЫ (blocks) -------------------------------------------------------

П1 (ЗАКРЫТ, M1). Контекстная форма ``ode_fn(z, t, ctx)`` реализована
    (``ode_context.py``, ``call_ode_fn``); старая форма ``(z, t)`` сохранена
    (арность определяется по сигнатуре). ``ctx.x('left'/'right')`` читает
    ``X`` на границе текущего слоя. ``ODESourceBlock`` переведён на обе формы.

П2 (ЗАКРЫТ, M2). Блок связки ``CoupledBoundaryBlock`` (``coupled_block.py``)
    владеет левым ГУ и шагом ОДУ и САМ итерирует слой до сходимости
    (``method='auto'/'fixed_point'/'newton'/'explicit'``). Диагностика —
    ``history``/``max_iters``/``max_residual``. ``depends_on=['hyp']``.

П3. ``ODESourceBlock`` инициализируется КОНСТАНТОЙ ``init_val``
    (``ode_source.py:22,59``). В новом кейсе ``init_val=y0(s0)`` достаточно;
    общий случай ``z(t0)=решение`` не поддержан.

П4. ``DeferredBoundaryBlock`` жёстко фиксирует роль компоненты:
    left→``y``, right→``x`` (``deferred_block.py:53-62``;
    ``boundary.py:101-123``). Для кейса СОВПАДАЕТ (``y(s0,t)=z``, side='left') —
    НЕ блокер; параметр ``component``/``role`` нужен при обобщении.

П5. ``Block.provides`` (``system/block.py:34-37``) объявлен, но сортировкой
    НЕ используется; цикл на уровне переменных невидим. Нужен для общих SCC.

МИНИМАЛЬНЫЕ ИЗМЕНЕНИЯ (сводно): контекстный ``ode_fn`` (M1, реализовано) +
``CoupledBoundaryBlock`` (M2, реализовано) + явный ``depends_on=['hyp']``
(задаётся в сборке кейса ноутбуком). Остаются как ограничения на будущее:
``component``/``role`` (П4), общий SCC-механизм (M3–M5).
"""
from .boundary import boundary_ode_step, boundary_plain_step
from .hyp_block import HypBlock
from .ode_block import ODEBlock
from .plain_block import PlainBoundaryBlock
from .ode_source import ODESourceBlock
from .deferred_block import DeferredBoundaryBlock
from .coupled_block import CoupledBoundaryBlock
from .ode_context import ODEContext, call_ode_fn

__all__ = [
    'boundary_ode_step', 'boundary_plain_step',
    'HypBlock', 'ODEBlock', 'PlainBoundaryBlock',
    'ODESourceBlock', 'DeferredBoundaryBlock',
    'CoupledBoundaryBlock', 'ODEContext', 'call_ode_fn',
]
