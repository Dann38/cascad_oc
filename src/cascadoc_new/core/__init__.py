"""Базовые типы: точка и переменные.

АРХИТЕКТУРНАЯ ЗАМЕТКА: кейс ``cases/case1`` (роль: архитектор).
Постановка изменилась (ОДУ читает ``x(s0,t)``), поэтому ``z`` теперь читается
ИЗ связки на том же слое — см. план
``.kilo/plans/1794223868393-case1-architecture.md``.

Три вида переменных (см. ``variable.py``): ``AnalyticVariable`` (формула
``f(point)`` на лету), ``NumericVariable`` (хранит ``ndarray`` в узлах),
``DeferredVariable`` (ленивая ссылка на ``NumericVariable``-источник).

Роль ``z`` в кейсе:
  * ``Z_numeric = sys.var_numeric('Z_numeric', dim=1)`` — хранилище;
  * ``Z = sys.var_deferred('Z', source='Z_numeric')`` — ссылка (если потребитель
    читает ``z`` на том же слое). ``at(point)`` делает ОДИН переход к источнику
    (``variable.py:95-100``) и требует, чтобы источник уже имел значение, иначе
    ``RuntimeError`` (``variable.py:101-107``).
  * В минимальном пути связки (``CoupledBoundaryBlock``) ``DeferredVariable`` не
    обязательна: блок пишет ``Z_numeric`` напрямую. ``DeferredVariable.peek``
    нужен лишь для ОБЩЕГО пути (итератор + ``DeferredBoundaryBlock``).

--- ПРОБЕЛЫ (core) ---------------------------------------------------------

П1 (ТЕПЕРЬ БЛОКИРУЮЩИЙ для O(dt^2)). ``DeferredVariable`` — строго одношаговая
    ссылка без ``peek(point)``/непадающего доступа к текущей оценке. Итератору
    связанной группы нужно читать ПРОМЕЖУТОЧНОЕ значение на слое. Раньше это
    считалось «для будущих кейсов»; теперь связка актуальна.
    МИНИМАЛЬНОЕ ИЗМЕНЕНИЕ: ``peek(point) -> Optional`` (текущая оценка/``None``);
    ``at()`` оставить строгим. См. ``REVISION_ARCH.md`` §4.1(5).

П2. ``DeferredVariable`` не имеет ``store`` — писать результат надо в источник
    (``Z_numeric``), а не в ``Z``. Соответствует замыслу; помнить при итерации.

П3. ``NumericVariable.at`` уже возвращает ``None`` при отсутствии значения (не
    падает), т.е. чтение ``X(s0,t)`` в ``ode_fn`` возможно МЕХАНИЧЕСКИ, проблема
    только в том, что значение слоя ещё не посчитано (порядок/итерация), а не в
    доступе к ``NumericVariable``.
"""
from .point import Point
from .variable import Variable, AnalyticVariable, NumericVariable, DeferredVariable
from .utils import normalize_float, PRECISION

__all__ = [
    'Point',
    'Variable', 'AnalyticVariable', 'NumericVariable', 'DeferredVariable',
    'normalize_float', 'PRECISION',
]
