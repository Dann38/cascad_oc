"""Визуализация.

АРХИТЕКТУРНАЯ ЗАМЕТКА: кейс ``cases/case1`` (роль: архитектор).
Примечание: после смены постановки (ОДУ читает ``x(s0,t)``, связка на слое)
отрисовка НЕ меняется — рисовать по-прежнему ``X`` и ``Z_numeric``; замечание
ниже актуально. См. план ``.kilo/plans/1794223868393-case1-architecture.md``.

Требование кейса «отрисовать любую неизвестную и её срез (например
``x(s, t1)``)» закрывается штатно:
  * поле неизвестной: ``Plotter.plot_field('X', component=0)``;
  * срез по ``t``: ``Plotter.plot_slice([('X', 0)], t=mesh.T1)`` — ближайший
    уровень ``t`` (``plotter.py:134-141``), точки берутся по узлам сетки,
    сортируются по ``s`` (``plotter.py:270-286``);
  * срез по ``s``: ``Plotter.plot_slice(('X', 0), s=mesh.S0)``;
  * ``z(t)`` на границе: рисовать как ``plot_slice(('Z_numeric', 0), s=mesh.S0)``;
  * на том же графике удобно накладывать аналитический эталон (callable
    ``lambda s, t: ...`` рисуется непрерывной линией, ``plotter.py:287-291``).
Проверено: ``plot_slice([('X', 0), (lambda s,t: x_an(s,t))], t=mesh.T1)``
работает.

--- ПРОБЕЛ (viz) -----------------------------------------------------------

П1. ``_make_getter`` (``plotter.py:90-126``) считает «численной» ТОЛЬКО
    ``NumericVariable`` (``plotter.py:101``). ``DeferredVariable`` попадает в
    ветку «аналитика»: в ``plot_slice``/``plot_field`` значение досчитывается в
    НЕПРЕРЫВНЫХ точках (``plotter.py:287-291``), где ``Z_numeric`` пуст, и
    ``DeferredVariable.at`` бросает ``RuntimeError`` (``core/variable.py:101-107``).
    Проверено: ``plot_slice('Z', s=mesh.S0)`` падает, а
    ``plot_slice(('Z_numeric', 0), s=mesh.S0)`` работает.

    МИНИМАЛЬНОЕ ИЗМЕНЕНИЕ: в ``Plotter._make_getter`` трактовать
    ``DeferredVariable`` как численную (``is_numeric = isinstance(var,
    (NumericVariable, DeferredVariable))``), чтобы рисование шло по узлам
    сетки, где значение уже посчитано. До внесения — документировать правило
    «рисовать источник (``Z_numeric``), а не отложенную ссылку (``Z``)».

П2. ``plot_field`` отложенной/граничной величины покажет только столбец
    ``s = s0`` (у ``Z_numeric`` значения лишь на границе); для ``nan`` вне
    столбца ``plot_field`` уже отфильтровывает их (``plotter.py:217-218``).
"""
from .plotter import Plotter, plot_mesh, plot_field, plot_slice, plot_surface

__all__ = ['Plotter', 'plot_mesh', 'plot_field', 'plot_slice', 'plot_surface']
