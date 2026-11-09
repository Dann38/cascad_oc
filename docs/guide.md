# Путеводитель: как собрать систему, блоки и связи

Это пошаговое руководство отвечает на вопрос «**как этим пользоваться**»:
как создать `System`, зарегистрировать переменные, построить сетку и блоки,
**связать блоки через переменные** и прочитать результат. Всё показано на
одном сквозном примере — гиперболическая система + граничное ОДУ,
у которого правая граница задаётся **вычисляемой в процессе** переменной `z`.

Математический эталон примера (постановка, выводы, угловая согласованность,
замкнутое решение) — в [`math/06_example_reference.md`](../math/06_example_reference.md).
Рабочий запускаемый код — в [`example/cascadoc_new_guide.py`](../example/cascadoc_new_guide.py)
и ноутбуке [`example/cascadoc_new_guide.ipynb`](../example/cascadoc_new_guide.ipynb).

Перед чтением полезно просмотреть [обзор архитектуры](architecture.md) и
[базовые типы](architecture/core.md): здесь мы ими пользуемся, а не
пересказываем.

---

## 0. Что мы собираем (одной картинкой)

| Что | Объект | Роль в примере |
|-----|--------|----------------|
| Реестр всего | `System` | хранит переменные и композицию блоков |
| Геометрия | `CharacteristicMesh` | сетка вдоль характеристик по `(s, t)` |
| ДУЧП внутри области | `HypBlock` | решает `x_t − C1·x_s = …`, `y_t + C2·y_s = …` |
| Левая граница `s = S0` | `PlainBoundaryBlock` | задаёт `y(S0,t) = y_l(t)` |
| Правый «источник» | `ODESourceBlock` | решает `dz/dt = f(z,t)`, пишет в `NumericVariable('Z_numeric')` |
| Правый «потребитель» | `DeferredBoundaryBlock` | читает `z` через `DeferredVariable('Z')`, ставит `x(S1,t) = z(t)` |

