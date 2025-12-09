"""
Характеристика гиперболического уравнения.
Представляет собой линию в пространстве (S, T).
"""
from typing import Tuple, Optional, Dict, List
from .rectangle import Rectangle
EPS = 1e-10
class Characteristic:
    """Характеристика с узлами внутри расчетной области"""
    
    def __init__(self, center: Tuple[float, float], dt: float, 
                 step: float, frame: Rectangle):
        self.center = center
        self.dt = dt
        self.step = step
        self.frame = frame
        self.internal_nodes: Dict[int, Tuple[float, float]] = {}
        self.boundary_nodes: Tuple[Optional[Tuple[float, float]], 
                                  Optional[Tuple[float, float]]] = (None, None)
        
        self._build_characteristic()

    @property
    def k(self):
        return self.dt/self.step
    
    def _build_characteristic(self):
        """Основной метод построения характеристики"""
        intersections = self._find_boundary_intersections()
        if not intersections:
            return
            
        self._set_boundary_nodes(intersections)
        self._generate_internal_nodes()
    
    def _find_boundary_intersections(self) -> List[Tuple[float, float]]:
        """Находит пересечения с границами области"""
        s0, t0 = self.center
        intersections = []
        
        # Проверяем все 4 границы
        boundaries = [
            (self.frame.S0, 'vertical'), (self.frame.S1, 'vertical'),
            (self.frame.T0, 'horizontal'), (self.frame.T1, 'horizontal')
        ]
        
        for boundary_value, boundary_type in boundaries:
            point = self._intersect_with_boundary(boundary_value, boundary_type)
            if point and self.frame.contains(point[0], point[1]):
                intersections.append((round(point[0], 10), round(point[1], 10)))
                
        return intersections
    
    def _intersect_with_boundary(self, value: float, 
                               boundary_type: str) -> Optional[Tuple[float, float]]:
        """Вычисляет точку пересечения с конкретной границей"""
        s0, t0 = self.center
        
        if boundary_type == 'vertical':
            return self._intersect_vertical(value, s0, t0)
        else:  # horizontal
            return self._intersect_horizontal(value, s0, t0)
    
    def _intersect_vertical(self, s: float, s0: float, t0: float) -> Optional[Tuple[float, float]]:
        """Пересечение с вертикальной границей s=const"""
        if abs(self.step) < EPS:
            return None
            
        k = (s - s0) / self.step
        t = t0 + k * self.dt
        return (s, t) if self.frame.T0-EPS <= t <= self.frame.T1+EPS else None
    
    def _intersect_horizontal(self, t: float, s0: float, t0: float) -> Optional[Tuple[float, float]]:
        """Пересечение с горизонтальной границей t=const"""
        if abs(self.dt) < EPS:
            return None
            
        k = (t - t0) / self.dt
        s = s0 + k * self.step
        return (s, t) if self.frame.S0-EPS <= s <= self.frame.S1+EPS else None
    
    def _set_boundary_nodes(self, intersections: List[Tuple[float, float]]):
        """Устанавливает крайние узлы на границах"""
        intersections.sort(key=lambda p: p[0])
        self.boundary_nodes = (intersections[0], intersections[-1])
    
    def _generate_internal_nodes(self):
        """Генерирует узлы между граничными точками"""
        left_node, right_node = self.boundary_nodes
        if not left_node or not right_node:
            return
            
        s0, t0 = self.center
        k_left =int(self._calculate_k(left_node, s0, t0))
        k_right = int(self._calculate_k(right_node, s0, t0))
        
        k_array = []
        for k in range(k_left, k_right + 1):
            s = s0 + k * self.step
            t = t0 + k * self.dt
            if self.frame.contains(s, t):
                self.internal_nodes[k] = (s, t)
                k_array.append(k)
        self.k_left = min(k_array)
        self.k_right = max(k_array)

    
    def _calculate_k(self, point: Tuple[float, float], s0: float, t0: float) -> int:
        """Вычисляет индекс k для точки на характеристике"""
        s, t = point
        if abs(self.step) > 1e-10:
            return round((s - s0) / self.step)
        else:
            return round((t - t0) / self.dt)
    
    def get_node(self, index: int) -> Optional[Tuple[float, float]]:
        """Возвращает узел по индексу"""
        if index < self.k_left:
            return self.boundary_nodes[0]
        elif index > self.k_right:
            return self.boundary_nodes[1]
        return self.internal_nodes.get(index)
    
    def get_boundary_nodes(self):
        """Возвращает граничные узлы"""
        return self.boundary_nodes