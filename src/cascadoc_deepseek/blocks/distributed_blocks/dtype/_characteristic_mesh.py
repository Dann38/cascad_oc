import math
import matplotlib.pyplot as plt
from dataclasses import dataclass
from typing import Tuple, Optional, Dict, List
from .base_mesh import BaseMesh
import numpy as np

@dataclass
class Rectangle:
    """Область-рамка: прямоугольник в координатах (S, T)"""
    S0: float
    S1: float  
    T0: float
    T1: float

    @property
    def center(self) -> Tuple[float, float]:
        """Центр рамки"""
        return (self.S0 + self.S1) / 2, (self.T0 + self.T1) / 2
class Characteristic:
    """Характеристика (прямая линия) с вычислением пересечений с границами"""
    
    def __init__(self, center: Tuple[float, float], dt: float, step: float, 
                 # num_points: int, 
                 frame: Rectangle):
        self.center = center
        self.dt = dt
        self.step = step
        # self.num_points = num_points
        self.frame = frame
        
        # Основные узлы внутри рамки
        self.internal_nodes = dict()
        
        # Крайние узлы пересечения с границами
        self.left_bound_node = None
        self.right_bound_node = None
        
        self._build_characteristic()
    
    def _build_characteristic(self):
        """Построение характеристики с вычислением пересечений с границами"""
        s0, t0 = self.center
        
        # Вычисляем точки пересечения со всеми границами
        intersections = self._find_boundary_intersections(s0, t0)
        
        if not intersections:
            return
        
        # Находим самую левую и самую правую точки пересечения
        intersections.sort(key=lambda p: p[0])  # сортируем по S
        self.left_bound_node = intersections[0]
        self.right_bound_node = intersections[-1]

        
        # Генерируем внутренние узлы между крайними точками
        self._generate_internal_nodes(s0, t0)
    
    def _find_boundary_intersections(self, s0: float, t0: float) -> List[Tuple[float, float]]:
        """Находит все точки пересечения характеристики с границами рамки"""
        intersections = []
        
        # Проверяем пересечение с каждой из 4 границ # Замена
        t_left = self._intersection(self.frame.S0, s0, t0, self.step, self.dt, self.frame.T0, self.frame.T1)
        t_right = self._intersection(self.frame.S1, s0, t0, self.step, self.dt, self.frame.T0, self.frame.T1)
        s_bottom = self._intersection(self.frame.T0, t0, s0, self.dt, self.step, self.frame.S0, self.frame.S1)
        s_top = self._intersection(self.frame.T1, t0, s0, self.dt, self.step, self.frame.S0, self.frame.S1)
        if t_left:
            intersections.append((self.frame.S0, t_left))
        if t_right:
            intersections.append((self.frame.S1, t_right))
        if s_bottom:
            intersections.append((s_bottom, self.frame.T0))
        if s_top:
            intersections.append((s_top, self.frame.T1))
        return intersections
        
    def _intersection(self, x, x0, y0, dx, dy, yl, yr):
        if abs(dx) < 1e-10:
            return None
        count_step = (x-x0)/dx
        y = y0 + count_step*dy
        return y if yl <= y and y <= yr else None

    
    def _generate_internal_nodes(self, s0: float, t0: float):
        """Генерирует внутренние узлы характеристики между крайними точками"""
        if not self.left_bound_node or not self.right_bound_node:
            return
        
        # Определяем направление от левой к правой границе
        left_s, left_t = self.left_bound_node
        right_s, right_t = self.right_bound_node
        
        # Вычисляем параметр k для левой и правой границ
        if abs(self.step) > 1e-10:
            k_left = (left_s - s0) / self.step
            k_right = (right_s - s0) / self.step
        else:
            k_left = (left_t - t0) / self.dt
            k_right = (right_t - t0) / self.dt
        count = int(max(abs(k_left), abs(k_right)))
        
        for k in range(-count, count + 1):
            s = s0 + k * self.step
            t = t0 + k * self.dt
            
            # Дополнительная проверка, что узел внутри рамки
            if (self.frame.S0 <= s and s <= self.frame.S1 and 
                self.frame.T0 <= t and t <= self.frame.T1):
                self.internal_nodes[k] = (s, t)
    
    def __call__(self, index: int) -> Optional[Tuple[float, float]]:
        """Возвращает узел по индексу (только внутренние узлы)"""
        if index in self.internal_nodes:
            return self.internal_nodes[index]
        return None
    
    def __len__(self):
        return len(self.internal_nodes)
    
    def get_boundary_nodes(self) -> Tuple[Optional[Tuple[float, float]], 
                                         Optional[Tuple[float, float]]]:
        """Возвращает крайние узлы на границах"""
        return self.left_bound_node, self.right_bound_node

    def plot(self, color, node_size):
        l, r = self.left_bound_node, self.right_bound_node
        if l and r:
            # Рисуем линию между крайними узлами
            plt.plot([l[0], r[0]], [l[1], r[1]], 
                   f'{color}-', alpha=0.6, linewidth=0.8)
        
        # Рисуем внутренние узлы отрицательных характеристик
        for _, node in self.internal_nodes.items():
            plt.scatter(node[0], node[1], c='blue', s=node_size//2, alpha=0.5)

class CharacteristicMesh(BaseMesh):
    """Сетка характеристик с улучшенной обработкой границ"""
    
    def __init__(self, config):
        S0, S1 = np.float64(config['S'][0]), np.float64(config['S'][1])
        T0, T1 = np.float64(config['T'][0]), np.float64(config['T'][1])
        C1, C2 = np.float64(config['C'][0]), np.float64(config['C'][1])

        frame = Rectangle(S0=S0, S1=S1, T0=T0, T1=T1)
        
        self.center = frame.center
        if 'm' in config:
            M = config['m']*2
            ds = (S1-S0)/M
            dt1 = ds/C1 
            dt2 = ds/C2
        elif 'h' in config: # Для запаздывания
            dt = config['h']
            ds = dt*C1*C2/(C1+C2)
            dt1 = ds/C1 
            dt2 = ds/C2

        self.ds = ds
        self.dt1 = dt1  # для отрицательных характеристик
        self.dt2 = dt2  # для положительных характеристик  
        self.frame = frame
        
        RS = (self.frame.S1-self.frame.S0)/2
        RT = (self.frame.T1-self.frame.T0)/2

        i_r = math.ceil(max(RS/ds, RT/dt1))
        j_r = math.ceil(max(RS/ds, RT/dt2))
        self.i_min, self.i_max = -i_r, i_r
        self.j_min, self.j_max = -j_r, j_r
        
        # Хранилище узлов
        self.nodes: Dict[Tuple[int, int], Tuple[float, float]] = {}
        
        # Списки характеристик
        self.positive_chars = dict()  # положительные характеристики (красные)
        self.negative_chars = dict()  # отрицательные характеристики (синие)
        
        self._build_grid()
    
    def _build_grid(self):
        # """Построение сетки узлов и характеристик"""
        # s0, t0 = self.center
        
        # # Строим все узлы сетки
        # for i in range(self.i_min, self.i_max + 1):
        #     for j in range(self.j_min, self.j_max + 1):
        #         s = s0 + (i + j) * self.ds
        #         t = t0 - i * self.dt1 + j * self.dt2
                
        #         # Проверяем попадание в рамку
        #         if (self.frame.S0 <= s and s <= self.frame.S1 and 
        #             self.frame.T0 <= t and t <= self.frame.T1):
        #             self.nodes[(i, j)] = (s, t)
        
        # Строим характеристики
        self._build_characteristics()
        
        # # Формируем характеристики на границах
        # self._build_boundary_characteristics()
    
    def _build_characteristics(self):
        """Построение положительных и отрицательных характеристик"""
        s0, t0 = self.center
        
        # Отрицательные характеристики (синие) - фиксируем i, меняем j
        for j in range(self.j_min, self.j_max + 1):
            # Центр для отрицательной характеристики
            char_center = (s0 + j * self.ds, t0 + j * self.dt2)
            char = Characteristic(
                center=char_center,
                dt=-self.dt1,  # изменение по времени для отрицательных
                step=self.ds,
                # num_points=abs(self.j_max - self.j_min),
                frame=self.frame
            )
            if char.internal_nodes or char.get_boundary_nodes()[0]:
                self.negative_chars[j] = char
        
        # Положительные характеристики (красные) - фиксируем j, меняем i
        for i in range(self.i_min, self.i_max + 1):
            # Центр для положительной характеристики
            char_center = (s0 + i * self.ds, t0 - i * self.dt1)
            char = Characteristic(
                center=char_center,
                dt=self.dt2,  # изменение по времени для положительных
                step=self.ds,
                # num_points=abs(self.i_max - self.i_min),
                frame=self.frame
            )
            if char.internal_nodes or char.get_boundary_nodes()[0]:
                self.positive_chars[i] = char
    
    
    def get_node(self, i: int, j: int) -> Optional[Tuple[float, float]]:
        """Возвращает узел по индексам (i, j)"""
        node = self.negative_chars[j](i)
        if node:
            return node
        node = self.positive_chars[i](j)
        if node:
            return node
        return None
        # return self.nodes.get((i, j))
    
    def get_preceding_nodes(self, i: int, j: int) -> Dict[str, Optional[Tuple[float, float]]]:
        """Возвращает предшествующие узлы для шага по времени"""
        return {
            'left': self.get_node(i - 1, j),    # по отрицательной характеристике
            'right': self.get_node(i, j - 1),   # по положительной характеристике  
            'center': self.get_node(i - 1, j - 1)  # диагональный узел
        }


    def get_boundary_nodes(self):
        boundary_nodes = []
        for char in list(self.positive_chars.values()) + list(self.negative_chars.values()):
            left_node, right_node = char.get_boundary_nodes()
            if left_node:
                boundary_nodes.append(left_node)
            if right_node:
                boundary_nodes.append(right_node)
        return boundary_nodes
    
    def plot(self, figsize=(12, 8), node_size=20):
        """Визуализация характеристической сетки с улучшенной отрисовкой границ"""
        
        # Рисуем положительные характеристики (красным)
        for  char in self.positive_chars.values():
            char.plot(color='r', node_size=node_size)
        for  char in self.negative_chars.values():
            char.plot(color='b', node_size=node_size)
        
        boundary_nodes = self.get_boundary_nodes()
        if boundary_nodes:
            x_bnd, y_bnd = zip(*boundary_nodes)
            plt.scatter(x_bnd, y_bnd, c='orange', s=node_size*2, 
                      marker='X', label='Крайние узлы', zorder=6)
        
        # Отмечаем центральный узел особо
        center_node = self.get_node(0, 0)
        print(center_node)
        if center_node:
            plt.scatter([center_node[0]], [center_node[1]], 
                      c='yellow', s=node_size*3, edgecolors='black', 
                      label='Центр (0,0)', zorder=7)
        
        
