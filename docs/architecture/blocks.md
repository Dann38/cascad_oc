# Блоки (`blocks`)

`blocks/` собирает гиперболическую задачу как **композицию блоков**:
каждый блок решает свою часть узлов и пишет результат в общие
`NumericVariable`. Границы описываются отдельными блоками — поэтому
`HypBlock` не знает, чем именно задана граница, а лишь считает внутренность.

Композиция собирается `System.add_block` и запускается `System.solve()`
(см. [`system`](system.md#solve)).

---

## Карта блоков

| Блок | Роль | Читает | Пишет |
|------|------|--------|-------|
| `HypBlock` | внутренность `S0 < s < S1`, начальный и выходной слои | коэффициенты `B`, `F`; `x0`, `y0`; соседние узлы `X` | `X` (внутренние узлы, `t=T0`, `t=T1`) |
| `ODEBlock` | граница `s = const` как ОДУ с `G` | `B`, `F`, `G`; соседний узел `X` | `X` (граничные узлы) |
| `PlainBoundaryBlock` | граница, заданная напрямую `value_fn(t)` | `B`, `F`; соседний узел `X` | `X` (граничные узлы) |
| `ODESourceBlock` | блок-источник: `dz/dt = f(z,t)` | — | `source_var` (численная) |
| `DeferredBoundaryBlock` | граница, читающая отложенную переменную | `deferred_var`; `B`, `F`; соседний `X` | `X` (граничные узлы) |

---

## `HypBlock` — гиперболический ДУЧП-блок

**Файл:** `blocks/hyp_block.py`.

### Назначение

Решает только «свою» часть узлов: начальный слой `t = T0`, **внутренние**
узлы `S0 < s < S1` на каждом слое и выходной слой `t = T1`. Граничные узлы
`s = S0`/`s = S1` ведут соседние блоки, которые пишут в те же точки
хранилища. Поэтому `HypBlock` **не содержит коэффициентов `G`** и не
различает способ задания границы.

### Публичный интерфейс

```python
hyp = HypBlock('hyp', sys, mesh)
hyp.solver                 # TrapezoidalSolver(system)
hyp.layer_times()          # {T0, T1} ∪ {t внутренних узлов}
hyp.solve_layer(t)         # при t==T0 решает начальный слой; решает внутренность
hyp.finalize(t_last)       # solver.solve_final(mesh) — сборка выходной границы
```

- Внутри `solve_layer` граничные узлы (`s == S0`/`s == S1`) **пропускаются**.
- `finalize` вызывается после всех слоёв: выходная граница нужна с уже
  посчитанными соседями.

### Связи

Читает `x0/y0`, `B`, `F` и `X` соседних узлов; пишет `X`. Не зависит от
конкретного граничного блока.

---

## `ODEBlock` — граница как ОДУ

**Файл:** `blocks/ode_block.py`.

### Назначение

Ведёт границу `s = S0` (`side='left'`) или `s = S1` (`side='right'`),
заданную ОДУ с коэффициентами `G`, **сцепленным** с приходящей
характеристикой из `HypBlock`.

### Публичный интерфейс

```python
blk = ODEBlock('ode_left', sys, mesh, side='left')   # side ∈ {'left','right'}
blk.s_const                # S0 или S1
blk.layer_times()          # времена граничных узлов
blk.solve_layer(t)
```

- `side='left'`: значение компоненты `x` берётся по характеристике справа,
  компонента `y` решается шагом `boundary_ode_step`.
- `side='right'`: симметрично — `y` по характеристике, `x` через ОДУ.

### Связи

Читает `B`, `F`, `G`, соседние узлы `X`; пишет `X` граничных узлов.
Связан с `HypBlock` через общие точки (не через объект-связку).

---

## `PlainBoundaryBlock` — граница, заданная напрямую

**Файл:** `blocks/plain_block.py`.

### Назначение

Самый простой вид границы: недостающая компонента известна как функция
времени `value_fn(t)`, вторая досчитывается по приходящей характеристике.

### Публичный интерфейс

```python
blk = PlainBoundaryBlock('plain_left', sys, mesh, side='left', value_fn=bc_left)
blk.s_const; blk.value_fn
blk.layer_times(); blk.solve_layer(t)
```

- `side='left'`: известна компонента `y = value_fn(t)`, `x` — по характеристике.
- `side='right'`: известна компонента `x = value_fn(t)`, `y` — по характеристике.
- Внутри вызывает `boundary_plain_step` с `float(self.value_fn(node.point[1]))`.

### Связи

Позже такой блок заменяется на `ODEBlock` с той же ролью — отсюда единая
композиция.

---

## `ODESourceBlock` — блок-источник для отложенных переменных

**Файл:** `blocks/ode_source.py`.

### Назначение

Решает ОДУ `dz/dt = ode_fn(z, t)` на граничных узлах и пишет результат в
`source_var`. Производит значение для `DeferredVariable`.

### Публичный интерфейс

```python
blk = ODESourceBlock('z_source', sys, mesh,
                     source_var='Z_num', ode_fn=f, init_val=z0, side='right')
blk.provides               # == source_var
blk.layer_times()
blk.solve_layer(t)
```

- На первом слое пишет `init_val`.
- Далее — шаг трапеций `z_new = z_prev + 0.5·dt·(f_prev + f_new)` с
  внутренней итерацией (до 20 шагов, порог `1e-14`) по значению `z`.
- Пишет через `node[self.source_var] = z_new`.

### Связи и ограничения

- **Источник** ребра `отложенная → потребитель`. Потребитель —
  `DeferredBoundaryBlock` с `depends_on=[имя источника]`.
- ОДУ **автономно**: `ode_fn(z, t)` **не видит** состояние ДУЧП на том же слое;
  начальное `z(T0)` — константа, не значение решения. Из-за этого связь
  «источник ↔ решение» невозможна (см. [ограничения](../architecture.md#known-limitations)).

---

## `DeferredBoundaryBlock` — граница из отложенной переменной

**Файл:** `blocks/deferred_block.py`.

### Назначение

Граничный блок, читающий недостающую компоненту не из формулы, а из
`DeferredVariable`, которую заполнил блок-источник в ходе решения.

### Публичный интерфейс

```python
blk = DeferredBoundaryBlock('deferred_right', sys, mesh,
                            side='right', deferred_var='Z',
                            source_block='z_source')
blk.s_const; blk.deferred_var
blk.layer_times(); blk.solve_layer(t)
```

- На слое читает `val = node[self.deferred_var]`, затем считает граничное
  значение через `boundary_plain_step`.
- `source_block` (если задан) заполняет `depends_on`, обеспечивая порядок
  «источник → потребитель».

### Связи и ограничения

- Жёсткая роль компоненты: `side='left'` → отложенная переменная задаёт `y`,
  `side='right'` → задаёт `x`. Произвольную компоненту через API не выбрать
  (см. [ограничения](../architecture.md#known-limitations)).
- `DeferredVariable.at` при отсутствии значения **бросает `RuntimeError`** —
  слой обязан быть готов.

---

## Переиспользуемые шаги границы (`boundary.py`)

**Файл:** `blocks/boundary.py`.

Оба шага решают одну задачу — «досчитать узел на границе, зная приходящую
характеристику» — но граничное условие задаётся по-разному. Схема — трапеции
(Crank–Nicolson).

```python
boundary_ode_step(system, point,
                  prev_point, prev_state,      # тот же граничный узел с прошлого слоя (шаг ОДУ)
                  char_point, char_state,      # приходящая характеристика (шаг ДУЧП)
                  side) -> np.ndarray          # state

boundary_plain_step(system, point,
                    char_point, char_state,
                    value, side) -> np.ndarray
```

### Роли компонент

| Шаг | `side='left'` (`s=S0`) | `side='right'` (`s=S1`) |
|-----|------------------------|-------------------------|
| `boundary_ode_step` | ОДУ задаёт компоненту 1 (`y`) через `G21, G22`; компонента 0 (`x`) приходит по характеристике | ОДУ задаёт компоненту 0 (`x`) через `G11, G12`; компонента 1 (`y`) по характеристике |
| `boundary_plain_step` | известно `y = value`; `x` по характеристике | известно `x = value`; `y` по характеристике |

Коэффициенты читаются общим хелпером `_coef(system, name, point)`.
Обе функции **бросают `ValueError`** при неизвестном `side`.

### Связи

Вызываются блоками `ODEBlock`, `PlainBoundaryBlock`,
`DeferredBoundaryBlock`. Это шаг «в сыром виде»; для монолитного пути ту же
роль играют `left_solve`/`right_solve` в `TrapezoidalSolver`.

---

## Ссылки

- Назад: [`mesh-and-solvers`](mesh-and-solvers.md).
- Далее: [`problem-and-viz`](problem-and-viz.md).
- Поток зависимостей и циклы: [обзор](../architecture.md#known-limitations).
