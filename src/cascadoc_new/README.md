# CascadOC — новая архитектура

## Ключевая идея

Решение каскадных систем ДУЧП + ОДУ для задач оптимального управления.

В центре архитектуры — **точки** (`Point`) и **именованные переменные** (`Variable`),
определённые на точках сетки. Переменная может быть аналитической
(вычисляется на лету), численной (хранит значения) или ссылочной
(берётся из другой переменной, resolved во время решения).

## Точка `Point`

Точка хранит произвольное число координат и служит единым аргументом функции
вместо списка отдельных чисел. Точки **конкатенируются** оператором `|`:

```python
Point(0, 1) | Point(2, 3)      # → Point(0, 1, 2, 3)
Point(1) | Point(2) | Point(3) # → Point(1, 2, 3)
```

Координаты доступны по индексу: `point[0]`, `point[1]`.

## Основные типы

### `Variable` — именованная величина

```python
# Аналитическая: f(point) — не хранит данные, считает при каждом запросе
var = AnalyticVariable('B11', lambda point: -2 * point[0], dim=1)

# Численная: хранит np.ndarray(dim,) в каждой точке
var = NumericVariable('X', dim=2)
var.store(Point(s, t), np.array([x, y]))
val = var.at(Point(s, t))  # → np.ndarray(2,)

# Ссылочная: значение берётся из другой переменной во время решения
var = DeferredVariable('Z', source='Z_numeric')
```

Аналитические — для коэффициентов (B, F, G, C, ...).  
Численные — для состояния и сопряжённых переменных (X, PSI, p).  
Ссылочные (`DeferredVariable`) — для переменных, которые заполняются
блоком-производителем в ходе ``System.solve()``.

### `Node` — точка с ленивым доступом к переменным

```python
n = sys.node(Point(s, t))

n['X']       # → np.ndarray(dim,)  — чтение/вычисление
n['B11']     # → float             — аналитика на лету
n['X'] = [x, y]  # запись (только numeric)
n['X'][0]    # → float — компонента
n.is_computed('X')  # проверка
```

Node **не хранит данные** — только `Point` и ссылку на System. Чтение/запись идут
в реестр переменных System. Каждая точка в системе ровно одна: совпадающие
по координате узлы — это один и тот же узел.

### `System` — реестр переменных

```python
sys = System()
sys.var_analytic('B11', lambda point: -2 * point[0], dim=1)  # коэффициент
sys.var_analytic('C1', 1)              # константа: число вместо функции
sys.var_const('C2', 2)                 # то же самое, сахар
sys.var_callable('phi_dx', fn)         # функция, зависящая от состояния
sys.var_numeric('X', dim=2)            # вектор состояния
sys.var_numeric('PSI', dim=2)          # сопряжённый вектор
sys.var_numeric('p', dim=1)            # сопряжённая переменная (скаляр)
sys.var_deferred('Z', source='Z_num')  # ссылочная переменная

n = sys.node(Point(s, t))              # узел с привязкой
```

Размерность переменной (dim) — число компонент. Для ДУЧП 2×2 dim=2, для ОДУ dim=1, для 3D систем — число уравнений.

## Сетка

### `CharacteristicMesh` — сетка для гиперболических систем

Строит узлы `(i, j) -> Node(Point(s, t))` вдоль характеристик `ds/dt = +C1` и
`ds/dt = -C2`. Геометрию (S, T, C) и шаг (m или h) берёт из System. Классифицирует
узлы на `center` / `start_l` / `start_r` / `final_l` / `final_r`, хранит топологию
и умеет выдавать соседей по характеристикам.

```python
mesh = CharacteristicMesh(sys, m=5)
mesh.get_center_node(i, j)          # → Node
mesh.get_center_node_left(i, j)     # → Node (или граничный)
mesh.is_from_center(i, j)           # внутри области
```

Сетка **не хранит решения** — только узлы-точки. Значения живут в System.

## Композиция блоков

Гиперболическая задача собирается как **композиция блоков** (`System.blocks`),
а не монолитный решатель. Блок — единица системы, решающая свою часть узлов
послойно по времени:

* `HypBlock` — внутренность `S0 < s < S1`, начальный и выходной слои;
* `ODEBlock` — граница `s = const`, заданная **ОДУ** с коэффициентами `G`,
  сцепленным с приходящей характеристикой из `HypBlock`;
* `PlainBoundaryBlock` — граница, значение на которой задано **напрямую**
  функцией времени;
* `ODESourceBlock` — решает ОДУ на границе и пишет результат в численную
  переменную (источник для отложенных переменных);
* `DeferredBoundaryBlock` — граничный блок, читающий значение из отложенной
  переменной (`DeferredVariable`).

Блоки не хранят значения: «интерфейс» между ними — общее хранилище
`NumericVariable`. Узел `Point(s, t)` один и тот же для всех блоков,
поэтому обмен идёт без отдельных объектов-связок.

```python
from cascadoc_new import build_hyp_blocks

sys, mesh, hyp = build_hyp_blocks(
    S=(0, 1), T=(0, 0.5), C=(1, 2),
    B=(B11, B12, B21, B22), F=(F1, F2), G=((G11, G12), (G21, G22)),
    x0=x0, y0=y0, phi_dx=phi_dx, phi_dy=phi_dy,
    m=100,
    boundaries='ode',          # или 'plain' с bc_left/bc_right
)
sys.solve()                    # послойно по t
```

