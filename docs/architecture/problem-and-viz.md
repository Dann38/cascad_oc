# Сборка задачи и визуализация (`problem`, `viz`)

Модули: `problem/setup.py`, `viz/plotter.py`.

---

## `build_hyp_blocks` — сборка задачи композицией блоков

**Файл:** `problem/setup.py`.

### Назначение

Собрать гиперболическую задачу как **композицию блоков**: зарегистрировать
переменные, построить сетку, добавить `HypBlock` и граничные блоки.

### Публичный интерфейс

```python
sys, mesh, hyp = build_hyp_blocks(
    S=(0, 1), T=(0, 0.5), C=(1, 2),
    B=(B11, B12, B21, B22),          # каждый: f(s, t) -> float
    F=(F1, F2),
    G=((G11, G12), (G21, G22)),      # каждый: f(t) -> float
    x0=x0, y0=y0,                    # f(s) -> float
    phi_dx=phi_dx, phi_dy=phi_dy,    # f(s, x, y) -> float
    m=None, h=None,                  # m точек или шаг h по t
    boundaries='ode',                # 'ode' | 'plain'
    bc_left=None, bc_right=None,     # функции t, нужны при boundaries='plain'
)
sys.solve()                          # запуск послойно по t
```

- При `boundaries='ode'` добавляются `ODEBlock('ode_left')` и
  `ODEBlock('ode_right')`.
- При `boundaries='plain'` добавляются
  `PlainBoundaryBlock('plain_left'/'plain_right')`; обязательно нужны
  `bc_left` и `bc_right`, иначе `ValueError`.
- Неизвестный режим → `ValueError`.
- Возвращает `(System, CharacteristicMesh, HypBlock)`.

### Что регистрируется во `System`

Аналитические: `C1, C2, S0, S1, T0, T1`, `B11, B12, B21, B22`, `F1, F2`,
`G11, G12, G21, G22`, `x0, y0`.
Callable: `phi_dx`, `phi_dy`.
Численные: `X` (dim=2), `PSI` (dim=2), `p` (dim=1).

### Связи

Внутренний хелпер `_register_variables` используется и `build_hyp_blocks`,
и `build_hyp_system`.

---

## `build_hyp_system` — монолитный путь

```python
sys, mesh, solver = build_hyp_system(S, T, C, B, F, G, x0, y0,
                                     phi_dx, phi_dy, m=None, h=None)
solver.solve_forward(mesh)
solver.solve_adjoint(mesh)
```

Возвращает `(System, CharacteristicMesh, TrapezoidalSolver)` — **без блоков**.
Это старая монолитная схема; служит эталоном для сверки с блочной сборкой
(оба пути используют одинаковые шаги схемы трапеций).

---

## `Plotter` — визуализация

**Файл:** `viz/plotter.py`.

### Назначение

Отдельный подпакет: ни сетка, ни решатель не знают о `matplotlib`
(`mesh` больше не импортирует его). Вся отрисовка работает поверх готовых
`System` и `CharacteristicMesh`.

### Публичный интерфейс

```python
from cascadoc_new import Plotter
viz = Plotter(sys, mesh)

viz.plot_mesh()                                  # геометрия сетки
viz.plot_field('X', component=0)                 # псевдоцветное поле
viz.plot_slice([('X', 0), ('X', 1), x_an], t=mesh.T1, labels=[...])
viz.plot_surface('X', component=0)               # 3D-поверхность z = f(s, t)
```

Все методы принимают необязательный `ax` и **возвращают его же**, поэтому
графики легко компонуются в подграфики.

Функция для отрисовки задаётся одним из способов:

| Запись | Значение |
|--------|----------|
| `'X'` | имя переменной `System` (численной, аналитической или отложенной) |
| `('X', 1)` | компонента векторной переменной |
| `lambda point: ...` | `f(Point) -> float` |
| `lambda s, t: ...` | `f(s, t) -> float` |
| число | константа |

- Численные переменные рисуются **по узлам сетки** (фактические данные
  решения), аналитические/callable — по непрерывной линии (`samples` точек):
  удобно сравнивать решение с аналитическим эталоном.
- `plot_slice` требует ровно один из `s`/`t`; координата фиксируется на
  ближайшем уровне сетки.
- Внутри сопоставление координат с индексами только в визуализации:
  `_COORD_IDX = {'s': 0, 't': 1}` — это соглашение отрисовки, а не свойство
  `Point`.

### Функции-обёртки

```python
plot_mesh(mesh, **kw)
plot_field(mesh, expr, **kw)
plot_slice(mesh, exprs, **kw)
plot_surface(mesh, expr, **kw)
```

Принимают `mesh` напрямую и создают `Plotter` внутри.

### Связи

Читает `System` (переменные, `node()`) и `CharacteristicMesh` (узлы, `S/T`).
Ничего не пишет.

---

## Ссылки

- Назад: [`blocks`](blocks.md).
- Обзор: [архитектура](../architecture.md).
- Путеводитель [`guide.md`](../guide.md) — как собрать систему, блоки и связи.
- Пример [`../../example/cascadoc_new_guide.ipynb`](../../example/cascadoc_new_guide.ipynb) — рабочий пример.
