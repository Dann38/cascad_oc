from .problem import HypProblem
import numpy as np
from typing import Tuple
import matplotlib.pyplot as plt
class Mesh:
    def __init__(self, problem: HypProblem, m: int = None, h: float = None) -> None:
        m_eps = 6
        eps = 0.1**m_eps
        
        self.C1 = problem.C1
        self.C2 = problem.C2
        self.S0 = problem.S0
        self.S1 = problem.S1
        self.T0 = problem.T0
        self.T1 = problem.T1

        Sc = (self.S1+self.S0)/2
        Tc = (self.T1+self.T0)/2

        if m:
            M = m*2
            DeltaS = (self.S1-self.S0)/M
            Delta1T = 1/self.C1*DeltaS 
            Delta2T = 1/self.C2*DeltaS
            DeltaT = Delta1T+Delta2T
        elif h: # Для запаздывания
            DeltaT = h
            DeltaS = DeltaT*self.C1*self.C2/(self.C1+self.C2)
            Delta1T = 1/self.C1*DeltaS 
            Delta2T = 1/self.C2*DeltaS
        self.dS = DeltaS
        self.d1T = Delta1T
        self.d2T = Delta2T
        
        self.__T_min_ij = (2*self.T0-(self.T1-self.T0))/(2*DeltaS)
        self.__T_max_ij = (2*self.T1-(self.T1-self.T0))/(2*DeltaS)
        self.__S_min_ij = (self.S0-Sc)/DeltaS
        self.__S_max_ij = (self.S1-Sc)/DeltaS


        min_j = int((self.__S_max_ij*self.C1+self.__T_max_ij)/(1/self.C1+1/self.C2))
        min_i = int(self.__S_max_ij+min_j) 



        self.__L = np.array([[DeltaS,   DeltaS], 
                    [-Delta1T, Delta2T]])
        self.__v = np.array([Sc, Tc])

        Ind = np.array([[[i, j] for j in range(-min_j, min_j+1)] for i in range(-min_i, min_i+1)])

        Ind_cord = np.array([[(self.__L@vec+self.__v).round(m_eps) for vec in row] for row in Ind])

        nodes_center = []
        nodes_start_l = []
        nodes_start_r = []
        nodes_final_l = []
        nodes_final_r = []

        for row_cord, row_ind in zip(Ind_cord, Ind):
            for vec, inds in zip(row_cord, row_ind) :
                if self.is_from_center(inds[0], inds[1]):
                    nodes_center.append([inds[0], inds[1], vec[0], vec[1]])
                    if vec[0] == self.S0:
                        if not self.is_from_center(inds[0]+1, inds[1]-1): 
                            nodes_start_l.append([inds[0], inds[1], self.S0, self.T0])
                        if not self.is_from_center(inds[0]+1, inds[1]):
                            si = vec[0] + (vec[1]-self.T0)*self.C1
                            nodes_start_r.append([inds[0], inds[1], si, self.T0])

                        if not self.is_from_center(inds[0], inds[1]+1):
                            si = vec[0] + (self.T1 - vec[1])*self.C2 
                            nodes_final_r.append([inds[0], inds[1], si, self.T1])
                        if not self.is_from_center(inds[0]-1, inds[1]+1):
                            nodes_final_l.append([inds[0], inds[1], self.S0, self.T1])
                    elif vec[0] == self.S1:
                        if not self.is_from_center(inds[0], inds[1]-1):
                            si = vec[0] - (vec[1]-self.T0)*self.C2 
                            nodes_start_l.append([inds[0], inds[1], si, self.T0])
                        if not self.is_from_center(inds[0]+1, inds[1]-1):
                            nodes_start_r.append([inds[0], inds[1], self.S1, self.T0])

                        if not self.is_from_center(inds[0]-1, inds[1]+1):
                            nodes_final_r.append([inds[0], inds[1], self.S1, self.T1])
                        if not self.is_from_center(inds[0]-1, inds[1]):
                            si = vec[0] - (self.T1 - vec[1])*self.C1
                            nodes_final_l.append([inds[0], inds[1], si, self.T1])
                    else:
                        if not self.is_from_center(inds[0], inds[1]-1):
                            si = vec[0] - (vec[1]-self.T0)*self.C2 
                            nodes_start_l.append([inds[0], inds[1], si, self.T0])
                        if not self.is_from_center(inds[0]+1, inds[1]):
                            si = vec[0] + (vec[1]-self.T0)*self.C1
                            nodes_start_r.append([inds[0], inds[1], si, self.T0])

                        if not self.is_from_center(inds[0], inds[1]+1):
                            si = vec[0] + (self.T1 - vec[1])*self.C2 
                            nodes_final_r.append([inds[0], inds[1], si, self.T1])
                        if not self.is_from_center(inds[0]-1, inds[1]):
                            si = vec[0] - (self.T1 - vec[1])*self.C1
                            nodes_final_l.append([inds[0], inds[1], si, self.T1])


        self.nodes_center = self.time_sort(nodes_center)
        self.nodes_center_dict = self.get_dict(self.nodes_center)

        self.nodes_start_l = self.time_sort(nodes_start_l)
        self.nodes_start_l_dict = self.get_dict(self.nodes_start_l)

        self.nodes_start_r = self.time_sort(nodes_start_r)
        self.nodes_start_r_dict = self.get_dict(self.nodes_start_r)

        self.nodes_final_l = self.time_sort(nodes_final_l)
        self.nodes_final_l_dict = self.get_dict(self.nodes_final_l)

        self.nodes_final_r = self.time_sort(nodes_final_r)
        self.nodes_final_r_dict = self.get_dict(self.nodes_final_r)


        self.rez_nodes_start_l = [[[None, None], [None, None, None]] for i in self.nodes_start_l]
        self.rez_nodes_start_r =  [[[None, None], [None, None, None]] for i in self.nodes_start_r]
        self.rez_nodes_center =  [[[None, None], [None, None, None]] for i in self.nodes_center]
        self.rez_nodes_final_l =  [[[None, None], [None, None, None]] for i in self.nodes_final_l]
        self.rez_nodes_final_r =  [[[None, None], [None, None, None]] for i in self.nodes_final_r]

    def time_sort(self, array):
        ar = np.array(array)
        indexs = [(self.__L @ a[:2]+self.__v)[1] for a in ar]
        index = np.argsort(indexs)
        return ar[index, :]

    def get_dict(self, array):
        nodes_dict = dict()
        
        for index, node in enumerate(array):
            i = int(node[0])
            j = int(node[1])
            if i in nodes_dict.keys():
                nodes_dict[i][j] = index
            else:
                nodes_dict[i] = {j: index}
        return nodes_dict
    
    def get_from_center(self, i, j):
        return self.nodes_center[self.nodes_center_dict[i][j]]

    # def is_from_center(self, i, j):
    #     return i in self.nodes_center_dict.keys() and j in self.nodes_center_dict[i].keys()
    
    def is_from_center(self, i, j):
        t_ind = 1/self.C2*j-1/self.C1*i
        s_ind = i+j
        return (self.__T_min_ij <= t_ind) and (self.__T_max_ij >= t_ind) and \
               (self.__S_min_ij <= s_ind) and (self.__S_max_ij >= s_ind)
    
    def get_center_node(self, i, j):
        node_index = self.nodes_center_dict[i][j]
        node = self.nodes_center[node_index]
        node_rez = self.rez_nodes_center[node_index]
        return node, node_rez
    
    def get_center_node_stxy(self, i, j):
        node, node_rez = self.get_center_node(i, j)
        s, t = node[2], node[3]
        x, y = node_rez[0][0], node_rez[0][1]
        return s, t, x, y

    def get_left_node(self, i, j):
        node_l_index = self.nodes_final_l_dict[i][j]
        node_l = self.nodes_final_l[node_l_index]
        node_l_rez = self.rez_nodes_final_l[node_l_index]
        return node_l, node_l_rez

    def get_left_node_stxy(self, i, j):
        node, node_rez = self.get_left_node(i, j)
        s, t = node[2], node[3]
        x, y = node_rez[0][0], node_rez[0][1]
        return s, t, x, y

    def get_right_node(self, i, j):
        node_r_index = self.nodes_final_r_dict[i][j]
        node_r = self.nodes_final_r[node_r_index]
        node_r_rez = self.rez_nodes_final_r[node_r_index]
        return node_r, node_r_rez
    
    def get_right_node_stxy(self, i, j):
        node, node_rez = self.get_right_node(i, j)
        s, t = node[2], node[3]
        x, y = node_rez[0][0], node_rez[0][1]
        return s, t, x, y

    def get_center_node_left(self, i, j):
        if self.is_from_center(i ,j-1):
            node_l_index = self.nodes_center_dict[i][j-1]
            node_l = self.nodes_center[node_l_index]
            node_l_rez = self.rez_nodes_center[node_l_index]
        else:
            node_l_index = self.nodes_start_l_dict[i][j]
            node_l = self.nodes_start_l[node_l_index]
            node_l_rez = self.rez_nodes_start_l[node_l_index]

        return node_l, node_l_rez
    
    def get_center_node_left_stxy(self, i, j):
        node, node_rez = self.get_center_node_left( i, j)
        s, t = node[2], node[3]
        x, y = node_rez[0][0], node_rez[0][1]
        return s, t, x, y


    def get_center_node_right(self, i, j):
        if self.is_from_center(i+1 ,j):
            node_r_index = self.nodes_center_dict[i+1][j]
            node_r = self.nodes_center[node_r_index]
            node_r_rez = self.rez_nodes_center[node_r_index]
        else:
            node_r_index = self.nodes_start_r_dict[i][j]
            node_r = self.nodes_start_r[node_r_index]
            node_r_rez = self.rez_nodes_start_r[node_r_index]

        return node_r, node_r_rez
    
    def get_center_node_right_stxy(self, i, j):
        node, node_rez = self.get_center_node_right( i, j)
        s, t = node[2], node[3]
        x, y = node_rez[0][0], node_rez[0][1]
        return s, t, x, y

    def get_s0_node_left(self, i, j):
        if self.is_from_center(i+1 ,j-1):
            node_l_index = self.nodes_center_dict[i+1][j-1]
            node_l = self.nodes_center[node_l_index]
            node_l_rez = self.rez_nodes_center[node_l_index]
        else:
            node_l_index = self.nodes_start_l_dict[i][j]
            node_l = self.nodes_start_l[node_l_index]
            node_l_rez = self.rez_nodes_start_l[node_l_index]

        return node_l, node_l_rez
    
    def get_s0_node_left_stxy(self, i, j):
        node, node_rez = self.get_s0_node_left( i, j)
        s, t = node[2], node[3]
        x, y = node_rez[0][0], node_rez[0][1]
        return s, t, x, y
    
    def get_s1_node_right(self, i, j):
        if self.is_from_center(i+1 ,j-1):
            node_r_index = self.nodes_center_dict[i+1][j-1]
            node_r = self.nodes_center[node_r_index]
            node_r_rez = self.rez_nodes_center[node_r_index]
        else:
            node_r_index = self.nodes_start_r_dict[i][j]
            node_r = self.nodes_start_r[node_r_index]
            node_r_rez = self.rez_nodes_start_r[node_r_index]

        return node_r, node_r_rez
    
    def get_s1_node_right_stxy(self, i, j):
        node, node_rez = self.get_s1_node_right( i, j)
        s, t = node[2], node[3]
        x, y = node_rez[0][0], node_rez[0][1]
        return s, t, x, y

    def get_stxy_c_3node(self, s1:float, t1:float, x1:float, y1:float, 
                               s2:float, t2:float, x2:float, y2:float, 
                               s3:float, t3:float, c:float) -> Tuple[float, float, float, float]:
        if t1==t2:
            if t3==t2:
                return s1, t1, x1, y1
            else:
                raise ValueError
        if t1 > t2:
            raise ValueError
        
        c12 = (s1-s2)/(t1-t2)  
        t = 1/(c12-c)*(c12*t1-c*t3 + s3 - s1)
        dt = t-t1
        alpha = dt/(t2-t1)
        s = s1 + alpha*(s2-s1)
        x = x1 + alpha*(x2-x1)
        y = y1 + alpha*(y2-y1)

        return s, t, x, y
    

    # PSI =============================================================
    def get_center_conj_node_stxy(self, i, j):
        node, node_rez = self.get_center_node(i, j)
        s, t = node[2], node[3]
        psi1, psi2, p = node_rez[1][0], node_rez[1][1], node_rez[1][2]
        return s, t, psi1, psi2, p

    def get_final_l_conj_node_stxy(self, i, j):
        node_l_index = self.nodes_final_l_dict[i][j]
        node = self.nodes_final_l[node_l_index]
        node_rez = self.rez_nodes_final_l[node_l_index]
        s, t = node[2], node[3]
        psi1, psi2, p1 = node_rez[1][0], node_rez[1][1], node_rez[1][2]
        return s, t, psi1, psi2, p1

    def get_final_r_conj_node_stxy(self, i, j):
        node_r_index = self.nodes_final_r_dict[i][j]
        node = self.nodes_final_r[node_r_index]
        node_rez = self.rez_nodes_final_r[node_r_index]
        s, t = node[2], node[3]
        psi1, psi2, p2 = node_rez[1][0], node_rez[1][1], node_rez[1][2]
        return s, t, psi1, psi2, p2

    def get_center_node_conj_left_stxy(self, i, j):
        if self.is_from_center(i-1 ,j):
            return self.get_center_conj_node_stxy(i-1 ,j)
        else:
            return self.get_final_l_conj_node_stxy(i, j)

    def get_center_node_conj_right_stxy(self, i, j):
        if self.is_from_center(i ,j+1):
            return self.get_center_conj_node_stxy(i ,j+1)
        else:
            return self.get_final_r_conj_node_stxy(i, j)
    
    def get_s0_node_conj_left_stxy(self, i, j):
        if self.is_from_center(i-1 ,j+1):
            return self.get_center_conj_node_stxy(i-1 ,j+1)
        else:
            return self.get_final_l_conj_node_stxy(i, j)

    def get_s1_node_conj_right_stxy(self, i, j):
        if self.is_from_center(i-1 ,j+1):
            return self.get_center_conj_node_stxy(i-1 ,j+1)
        else:
            return self.get_final_r_conj_node_stxy(i, j)
        
    def get_right_conj_node_stxy(self, i, j):
        node_r_index = self.nodes_start_r_dict[i][j]
        node = self.nodes_start_r[node_r_index]
        node_rez = self.rez_nodes_start_r[node_r_index]
        s, t = node[2], node[3]
        psi1, psi2, p = node_rez[1][0], node_rez[1][1], node_rez[1][2]
        return s, t, psi1, psi2, p

    def get_left_conj_node_stxy(self, i, j):
        node_l_index = self.nodes_start_l_dict[i][j]
        node = self.nodes_start_l[node_l_index]
        node_rez = self.rez_nodes_start_l[node_l_index]
        s, t = node[2], node[3]
        psi1, psi2, p = node_rez[1][0], node_rez[1][1], node_rez[1][2]
        return s, t, psi1, psi2, p
    

    def get_border(self, type_border='start', sort_t=False, sort_s=False):
        """
        0.0-i
        0.1-j
        0.2-s
        0.3-t
        
        0.0-x
        0.1-y
        1.0-psi1
        1.1-psi2
        1.2-p1|p2

        TODO: CONST 
        NODE_I = [0, 0], 
        NODE_J = [0, 1],
        NODE_S = [0, 2],
        NODE_T = [0, 3],
        ...
        """
        
        nodes = []

        if type_border in ('left', 'right'): 
            type_ = self.S0 if type_border == "left" else self.S1
            t_h = []
            for r, n in zip(self.rez_nodes_start_l+self.rez_nodes_start_r+\
                        self.rez_nodes_center+\
                        self.rez_nodes_final_l+self.rez_nodes_final_r, 
                        self.nodes_start_l.tolist() + self.nodes_start_r.tolist() +\
                        self.nodes_center.tolist() + \
                        self.nodes_final_l.tolist()+self.nodes_final_r.tolist()):
                if n[2] == type_:
                    t_h.append(n[3])
                    nodes.append((n, r))
                    
        elif type_border == "final":
            for n, r in zip(self.nodes_final_l.tolist()+self.nodes_final_r.tolist(), 
                         self.rez_nodes_final_l+self.rez_nodes_final_r):
                nodes.append((n, r))
        elif type_border == "start":
            for n, r in zip(self.nodes_start_l.tolist()+self.nodes_start_r.tolist(), 
                         self.rez_nodes_start_l+self.rez_nodes_start_r):
                nodes.append((n, r))

        if sort_s:
            s_ = [node[0][2] for node in nodes]
            indexs = np.argsort(s_)
            nodes = [nodes[i] for i in indexs]
        
        if sort_t:
            t_ = [node[0][3] for node in nodes]
            indexs = np.argsort(t_)
            nodes = [nodes[i] for i in indexs]

        return nodes
    
