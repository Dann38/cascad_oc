"""
Гиперболический блок для решения систем гиперболических уравнений.
Использует характеристическую сетку и метод характеристик.
"""
from typing import Dict, Any, Callable, Tuple, Optional
import numpy as np
from cascadoc.blocks.distributed_blocks.base_distributed_block import BaseDistributedBlock
from cascadoc.blocks.distributed_blocks.dtype.characteristic_mesh import CharacteristicMesh

class HyperbolicBlock(BaseDistributedBlock):
    """Блок для решения гиперболических систем уравнений"""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name)
        self.config = config
        self.c1 = config['C'][0]
        self.c2 = config['C'][1]
        self._setup_coefficient_functions(config)
    
    def _setup_coefficient_functions(self, config: Dict[str, Any]):
        """Настройка функций коэффициентов системы"""
        # Коэффициенты B матрицы
        self.B11 = config.get('B11', lambda s, t: 0.0)
        self.B12 = config.get('B12', lambda s, t: 0.0) 
        self.B21 = config.get('B21', lambda s, t: 0.0)
        self.B22 = config.get('B22', lambda s, t: 0.0)
        
        # Правые части
        self.F1 = config.get('F1', lambda s, t: 0.0)
        self.F2 = config.get('F2', lambda s, t: 0.0)
        
        # Граничные условия
        self.left_boundary = config.get('left_boundary', None)
        self.right_boundary = config.get('right_boundary', None)
        
        # Начальные условия
        self.initial_x = config.get('initial_x', lambda s: 0.0)
        self.initial_y = config.get('initial_y', lambda s: 0.0)
    
    def build_mesh(self) -> None:
        """Построение характеристической сетки"""
        self.mesh = CharacteristicMesh(self.config)
    
    def _initialize_solution(self) -> None:
        """Инициализация решения на сетке с двумя переменными"""
        if self.mesh and (self.initial_x or self.initial_y):
            self.solution = {}
            # Заполняем начальными условиями
            for (i, j), node in self.mesh.nodes.items():
                s, t_val = node
                # Для узлов на начальном временном слое
                if abs(t_val - self.mesh.frame.T0) < 1e-10:
                    x_val = self.initial_x(s) if callable(self.initial_x) else 0.0
                    y_val = self.initial_y(s) if callable(self.initial_y) else 0.0
                    self.solution[(i, j)] = (x_val, y_val)
                else:
                    # Для остальных узлов инициализируем нулями
                    self.solution[(i, j)] = (0.0, 0.0)
    
    def _apply_boundary_conditions(self, t: float) -> None:
        """Применение граничных условий"""
        if not self.solution:
            return
            
        # Применяем левое граничное условие
        if self.left_boundary and callable(self.left_boundary):
            for (i, j), node in self.mesh.nodes.items():
                s, t_node = node
                if abs(s - self.mesh.frame.S0) < 1e-10 and abs(t_node - t) < 1e-10:
                    # На левой границе: y определяется граничным условием
                    current_x, current_y = self.solution.get((i, j), (0.0, 0.0))
                    new_y = self.left_boundary(t)
                    self.solution[(i, j)] = (current_x, new_y)
        
        # Применяем правое граничное условие  
        if self.right_boundary and callable(self.right_boundary):
            for (i, j), node in self.mesh.nodes.items():
                s, t_node = node
                if abs(s - self.mesh.frame.S1) < 1e-10 and abs(t_node - t) < 1e-10:
                    # На правой границе: x определяется граничным условием
                    current_x, current_y = self.solution.get((i, j), (0.0, 0.0))
                    new_x = self.right_boundary(t)
                    self.solution[(i, j)] = (new_x, current_y)
    
    def _solve_step(self, t: float, dt: float) -> Dict[Tuple[int, int], Tuple[float, float]]:
        """Решение на одном шаге по времени"""
        new_solution = {}
        
        # Проходим по всем узлам сетки в порядке возрастания времени
        sorted_nodes = sorted(self.mesh.nodes.items(), 
                            key=lambda item: item[1][1])  # сортируем по времени
        
        for (i, j), node in sorted_nodes:
            s, t_node = node
            
            # Пропускаем узлы, которые уже были обработаны или время которых > t
            if t_node > t + dt or (i, j) in new_solution:
                continue
                
            new_solution[(i, j)] = self._solve_node(i, j, t_node)
        
        return new_solution
    
    def _solve_node(self, i: int, j: int, t: float) -> Tuple[float, float]:
        """Решение в конкретном узле сетки"""
        # Получаем предшествующие узлы
        preceding = self.mesh.get_preceding_nodes(i, j)
        
        # Проверяем, есть ли достаточное количество предшествующих узлов
        has_left = preceding['left'] is not None
        has_right = preceding['right'] is not None
        has_center = preceding['center'] is not None
        
        if has_left and has_right:
            return self._solve_center_node(i, j, t, preceding)
        else:
            # Для граничных узлов или узлов без достаточных данных
            return self._solve_boundary_node(i, j, t, preceding)
    
    def _solve_center_node(self, i: int, j: int, t: float, 
                          preceding: Dict[str, Any]) -> Tuple[float, float]:
        """Решение во внутреннем узле"""
        s, t_current = self.mesh.get_node(i, j)
        
        # Получаем значения из предшествующих узлов
        left_node = preceding['left']
        right_node = preceding['right']
        
        if not left_node or not right_node:
            return self.solution.get((i, j), (0.0, 0.0))
        
        # Координаты и значения в левом узле
        sl, tl = left_node
        left_index = self._find_node_index(sl, tl)
        xl, yl = self.solution.get(left_index, (0.0, 0.0)) if left_index else (0.0, 0.0)
        
        # Координаты и значения в правом узле  
        sr, tr = right_node
        right_index = self._find_node_index(sr, tr)
        xr, yr = self.solution.get(right_index, (0.0, 0.0)) if right_index else (0.0, 0.0)
        
        # Шаги по времени
        hl = t_current - tl
        hr = t_current - tr
        
        # Решаем систему уравнений для центрального узла
        return self._center_solve(s, t_current, sl, tl, xl, yl, hl, sr, tr, xr, yr, hr)
    
    def _solve_boundary_node(self, i: int, j: int, t: float,
                            preceding: Dict[str, Any]) -> Tuple[float, float]:
        """Решение в граничном узле"""
        s, t_current = self.mesh.get_node(i, j)
        
        # Для граничных узлов используем упрощенные методы
        if abs(s - self.mesh.frame.S0) < 1e-10:  # Левая граница
            return self._solve_left_boundary(i, j, t, preceding)
        elif abs(s - self.mesh.frame.S1) < 1e-10:  # Правая граница
            return self._solve_right_boundary(i, j, t, preceding)
        else:
            # Для узлов без достаточных данных используем интерполяцию
            return self._interpolate_node(i, j, t)
    
    def _solve_left_boundary(self, i: int, j: int, t: float,
                            preceding: Dict[str, Any]) -> Tuple[float, float]:
        """Решение на левой границе"""
        s, t_current = self.mesh.get_node(i, j)
        
        # На левой границе y задается граничным условием
        if self.left_boundary and callable(self.left_boundary):
            y_value = self.left_boundary(t_current)
        else:
            y_value = 0.0
            
        # x вычисляем из доступных данных
        x_value = 0.0
        if preceding['right']:
            sr, tr = preceding['right']
            right_index = self._find_node_index(sr, tr)
            if right_index:
                xr, yr = self.solution.get(right_index, (0.0, 0.0))
                # Простая экстраполяция для x
                x_value = xr
            
        return (x_value, y_value)
    
    def _solve_right_boundary(self, i: int, j: int, t: float,
                             preceding: Dict[str, Any]) -> Tuple[float, float]:
        """Решение на правой границе"""
        s, t_current = self.mesh.get_node(i, j)
        
        # На правой границе x задается граничным условием
        if self.right_boundary and callable(self.right_boundary):
            x_value = self.right_boundary(t_current)
        else:
            x_value = 0.0
            
        # y вычисляем из доступных данных  
        y_value = 0.0
        if preceding['left']:
            sl, tl = preceding['left']
            left_index = self._find_node_index(sl, tl)
            if left_index:
                xl, yl = self.solution.get(left_index, (0.0, 0.0))
                # Простая экстраполяция для y
                y_value = yl
            
        return (x_value, y_value)
    
    def _center_solve(self, s: float, t: float, sl: float, tl: float, 
                     xl: float, yl: float, hl: float, sr: float, tr: float,
                     xr: float, yr: float, hr: float) -> Tuple[float, float]:
        """Решение системы уравнений для центрального узла"""
        # Коэффициенты в текущей точке
        B11, B12 = self.B11(s, t), self.B12(s, t)
        B21, B22 = self.B21(s, t), self.B22(s, t)
        F1, F2 = self.F1(s, t), self.F2(s, t)
        
        # Коэффициенты в предшествующих точках
        B11_r, B12_r = self.B11(sr, tr), self.B12(sr, tr)
        B21_l, B22_l = self.B21(sl, tl), self.B22(sl, tl)
        F1_r, F2_l = self.F1(sr, tr), self.F2(sl, tl)
        
        # Матрица системы
        A = np.array([
            [1 - hr/2 * B11, -hr/2 * B12],
            [-hl/2 * B21, 1 - hl/2 * B22]
        ])
        
        # Вектор правой части
        b = np.array([
            xr + hr/2 * (B11_r * xr + B12_r * yr + F1 + F1_r),
            yl + hl/2 * (B21_l * xl + B22_l * yl + F2 + F2_l)
        ])
        
        try:
            solution = np.linalg.solve(A, b)
            return (float(solution[0]), float(solution[1]))
        except np.linalg.LinAlgError:
            # Если матрица вырождена, используем простую интерполяцию
            return ((xl + xr) / 2, (yl + yr) / 2)
    
    def _find_node_index(self, s: float, t: float) -> Optional[Tuple[int, int]]:
        """Нахождение индексов узла по координатам"""
        for (i, j), node in self.mesh.nodes.items():
            if abs(node[0] - s) < 1e-10 and abs(node[1] - t) < 1e-10:
                return (i, j)
        return None
    
    def _interpolate_node(self, i: int, j: int, t: float) -> Tuple[float, float]:
        """Интерполяция значения в узле"""
        # Простая интерполяция из соседних узлов
        x_sum, y_sum, count = 0.0, 0.0, 0
        
        for di in [-1, 0, 1]:
            for dj in [-1, 0, 1]:
                if di == 0 and dj == 0:
                    continue
                    
                neighbor_node = self.mesh.get_node(i + di, j + dj)
                if neighbor_node and (i + di, j + dj) in self.solution:
                    x_val, y_val = self.solution[(i + di, j + dj)]
                    x_sum += x_val
                    y_sum += y_val
                    count += 1
        
        if count > 0:
            return (x_sum / count, y_sum / count)
        else:
            return (0.0, 0.0)