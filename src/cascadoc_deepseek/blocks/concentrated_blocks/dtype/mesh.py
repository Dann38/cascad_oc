import matplotlib.pyplot as plt
import numpy as np
from dataclasses import dataclass
from .base_mesh import BaseMesh
@dataclass
class Rectangle:
    """Область-рамка: прямоугольник в координатах (S, T)"""
    S0: float
    S1: float  
    T0: float
    T1: float

class Mesh(BaseMesh):
    """Сетка для ODE блока - вертикальная линия узлов на границе"""
    
    def __init__(self, config):
        S0, S1 = config['S'][0], config['S'][1]
        T0, T1 = config['T'][0], config['T'][1]
        
        self.frame = Rectangle(S0=S0, S1=S1, T0=T0, T1=T1)
        self.boundary_position = config['boundary_position']
        self.boundary_side = config.get('boundary_side', 'left')
        
        # Параметры дискретизации времени
        if 'dt' in config:
            self.dt = config['dt']
            self.time_nodes = self._build_nodes_with_dt()
        elif 'num_points' in config:
            self.dt = (T1 - T0) / config['num_points']
            self.time_nodes = self._build_nodes_with_dt()
        elif 'mesh' in config:
            self.time_nodes = config['mesh']
        else:
            raise Exception('no mesh')
        
        # Собираем все узлы сетки
        self.nodes = []
        self._build_grid()
        
    def _build_nodes_with_dt(self):
        """Строит временные узлы с заданным шагом dt"""
        T0, T1 = self.frame.T0, self.frame.T1
        num_steps = int((T1 - T0) / self.dt) + 1
        return [T0 + i * self.dt for i in range(num_steps)]
    
    def _build_grid(self):
        """Строит сетку узлов - все точки имеют одинаковую координату S"""
        s = self.boundary_position
        for t in self.time_nodes:
            if self.frame.T0 <= t <= self.frame.T1:
                self.nodes.append((s, t))
    
    def get_boundary_nodes(self):
        """Возвращает все узлы сетки (все они находятся на границе)"""
        return self.nodes
    
    def get_node(self, index):
        """Возвращает узел по индексу"""
        if 0 <= index < len(self.nodes):
            return self.nodes[index]
        return None
    
    def get_preceding_nodes(self, current_index):
        """Возвращает предыдущие узлы"""
        if current_index == 0:
            return {'previous': None, 'current': self.nodes[0]}
        else:
            return {
                'previous': self.nodes[current_index - 1],
                'current': self.nodes[current_index]
            }
    
    def plot(self, figsize=(12, 8), node_size=30):
        """Визуализация сетки ODE как вертикальной линии узлов"""
        
        if not self.nodes:
            return
            
        # Разделяем координаты
        s_coords, t_coords = zip(*self.nodes)
        
        # Рисуем вертикальную линию узлов
        plt.scatter(s_coords, t_coords, c='green', s=node_size, 
                   label='Узлы ODE сетки', zorder=5)
        
        # Соединяем узлы линией для наглядности
        plt.plot(s_coords, t_coords, 'g--', alpha=0.5, linewidth=1)
        
        # Подписываем несколько узлов для ориентира
        num_labels = min(5, len(self.nodes))
        step = max(1, len(self.nodes) // num_labels)
        for i in range(0, len(self.nodes), step):
            s, t = self.nodes[i]
            plt.annotate(f'({s:.1f}, {t:.2f})', 
                        xy=(s, t), xytext=(5, 5),
                        textcoords='offset points', fontsize=8,
                        alpha=0.7)