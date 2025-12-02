"""
Блок функции для представления граничных условий и внешних воздействий.
Может задавать значения как функции времени или константы.
"""
from typing import Dict, Any, Callable, Union, Optional
import numpy as np
from cascadoc.blocks.concentrated_blocks.base_concentrated_block import BaseConcentratedBlock

class FunctionBlock(BaseConcentratedBlock):
    """
    Блок функции для задания граничных условий и внешних воздействий.
    
    Может использоваться как:
    - Постоянное значение (константа)
    - Функция времени
    - Функция времени и состояния других блоков
    """
    
    def __init__(self, name: str, 
                 function: Union[Callable, float, int],
                 function_type: str = "time"):
        """
        Args:
            name: Имя блока
            function: Функция или константа. Может быть:
                     - callable: function(t) или function(t, inputs)
                     - float/int: постоянное значение
            function_type: Тип функции:
                         - "time": функция только от времени f(t)
                         - "time_inputs": функция от времени и входов f(t, inputs)
                         - "constant": постоянное значение
        """
        super().__init__(name)
        
        self.function = function
        self.function_type = function_type
        self.current_value = 0.0
        self.history = []
        
        # Проверяем тип функции
        self._validate_function()
    
    def _validate_function(self):
        """Проверка корректности задания функции"""
        if self.function_type == "constant":
            if not isinstance(self.function, (int, float)):
                try:
                    # Пробуем вызвать как функцию без аргументов
                    self.function = float(self.function())
                except:
                    raise ValueError("Для constant типа function должен быть числом или callable без аргументов")
        
        elif self.function_type in ["time", "time_inputs"]:
            if not callable(self.function):
                raise ValueError("Для time и time_inputs типов function должен быть callable")
    
    def initialize(self, initial_conditions: Optional[Dict[str, Any]] = None) -> None:
        """Инициализация блока функции"""
        if initial_conditions is None:
            initial_conditions = {}
        
        t0 = initial_conditions.get('t0', 0.0)
        self.current_time = np.float64(t0)
        self.initialized = True
        
        # Вычисляем начальное значение
        self._compute_value(t0, {})
        
        # Сохраняем в историю
        self.history = [(self.current_time, self.current_value)]
        
        print(f"Function Block '{self.name}' initialized: t0={t0}, value0={self.current_value}")
    
    def _compute_value(self, t: float, inputs: Dict[str, Any]) -> float:
        """Вычисление значения функции"""
        try:
            if self.function_type == "constant":
                if callable(self.function):
                    return float(self.function())
                else:
                    return float(self.function)
                    
            elif self.function_type == "time":
                return float(self.function(t))
                
            elif self.function_type == "time_inputs":
                return float(self.function(t, inputs))
                
            else:
                raise ValueError(f"Неизвестный тип функции: {self.function_type}")
                
        except Exception as e:
            raise RuntimeError(f"Ошибка вычисления функции в блоке {self.name}: {e}")
    
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
    
    def step(self, t: float, dt: float) -> Dict[str, Any]:
        """Шаг решения для блока функции"""
        if not self.initialized:
            raise RuntimeError(f"Function Block {self.name} is not initialized")
        
        # Собираем входные данные
        inputs = self._collect_inputs(t)
        
        # Вычисляем значение
        self.current_value = self._compute_value(t, inputs)
        self.current_time = t + dt
        
        # Сохраняем в историю
        self.history.append((self.current_time, self.current_value))
        
        return {
            'value': self.current_value,
            't': self.current_time,
            'ready_until': self.current_time
        }
    
    def get_value_at_time(self, t: float) -> float:
        """Получение значения в заданный момент времени"""
        if not self.history:
            return self._compute_value(t, {})
        
        # Ищем ближайшее значение в истории
        for i, (time, value) in enumerate(self.history):
            if time >= t:
                if i == 0:
                    return value
                # Линейная интерполяция
                t_prev, value_prev = self.history[i-1]
                alpha = (t - t_prev) / (time - t_prev)
                return value_prev + alpha * (value - value_prev)
        
        # Если время больше всех в истории, возвращаем последнее значение
        return self.history[-1][1]
    
    def get_current_value(self) -> float:
        """Получение текущего значения"""
        return self.current_value