# Сетка и решатели (`mesh`, `solvers`)

Модули: `mesh/mesh.py`, `solvers/solver.py`.

---

## `CharacteristicMesh` — характеристическая сетка

**Файл:** `mesh/mesh.py`.

### Назначение

Строит узлы `(i, j) → Node(Point(s, t))` вдоль характеристик
`ds/dt = +C1` и `ds/dt = -C2` для гиперболической системы. Отвечает **только
за геометрию и топологию** — решения не хранит (значения живут в `System`).

### Классы узлов

| Группа | Смысл |
|--------|-------|
| `center` | узлы области `S0 ≤ s ≤ S1`, `T0 ≤ t ≤ T1` |
| `start_l` | входная граница `t = T0` (семейство `L`) |
| `start_r` | входная граница `t = T0` (семейство `R`) |
| `final_l` | выходная граница `t = T1` (семейство `L`) |
| `final_r` | выходная граница `t = T1` (семейство `R`) |

Для каждой группы хранятся: словарь `group[(i, j)] -> Node`, список
`order_group` (индексы в порядке добавления, отсортированы по `t`) и
`nodes_group` (список узлов).

### Публичный интерфейс

```python
mesh = CharacteristicMesh(sys, m=5)      # либо h=<шаг по t>

# геометрия (берётся из System как единого источника правды)
mesh.S0, mesh.S1, mesh.T0, mesh.T1, mesh.C1, mesh.C2
mesh.dS, mesh.dT, mesh.d1T, mesh.d2T     # шаги

# доступ к узлам
mesh.get_center_node(i, j)
mesh.get_center_node_left(i, j)          # сосед по характеристике L (или граничный)
mesh.get_center_node_right(i, j)         # сосед по характеристике R
mesh.is_from_center(i, j)                # внутри области?

# «конъюгатные» (обратный ход) соседи
mesh.get_center_node_conj_left / conj_right(i, j)  # и др.

# интерполяция выхода характеристики на отрезок
mesh.get_stxy_c_3node(p1, st1, p2, st2, p3, c)     # → (Point, state)

# границы
mesh.get_border(type_border='start'|'final'|'left'|'right', sort_s, sort_t)
```

- Дискретизация задаётся **либо** `m` (число точек), **либо** `h` (шаг по `t`);
  иначе `ValueError`.
- Геопараметры `C1, C2, S0, S1, T0, T1` читаются из `System`
  (`_const` берёт значение в `Point(0, 0)`).
- `get_stxy_c_3node` линейно интерполирует состояние выход характеристики с
  наклоном `c` на отрезок между `p1` и `p2`; используется решателем при сборке
  границы.
- Сетка **не хранит решения** — только узлы-точки.
- Визуализация из сетки вынесена: `mesh` больше не импортирует `matplotlib`.

### Связи

Создаётся поверх `System`; её узлы — те же `Point`, что и в хранилище
`NumericVariable`. Читается блоками и `TrapezoidalSolver`.

---

## `Solver` — базовый интерфейс решателя

**Файл:** `solvers/solver.py`.

```python
class Solver(ABC):
    scheme: str = "base"
    def __init__(self, system: System): ...
    @abstractmethod
    def solve_forward(self, mesh) -> None: ...   # прямой ход: X
    @abstractmethod
    def solve_adjoint(self, mesh) -> None: ...   # сопряжённый: PSI (и p)
```

Имя конкретного наследника = название схемы дискретизации. Прямой ход
считается от `T0` к `T1`, сопряжённый — обратно.

---

## `TrapezoidalSolver` — схема трапеций (Crank–Nicolson)

### Назначение

Монолитный решатель гиперболической системы на характеристической сетке:
коэффициенты (`B, F, G, C`) читает из аналитических переменных, состояние
`X`, сопряжённое `PSI` и прокси `p` пишет в численные переменные.

### Публичный интерфейс

```python
solver = TrapezoidalSolver(sys)

solver.solve_forward(mesh)   # = solve_initial + solve_center + solve_final
solver.solve_adjoint(mesh)   # = solve_initial_adjoint + ..._center_ + ..._final_
```

Прямой ход:

| Метод | Что делает |
|-------|------------|
| `solve_initial` | начальный слой `t = T0`: `X = [x0, y0]` |
| `solve_center` | внутренние и граничные узлы `center` (left/center/right схема) |
| `solve_final` | выходной слой `t = T1` |

Сопряжённый ход:

| Метод | Что делает |
|-------|------------|
| `solve_initial_adjoint` | терминальные `PSI = [phi_dx, phi_dy]`; `p = 0` на границах |
| `solve_center_adjoint` | узлы `center` в обратном порядке |
| `solve_final_adjoint` | входные границы `start_l`/`start_r`; `p` постоянно вдоль граничной характеристики |

Шаги схемы: `center_solve`, `left_solve`, `right_solve`,
`center_conj_solve`, `left_conj_solve`, `right_conj_solve` — собирают
матрицу 2×2 и решают `np.linalg.solve`.

### Связи

Читает аналитические коэффициенты через `_coef(name, point)`; пишет
`X`/`PSI`/`p` через узлы. Используется `HypBlock`
(`HypBlock.solver = TrapezoidalSolver(system)`) и функцией `build_hyp_system`.

> `TrapezoidalSolver` — **монолитный** путь (`build_hyp_system`). Блочный путь
> (`build_hyp_blocks`) использует те же шаги схемы, но через `HypBlock`
> и граничные блоки. Оба должны давать совпадающий результат.

---

## Ссылки

- Назад: [`system`](system.md).
- Далее: [`blocks`](blocks.md).
- Сборка: [`problem-and-viz`](problem-and-viz.md).
