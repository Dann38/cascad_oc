"""
Тесты для характеристик гиперболических уравнений.
Проверяет построение характеристик и узлов.
"""
import unittest
import sys
import os

from cascadoc.blocks.distributed_blocks.dtype.rectangle import Rectangle
from cascadoc.blocks.distributed_blocks.dtype.characteristic import Characteristic

class TestCharacteristic(unittest.TestCase):
    """Тесты для класса Characteristic"""
    
    def setUp(self):
        """Подготовка тестовой области и характеристик"""
        self.frame = Rectangle(S0=0.0, S1=10.0, T0=0.0, T1=5.0)
    
    def test_vertical_characteristic(self):
        """Тест вертикальной характеристики (dt=0)"""
        center = (5.0, 2.5)
        char = Characteristic(center, dt=0.0, step=1.0, frame=self.frame)
        
        # Должна пересекать левую и правую границы
        left_node, right_node = char.get_boundary_nodes()
        
        self.assertIsNotNone(left_node)
        self.assertIsNotNone(right_node)
        self.assertEqual(left_node[0], 0.0)  # левая граница
        self.assertEqual(right_node[0], 10.0) # правая граница
        self.assertEqual(left_node[1], 2.5)   # время не меняется
        self.assertEqual(right_node[1], 2.5)
    
    def test_horizontal_characteristic(self):
        """Тест горизонтальной характеристики (step=0)"""
        center = (5.0, 2.5)
        char = Characteristic(center, dt=1.0, step=0.0, frame=self.frame)
        
        # Должна пересекать нижнюю и верхнюю границы
        left_node, right_node = char.get_boundary_nodes()
        
        self.assertIsNotNone(left_node)
        self.assertIsNotNone(right_node)
        self.assertEqual(left_node[1], 0.0)  # нижняя граница
        self.assertEqual(right_node[1], 5.0) # верхняя граница
        self.assertEqual(left_node[0], 5.0)  # пространство не меняется
        self.assertEqual(right_node[0], 5.0)
    
    def test_diagonal_characteristic(self):
        """Тест диагональной характеристики"""
        center = (5.0, 2.5)
        char = Characteristic(center, dt=1.0, step=1.0, frame=self.frame)
        
        # Должна пересекать границы области
        left_node, right_node = char.get_boundary_nodes()
        
        self.assertIsNotNone(left_node)
        self.assertIsNotNone(right_node)
        
        # Проверяем, что точки на границах
        self.assertTrue(self.frame.contains(left_node[0], left_node[1]))
        self.assertTrue(self.frame.contains(right_node[0], right_node[1]))
    
    def test_internal_nodes_generation(self):
        """Тест генерации внутренних узлов"""
        center = (5.0, 2.5)
        char = Characteristic(center, dt=1.0, step=1.0, frame=self.frame)
        
        # Должны быть сгенерированы внутренние узлы
        self.assertGreater(len(char.internal_nodes), 0)
        
        # Все узлы должны быть внутри области
        for node in char.internal_nodes.values():
            self.assertTrue(self.frame.contains(node[0], node[1]))
    
    def test_get_node_method(self):
        """Тест метода получения узла по индексу"""
        center = (5.0, 2.5)
        char = Characteristic(center, dt=1.0, step=1.0, frame=self.frame)
        
        # Проверяем существующий узел
        if char.internal_nodes:
            test_index = list(char.internal_nodes.keys())[0]
            node = char.get_node(test_index)
            self.assertIsNotNone(node)
            self.assertEqual(node, char.internal_nodes[test_index])
        
        # Проверяем несуществующий узел
        non_existent_index = 9999
        node = char.get_node(non_existent_index)
        self.assertIsNone(node)
    
    def test_characteristic_outside_frame(self):
        """Тест характеристики, не пересекающей область"""
        center = (10.0, 16.0)  # вне области
        char = Characteristic(center, dt=1.0, step=1.0, frame=self.frame)
        
        # Не должно быть граничных узлов и внутренних узлов
        left_node, right_node = char.get_boundary_nodes()
        self.assertIsNone(left_node)
        self.assertIsNone(right_node)
        self.assertEqual(len(char.internal_nodes), 0)

if __name__ == '__main__':
    unittest.main()