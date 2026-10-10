# CascadOC — новая архитектура

## Ключевая идея

Решение каскадных систем ДУЧП + ОДУ для задач оптимального управления.

В центре архитектуры — **точки** (`Point`) и **именованные переменные** (`Variable`),
определённые на точках (s,t) сетки. Переменная может быть аналитической
(вычисляется на лету) или численной (хранит значения).

## Точка `Point`

Точка хранит произвольное число координат и служит единым аргументом функции
вместо списка отдельных чисел. Точки **конкатенируются** оператором `|`:

```python
Point(0, 1) | Point(2, 3)      # → Point(0, 1, 2, 3)
Point(i, j) | Point(s, t)      # → Point(i, j, s, t)
Point(1) | Point(2) | Point(3) # → Point(1, 2, 3)
```

Для координат (s,t) доступны `point.s` и `point.t`.

## Основные типы

### `Variable` — именованная величина

```python
# Аналитическая: f(point) — не хранит данные, считает при каждом запросе
var = AnalyticVariable('B11', lambda point: -2 * point.s, dim=1)

# Численная: хранит np.ndarray(dim,) в каждой точке
var = NumericVariable('X', dim=2)
var.store(Point(s, t), np.array([x, y]))
val = var.at(Point(s, t))  # → np.ndarray(2,)
```

Аналитические — для коэффициентов (B, F, G, C, ...).  
Численные — для состояния и сопряжённых переменных (X, PSI, p).

### `Node` — точка с lazy-доступом к переменным

```python
n = sys.node(Point(s, t))

n['X']       # → np.ndarray(dim,)  — чтение/вычисление
n['B11']     # → float             — аналитика на лету
n['X'] = [x, y]  # запись (только numeric)
n['X'][0]    # → float — компонента
n.s, n.t     # координаты точки
n.is_computed('X')  # проверка
```

Node **не хранит данные** — только `Point` и ссылку на System. Чтение/запись идут
в реестр переменных System. Каждая точка `(s,t)` в системе ровно одна: совпадающие
по координате узлы роли — это один и тот же узел.

### `System` — реестр переменных

```python
sys = System()
sys.var_analytic('B11', lambda point: -2 * point.s, dim=1)  # коэффициент
sys.var_analytic('C1', 1)              # константа: число вместо функции
sys.var_const('C2', 2)                 # то же самое, сахар
sys.var_callable('phi_dx', fn)         # функция, зависящая от состояния
sys.var_numeric('X', dim=2)            # вектор состояния
sys.var_numeric('PSI', dim=2)          # сопряжённый вектор
sys.var_numeric('p', dim=1)            # adjoint proxy

n = sys.node(Point(s, t))              # узел с привязкой
```

Размерность переменной (dim) — число компонент. Для ДУЧП 2×2 dim=2, для ОДУ dim=1, для 3D систем — число уравнений.

## Сетка и решатель

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

### `TrapezoidalSolver` — схема трапеций (Crank–Nicolson)

Решатели называются по схеме дискретизации; базовый интерфейс — `Solver`
(`solve_forward` / `solve_adjoint`). Функции шага схемы принимают координаты
как `Point`:

```python
solver = TrapezoidalSolver(sys)
solver.solve_forward(mesh)   # считает X
solver.solve_adjoint(mesh)   # считает PSI и p (использует X)

# шаг схемы принимает точки, а не список чисел:
# center_solve(point, point_l, point_r, st_l, st_r)
```

## Порядок вычислений

Прямой ход (от T0 к T1) → сопряжённый ход (от T1 к T0).

```python
solver.solve_forward(mesh)   # X записан в sys.variables['X']
solver.solve_adjoint(mesh)   # PSI записан в sys.variables['PSI']
```

## Сборка задачи

```python
from cascadoc_new import build_hyp_system

sys, mesh, solver = build_hyp_system(
    S=(0, 1), T=(0, 0.5), C=(1, 2),
    B=(B11, B12, B21, B22), F=(F1, F2), G=((G11, G12), (G21, G22)),
    x0=x0, y0=y0, phi_dx=phi_dx, phi_dy=phi_dy,
    m=100,
)
solver.solve_forward(mesh)
solver.solve_adjoint(mesh)
```

Здесь `B, F` задаются как `f(s, t)`, `G` как `g(t)`, `x0/y0` как `f(s)`,
`phi_dx/phi_dy` как `f(s, x, y)`; внутри они оборачиваются в функции от `Point`.

## Композиция блоков: границы как ОДУ

Гиперболическая задача собирается как **композиция блоков** (`System.blocks`),
а не как один монолитный решатель. Блок — это единица системы, которая решает
свою часть узлов послойно по времени `t`:

* `HypBlock` — внутренность `S0 < s < S1`, начальный (`t = T0`) и выходной
  (`t = T1`) слои. Про границы `s = S0/S1` блок ничего не знает;
* `ODEBlock` — граница `s = const`, заданная **ОДУ** (коэффициенты `G`),
  сцепленным с приходящей характеристикой из `HypBlock`;
* `PlainBoundaryBlock` — та же роль границы, но значение задано **напрямую**
  функцией времени (промежуточный, самый простой случай).

