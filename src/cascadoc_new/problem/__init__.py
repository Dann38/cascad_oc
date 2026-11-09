"""Сборка задачи.

АРХИТЕКТУРНАЯ ЗАМЕТКА: кейс ``cases/case1`` (роль: архитектор).
ПОСТАНОВКА ИЗМЕНИЛАСЬ (ОДУ читает ``x(s0,t)``): кейс теперь содержит ЦИКЛ на
слое, поэтому прежний эскиз (``ODESourceBlock`` с ``ode_fn=lambda z,t:
f(t,z,N(t))``) УСТАРЕЛ. См. план
``.kilo/plans/1794223868393-case1-architecture.md``.

``build_hyp_blocks`` (``setup.py:82-124``) поддерживает ТОЛЬКО однородные
границы: ``boundaries='ode'`` или ``boundaries='plain'`` (``setup.py:113-122``).
Смешанный режим и режим связки/отложенной границы ОТСУТСТВУЮТ. Поэтому кейс
через ``build_hyp_blocks`` НЕ собирается.

РЕКОМЕНДУЕМЫЙ ПУТЬ (публичное API): ``build_hyp_system`` (``setup.py:60-79``)
регистрирует переменные и создаёт ``CharacteristicMesh``, НО не добавляет блоки;
далее блоки добавляются вручную. Для НОВОЙ постановки нужен блок связки
(``CoupledBoundaryBlock``, см. ``blocks/``), который гоняет итерации слоя:

    sys, mesh, _ = build_hyp_system(
        S=(s0, s1), T=(t0, t1), C=(c1, c2),
        B=(B11, B12, B21, B22), F=(F1, F2),
        G=((lambda t: 0.0, lambda t: 0.0),
           (lambda t: 0.0, lambda t: 0.0)),      # в прямом кейсе не нужно
        x0=x0, y0=y0, phi_dx=..., phi_dy=..., m=40)
    sys.var_numeric('Z_numeric', dim=1)
    sys.add_block(HypBlock('hyp', sys, mesh))
    sys.add_block(PlainBoundaryBlock('right_plain', sys, mesh, 'right', value_fn=N))
    coupled = CoupledBoundaryBlock('left_coupled', sys, mesh, side='left',
        source_var='Z_numeric',
        ode_fn=lambda z, t, ctx: f(t, z, ctx.x('left')),   # x(s0,t) того же слоя
        init_val=y0(s0), method='fixed_point', tol=1e-12, max_iter=50)
    coupled.depends_on = ['hyp']
    sys.add_block(coupled)
    sys.solve()

Замечания по ``build_hyp_system``: он ОБЯЗУЕТ передать ``G`` и ``phi_dx/phi_dy``
позиционно, хотя в кейсе они не нужны — передаём заглушки. ``_register_variables``
(``setup.py:9-57``) регистрирует также ``PSI``/``p`` (сопряжённые) — в прямом
кейсе не используются.

--- ПРОБЕЛЫ (problem) ------------------------------------------------------

П1 (главный). Нет сборщика под смешанные границы и под связку. Нет ни per-side
    параметра, ни режима 'coupled'/'deferred'. МИНИМАЛЬНОЕ ИЗМЕНЕНИЕ: расширить
    ``build_hyp_blocks`` до per-side задания, например
    ``boundaries=('coupled','plain')`` или список спецификаций блоков, либо
    добавить ``build_hyp_coupled`` для сценария «слева связка, справа заданная».

П2. Публичный builder регистрирует фиксированный набор имён (``B..F, G, x0, y0,
    X, PSI, p``), но не даёт удобного способа добавить пользовательские
    неизвестные (``Z_numeric``/``Z``); их регистрируют вручную. Приемлемо;
    задокументировать как штатный шаг.

П3. ``build_hyp_system`` возвращает неиспользуемый в блоковой сборке
    ``TrapezoidalSolver``.
"""
from .setup import build_hyp_system, build_hyp_blocks

__all__ = ['build_hyp_system', 'build_hyp_blocks']
