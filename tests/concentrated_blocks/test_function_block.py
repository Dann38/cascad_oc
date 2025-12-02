"""
Тесты для блока функции.
Проверяет различные типы функций и граничных условий.
"""
import unittest
import numpy as np
from cascadoc.blocks.concentrated_blocks.function_block import FunctionBlock
from cascadoc.blocks.concentrated_blocks.function_helpers import (
    create_constant_block, 
    create_sinusoidal_block,
    create_step_block,
    create_ramp_block
)

class TestFunctionBlock(unittest.TestCase):
    """Тесты для FunctionBlock"""
    
    def test_constant_function(self):
        """Тест постоянной функции"""
        block = FunctionBlock("constant", 5.0, function_type="constant")
        block.initialize({'t0': 0.0})
        
        result = block.step(0.0, 0.1)
        self.assertEqual(result['value'], 5.0)
        self.assertEqual(block.get_current_value(), 5.0)
    
    def test_time_function(self):
        """Тест функции времени"""
        def linear_func(t):
            return 2.0 * t + 1.0
        
        block = FunctionBlock("linear", linear_func, function_type="time")
        block.initialize({'t0': 0.0})
        
        result = block.step(1.0, 0.1)
        self.assertEqual(result['value'], 3.0)  # 2*1 + 1 = 3
    
    def test_callable_constant(self):
        """Тест callable константы"""
        def constant_func():
            return 7.5
        
        block = FunctionBlock("callable_constant", constant_func, function_type="constant")
        block.initialize()
        
        result = block.step(0.0, 0.1)
        self.assertEqual(result['value'], 7.5)
    
    def test_value_at_time(self):
        """Тест получения значения в произвольный момент времени"""
        block = FunctionBlock("test", lambda t: t**2, function_type="time")
        block.initialize({'t0': 0.0})
        
        # Делаем несколько шагов для заполнения истории
        block.step(0.0, 0.1)
        block.step(0.1, 0.1)
        block.step(0.2, 0.1)
        
        # Проверяем интерполяцию
        value = block.get_value_at_time(0.15)
        self.assertAlmostEqual(value, 0.15**2, places=2)
    
    def test_invalid_function_type(self):
        """Тест обработки неверного типа функции"""
        with self.assertRaises(ValueError):
            FunctionBlock("invalid", 5.0, function_type="invalid_type")
    
    def test_invalid_callable(self):
        """Тест обработки неверного callable для constant типа"""
        with self.assertRaises(ValueError):
            FunctionBlock("invalid", lambda t: t, function_type="constant")

class TestFunctionHelpers(unittest.TestCase):
    """Тесты для вспомогательных функций"""
    
    def test_constant_block(self):
        """Тест создания постоянного блока"""
        block = create_constant_block("const", 3.14)
        block.initialize()
        
        result = block.step(0.0, 0.1)
        self.assertEqual(result['value'], 3.14)
    
    def test_sinusoidal_block(self):
        """Тест создания синусоидального блока"""
        block = create_sinusoidal_block("sin", amplitude=2.0, frequency=1.0)
        block.initialize({'t0': 0.0})
        
        result = block.step(0.25, 0.1)  # sin(2π*0.25) = sin(π/2) = 1
        self.assertAlmostEqual(result['value'], 2.0, places=2)  # 2 * 1 = 2
    
    def test_step_block(self):
        """Тест создания ступенчатого блока"""
        block = create_step_block("step", step_time=1.0, initial_value=0.0, final_value=5.0)
        block.initialize({'t0': 0.0})
        
        # До step_time
        result1 = block.step(0.5, 0.1)
        self.assertEqual(result1['value'], 0.0)
        
        # После step_time
        result2 = block.step(1.5, 0.1)
        self.assertEqual(result2['value'], 5.0)
    
    def test_ramp_block(self):
        """Тест создания линейного блока"""
        block = create_ramp_block("ramp", start_time=1.0, end_time=3.0, 
                                 initial_value=0.0, final_value=10.0)
        block.initialize({'t0': 0.0})
        
        # В середине рампы
        result = block.step(2.0, 0.1)
        self.assertEqual(result['value'], 5.0)  # (10-0)/(3-1) * (2-1) = 5

if __name__ == '__main__':
    unittest.main()