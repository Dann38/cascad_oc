"""
Визуализация характеристических сеток.
Отделен от логики расчета для упрощения тестирования.
"""
import matplotlib.pyplot as plt
from typing import List, Tuple
from cascadoc.blocks.distributed_blocks.dtype.characteristic_mesh import CharacteristicMesh

def plot_characteristic_mesh(mesh: CharacteristicMesh, figsize=(12, 8), node_size=20):
    """Визуализирует характеристическую сетку"""
    plt.figure(figsize=figsize)
    _plot_characteristics(mesh, node_size)
    _plot_boundary_nodes(mesh, node_size)
    _plot_center_node(mesh, node_size)
    _setup_plot()

def _plot_characteristics(mesh: CharacteristicMesh, node_size: int):
    """Рисует характеристики"""
    for char in mesh.positive_chars.values():
        _plot_single_characteristic(char, 'r', node_size)
    for char in mesh.negative_chars.values():
        _plot_single_characteristic(char, 'b', node_size)

def _plot_single_characteristic(char, color: str, node_size: int):
    """Рисует одну характеристику"""
    left, right = char.get_boundary_nodes()
    if left and right:
        plt.plot([left[0], right[0]], [left[1], right[1]], 
                f'{color}-', alpha=0.6, linewidth=0.8)
    
    for node in char.internal_nodes.values():
        plt.scatter(node[0], node[1], c=color, s=node_size//2, alpha=0.5)

def _plot_boundary_nodes(mesh: CharacteristicMesh, node_size: int):
    """Рисует граничные узлы"""
    boundary_nodes = mesh.get_boundary_nodes()
    if boundary_nodes:
        x_bnd, y_bnd = zip(*boundary_nodes)
        plt.scatter(x_bnd, y_bnd, c='orange', s=node_size*2, 
                   marker='X', label='Граничные узлы', zorder=6)

def _plot_center_node(mesh: CharacteristicMesh, node_size: int):
    """Выделяет центральный узел"""
    center_node = mesh.get_node(0, 0)
    if center_node:
        plt.scatter([center_node[0]], [center_node[1]], 
                   c='yellow', s=node_size*3, edgecolors='black',
                   label='Центр (0,0)', zorder=7)

def _setup_plot():
    """Настраивает внешний вид графика"""
    plt.xlabel('S')
    plt.ylabel('T')
    plt.title('Характеристическая сетка')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.show()