from ..base_concentrated_block import BaseConcentratedBlock
from typing import List, Dict

ON_S = 0
ON_T = 1

class FunBlock(BaseConcentratedBlock):
    def __init__(self, name_block, type_block: int, fun: callable, mesh: Dict[int, float], other_coord: int):
        if  not type_block in  (ON_S, ON_T):
            raise Exception("НЕТ ТАКОГО ТИПА (либо ON_S = 0, ON_T = 1)") 
        self.type = type_block
        self.name_block = name_block
        self.mesh = mesh
        self.hash_mesh = {val:ind for ind, val in  mesh.items()}
        self.fun = fun
        self.rez = {ind:fun(val) for ind, val in mesh.items()}
        self.other_coord = other_coord


    def __call__(self, index = None, coord = None):
        if (index is None and coord is None) or (index is not None and coord is not None):
            raise Exception("НУЖНО УКАЗАТЬ ЛИБО ИНДЕКС УЗЛА, ЛИБО ЕГО КООРДИНАТУ")
        if index is not None:
            return self.rez[index]
        
        if not coord in self.hash_mesh:
            raise Exception("ИНТЕРПОЛЯЦИЯ ЕЩЕ НЕ ВСТРОЕНА")

        index = self.hash_mesh[coord] 
        return self.rez[index]
    
    def get_mesh(self):
        return [
            {
                "s": cord if self.type == ON_S else self.other_coord,
                "t": cord if self.type == ON_T else self.other_coord,
                "ind": ind,
                "x": self.rez[ind],
                "name_block": self.name_block
            } for ind, cord in self.mesh.items()
        ]

