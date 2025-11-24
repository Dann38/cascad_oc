from ..base_block import BaseBlock
from .dtype import CharacteristicMesh
import matplotlib.pyplot as plt
import numpy as np


class HypBlock(BaseBlock):
    def __init__(self, config):
        super().__init__(config)
        pass

    def build_mesh(self):
        self.mesh = CharacteristicMesh(self.config)
        

    def plot_mesh(self):
        self.mesh.plot()
        self.plot_border()
        # Настройки графика
        plt.xlabel('S (пространство)')
        plt.ylabel('T (время)')
        plt.title('Характеристическая сетка с граничными узлами\n'
                    'Красные - положительные характеристики, Синие - отрицательные\n'
                    'Оранжевые X - крайние узлы на границах')
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.tight_layout()

    def plot_border(self):
        S, T = self.config['S'], self.config['T']

        s = [S[0], S[1], S[1], S[0], S[0]]
        t = [T[0], T[0], T[1], T[1], T[0]]
        plt.plot(s, t, 'r-')

    def one_time_step(self, dt):
        pass
