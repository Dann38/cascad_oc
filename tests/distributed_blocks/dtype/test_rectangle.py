"""
Тесты для прямоугольной области расчета.
Проверяет границы, центр и проверку содержания точек.
"""
import unittest
import sys
import os


from cascadoc.blocks.distributed_blocks.dtype.rectangle import Rectangle

class TestRectangle(unittest.TestCase):
    """Тесты для класса Rectangle"""
    
    def setUp(self):
        """Подготовка тестового прямоугольника"""
        self.rect = Rectangle(S0=0.0, S1=10.0, T0=0.0, T1=5.0)
    
    def test_center_calculation(self):
        """Тест вычисления центра"""
        center = self.rect.center
        self.assertEqual(center, (5.0, 2.5))
    
    def test_contains_inside_point(self):
        """Тест проверки точки внутри области"""
        self.assertTrue(self.rect.contains(5.0, 2.5))
        self.assertTrue(self.rect.contains(1.0, 1.0))
        self.assertTrue(self.rect.contains(9.0, 4.0))
    
    def test_contains_boundary_points(self):
        """Тест проверки точек на границе"""
        self.assertTrue(self.rect.contains(0.0, 2.5))  # левая граница
        self.assertTrue(self.rect.contains(10.0, 2.5)) # правая граница
        self.assertTrue(self.rect.contains(5.0, 0.0))  # нижняя граница
        self.assertTrue(self.rect.contains(5.0, 5.0))  # верхняя граница
    
    def test_contains_outside_points(self):
        """Тест проверки точек вне области"""
        self.assertFalse(self.rect.contains(-1.0, 2.5))  # слева
        self.assertFalse(self.rect.contains(11.0, 2.5))  # справа
        self.assertFalse(self.rect.contains(5.0, -1.0))  # снизу
        self.assertFalse(self.rect.contains(5.0, 6.0))   # сверху
    
    def test_contains_corner_cases(self):
        """Тест угловых случаев"""
        self.assertTrue(self.rect.contains(0.0, 0.0))   # нижний левый угол
        self.assertTrue(self.rect.contains(10.0, 5.0))  # верхний правый угол

if __name__ == '__main__':
    unittest.main()