Блоки не хранят значения: «интерфейс» между ними — общее хранилище
`NumericVariable`. Узел `Point(s, t)` один и тот же для `HypBlock` и
`ODEBlock`, поэтому обмен идёт без отдельных объектов-связок.

```python
from cascadoc_new import build_hyp_blocks

sys, mesh, hyp = build_hyp_blocks(
    S=(0, 1), T=(0, 0.5), C=(1, 2),
    B=(B11, B12, B21, B22), F=(F1, F2), G=((G11, G12), (G21, G22)),
    x0=x0, y0=y0, phi_dx=phi_dx, phi_dy=phi_dy,
    m=100,
    boundaries='ode',          # или 'plain' с bc_left/bc_right
)
sys.solve()                    # послойно по t: HypBlock + два ODEBlock
```

### Промежуточная логика границ (3 шага)

1. **Граница просто задана** — `PlainBoundaryBlock`: недостающая компонента
   известна как `value_fn(t)`, вторая досчитывается по характеристике
   (`boundary_plain_step`).
2. **Граница как ОДУ** — `ODEBlock`: компонента на границе живёт во времени
   (`dy/dt = G21·x + G22·y` слева, `dx/dt = G11·x + G12·y` справа) и
   алгебраически сцеплена с ДУЧП (`boundary_ode_step`).
3. **Одна переиспользуемая логика** — шаг граничного ОДУ вынесен в одну
   функцию `boundary_ode_step(system, point, prev, char, side)`; левая и правая
   границы — это один и тот же шаг с переставленными ролями компонент.

Порядок решения задаёт `System.solve()`: слои по возрастанию `t`, на каждом
слое блоки независимы (зависимости лежат на более ранних слоях). Сборка
выходной границы `t = T1` выполняется пост-шагом `Block.finalize` — после того,
как граничные блоки закончили слой `T1`.

`HypBlock` + `ODEBlock` дают результат, побитово совпадающий с
`TrapezoidalSolver`, но граничное ОДУ больше не «зашито» в решатель.

## Визуализация

Вся отрисовка вынесена в отдельный подпакет `cascadoc_new.viz` и не затрагивает
сетку/решатель: `cascadoc_new.mesh` больше не импортирует matplotlib.

```python
from cascadoc_new import Plotter

viz = Plotter(sys, mesh)

viz.plot_mesh()                        # геометрия сетки

# любая функция на (s, t): имя переменной, компонента, callable или число
viz.plot_field('X', component=0)       # псевдоцветное поле
viz.plot_field(lambda s, t: s * t)     # произвольная функция

# разрез при фиксированном s или t; сразу несколько функций на графике
viz.plot_slice([('X', 0), ('X', 1), x_an], t=mesh.T1,
               labels=['X[0]', 'X[1]', 'x_an'])
viz.plot_slice([('PSI', 0), ('PSI', 1)], s=mesh.S0)

viz.plot_surface('X', component=0)     # 3D поверхность z = f(s, t)
```

Функция задаётся одним из способов:

| Запись | Значение |
|--------|----------|
| `'X'` | имя переменной System (численной или аналитической) |
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
│   ├── variable.py    Variable / AnalyticVariable / NumericVariable
│   └── utils.py       normalize_float, PRECISION
├── system/     # модель значений
│   ├── node.py        Node
│   ├── system.py      System (+ blocks, solve)
│   └── block.py       Block — единица композиции
├── mesh/       # геометрия
│   └── mesh.py        CharacteristicMesh
├── solvers/    # численные схемы
│   └── solver.py      Solver, TrapezoidalSolver
├── blocks/     # композиция: ДУЧП + граничные ОДУ
│   ├── boundary.py    boundary_ode_step / boundary_plain_step
│   ├── hyp_block.py   HypBlock
│   ├── ode_block.py   ODEBlock
│   └── plain_block.py PlainBoundaryBlock
├── problem/    # сборка задачи
│   └── setup.py       build_hyp_system, build_hyp_blocks
└── viz/        # визуализация
    └── plotter.py     Plotter + функции-обёртки
```

| Подпакет | Модули | Назначение |
|----------|--------|------------|
| `core` | `point.py`, `variable.py`, `utils.py` | базовые типы: точка, переменные, утилиты |
| `system` | `node.py`, `system.py`, `block.py` | реестр переменных, узлы-обёртки и блоки композиции |
| `mesh` | `mesh.py` | характеристическая сетка |
| `solvers` | `solver.py` | базовая схема `Solver` и `TrapezoidalSolver` |
| `blocks` | `boundary.py`, `hyp_block.py`, `ode_block.py`, `plain_block.py` | композиция ДУЧП + граничных ОДУ |
| `problem` | `setup.py` | сборка задачи (`build_hyp_system`, `build_hyp_blocks`) |
| `viz` | `plotter.py` | визуализация: сетка, поля, разрезы, 3D |

Публичный API остаётся плоским: классы и функции доступны прямо из
`cascadoc_new` (например, `from cascadoc_new import Point, build_hyp_system`).

## Для Rust

`NumericVariable._data` — плоский Dict. Для Rust потребуется:
- `Vec<(f64, f64, Array1<f64>)>` или `HashMap<(i64,i64), Array1<f64>>`
- `AnalyticVariable` → трейт с методом `at(&self, point: Point) -> Array1<f64>`

Контракт интерфейса не меняется.
