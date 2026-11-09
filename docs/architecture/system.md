# Система и композиция (`system`)

Модули: `system/node.py`, `system/system.py`, `system/block.py`.
Здесь живёт **реестр переменных** (`System`), **узел-обёртка** (`Node`) и
**единица композиции** (`Block`).

---

## `Node` — точка с доступом к переменным

**Файл:** `system/node.py`.

### Назначение

Тонкая обёртка над `Point`, дающая доступ к переменным системы по имени.
Узел **не хранит данные** — только `Point` и ссылку на `System`;
чтение/запись идут в реестр переменных.

### Публичный интерфейс

```python
node = sys.node(Point(s, t))    # предпочтительный способ

node['X']            # чтение: np.ndarray(dim,) для вектора, float для dim=1
node['B11']          # аналитика считается на лету
node['X'] = [x, y]   # запись (только в численную переменную)
'X' in node          # есть ли переменная в системе
node.is_computed('X')# True, если значение есть в хранилище (или аналитика)
node.point           # сам Point
```

- Конструктор: `Node(point: Point, system: Optional[System] = None)`.
  **Двойной логики нет**: аргумент — всегда `Point` (старый вариант
  `Node(s, t)` удалён, см. `замечания.md`).
- `__getitem__`: берёт переменную по имени; для `dim=1` и одномерного
  массива возвращает скаляр `val[0]`; для отсутствующего значения — `None`.
- `__setitem__`: запрещает запись в `AnalyticVariable` (`TypeError`),
  иначе `store`.
- Свойств `s`/`t` у `Node` **нет** (см. `замечания.md`) — доступ к
  координатам через `node.point[i]`.

### Связи

Читает/пишет переменные `System`; используется всеми блоками и решателем.
Свойство «каждая точка ровно одна» — общее для системы (в хранилище
`NumericVariable` ключ — координаты), а не свойство конкретной геометрии.

---

## `System` — реестр переменных и композиция блоков

**Файл:** `system/system.py`.

### Назначение

Единое хранилище переменных + список блоков + порядок их решения.

### Публичный интерфейс — переменные

```python
sys = System()

# аналитические (коэффициенты, константы, начальные данные)
sys.var_analytic('B11', lambda point: -2 * point[0], dim=1)
sys.var_const('C1', 1)                      # сахар для константы

# функция, зависящая от состояния (не только от точки)
sys.var_callable('phi_dx', fn)              # fn(point, x, y)
sys.get_callable('phi_dx')

# численные (состояние / сопряжённое / прокси)
sys.var_numeric('X', dim=2)
sys.var_numeric('PSI', dim=2)
sys.var_numeric('p', dim=1)

# отложенные (ссылка на численную переменную-источник)
sys.var_deferred('Z', source='Z_num', dim=1)

sys.variables        # Dict[str, Variable] — основной реестр
sys.functions        # Dict[str, Callable] — callable-функции (phi_*)
sys.blocks           # List[Block]

sys.get_var('X'); sys.dim('X'); sys.list_variables()
sys.list_analytic(); sys.list_numeric()
```

- `var_analytic`/`var_numeric`/`var_deferred` **падают** `ValueError`,
  если имя уже занято.
- `var_deferred` сразу вызывает `variable.bind(sys)`.
- `var_callable` — для функций, зависящих от состояния (терминальные
  условия `phi_dx(point, x, y)`); они хранятся в `functions`, не в `variables`.

### Публичный интерфейс — композиция и решение

```python
sys.add_block(block)     # регистрирует блок (проставляет block.system)
sys.solve()              # решает послойно по t

sys.node(point)          # создать Node
```

### `solve()` {#solve}

```python
def solve(self):
    times = sorted({t for block in self.blocks for t in block.layer_times()})
    sorted_blocks = self._sort_blocks()
    for t in times:
        for block in sorted_blocks:
            if block.has_layer(t):
                block.solve_layer(t)
    for block in self.blocks:
        block.finalize(times[-1])
```

- Слои `t` собираются из всех блоков и обрабатываются по возрастанию.
- На каждом слое блоки идут в порядке `_sort_blocks()`.
- После всех слоёв — однократный `finalize` (нужен `HypBlock` для выходной
  границы `t = T1`).
- Это **один последовательный проход**, без итераций/совместного решения.

### `_sort_blocks()` — топологическая сортировка (Кана)

- Рёбра строятся по `Block.depends_on`: если `A` зависит от `B`, то `B`
  выполняется раньше `A`.
- Блоки без зависимостей сохраняют порядок добавления.
- **Цикл не детектируется**: блоки из цикла не получают `in_degree == 0`,
  поэтому добавляются хвостом `result + remaining` в порядке `add_block`.
  Ошибки нет — порядок молча неверный. Это ключевое ограничение
  (см. [ограничения](../architecture.md#known-limitations)).

### Связи

`System` — центральный узел: `Node` делегирует ему доступ; блоки пишут/читают
через общее хранилище `NumericVariable`; `CharacteristicMesh` и решатели
берут из него геометрию и коэффициенты.

---

## `Block` — единица композиции

**Файл:** `system/block.py`.

### Назначение

Абстрактный базовый класс: блок отвечает за свою часть узлов и умеет решать
их на слое `t`. Блоки **не хранят значения** — «интерфейс» между ними это
совпадающие точки `Point` в общих `NumericVariable`.

### Публичный интерфейс

```python
class Block(ABC):
    def __init__(self, name: str, system: System): ...

    @property
    def depends_on(self) -> List[str]: ...     # имена блоков-предшественников
    @depends_on.setter
    def depends_on(self, deps): ...

    @property
    def provides(self) -> str: ...             # имя производимой переменной ('')

    @abstractmethod
    def layer_times(self) -> List[float]: ...  # времена слоёв блока
    @abstractmethod
    def solve_layer(self, t: float) -> None: ...# решить свои узлы на слое t

    def has_layer(self, t) -> bool: ...        # есть ли у блока слой t
    def finalize(self, t_last: float) -> None: ...  # пост-шаг (по умолчанию пуст)
```

- `depends_on` — **ручной** список имён блоков (не выводится из переменных).
- `provides` объявлен для блоков-источников (`ODESourceBlock`), но
  **сортировкой не используется**.
- `finalize` — однократный пост-проход после всех слоёв.

### Связи

Каждый конкретный блок (см. [`blocks`](blocks.md)) наследует `Block`,
получает `System` и `CharacteristicMesh` и пишет результаты в `NumericVariable`
через узлы. `System._sort_blocks`/`solve` вызывают их методы.

---

## Ссылки

- Назад: [`core`](core.md).
- Далее: [`mesh-and-solvers`](mesh-and-solvers.md).
- Механизм отложенных значений и циклы: [обзор → «Известные ограничения»](../architecture.md#known-limitations).
