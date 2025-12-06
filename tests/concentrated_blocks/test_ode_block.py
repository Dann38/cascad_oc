"""
Тесты для блока ОДУ.
Проверяет решение различных типов ОДУ и соединение с другими блоками.
"""
import unittest
import numpy as np
from cascadoc_deepseek.blocks.concentrated_blocks.ode_block import ODEBlock
from cascadoc_deepseek.blocks.concentrated_blocks.ode_helpers import create_linear_ode

class TestODEBlock(unittest.TestCase):
    """Тесты для ODEBlock"""
    
    def test_exponential_decay(self):
        """Тест решения dy/dt = -y (экспоненциальный распад)"""
        def rhs(t, state, inputs):
            return -state
        
        ode = ODEBlock("test_ode", rhs, initial_state=1.0)
        ode.initialize()
        
        # Делаем несколько шагов
        t, dt = 0.0, 0.1
        for _ in range(10):
            result = ode.step(t, dt)
            t += dt
        
        # Проверяем, что решение экспоненциально убывает
        self.assertLess(result['state'], 1.0)
        self.assertGreater(result['state'], 0.0)
    
    def test_linear_ode_helper(self):
        """Тест создания линейного ОДУ через helper"""
        rhs = create_linear_ode(a=-2.0, b=1.0)
        ode = ODEBlock("linear_ode", rhs, initial_state=0.5)
        ode.initialize()
        
        result = ode.step(0.0, 0.1)
        self.assertIsInstance(result['state'], float)
    
    def test_initial_conditions(self):
        """Тест различных начальных условий"""
        def rhs(t, state, inputs):
            return 1.0  # dy/dt = 1
        
        ode = ODEBlock("constant_derivative", rhs)
        
        # Тест с явными начальными условиями
        ode.initialize({'state': 10.0, 't0': 5.0})
        self.assertEqual(ode.state, 10.0)
        self.assertEqual(ode.current_time, 5.0)
    
    def test_solution_history(self):
        """Тест сохранения истории решений"""
        def rhs(t, state, inputs):
            return 2.0
        
        ode = ODEBlock("history_test", rhs, initial_state=0.0)
        ode.initialize()
        
        # Делаем несколько шагов
        steps = 5
        for i in range(steps):
            ode.step(i * 0.1, 0.1)
        
        # Проверяем историю
        self.assertEqual(len(ode.history), steps + 1)  # +1 для начального состояния
        
        # Проверяем интерполяцию
        interpolated = ode.get_solution_at_time(0.05)
        self.assertIsNotNone(interpolated)
        self.assertGreater(interpolated, 0.0)
    
    def test_error_handling(self):
        """Тест обработки ошибок в правой части"""
        def bad_rhs(t, state, inputs):
            raise ValueError("Test error")
        
        ode = ODEBlock("error_test", bad_rhs)
        ode.initialize({'state': 1.0})
        
        with self.assertRaises(RuntimeError):
            ode.step(0.0, 0.1)

if __name__ == '__main__':
    unittest.main()