"""
Настройка дискретизации для характеристической сетки.
Вычисляет шаги по пространству и времени.
"""
import math
import numpy as np
from typing import Dict
from .rectangle import Rectangle

class Discretization:
    """Управляет параметрами дискретизации сетки"""
    
    def __init__(self, config: Dict, frame: Rectangle):
        self.frame = frame
        self.config = config
        self._setup_parameters()
    
    def _setup_parameters(self):
        """Вычисляет шаги дискретизации"""
        C1, C2 = np.float64(self.config['C'][0]), np.float64(self.config['C'][1])
        
        if 'm' in self.config:
            self._setup_from_m(C1, C2)
        elif 'h' in self.config:
            self._setup_from_h(C1, C2)
        else:
            raise ValueError("Конфигурация должна содержать 'm' или 'h'")
    
    def _setup_from_m(self, C1: float, C2: float):
        """Настройка по количеству точек"""
        M = self.config['m'] * 2
        self.ds = (self.frame.S1 - self.frame.S0) / M
        self.dt1 = self.ds / C1 
        self.dt2 = self.ds / C2
    
    def _setup_from_h(self, C1: float, C2: float):
        """Настройка по шагу времени"""
        dt = self.config['h']
        self.ds = dt * C1 * C2 / (C1 + C2)
        self.dt1 = self.ds / C1
        self.dt2 = self.ds / C2
    
    def calculate_index_ranges(self):
        """Вычисляет диапазоны индексов"""
        RS = (self.frame.S1 - self.frame.S0) / 2
        RT = (self.frame.T1 - self.frame.T0) / 2

        i_r = math.ceil(max(RS / self.ds, RT / self.dt1))
        j_r = math.ceil(max(RS / self.ds, RT / self.dt2))
        
        return (-i_r, i_r), (-j_r, j_r)