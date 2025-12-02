"""
Характеристическая сетка для гиперболических систем.
Координатная сетка на основе характеристик уравнений.
"""
from typing import Dict, Tuple, Optional, List
from .base_mesh import BaseMesh
from .rectangle import Rectangle
from .discretization import Discretization
from .characteristic import Characteristic

class CharacteristicMesh(BaseMesh):
    """Сетка на основе характеристик гиперболических уравнений"""
    
    def __init__(self, config: Dict):
        self._setup_frame(config)
        self._setup_discretization(config)
        self._setup_storage()
        self._build_grid()
    
    def _setup_frame(self, config: Dict):
        """Инициализирует расчетную область"""
        S0, S1 = config['S'][0], config['S'][1]
        T0, T1 = config['T'][0], config['T'][1]
        self.frame = Rectangle(S0, S1, T0, T1)
        self.center = self.frame.center
    
    def _setup_discretization(self, config: Dict):
        """Настраивает параметры дискретизации"""
        discretization = Discretization(config, self.frame)
        self.ds = discretization.ds
        self.dt1 = discretization.dt1
        self.dt2 = discretization.dt2
        self.i_range, self.j_range = discretization.calculate_index_ranges()
    
    def _setup_storage(self):
        """Инициализирует хранилища данных"""
        self.nodes: Dict[Tuple[int, int], Tuple[float, float]] = {}
        self.positive_chars: Dict[int, Characteristic] = {}
        self.negative_chars: Dict[int, Characteristic] = {}
    
    def _build_grid(self):
        """Строит сетку характеристик и узлов"""
        self._build_characteristics()
        self._build_nodes()
    
    def _build_characteristics(self):
        """Строит положительные и отрицательные характеристики"""
        self._build_negative_characteristics()
        self._build_positive_characteristics()
    
    def _build_negative_characteristics(self):
        """Строит отрицательные характеристики (фиксированный j)"""
        s0, t0 = self.center
        j_min, j_max = self.j_range
        
        for j in range(j_min, j_max + 1):
            center = (s0 + j * self.ds, t0 + j * self.dt2)
            char = Characteristic(center, -self.dt1, self.ds, self.frame)
            if char.internal_nodes:
                self.negative_chars[j] = char
    
    def _build_positive_characteristics(self):
        """Строит положительные характеристики (фиксированный i)"""
        s0, t0 = self.center
        i_min, i_max = self.i_range
        
        for i in range(i_min, i_max + 1):
            center = (s0 + i * self.ds, t0 - i * self.dt1)
            char = Characteristic(center, self.dt2, self.ds, self.frame)
            if char.internal_nodes:
                self.positive_chars[i] = char
    
    def _build_nodes(self):
        """Строит все узлы сетки"""
        s0, t0 = self.center
        i_min, i_max = self.i_range
        j_min, j_max = self.j_range
        
        for i in range(i_min, i_max + 1):
            for j in range(j_min, j_max + 1):
                node = self._calculate_node(i, j, s0, t0)
                if node and self.frame.contains(node[0], node[1]):
                    self.nodes[(i, j)] = node
    
    def _calculate_node(self, i: int, j: int, s0: float, t0: float) -> Tuple[float, float]:
        """Вычисляет координаты узла по индексам"""
        s = s0 + (i + j) * self.ds
        t = t0 - i * self.dt1 + j * self.dt2
        return (s, t)
    
    def get_node(self, i: int, j: int) -> Optional[Tuple[float, float]]:
        """Возвращает узел по индексам"""
        return self.nodes.get((i, j))
    
    def get_preceding_nodes(self, i: int, j: int) -> Dict[str, Optional[Tuple[float, float]]]:
        """Возвращает узлы для шага по времени"""
        return {
            'left': self.get_node(i - 1, j),
            'right': self.get_node(i, j - 1),
            'center': self.get_node(i - 1, j - 1)
        }
    
    def get_boundary_nodes(self) -> List[Tuple[float, float]]:
        """Собирает все граничные узлы"""
        boundary_nodes = []
        all_chars = list(self.positive_chars.values()) + list(self.negative_chars.values())
        
        for char in all_chars:
            left, right = char.get_boundary_nodes()
            if left and left not in boundary_nodes:
                boundary_nodes.append(left)
            if right and right not in boundary_nodes:
                boundary_nodes.append(right)
                
        return boundary_nodes