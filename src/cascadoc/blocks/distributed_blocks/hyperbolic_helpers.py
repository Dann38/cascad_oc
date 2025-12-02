"""
Вспомогательные функции для создания гиперболических систем.
Упрощают настройку стандартных гиперболических систем.
"""
from typing import Dict, Any, Callable

def create_linear_hyperbolic_system(c1: float, c2: float, 
                                  B_coeffs: Dict[str, float] = None) -> Dict[str, Any]:
    """Создает линейную гиперболическую систему с постоянными коэффициентами"""
    if B_coeffs is None:
        B_coeffs = {}
    
    config = {
        'C': [c1, c2],
        'B11': lambda s, t: B_coeffs.get('B11', 0.0),
        'B12': lambda s, t: B_coeffs.get('B12', 0.0),
        'B21': lambda s, t: B_coeffs.get('B21', 0.0), 
        'B22': lambda s, t: B_coeffs.get('B22', 0.0),
        'F1': lambda s, t: B_coeffs.get('F1', 0.0),
        'F2': lambda s, t: B_coeffs.get('F2', 0.0)
    }
    
    return config

def create_wave_equation(c: float, damping: float = 0.0) -> Dict[str, Any]:
    """Создает конфигурацию для волнового уравнения"""
    # Волновое уравнение: u_tt = c² u_xx - damping * u_t
    # Преобразуется в систему:
    # v = u_t, w = c u_x
    # v_t - c w_x = -damping * v
    # w_t - c v_x = 0
    
    config = {
        'C': [c, c],
        'B11': lambda s, t: -damping,
        'B12': lambda s, t: 0.0,
        'B21': lambda s, t: 0.0,
        'B22': lambda s, t: 0.0,
        'F1': lambda s, t: 0.0,
        'F2': lambda s, t: 0.0
    }
    
    return config

def create_transport_equation(velocity: float, decay: float = 0.0) -> Dict[str, Any]:
    """Создает конфигурацию для уравнения переноса"""
    # Уравнение переноса: u_t + velocity * u_x = -decay * u
    config = {
        'C': [velocity, 0.0],
        'B11': lambda s, t: -decay,
        'B12': lambda s, t: 0.0,
        'B21': lambda s, t: 0.0, 
        'B22': lambda s, t: 0.0,
        'F1': lambda s, t: 0.0,
        'F2': lambda s, t: 0.0
    }
    
    return config

def add_boundary_conditions(config: Dict[str, Any], 
                          left_bc: Callable = None,
                          right_bc: Callable = None) -> Dict[str, Any]:
    """Добавляет граничные условия к конфигурации"""
    config['left_boundary'] = left_bc
    config['right_boundary'] = right_bc
    return config

def add_initial_conditions(config: Dict[str, Any],
                         x0: Callable = None, 
                         y0: Callable = None) -> Dict[str, Any]:
    """Добавляет начальные условия к конфигурации"""
    config['initial_x'] = x0 or (lambda s: 0.0)
    config['initial_y'] = y0 or (lambda s: 0.0)
    return config