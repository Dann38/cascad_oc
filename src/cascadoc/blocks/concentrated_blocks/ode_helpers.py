"""
Вспомогательные функции для создания правых частей ОДУ.
Упрощают создание стандартных ОДУ.
"""
from typing import Dict, Any, Callable

def create_linear_ode(a: float, b: float = 0.0) -> Callable:
    """Создает правую часть для линейного ОДУ: dy/dt = a*y + b"""
    def rhs(t: float, state: float, inputs: Dict[str, Any]) -> float:
        return a * state + b
    return rhs

def create_oscillator(omega: float, damping: float = 0.0) -> Callable:
    """Создает правую часть для осциллятора: d²y/dt² + 2ζω dy/dt + ω²y = 0"""
    def rhs(t: float, state: Any, inputs: Dict[str, Any]) -> Any:
        # state должен быть массивом [position, velocity]
        y, v = state
        dvdt = -2 * damping * omega * v - omega**2 * y
        return np.array([v, dvdt])
    return rhs

def create_forced_ode(base_rhs: Callable, input_name: str, gain: float = 1.0) -> Callable:
    """Добавляет внешнее воздействие к существующей правой части"""
    def rhs(t: float, state: Any, inputs: Dict[str, Any]) -> Any:
        base_derivative = base_rhs(t, state, inputs)
        external_input = inputs.get(input_name, 0.0)
        return base_derivative + gain * external_input
    return rhs

def create_coupled_ode(base_rhs: Callable, coupling_terms: Dict[str, float]) -> Callable:
    """Создает ОДУ со связями с другими блоками"""
    def rhs(t: float, state: Any, inputs: Dict[str, Any]) -> Any:
        derivative = base_rhs(t, state, inputs)
        
        # Добавляем coupling terms
        for input_name, gain in coupling_terms.items():
            external_value = inputs.get(input_name, 0.0)
            derivative += gain * external_value
            
        return derivative
    return rhs