# Документация пакета `cascadoc_new`

`cascadoc_new` — библиотека для решения каскадных систем
ДУЧП + ОДУ (метод характеристик) в задачах оптимального управления.
В центре архитектуры — **точки** (`Point`), **именованные переменные**
(`Variable`) и **композиция блоков** (`Block`), решаемая послойно по времени.

Документация описывает **текущее** состояние кода и намеренно не приукрашивает
его: где механизм ограничен или работает неполно — это отмечено явно
(см. [Известные ограничения](architecture.md#known-limitations)).

> Это индекс-страница. Разделы ниже — ссылки на подробные описания.
> Путеводитель и рабочий пример — в файлах `guide.md` и `example/` (см. таблицу).

---

## Карта разделов

| Раздел | Файл | Что внутри |
|--------|------|------------|
| Обзор архитектуры | [`architecture.md`](architecture.md) | карта слоёв, поток данных, «кто что пишет/читает», ключевые контракты |
| Базовые типы (`core`) | [`architecture/core.md`](architecture/core.md) | `Point`, `Variable`, `AnalyticVariable`, `NumericVariable`, `DeferredVariable`, утилиты |
| Система и композиция (`system`) | [`architecture/system.md`](architecture/system.md) | `Node`, `System`, `Block`, `solve()`, топологическая сортировка, механизм отложенных значений (DAG) |
| Сетка и решатели (`mesh`, `solvers`) | [`architecture/mesh-and-solvers.md`](architecture/mesh-and-solvers.md) | `CharacteristicMesh`, `Solver`, `TrapezoidalSolver` |
| Блоки (`blocks`) | [`architecture/blocks.md`](architecture/blocks.md) | `HypBlock`, `ODEBlock`, `PlainBoundaryBlock`, `ODESourceBlock`, `DeferredBoundaryBlock`, `boundary_ode_step`/`boundary_plain_step` |
| Сборка и визуализация (`problem`, `viz`) | [`architecture/problem-and-viz.md`](architecture/problem-and-viz.md) | `build_hyp_blocks`, `build_hyp_system`, `Plotter` |
| Известные ограничения и roadmap | [`architecture.md#known-limitations`](architecture.md#known-limitations) | циклические зависимости, текущий статус, ссылки на `REVISION_ARCH.md` |
| Путеводитель (руководство) | [`guide.md`](guide.md) | пошагово: система, переменные, сборка сетки и блоков, связи через вычисляемую переменную, запуск и чтение результата |
| Пример | [`../example/cascadoc_new_guide.ipynb`](../example/cascadoc_new_guide.ipynb), [`../example/cascadoc_new_guide.py`](../example/cascadoc_new_guide.py) | рабочий пример: гиперболическая система + граничное ОДУ, правая граница через вычисляемую `z`; сверка с эталоном |

Разделы `guide.md` и каталог `example/` содержат путеводитель и запускаемый
пример; они дополняют архитектурные страницы, а не заменяют их.

---

## Подпакеты: назначение

Направление зависимостей — от `core` к `viz` (без циклов).

| Подпакет | Модули | Назначение |
|----------|--------|------------|
| `core` | `point.py`, `variable.py`, `utils.py` | базовые типы: точка, три вида переменных, нормировка координат |
| `system` | `node.py`, `system.py`, `block.py` | реестр переменных (`System`), узел-обёртка (`Node`), базовый блок (`Block`) |
| `mesh` | `mesh.py` | характеристическая сетка (`CharacteristicMesh`) |
| `solvers` | `solver.py` | базовый интерфейс `Solver` и схема `TrapezoidalSolver` |
| `blocks` | `boundary.py`, `hyp_block.py`, `ode_block.py`, `plain_block.py`, `ode_source.py`, `deferred_block.py` | композиция ДУЧП + граничных ОДУ + блоков-источников |
| `problem` | `setup.py` | сборка задачи (`build_hyp_blocks`, `build_hyp_system`) |
| `viz` | `plotter.py` | визуализация: сетка, поля, разрезы, 3D |

Публичный API плоский: перечисленное доступно прямо из `cascadoc_new`
(например, `from cascadoc_new import Point, build_hyp_blocks`).

---

## Быстрый взгляд

```python
from cascadoc_new import build_hyp_blocks

sys, mesh, hyp = build_hyp_blocks(
    S=(0, 1), T=(0, 0.5), C=(1, 2),
    B=(B11, B12, B21, B22), F=(F1, F2), G=((G11, G12), (G21, G22)),
    x0=x0, y0=y0, phi_dx=phi_dx, phi_dy=phi_dy,
    m=100, boundaries='ode',          # или 'plain' с bc_left/bc_right
)
sys.solve()                            # послойно по t
```

Подробности сборки и запуска — в разделе
[Сборка и визуализация](architecture/problem-and-viz.md), пошаговое
руководство — в [`guide.md`](guide.md), сквозной запускаемый пример —
в [`../example/cascadoc_new_guide.ipynb`](../example/cascadoc_new_guide.ipynb).

---

## Как читать документацию

1. Начните с [обзора архитектуры](architecture.md) — там карта связей и
   сквозной поток данных «источник → хранилище → потребитель».
2. Затем — базовые типы ([`core`](architecture/core.md)) и
   система ([`system`](architecture/system.md)): без них блоки не читаются.
3. Дальше — по необходимости: [сетка/решатели](architecture/mesh-and-solvers.md),
   [блоки](architecture/blocks.md),
   [сборка/визуализация](architecture/problem-and-viz.md).

Каждая страница построена по одному шаблону: **назначение → публичный
интерфейс → связи с другими объектами → ограничения**.
