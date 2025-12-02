"""
Тесты для характеристической сетки.
Проверяет построение сетки, узлов и граничных условий.
"""
import unittest
import sys
import os

from cascadoc.blocks.distributed_blocks.dtype.characteristic_mesh import CharacteristicMesh

class TestCharacteristicMesh(unittest.TestCase):
    """Тесты для класса CharacteristicMesh"""
    
    def setUp(self):
        """Подготовка тестовой конфигурации"""
        self.config = {
            'S': [0.0, 10.0],
            'T': [0.0, 5.0],
            'C': [2.0, 3.0],
            'm': 20
        }
    
    def test_mesh_initialization(self):
        """Тест инициализации сетки"""
        mesh = CharacteristicMesh(self.config)
        
        # Проверяем основные атрибуты
        self.assertIsNotNone(mesh.frame)
        self.assertIsNotNone(mesh.center)
        self.assertIsInstance(mesh.ds, float)
        self.assertIsInstance(mesh.dt1, float)
        self.assertIsInstance(mesh.dt2, float)
        
        # Проверяем хранилища
        self.assertIsInstance(mesh.nodes, dict)
        self.assertIsInstance(mesh.positive_chars, dict)
        self.assertIsInstance(mesh.negative_chars, dict)
    
    def test_node_calculation(self):
        """Тест вычисления узлов сетки"""
        mesh = CharacteristicMesh(self.config)
        
        # Проверяем центральный узел
        center_node = mesh.get_node(0, 0)
        self.assertIsNotNone(center_node)
        self.assertEqual(center_node, mesh.center)
        
        # Проверяем, что все узлы внутри области
        for node in mesh.nodes.values():
            self.assertTrue(mesh.frame.contains(node[0], node[1]))
    
    def test_preceding_nodes(self):
        """Тест получения предшествующих узлов"""
        mesh = CharacteristicMesh(self.config)
        
        # Для центрального узла должны быть предшественники
        preceding = mesh.get_preceding_nodes(0, 0)
        
        self.assertIsInstance(preceding, dict)
        self.assertIn('left', preceding)
        self.assertIn('right', preceding)
        self.assertIn('center', preceding)
    
    def test_boundary_nodes(self):
        """Тест получения граничных узлов"""
        mesh = CharacteristicMesh(self.config)
        
        boundary_nodes = mesh.get_boundary_nodes()
        
        self.assertIsInstance(boundary_nodes, list)
        
        # Все граничные узлы должны быть на границах
        for node in boundary_nodes:
            s, t = node
            on_boundary = (s == mesh.frame.S0 or s == mesh.frame.S1 or 
                          t == mesh.frame.T0 or t == mesh.frame.T1)
            self.assertTrue(on_boundary, f"Node {node} not on boundary")
    
    def test_characteristics_generation(self):
        """Тест генерации характеристик"""
        mesh = CharacteristicMesh(self.config)
        
        # Должны быть созданы характеристики
        self.assertGreater(len(mesh.positive_chars), 0)
        self.assertGreater(len(mesh.negative_chars), 0)
        
        # Проверяем структуру характеристик
        for char in mesh.positive_chars.values():
            self.assertIsNotNone(char.internal_nodes)
        
        for char in mesh.negative_chars.values():
            self.assertIsNotNone(char.internal_nodes)
    
    def test_mesh_with_different_config(self):
        """Тест сетки с другой конфигурацией (шаг времени)"""
        config_h = {
            'S': [0.0, 10.0],
            'T': [0.0, 5.0],
            'C': [2.0, 3.0],
            'h': 0.1
        }
        
        mesh = CharacteristicMesh(config_h)
        
        # Должна успешно инициализироваться
        self.assertIsNotNone(mesh.frame)
        self.assertIsNotNone(mesh.ds)
        self.assertIsNotNone(mesh.dt1)
        self.assertIsNotNone(mesh.dt2)
        
        # Должны быть узлы
        self.assertGreater(len(mesh.nodes), 0)

if __name__ == '__main__':
    unittest.main()