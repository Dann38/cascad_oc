"""
Блок для решения обыкновенных дифференциальных уравнений (ОДУ).
Может использоваться как самостоятельный блок или для граничных условий.
"""
import numpy as np
from typing import Dict, Any, Callable, Optional
from cascadoc.blocks.concentrated_blocks.base_concentrated_block import BaseConcentratedBlock

class ODEBlock(BaseConcentratedBlock):
    """Блок для решения ОДУ с возможностью соединения с другими блоками"""
    
    def __init__(self, name: str, rhs_function: Callable, initial_state: float = 0.0):
        """
        Args:
            name: Имя блока
            rhs_function: Функция правой части ОДУ: f(t, state, inputs) -> derivative
            initial_state: Начальное состояние
        """
        super().__init__(name)
        self.rhs_function = rhs_function
        self.initial_state = initial_state
        self.history = []  # История решений для отладки
    
    def _compute_derivative(self, t: float, state: Any) -> Any:
        """Вычисление производной с учетом входных сигналов"""
        # Собираем входные данные с соединенных блоков
        inputs = self._collect_inputs(t)
        
        try:
            return self.rhs_function(t, state, inputs)
        except Exception as e:
            raise RuntimeError(f"Error in ODE rhs_function for block {self.name}: {e}")
    
    def _collect_inputs(self, t: float) -> Dict[str, Any]:
        """Сбор входных данных с соединенных блоков"""
        inputs = {}
        for connection in self.connections:
            try:
                value = connection.get_value(t)
                if value is not None:
                    inputs[connection.source_boundary] = value
            except Exception as e:
                print(f"Warning: Failed to get input from {connection.source_boundary}: {e}")
        
        return inputs
    
    def initialize(self, initial_conditions: Optional[Dict[str, Any]] = None) -> None:
        """Инициализация блока ОДУ"""
        if initial_conditions is None:
            initial_conditions = {}
        
        # Используем переданное начальное состояние или значение по умолчанию
        state = initial_conditions.get('state', self.initial_state)
        t0 = initial_conditions.get('t0', 0.0)
        
        self.state = np.float64(state)
        self.current_time = np.float64(t0)
        self.initialized = True
        
        # Сохраняем начальное состояние в историю
        self.history = [(self.current_time, self.state)]
        
        print(f"ODE Block '{self.name}' initialized: t0={t0}, state0={state}")
    
    def step(self, t: float, dt: float) -> Dict[str, Any]:
        """Шаг решения ОДУ методом Рунге-Кутты 4-го порядка"""
        if not self.initialized:
            raise RuntimeError(f"ODE Block {self.name} is not initialized")
        
        # Метод Рунге-Кутты 4-го порядка
        k1 = self._compute_derivative(t, self.state)
        k2 = self._compute_derivative(t + dt/2, self.state + dt*k1/2)
        k3 = self._compute_derivative(t + dt/2, self.state + dt*k2/2)
        k4 = self._compute_derivative(t + dt, self.state + dt*k3)
        
        self.state += (dt / 6) * (k1 + 2*k2 + 2*k3 + k4)
        self.current_time = t + dt
        
        # Сохраняем в историю
        self.history.append((self.current_time, self.state))
        
        return {
            'state': self.state,
            't': self.current_time,
            'ready_until': self.current_time  # Отмечаем готовность данных
        }
    
    def get_solution_at_time(self, t: float) -> Optional[float]:
        """Получение решения в заданный момент времени (интерполяция)"""
        if not self.history:
            return None
            
        # Простой поиск ближайшего значения
        for i, (time, state) in enumerate(self.history):
            if time >= t:
                if i == 0:
                    return state
                # Линейная интерполяция между предыдущей и текущей точкой
                t_prev, state_prev = self.history[i-1]
                alpha = (t - t_prev) / (time - t_prev)
                return state_prev + alpha * (state - state_prev)
        
        return self.history[-1][1]  # Последнее известное значение