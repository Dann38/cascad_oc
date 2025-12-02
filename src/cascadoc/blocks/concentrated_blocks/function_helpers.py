"""
Вспомогательные функции для создания FunctionBlock.
Упрощают создание стандартных функций и граничных условий.
"""
from typing import Callable, Union
import numpy as np
from cascadoc.blocks.concentrated_blocks.function_block import FunctionBlock

def create_constant_block(name: str, value: float) -> FunctionBlock:
    """Создает блок с постоянным значением"""
    return FunctionBlock(name, value, function_type="constant")

def create_sinusoidal_block(name: str, amplitude: float = 1.0, 
                          frequency: float = 1.0, phase: float = 0.0) -> FunctionBlock:
    """Создает блок с синусоидальной функцией"""
    def sinusoid(t: float) -> float:
        return amplitude * np.sin(2 * np.pi * frequency * t + phase)
    
    return FunctionBlock(name, sinusoid, function_type="time")

def create_step_block(name: str, step_time: float = 1.0, 
                     initial_value: float = 0.0, final_value: float = 1.0) -> FunctionBlock:
    """Создает блок со ступенчатой функцией"""
    def step_function(t: float) -> float:
        return initial_value if t < step_time else final_value
    
    return FunctionBlock(name, step_function, function_type="time")

def create_ramp_block(name: str, start_time: float = 0.0, end_time: float = 1.0,
                     initial_value: float = 0.0, final_value: float = 1.0) -> FunctionBlock:
    """Создает блок с линейно нарастающей функцией"""
    def ramp_function(t: float) -> float:
        if t < start_time:
            return initial_value
        elif t > end_time:
            return final_value
        else:
            slope = (final_value - initial_value) / (end_time - start_time)
            return initial_value + slope * (t - start_time)
    
    return FunctionBlock(name, ramp_function, function_type="time")

def create_pulse_block(name: str, period: float = 1.0, duty_cycle: float = 0.5,
                      low_value: float = 0.0, high_value: float = 1.0) -> FunctionBlock:
    """Создает блок с импульсной функцией"""
    def pulse_function(t: float) -> float:
        phase = t % period
        return high_value if phase < period * duty_cycle else low_value
    
    return FunctionBlock(name, pulse_function, function_type="time")

def create_noise_block(name: str, amplitude: float = 1.0, 
                      seed: int = None) -> FunctionBlock:
    """Создает блок со случайным шумом"""
    rng = np.random.RandomState(seed)
    
    def noise_function(t: float) -> float:
        return amplitude * rng.randn()
    
    return FunctionBlock(name, noise_function, function_type="time")

def create_pid_controller(name: str, kp: float = 1.0, ki: float = 0.0, kd: float = 0.0,
                         setpoint: float = 0.0) -> FunctionBlock:
    """Создает блок ПИД-регулятора"""
    # Для ПИД-регулятора нужен доступ к входным данным (ошибке)
    integral = 0.0
    prev_error = 0.0
    prev_time = 0.0
    
    def pid_function(t: float, inputs: dict) -> float:
        nonlocal integral, prev_error, prev_time
        
        # Получаем текущее значение процесса
        process_value = inputs.get('process_value', 0.0)
        error = setpoint - process_value
        
        # Вычисляем производную и интеграл
        dt = t - prev_time if prev_time > 0 else 0.0
        if dt > 0:
            integral += error * dt
            derivative = (error - prev_error) / dt
        else:
            derivative = 0.0
        
        # Вычисляем выход ПИД
        output = kp * error + ki * integral + kd * derivative
        
        # Сохраняем для следующего шага
        prev_error = error
        prev_time = t
        
        return output
    
    return FunctionBlock(name, pid_function, function_type="time_inputs")

def create_lookup_table_block(name: str, time_points: list, values: list) -> FunctionBlock:
    """Создает блок с кусочно-линейной функцией по таблице"""
    if len(time_points) != len(values):
        raise ValueError("Количество точек времени и значений должно совпадать")
    
    def lookup_function(t: float) -> float:
        # Находим интервал
        for i in range(len(time_points) - 1):
            if time_points[i] <= t <= time_points[i + 1]:
                # Линейная интерполяция
                t0, t1 = time_points[i], time_points[i + 1]
                v0, v1 = values[i], values[i + 1]
                return v0 + (v1 - v0) * (t - t0) / (t1 - t0)
        
        # Экстраполяция: возвращаем первое или последнее значение
        if t < time_points[0]:
            return values[0]
        else:
            return values[-1]
    
    return FunctionBlock(name, lookup_function, function_type="time")