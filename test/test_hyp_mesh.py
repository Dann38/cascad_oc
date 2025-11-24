from unittest import TestCase
from cascadoc import HypBlock
import numpy as np
class Test(TestCase):
    def test_hyp_mesh(self):
        block = HypBlock({'C':[1.001, 1.999], 'S': [0, 1], 'T': [0, 0.5], 'm':3})
        block.build_mesh()
        indexes_true = [
            (-1, -1),
            (-1, 0),
            (-1, 1),
            (0, -2),
            (0, -1),
            (0, 0),
            (0, 1),
            (0, 2),
            (1, -1),
            (1, 0),
            (1, 1)
        ]
        coords = block.mesh.center_nodes

        r = sum(np.concat([np.array(coords)[:, 0]<1.0, np.array(coords)[:, 0]>0.0, np.array(coords)[:, 1]<0.5, np.array(coords)[:, 1]>0.0]))
        self.assertEqual(len(indexes_true), len(coords), 'count coords')
        self.assertEqual(int(r), 4*len(coords), 'node is not in block')

