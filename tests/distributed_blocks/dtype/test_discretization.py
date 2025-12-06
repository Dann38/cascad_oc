"""
Тесты для настройки дискретизации.
Проверяет вычисление шагов по пространству и времени.
"""
import unittest
import sys
import os

from cascadoc_deepseek.blocks.distributed_blocks.dtype.rectangle import Rectangle
from cascadoc_deepseek.blocks.distributed_blocks.dtype.discretization import Discretization

class TestDiscretization(unittest.TestCase):
    """Тесты для класса Discretization"""
    
    def setUp(self):
        """Подготовка тестовых данных"""
        self.frame = Rectangle(S0=0.0, S1=10.0, T0=0.0, T1=5.0)
    
    def test_setup_from_m(self):
        """Тест настройки по количеству точек"""
        config = {'m': 10, 'C': [2.0, 3.0]}
        disc = Discretization(config, self.frame)
        
        # Проверяем вычисленные шаги
        expected_ds = 0.5  # (10.0 - 0.0) / (10*2)
        expected_dt1 = 0.25  # ds / 2.0
        expected_dt2 = 0.16666666666666666  # ds / 3.0
        
        self.assertAlmostEqual(disc.ds, expected_ds)
        self.assertAlmostEqual(disc.dt1, expected_dt1)
        self.assertAlmostEqual(disc.dt2, expected_dt2)
    
    def test_setup_from_h(self):
        """Тест настройки по шагу времени"""
        config = {'h': 0.1, 'C': [2.0, 3.0]}
        disc = Discretization(config, self.frame)
        
        # Проверяем вычисленные шаги
        expected_ds = 0.1 * 2.0 * 3.0 / (2.0 + 3.0)  # h * C1 * C2 / (C1 + C2)
        expected_dt1 = expected_ds / 2.0
        expected_dt2 = expected_ds / 3.0
        
        self.assertAlmostEqual(disc.ds, expected_ds)
        self.assertAlmostEqual(disc.dt1, expected_dt1)
        self.assertAlmostEqual(disc.dt2, expected_dt2)
    
    def test_invalid_config(self):
        """Тест обработки невалидной конфигурации"""
        config = {'C': [2.0, 3.0]}  # нет ни 'm', ни 'h'
        
        with self.assertRaises(ValueError):
            Discretization(config, self.frame)
    
    def test_calculate_index_ranges(self):
        """Тест вычисления диапазонов индексов"""
        config = {'m': 10, 'C': [2.0, 3.0]}
        disc = Discretization(config, self.frame)
        
        i_range, j_range = disc.calculate_index_ranges()
        
        # Проверяем, что диапазоны вычислены корректно
        self.assertIsInstance(i_range, tuple)
        self.assertIsInstance(j_range, tuple)
        self.assertEqual(len(i_range), 2)
        self.assertEqual(len(j_range), 2)
        
        # Диапазоны должны быть симметричными относительно нуля
        self.assertEqual(i_range[0], -i_range[1])
        self.assertEqual(j_range[0], -j_range[1])

if __name__ == '__main__':
    unittest.main()