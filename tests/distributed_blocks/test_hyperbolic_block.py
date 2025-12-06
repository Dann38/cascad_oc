"""
Тесты для гиперболического блока.
Проверяет решение простых гиперболических систем.
"""
import unittest
import numpy as np
from cascadoc_deepseek.blocks.distributed_blocks.hyperbolic_block import HyperbolicBlock

class TestHyperbolicBlock(unittest.TestCase):
    """Тесты для HyperbolicBlock"""
    
    def test_initialization(self):
        """Тест инициализации гиперболического блока"""
        config = {
            'S': [0.0, 10.0],
            'T': [0.0, 5.0],
            'C': [1.0, 2.0],
            'm': 20
        }
        
        block = HyperbolicBlock("test_hyperbolic", config)
        self.assertEqual(block.name, "test_hyperbolic")
        self.assertEqual(block.c1, 1.0)
        self.assertEqual(block.c2, 2.0)
    
    def test_simple_transport(self):
        """Тест простого уравнения переноса"""
        config = {
            'S': [0.0, 5.0],
            'T': [0.0, 2.0],
            'C': [1.0, 0.0],  # только перенос вправо
            'm': 10,
            'B11': lambda s, t: 0.0,  # нет затухания
            'initial_x': lambda s: np.exp(-(s-2.5)**2),  # гауссов профиль
            'initial_y': lambda s: 0.0
        }
        
        block = HyperbolicBlock("transport", config)
        block.initialize({'initial_condition': config['initial_x']})
        
        # Проверяем, что сетка построена
        self.assertIsNotNone(block.mesh)
        self.assertGreater(len(block.mesh.nodes), 0)
    
    def test_boundary_conditions(self):
        """Тест граничных условий"""
        def left_bc(t):
            return np.sin(t)  # колебания на левой границе
            
        config = {
            'S': [0.0, 5.0],
            'T': [0.0, 2.0], 
            'C': [1.0, 1.0],
            'm': 10,
            'left_boundary': left_bc
        }
        
        block = HyperbolicBlock("bc_test", config)
        block.build_mesh()
        
        # Проверяем, что граничное условие установлено
        self.assertIsNotNone(block.left_boundary)
        self.assertEqual(block.left_boundary(0.5), np.sin(0.5))
    
    def test_mesh_building(self):
        """Тест построения сетки"""
        config = {
            'S': [0.0, 1.0],
            'T': [0.0, 1.0],
            'C': [1.0, 1.0],
            'm': 4
        }
        
        block = HyperbolicBlock("mesh_test", config)
        block.build_mesh()
        
        self.assertIsNotNone(block.mesh)
        self.assertGreater(len(block.mesh.nodes), 0)
        self.assertGreater(len(block.mesh.positive_chars), 0)
        self.assertGreater(len(block.mesh.negative_chars), 0)

if __name__ == '__main__':
    unittest.main()