Поток данных: **`ODESourceBlock → NumericVariable('Z_numeric') → DeferredVariable('Z') → DeferredBoundaryBlock`**.
Это направленный ациклический граф (DAG) «источник → потребитель»
(см. [ограничения](architecture.md#known-limitations)).

---

## 1. Постановка задачи

Неизвестные `x(s,t)`, `y(s,t)` и вычисляемая переменная `z(t)`:
область `s ∈ [S0, S1]`, `t ∈ [t0, T]`. Система — линейная 2×2 в форме

```
x_t − C1·x_s = B11·x + B12·y + F1        (C1 > 0)
y_t + C2·y_s = B21·x + B22·y + F2        (C2 > 0)
```

Начальные условия (НУ): `x(s,t0) = x0(s)`, `y(s,t0) = y0(s)`.
Граничные условия (ГУ): `x(S1,t) = z(t)` (правая граница),
`y(S0,t) = y_l(t)` (левая граница).
Граничное ОДУ: `dz/dt = a·z + b(t)`.

Выбор границ **согласован с направлениями характеристик**:
`x` переносится вдоль `ds/dt = −C1` и «входит» в область через `s = S1`
(там и задаётся `x`), а `y` переносится вдоль `ds/dt = +C2` и входит через
`s = S0` (там задаётся `y`). На каждой границе ровно одна входящая
компонента — задача корректна по типам условий (подробный вывод — в
[`math/06`](../math/06_example_reference.md), §1).

---

## 2. Ключевое замечание: угловая согласованность

Прежде чем кодировать, надо проверить **согласованность в углах**.

* Правый угол `(S1, t0)`: НУ даёт `x(S1,t0) = x0(S1)`, а ГУ даёт
  `x(S1,t0) = z(t0)`. Значит необходимо

  ```
  z(t0) = x0(S1).                        (2.1)
  ```

* Левый угол `(S0, t0)`: аналогично

  ```
  y_l(t0) = y0(S0).                      (2.2)
  ```

В нашем примере `x0 ≡ y0 ≡ 0`, поэтому нужны `z(t0) = 0` и `y_l(t0) = 0`.

Все НУ/ГУ и угловые условия (2.1)–(2.2) сохраняются, а граничное ОДУ
берём **неоднородным**:

```
dz/dt = a·z + b(t),   z(t0) = 0,   b(t) ≢ 0.        (2.3)
```

Угловое условие (2.1) выполняется автоматически (`z(t0) = 0`), а решение

```
z(t) = ∫_{t0}^{t} e^{a(t−τ)} b(τ) dτ
```

при `b ≢ 0` не равно нулю тождественно. Именно это ОДУ мы и решаем.
Конкретные параметры для сверки:

```
C1 = C2 = 1,   S0 = 0,   S1 = 1,   t0 = 0,   T = 1,
x0(s) = 0,   y0(s) = 0,   B = 0,   F = 0,
a = −1,   b(t) = 1        ⟹   z(t) = 1 − e^{−t},
y_l(t) = sin(π·t)         (y_l(0) = 0 — угол (S0,t0) согласован).
```

Замкнутый эталон (характеристики):

```
z(t)   = 1 − e^{−t}
x(s,t) = 0,                   s + t ≤ 1,
         1 − e^{−(s+t−1)},    s + t > 1.
y(s,t) = 0,                   t ≤ s,
         sin(π·(t − s)),      t > s.
```

> Более простой вариант: `a = 0`, `b(t) = 1` ⇒ `z(t) = t`,
> `x(s,t) = max(0, s + t − 1)`. Он удобен, если не нужна
> экспонента. Наша демонстрация использует `a = −1` (совпадает с
> [`math/06`](../math/06_example_reference.md), §3.2).

---

## 3. Шаг 1. Создать `System` и зарегистрировать переменные

`System` — это реестр: он хранит **именованные переменные** и список блоков.
Переменная — величина, определённая на точках `Point(s, t)`. Есть три вида
(см. [`core`](architecture/core.md)):

| Регистратор | Класс | Смысл |
|-------------|-------|-------|
| `var_analytic(name, fn)` / `var_const(name, value)` | `AnalyticVariable` | значение по формуле/константе, считается на лету |
| `var_callable(name, fn)` | — (в `System.functions`) | функция не от точки сетки, а от состояния: `fn(point, x, y)` |
| `var_numeric(name, dim=…)` | `NumericVariable` | хранилище значений в узлах (состояние) |
| `var_deferred(name, source=…)` | `DeferredVariable` | вычисляемая в процессе переменная: ленивая ссылка на `NumericVariable` |

`AnalyticVariable` обычно `dim=1` (возвращает `float`), но допускает и вектор.
Константу можно передать прямо: `sys.var_analytic('C1', 1)`.

```python
import math
from cascadoc_new import (System, Point, CharacteristicMesh, HypBlock,
                          PlainBoundaryBlock, ODESourceBlock,
                          DeferredBoundaryBlock)

# --- параметры задачи ---
C1 = C2 = 1.0
S0, S1 = 0.0, 1.0
T0, T1 = 0.0, 1.0
A_ODE = -1.0
def b_fn(t):  return 1.0
def y_l_fn(t): return math.sin(math.pi * t)

sys = System()

# (1) геометрия и коэффициенты — аналитические (главный источник правды).
#     CharacteristicMesh берёт из них C1, C2, S0, S1, T0, T1.
sys.var_analytic('C1', C1)
sys.var_analytic('C2', C2)
sys.var_analytic('S0', S0)
sys.var_analytic('S1', S1)
sys.var_analytic('T0', T0)
sys.var_analytic('T1', T1)

#     коэффициенты уравнений: чистый перенос, поэтому нули.
for name in ('B11', 'B12', 'B21', 'B22', 'F1', 'F2'):
    sys.var_analytic(name, lambda point: 0.0)
#     G-коэффициенты нужны сборке выходного слоя HypBlock.finalize
#     (G=0 ⇒ выходной слой досчитывается переносом вдоль характеристик).
for name in ('G11', 'G12', 'G21', 'G22'):
    sys.var_analytic(name, lambda point: 0.0)

#     начальные данные как функции s (здесь — тождественный нуль).
sys.var_analytic('x0', lambda point: 0.0)
sys.var_analytic('y0', lambda point: 0.0)

# (2) функции не от точки, а от состояния — для сопряжённого хода.
#     В этом примере сопряжённый ход не запускается; регистрация безвредна.
sys.var_callable('phi_dx', lambda point, x, y: 0.0)
sys.var_callable('phi_dy', lambda point, x, y: 0.0)

# (3) численное состояние: вектор [x, y] на каждом узле.
sys.var_numeric('X', dim=2)

# (4) вычисляемая в процессе переменная z:
#     - NumericVariable — «хранилище», куда пишет блок-источник;
#     - DeferredVariable — ленивая «ручка», которую читает потребитель.
sys.var_numeric('Z_numeric', dim=1)
sys.var_deferred('Z', source='Z_numeric')
```

Что произошло:

* `X` (`dim=2`) — состояние; это общее хранилище, через которое «общаются»
  блоки (узел `Point(s, t)` один и тот же для всех блоков).
* `Z_numeric` — численная переменная-источник; её заполнит `ODESourceBlock`.
* `Z` — `DeferredVariable`, привязанная к системе (`source='Z_numeric'`).
  Её `at(point)` читает значение из источника и **бросает `RuntimeError`**,
  если значение ещё не посчитано (это защита от неверного порядка блоков).

---

## 4. Шаг 2. Геометрия: `CharacteristicMesh`

Сетка строится **после** регистрации `C1, C2, S0, S1, T0, T1`: она читает их
из системы (единый источник правды). Аргумент `m` задаёт число точек
дискретизации, `h` — шаг по `t` (нужен ровно один из них).

```python
mesh = CharacteristicMesh(sys, m=40)
```

Сетка хранит узлы-`Node` в группах `nodes_center`, `nodes_start_l`,
`nodes_start_r`, `nodes_final_l`, `nodes_final_r`; у каждого узла
`node.point` — это `Point(s, t)`. Значения переменных сетка **не хранит** —
они живут в `System` (см. [`mesh-and-solvers`](architecture/mesh-and-solvers.md)).

---

## 5. Шаг 3. Собрать блоки

Блок — единица композиции, решающая «свою» часть узлов послойно по времени
`t` (см. [`blocks`](architecture/blocks.md)). В нашем примере четыре блока.

```python
# (1) внутренность области + начальный и выходной слои.
sys.add_block(HypBlock('hyp', sys, mesh))

# (2) левая граница s = S0: y(S0,t) = y_l(t) задана напрямую.
sys.add_block(PlainBoundaryBlock('left_plain', sys, mesh,
                                 side='left', value_fn=y_l_fn))

# (3) правый источник: решает dz/dt = a·z + b(t) и пишет z в Z_numeric.
sys.add_block(ODESourceBlock('z_source', sys, mesh,
                             source_var='Z_numeric',
                             ode_fn=lambda z, t: A_ODE * z + b_fn(t),
                             init_val=0.0,          # z(t0) = 0  (угол (S1,t0))
                             side='right'))

# (4) правая граница s = S1: читает z из DeferredVariable('Z')
#     и ставит x(S1,t) = z(t).
sys.add_block(DeferredBoundaryBlock('deferred_right', sys, mesh,
                                    side='right',
                                    deferred_var='Z',
                                    source_block='z_source'))
```

Разбор:

* **`HypBlock`** решает начальный слой `t = T0` (`x0, y0`), внутренние узлы
  `S0 < s < S1` и (в `finalize`) выходной слой `t = T1`. Граничные узлы он
  **пропускает** — их ведут граничные блоки.
* **`PlainBoundaryBlock(side='left')`** знает компоненту `y` (через
  `value_fn(t)`), а `x` досчитывает по приходящей характеристике.
* **`ODESourceBlock`** на каждом слое решает `dz/dt = ode_fn(z, t)` схемой
  трапеций и пишет результат в `source_var`. Его `ode_fn` имеет сигнатуру
  `Callable[[float, float], float]` (то есть `f(z, t)`) — именно поэтому
  `a·z + b(t)` выражается напрямую.
* **`DeferredBoundaryBlock(side='right')`** читает `z` из `Z` и через
  `boundary_plain_step` подставляет `x(S1,t) = z`, досчитывая `y`.

### Когда удобно `build_hyp_blocks`

Если обе границы заданы **напрямую** (не через вычисляемую переменную),
сборку `HypBlock` + двух `PlainBoundaryBlock` (или `ODEBlock`) можно получить
фабрикой `build_hyp_blocks` (см. [`problem-and-viz`](architecture/problem-and-viz.md)):

```python
from cascadoc_new import build_hyp_blocks

sys2, mesh2, hyp2 = build_hyp_blocks(
    S=(0, 1), T=(0, 1), C=(1, 1),
    B=(lambda s, t: 0.0,) * 4,
    F=(lambda s, t: 0.0,) * 2,
    G=((lambda t: 0.0,) * 2,) * 2,
    x0=lambda s: 0.0, y0=lambda s: 0.0,
    phi_dx=lambda s, x, y: 0.0, phi_dy=lambda s, x, y: 0.0,
    m=40, boundaries='plain',
    bc_left=y_l_fn,                     # y(S0,t)
    bc_right=lambda t: 1.0 - math.exp(-t),   # x(S1,t) = z(t) — здесь задана явно
)
sys2.solve()
```

**Важно:** `build_hyp_blocks` не умеет добавлять `ODESourceBlock` /
`DeferredBoundaryBlock` — это фабрика только для «простой» границы. Поэтому
сквозной пример со **связыванием через вычисляемую переменную** собирается
вручную, как в п. 5. Здесь `bc_right` — та же `z(t)`, но подставленная
напрямую (для сравнения двух путей).

---

## 6. Шаг 4. Как блоки связаны (интерфейс = совпадение точек)

Отдельного объекта «интерфейс» в библиотеке **нет** и не нужно
(см. [`block`](architecture/system.md)). Связь возникает из двух вещей:

1. **Общее хранилище по координатам.** Значения живут в `NumericVariable`
   системы, ключ — нормированные координаты `Point`. Два блока, обратившиеся
   к `Point(s, t)`, видят **одну и ту же** ячейку. Поэтому `HypBlock`,
   `PlainBoundaryBlock`, `ODESourceBlock` и `DeferredBoundaryBlock` на
   границе `s = S1` (или `s = S0`) работают с одними и теми же узлами — это и
   есть интерфейс.
2. **Отложенная переменная как ребро графа.** `DeferredVariable('Z')`
   объявлена с `source='Z_numeric'`. Её `at(point)` достаёт значение из
   источника в момент чтения:

   ```
   DeferredBoundaryBlock('deferred_right').solve_layer(t)
       └─ node['Z']  →  DeferredVariable('Z').at(point)
                          └─ Z_numeric.at(point)   # ← сюда писал ODESourceBlock
   ```

Чтобы блок-потребитель выполнялся **после** источника, у него заполнено
`depends_on`:

```python
DeferredBoundaryBlock(..., source_block='z_source')
# эквивалентно:
#   blk.depends_on = ['z_source']
```

`System._sort_blocks()` (топологическая сортировка Кана) учитывает
`depends_on` и на каждом слое ставит источник раньше потребителя.

---

## 7. Шаг 5. Запуск: `System.solve()`

`solve()` собирает все слои времени из блоков и проходит по ним **по
возрастанию `t`**; на каждом слое блоки выполняются в топологическом порядке;
после всех слоёв вызывается `finalize` (сборка выходной границы `t = T1`).

```python
sys.solve()      # послойно по t; внутри — топологический порядок блоков
```

Порядок на слое: сначала `z_source` (пишет `Z_numeric`), затем
`deferred_right` (читает `Z` ← `Z_numeric`), и независимые `HypBlock` /
`left_plain` на своих узлах.

---

## 8. Шаг 6. Чтение результата (`Node` и `Variable.at`)

Результат читается в двух стилях.

**Через `Node`** (по узлам сетки; удобно для полей и сравнения):

```python
for node in mesh.nodes_center:
    s, t = node.point[0], node.point[1]   # только индексный доступ!
    x, y = node['X']                      # X: dim=2 → np.ndarray([x, y])
    ...
    if s == S1:
        z = node['Z']                     # Z: dim=1 → float
```

**Через `Variable.at(point)`** (произвольная точка):

```python
p = Point(1.0, 0.5)
sys.variables['X'].at(p)     # np.ndarray([x, y])  — состояние
sys.variables['Z'].at(p)     # np.ndarray([z])     — вычисляемая переменная
sys.variables['B11'].at(p)   # 0.0                 — аналитическая
```

Полезно и `node.is_computed('X')` — вернёт `True`, если узел уже посчитан
(аналитические считаются всегда).

---

## 9. Сверка с аналитическим эталоном

Считаем максимальные отклонения численного решения от замкнутого эталона из
[`math/06`](../math/06_example_reference.md) (§3.2) на всех узлах:

```python
def z_ref(t):   return 1.0 - math.exp(-t)
def x_ref(s, t): return 0.0 if s + t <= 1.0 else 1.0 - math.exp(-(s + t - 1.0))
def y_ref(s, t): return 0.0 if t <= s else math.sin(math.pi * (t - s))

dx = dy = dz = 0.0
for node in mesh.nodes_center:
    s, t = node.point[0], node.point[1]
    x, y = node['X']
    dx = max(dx, abs(x - x_ref(s, t)))
    dy = max(dy, abs(y - y_ref(s, t)))
    if s == S1:
        dz = max(dz, abs(float(node['Z']) - z_ref(t)))
```

Ожидаемый результат (`m = 40`):

| Величина | Отклонение | Причина |
|----------|-----------|---------|
| `max|x − x_эт|` | `≈ 2·10⁻⁵` | `x = z` на границе, а `z` решается трапециями (`O(dT²)`) |
| `max|y − y_эт|` | `≈ 10⁻¹⁵` | перенос по характеристике при `B=F=0` воспроизводится точно |
| `max|z − z_эт|` | `≈ 2·10⁻⁵` | погрешность трапеций при интегрировании `dz/dt = −z + 1` |

Погрешность `x` и `z` — это `O(dT²)` схемы трапеций; она переносится в `x`
через условие `x(S1,t) = z(t)`. `y` совпадает с эталоном до машинной
точности. Фактический вывод запуска — в
[`example/cascadoc_new_guide.py`](../example/cascadoc_new_guide.py).

---

## 10. Ограничение: это DAG, а не петля

Связывание `z_source → deferred_right` **ациклично** и работает. Чего
текущая архитектура **не** умеет:

* **циклы/петли** — если правая часть ОДУ должна зависеть от состояния ДУЧП
  на том же слое, например `dz/dt = f(z, y(S1,t), t)`. `ODESourceBlock.ode_fn`
  автономен (`f(z, t)`), он **не видит** `y(S1,t)`; `System.solve()` делает
  один проход на слой без итераций, а `DeferredVariable.at` при отсутствии
  значения **бросает `RuntimeError`**. Блоки, попавшие в цикл, молча
  получают неверный порядок (`_sort_blocks` добавляет их в конец).

Поэтому наш пример демонстрирует именно **связывание** через вычисляемую
переменную, а не петлю. Полный список и разбор — в
[Известные ограничения](architecture.md#known-limitations) и
[`REVISION_ARCH.md`](../REVISION_ARCH.md).

---

## 11. Полный листинг

Сквозной запускаемый код — [`example/cascadoc_new_guide.py`](../example/cascadoc_new_guide.py)
(и тот же сценарий в ноутбуке [`example/cascadoc_new_guide.ipynb`](../example/cascadoc_new_guide.ipynb)).
Он печатает три отклонения `max|Δ|` из п. 9 и подтверждает, что пример
исполняется без ошибок.

---

## Ссылки

* Эталон примера: [`math/06_example_reference.md`](../math/06_example_reference.md).
* Рабочий код: [`example/cascadoc_new_guide.py`](../example/cascadoc_new_guide.py),
  [`example/cascadoc_new_guide.ipynb`](../example/cascadoc_new_guide.ipynb).
* Архитектура: [обзор](architecture.md), [`core`](architecture/core.md),
  [`system`](architecture/system.md), [`mesh-and-solvers`](architecture/mesh-and-solvers.md),
  [`blocks`](architecture/blocks.md), [`problem-and-viz`](architecture/problem-and-viz.md).
* Ограничения и roadmap: [`architecture.md#known-limitations`](architecture.md#known-limitations),
  [`REVISION_ARCH.md`](../REVISION_ARCH.md).
