from ..base_distributed_block import BaseDistibutedBlock
from typing import List, Dict
from .dtype import CharacteristicMesh

class HypBlock(BaseDistibutedBlock):
    def __init__(self,name_block, S0, S1, T0, T1, C1, C2, h, m):
        if (h is not None and m is not None) or (h is None and m is None):
            raise Exception("УКАЖИТЕ ЛИБО h ЛИБО m")
         
        config = {"S": [S0, S1], "T": [T0, T1], "C": [C1, C2]}
        if h:
            config["h"] = h
        else:
            config["m"] = m
        self.name_block = name_block
        self.mesher = CharacteristicMesh(config)
        # self.hash_mesh = {val:ind for ind, val in  mesh.items()}
        # self.fun = fun
        self.rez = dict()
        # self.other_coord = other_coord


    def add_index_val(self, index, val):
        self.rez[index] = val


    def __call__(self, index = None, coord = None):
        if (index is None and coord is None) or (index is not None and coord is not None):
            raise Exception("НУЖНО УКАЗАТЬ ЛИБО ИНДЕКС УЗЛА, ЛИБО ЕГО КООРДИНАТУ")
        if index is not None:
            return self.mesher.get_node(*index)
        
        i, j = self.mesher.get_indexes(*coord)
        return i, j
    
    def get_mesh(self):
        return [
            {
                "s": cord[0],
                "t": cord[1],
                "ind": ind,
                "x": self.rez[ind] if ind in self.rez else [None, None],
                "name_block": self.name_block
            } for ind, cord in self.mesher.nodes.items()
        ] + [
            {
                "s": cord[0],
                "t": cord[1],
                "ind": self.mesher.get_indexes(*cord),
                "x": self.rez[self.mesher.get_indexes(*cord)] if self.mesher.get_indexes(*cord) in self.rez else [None, None],
                "name_block": self.name_block
            } for  cord in self.mesher.get_boundary_nodes()
        ]