# PLOT MESH ====================================================
    def plot_border(self, border_type, fun, style, fun_name=None):
        is_t = border_type in ('left', 'right')
        is_s = border_type in ('final', 'start')
        nodes = self.get_border(type_border=border_type, sort_s=is_s, sort_t=is_t)
        if is_t:
            arg = [node[0][3] for node in nodes]
            arg_name = 't'
        elif is_s:
            arg = [node[0][2] for node in nodes]
            arg_name = 's'
        
        if type(fun) != str:
            f = fun(np.array(arg))
            ylabel = "function"
        elif fun == "x":
            f = [node[1][0][0] for node in nodes]
            ylabel = "x"
        elif fun == "y":
            f = [node[1][0][1] for node in nodes]
            ylabel = "y"
       
        if fun_name is None:
            fun_name = ylabel

        plt.plot(arg, f, style, label=fun_name)
        plt.ylabel(ylabel)
        plt.xlabel(arg_name)
        plt.grid()
        plt.legend()

    def plot_mesh(self):
        for node in self.nodes_center:
            i = int(node[0])
            j = int(node[1])
            s = node[2]
            t = node[3]
            if self.is_from_center(i, j-1):
                s_, t_, _, _ = self.get_center_node_stxy(i, j-1)
                plt.plot([s,s_], [t, t_], "g" )
            if self.is_from_center(i+1, j):
                s_, t_, _, _ = self.get_center_node_stxy(i+1, j)
                plt.plot([s,s_], [t, t_], "g")
            plt.scatter(x=s, y=t, color="b")

        for node in self.nodes_final_l:
            i = int(node[0])
            j = int(node[1])
            s = node[2]
            t = node[3]
            
            s_, t_, _, _ = self.get_center_node_stxy(i, j)
            plt.plot([s,s_], [t, t_], "g")
            plt.scatter(s, t, color="r", marker=".")

        for node in self.nodes_final_r:
            i = int(node[0])
            j = int(node[1])
            s = node[2]
            t = node[3]
            
            s_, t_, _, _ = self.get_center_node_stxy(i, j)
            plt.plot([s,s_], [t, t_], "g")
            plt.scatter(node[2], node[3], color="r", marker=".")
            
        for node in self.nodes_start_l:
            i = int(node[0])
            j = int(node[1])
            s = node[2]
            t = node[3]
            node, _ = self.get_center_node(i, j)
            plt.plot([s,node[2]], [t, node[3]], "g")
            plt.scatter(s, t, color="r", marker=".")

        for node in self.nodes_start_r:
            i = int(node[0])
            j = int(node[1])
            s = node[2]
            t = node[3]
            node, _ = self.get_center_node(i, j)
            plt.plot([s,node[2]], [t, node[3]], "g")
            plt.scatter(s, t, color="r", marker=".")


        plt.plot([self.S0, self.S1], [self.T0, self.T0], "r")
        plt.plot([self.S0, self.S1], [self.T1, self.T1], "r")
        plt.plot([self.S0, self.S0], [self.T0, self.T1], "r")
        plt.plot([self.S1, self.S1], [self.T0, self.T1], "r")


        plt.xlabel("s")
        plt.ylabel("t")
        # plt.savefig("mesh",format="eps")