### Режимы границ

1. **`boundaries='plain'`** — `PlainBoundaryBlock`: недостающая компонента
   известна как `value_fn(t)`, вторая досчитывается по характеристике
   (`boundary_plain_step`).
2. **`boundaries='ode'`** — `ODEBlock`: компонента на границе живёт во времени
   (`dy/dt = G21·x + G22·y` слева, `dx/dt = G11·x + G12·y` справа) и
   алгебраически сцеплена с ДУЧП (`boundary_ode_step`).
3. **Отложенная переменная** — `ODESourceBlock` + `DeferredBoundaryBlock`:
   граничное значение вычисляется в ходе решения, а не задаётся извне.

Порядок решения задаёт `System.solve()`: блоки сортируются топологически,
слои обрабатываются по возрастанию `t`. Зависимости между блоками
описываются полем `depends_on`.

## Визуализация

Вся отрисовка вынесена в отдельный подпакет `cascadoc_new.viz` и не затрагивает
сетку/решатель: `cascadoc_new.mesh` больше не импортирует matplotlib.

```python
from cascadoc_new import Plotter

viz = Plotter(sys, mesh)

viz.plot_mesh()                        # геометрия сетки

# любая функция на (s, t): имя переменной, компонента, callable или число
viz.plot_field('X', component=0)       # псевдоцветное поле
viz.plot_field(lambda point: point[0] * point[1])  # произвольная функция

# разрез при фиксированном s или t; сразу несколько функций на графике
viz.plot_slice([('X', 0), ('X', 1), x_an], t=mesh.T1,
               labels=['X[0]', 'X[1]', 'x_an'])
viz.plot_slice([('PSI', 0), ('PSI', 1)], s=mesh.S0)

viz.plot_surface('X', component=0)     # 3D поверхность z = f(s, t)
```

Функция задаётся одним из способов:

| Запись | Значение |
|--------|----------|
| `'X'` | имя переменной System (численной, аналитической или ссылочной) |
| `('X', 1)` | компонента векторной переменной |
| `lambda point: ...` | `f(Point) -> float` |
| `lambda s, t: ...` | `f(s, t) -> float` |
| число | константа |

Численные переменные рисуются по узлам сетки (фактические данные решения),
аналитические и callable — по непрерывной линии (`samples` точек), что удобно
для сравнения решения с аналитическим эталоном. Все методы принимают `ax` и
возвращают его же, поэтому графики можно компоновать в подграфики. Есть
функции-обёртки `plot_mesh`, `plot_field`, `plot_slice`, `plot_surface`,
принимающие `mesh` напрямую.

## Структура пакета

Код разбит на подпакеты по слоям; направление зависимостей —
от `core` к `viz` (без циклов).

```
cascadoc_new/
├── core/       # примитивы
│   ├── point.py       Point
│   ├── variable.py    Variable / AnalyticVariable / NumericVariable / DeferredVariable
│   └── utils.py       normalize_float, PRECISION
├── system/     # модель значений
│   ├── node.py        Node
│   ├── system.py      System (+ blocks, solve)
│   └── block.py       Block — единица композиции
├── mesh/       # геометрия
│   └── mesh.py        CharacteristicMesh
├── solvers/    # численные схемы
│   └── solver.py      Solver, TrapezoidalSolver
├── blocks/     # композиция: ДУЧП + граничные ОДУ + источники
│   ├── boundary.py    boundary_ode_step / boundary_plain_step
│   ├── hyp_block.py   HypBlock
│   ├── ode_block.py   ODEBlock
│   ├── plain_block.py PlainBoundaryBlock
│   ├── ode_source.py  ODESourceBlock
│   └── deferred_block.py  DeferredBoundaryBlock
├── problem/    # сборка задачи
│   └── setup.py       build_hyp_blocks
└── viz/        # визуализация
    └── plotter.py     Plotter + функции-обёртки
```

| Подпакет | Модули | Назначение |
|----------|--------|------------|
| `core` | `point.py`, `variable.py`, `utils.py` | базовые типы: точка, переменные, утилиты |
| `system` | `node.py`, `system.py`, `block.py` | реестр переменных, узлы-обёртки и блоки композиции |
| `mesh` | `mesh.py` | характеристическая сетка |
| `solvers` | `solver.py` | базовая схема `Solver` и `TrapezoidalSolver` |
| `blocks` | `boundary.py`, `hyp_block.py`, `ode_block.py`, `plain_block.py`, `ode_source.py`, `deferred_block.py` | композиция ДУЧП + граничных ОДУ + источники |
| `problem` | `setup.py` | сборка задачи (`build_hyp_blocks`) |
| `viz` | `plotter.py` | визуализация: сетка, поля, разрезы, 3D |

Публичный API остаётся плоским: классы и функции доступны прямо из
`cascadoc_new` (например, `from cascadoc_new import Point, build_hyp_blocks`).

## Для Rust

`NumericVariable._data` — плоский Dict. Для Rust потребуется:
- `Vec<(f64, f64, Array1<f64>)>` или `HashMap<(i64,i64), Array1<f64>>`
- `AnalyticVariable` → трейт с методом `at(&self, point: Point) -> Array1<f64>`

Контракт интерфейса не меняется.