from typing import Tuple
from .problem import HypProblem
import numpy as np
from .mesh import Mesh

class Solver:
    def solve_initial(self, mesh: Mesh, problem: HypProblem):
        for node in mesh.nodes_start_l:
            i, j, s, t = node[0], node[1], node[2], node[3]
            node_index = mesh.nodes_start_l_dict[i][j]
            mesh.rez_nodes_start_l[node_index][0][0]=problem.x0(s) 
            mesh.rez_nodes_start_l[node_index][0][1]=problem.y0(s)
            
        for node in mesh.nodes_start_r:
            i, j, s, t = node[0], node[1], node[2], node[3]
            node_index = mesh.nodes_start_r_dict[i][j]
            mesh.rez_nodes_start_r[node_index][0][0]=problem.x0(s) 
            mesh.rez_nodes_start_r[node_index][0][1]=problem.y0(s)


    def solver_initial_conj(self, mesh: Mesh, problem: HypProblem):
        for node in mesh.nodes_final_r:
            i, j, s, t = node[0], node[1], node[2], node[3]
            node_index = mesh.nodes_final_r_dict[i][j]
            x = mesh.rez_nodes_final_r[node_index][0][0]
            y = mesh.rez_nodes_final_r[node_index][0][1]

            mesh.rez_nodes_final_r[node_index][1][0]=-problem.phi_dx(s, x, y)
            mesh.rez_nodes_final_r[node_index][1][1]=-problem.phi_dy(s, x, y)
            if s==problem.S0:
                mesh.rez_nodes_final_r[node_index][1][2]=0
            elif s==problem.S1:
                mesh.rez_nodes_final_r[node_index][1][2]=0

        for node in mesh.nodes_final_l:
            i, j, s, t = node[0], node[1], node[2], node[3]
            node_index = mesh.nodes_final_l_dict[i][j]
            x = mesh.rez_nodes_final_l[node_index][0][0]
            y = mesh.rez_nodes_final_l[node_index][0][1]


            mesh.rez_nodes_final_l[node_index][1][0]=-problem.phi_dx(s, x, y) 
            mesh.rez_nodes_final_l[node_index][1][1]=-problem.phi_dy(s, x, y)
            if s==problem.S0:
                mesh.rez_nodes_final_l[node_index][1][2]=0
            elif s==problem.S1:
                mesh.rez_nodes_final_l[node_index][1][2]=0

    def solver_center(self, mesh: Mesh, hyp_problem):
        for node in mesh.nodes_center:
            i, j, s, t = node[0], node[1], node[2], node[3]

            if s==hyp_problem.S0:
                sl, tl, xl, yl = mesh.get_s0_node_left_stxy(i, j)
                sr, tr, xr, yr = mesh.get_center_node_right_stxy(i, j) 
            elif s==hyp_problem.S1:
                sl, tl, xl, yl = mesh.get_center_node_left_stxy(i, j)
                sr, tr, xr, yr = mesh.get_s1_node_right_stxy(i, j)
            else:
                sl, tl, xl, yl = mesh.get_center_node_left_stxy(i, j)
                sr, tr, xr, yr = mesh.get_center_node_right_stxy(i, j)   
            
            if s == hyp_problem.S0:
                x, y = self.left_solve(hyp_problem, s=s, t=t,
                                    sl=sl, tl=tl, xl=xl, yl=yl, hl=t-tl, 
                                    sr=sr, tr=tr, xr=xr, yr=yr, hr=t-tr)
            elif s == hyp_problem.S1:
                x, y = self.right_solve(hyp_problem, s=s, t=t,
                                    sl=sl, tl=tl, xl=xl, yl=yl, hl=t-tl, 
                                    sr=sr, tr=tr, xr=xr, yr=yr, hr=t-tr)
            else:
                x, y = self.center_solve(hyp_problem, s=s, t=t,
                                    sl=sl, tl=tl, xl=xl, yl=yl, hl=t-tl, 
                                    sr=sr, tr=tr, xr=xr, yr=yr, hr=t-tr)
            
            node_index = mesh.nodes_center_dict[i][j]
            mesh.rez_nodes_center[node_index][0][0]=x
            mesh.rez_nodes_center[node_index][0][1]=y  

    def solver_center_conj(self, mesh: Mesh, hyp_problem):
        
        for node in reversed(mesh.nodes_center):
            i, j, s, t = node[0], node[1], node[2], node[3]
            
            if s==hyp_problem.S0:
                sl, tl, psi1l, psi2l, p2l = mesh.get_s0_node_conj_left_stxy(i, j)
                sr, tr, psi1r, psi2r, _ = mesh.get_center_node_conj_right_stxy(i, j) 
            elif s==hyp_problem.S1:
                sl, tl, psi1l, psi2l, _ = mesh.get_center_node_conj_left_stxy(i, j)
                sr, tr, psi1r, psi2r, p1r = mesh.get_s1_node_conj_right_stxy(i, j)
            else:
                sl, tl, psi1l, psi2l, _  = mesh.get_center_node_conj_left_stxy(i, j)
                sr, tr, psi1r, psi2r, _  = mesh.get_center_node_conj_right_stxy(i, j)   
            
            node_index = mesh.nodes_center_dict[i][j]
            if s == hyp_problem.S0:
                psi1, psi2, p2 = self.left_conj_solve(hyp_problem, s=s, t=t,
                                    sl=sl, tl=tl, psi1l=psi1l, psi2l=psi2l, p2l=p2l, hl=t-tl, 
                                    sr=sr, tr=tr, psi1r=psi1r, psi2r=psi2r, hr=t-tr)
                
                mesh.rez_nodes_center[node_index][1][2]=p2
            elif s == hyp_problem.S1:
                psi1, psi2, p1 = self.right_conj_solve(hyp_problem, s=s, t=t,
                                    sl=sl, tl=tl, psi1l=psi1l, psi2l=psi2l, hl=t-tl, 
                                    sr=sr, tr=tr, psi1r=psi1r, psi2r=psi2r, p1r=p1r, hr=t-tr)

                mesh.rez_nodes_center[node_index][1][2]=p1
            else:
                psi1, psi2 = self.center_conj_solve(hyp_problem, s=s, t=t,
                                    sl=sl, tl=tl, psi1l=psi1l, psi2l=psi2l, hl=t-tl, 
                                    sr=sr, tr=tr, psi1r=psi1r, psi2r=psi2r, hr=t-tr)
            
            mesh.rez_nodes_center[node_index][1][0]=psi1
            mesh.rez_nodes_center[node_index][1][1]=psi2   
             

    def solver_final(self, mesh: Mesh, hyp_problem):
        final_r_nodes = []
        for node in mesh.nodes_final_r:
            i, j, s, t = node[0], node[1], node[2], node[3]
            
            if s == hyp_problem.S1:
                sr, tr, xr, yr = mesh.get_center_node_stxy(i, j)
                if mesh.is_from_center(i-1, j):
                    s2, t2, x2, y2 = mesh.get_center_node_stxy(i-1, j)
                    sl, tl, xl, yl = mesh.get_stxy_c_3node(sr, tr, xr, yr, s2, t2, x2, y2, s, t, hyp_problem.C2)
                    x, y = self.right_solve(hyp_problem, s=s, t=t,
                                sl=sl, tl=tl, xl=xl, yl=yl, hl=t-tl, 
                                sr=sr, tr=tr, xr=xr, yr=yr, hr=t-tr)
                    node_index = mesh.nodes_final_r_dict[i][j]
                    mesh.rez_nodes_final_r[node_index][0][0]=x
                    mesh.rez_nodes_final_r[node_index][0][1]=y 
                else:
                    final_r_nodes.append([i, j, sr, tr, xr, yr])
                continue
            sl, tl, xl, yl = mesh.get_center_node_stxy(i, j)
            s1, t1, x1, y1 = mesh.get_center_node_stxy(i+1, j)
            s2, t2, x2, y2 =mesh.get_center_node_stxy(i+1, j+1) if mesh.is_from_center(i+1, j+1) else mesh.get_right_node_stxy(i+1, j)
            sr, tr, xr, yr = mesh.get_stxy_c_3node(s1, t1, x1, y1, s2, t2, x2, y2,s, t, -hyp_problem.C1)
            x, y = self.center_solve(hyp_problem, s=s, t=t,
                                sl=sl, tl=tl, xl=xl, yl=yl, hl=t-tl, 
                                sr=sr, tr=tr, xr=xr, yr=yr, hr=t-tr)
            
            node_index = mesh.nodes_final_r_dict[i][j]
            mesh.rez_nodes_final_r[node_index][0][0]=x
            mesh.rez_nodes_final_r[node_index][0][1]=y 

        for node in mesh.nodes_final_l:
            i, j, s, t = node[0], node[1], node[2], node[3]
            
            if s == hyp_problem.S0:
                sl, tl, xl, yl = mesh.get_center_node_stxy(i, j)
                s2, t2, x2, y2 = mesh.get_center_node_stxy(i, j+1) if mesh.is_from_center(i, j+1) else mesh.get_right_node_stxy(i, j)
                sr, tr, xr, yr = mesh.get_stxy_c_3node(sl, tl, xl, yl, s2, t2, x2, y2, s, t, -hyp_problem.C1)
                x, y = self.left_solve(hyp_problem, s=s, t=t,
                                sl=sl, tl=tl, xl=xl, yl=yl, hl=t-tl, 
                                sr=sr, tr=tr, xr=xr, yr=yr, hr=t-tr)
                node_index = mesh.nodes_final_l_dict[i][j]
                mesh.rez_nodes_final_l[node_index][0][0]=x
                mesh.rez_nodes_final_l[node_index][0][1]=y 
                continue
            sr, tr, xr, yr = mesh.get_center_node_stxy(i, j)
            s1, t1, x1, y1 = mesh.get_center_node_stxy(i, j-1)
            s2, t2, x2, y2 =mesh.get_center_node_stxy(i-1, j-1) if mesh.is_from_center(i-1, j-1) else mesh.get_left_node_stxy(i, j-1)
            sl, tl, xl, yl = mesh.get_stxy_c_3node(s1, t1, x1, y1, s2, t2, x2, y2, s, t, hyp_problem.C2)
            
            x, y = self.center_solve(hyp_problem, s=s, t=t,
                                sl=sl, tl=tl, xl=xl, yl=yl, hl=t-tl, 
                                sr=sr, tr=tr, xr=xr, yr=yr, hr=t-tr)
            
            node_index = mesh.nodes_final_l_dict[i][j]
            mesh.rez_nodes_final_l[node_index][0][0]=x
            mesh.rez_nodes_final_l[node_index][0][1]=y  
        
        for i, j, sr, tr, xr, yr in final_r_nodes:
            s, t, _, _ = mesh.get_right_node_stxy(i, j)
            s2, t2, x2, y2 = mesh.get_left_node_stxy(i, j)
            sl, tl, xl, yl = mesh.get_stxy_c_3node(sr, tr, xr, yr, s2, t2, x2, y2, s, t, hyp_problem.C2)
            x, y = self.right_solve(hyp_problem, s=s, t=t,
                        sl=sl, tl=tl, xl=xl, yl=yl, hl=t-tl, 
                                sr=sr, tr=tr, xr=xr, yr=yr, hr=t-tr)
            node_index = mesh.nodes_final_r_dict[i][j]
            mesh.rez_nodes_final_r[node_index][0][0]=x
            mesh.rez_nodes_final_r[node_index][0][1]=y 

    def solver_final_conj(self, mesh: Mesh, hyp_problem):
        start_l_nodes = []
        for node in reversed(mesh.nodes_start_l):
            i, j, s, t = node[0], node[1], node[2], node[3]
            
            if s == hyp_problem.S0:
                sl, tl, psi1l, psi2l, p2l = mesh.get_center_conj_node_stxy(i, j)
                if mesh.is_from_center(i+1, j):
                    s2, t2, psi12, psi22, _ = mesh.get_center_node_stxy(i+1, j)
                    sr, tr, psi1r, psi2r = mesh.get_stxy_c_3node(s2, t2, psi12, psi22, sl, tl, psi1l, psi2l,  s, t, hyp_problem.C2)
                    psi1, psi2, p2 = self.left_conj_solve(hyp_problem, s=s, t=t,
                                    sl=sl, tl=tl, psi1l=psi1l, psi2l=psi2l, p2l=p2l, hl=t-tl, 
                                    sr=sr, tr=tr, psi1r=psi1r, psi2r=psi2r, hr=t-tr)
                    node_index = mesh.nodes_start_l_dict[i][j]
                    mesh.rez_nodes_start_l[node_index][1][0]=psi1
                    mesh.rez_nodes_start_l[node_index][1][1]=psi2
                    mesh.rez_nodes_start_l[node_index][1][2]=p2
                    left_p=p2
                else:  
                    start_l_nodes.append([i, j, s, t, sl, tl, psi1l, psi2l, p2l])
                continue
            sr, tr, psi1r, psi2r, _ = mesh.get_center_conj_node_stxy(i, j)
            s1, t1, psi11, psi21, _ = mesh.get_center_conj_node_stxy(i-1, j)
            s2, t2, psi12, psi22, _ =mesh.get_center_conj_node_stxy(i-1, j-1) if mesh.is_from_center(i-1, j-1) else mesh.get_left_conj_node_stxy(i-1, j)
            sl, tl, psi1l, psi2l, = mesh.get_stxy_c_3node(s2, t2, psi12, psi22,s1, t1, psi11, psi21, s, t, -hyp_problem.C1)
            
            psi1, psi2 = self.center_conj_solve(hyp_problem, s=s, t=t,
                                    sl=sl, tl=tl, psi1l=psi1l, psi2l=psi2l, hl=t-tl, 
                                    sr=sr, tr=tr, psi1r=psi1r, psi2r=psi2r, hr=t-tr)
            
            node_index = mesh.nodes_start_l_dict[i][j]
            mesh.rez_nodes_start_l[node_index][1][0]=psi1
            mesh.rez_nodes_start_l[node_index][1][1]=psi2  

        for node in reversed(mesh.nodes_start_r):
            i, j, s, t = node[0], node[1], node[2], node[3]
            
            if s == hyp_problem.S1:
                sr, tr, psi1r, psi2r, p1r = mesh.get_center_conj_node_stxy(i, j)
                s2, t2, psi12, psi22, _ = mesh.get_center_conj_node_stxy(i, j-1) if mesh.is_from_center(i, j-1) else mesh.get_left_conj_node_stxy(i, j)
                sl, tl, psi1l, psi2l = mesh.get_stxy_c_3node(s2, t2, psi12, psi22, sr, tr, psi1r, psi2r, s, t, -hyp_problem.C1)
                psi1, psi2, p1 = self.right_conj_solve(hyp_problem, s=s, t=t,
                                sl=sl, tl=tl, psi1l=psi1l, psi2l=psi2l, hl=t-tl, 
                                sr=sr, tr=tr, psi1r=psi1r, psi2r=psi2r, p1r=p1r, hr=t-tr)

                node_index = mesh.nodes_start_r_dict[i][j]
                mesh.rez_nodes_start_r[node_index][1][0]=psi1
                mesh.rez_nodes_start_r[node_index][1][1]=psi2
                mesh.rez_nodes_start_r[node_index][1][2]=p1
                right_p = p1
                continue
            sl, tl, psi1l, psi2l, _ = mesh.get_center_conj_node_stxy(i, j)
            s1, t1, psi11, psi21, _ = mesh.get_center_conj_node_stxy(i, j+1)
            s2, t2, psi12, psi22, _ = mesh.get_center_conj_node_stxy(i+1, j+1) if mesh.is_from_center(i+1, j+1) else mesh.get_right_conj_node_stxy(i, j+1)
            sr, tr, psi1r, psi2r = mesh.get_stxy_c_3node(s2, t2, psi12, psi22, s1, t1, psi11, psi21, s, t, hyp_problem.C2)
            psi1, psi2 = self.center_conj_solve(hyp_problem, s=s, t=t,
                                    sl=sl, tl=tl, psi1l=psi1l, psi2l=psi2l, hl=t-tl, 
                                    sr=sr, tr=tr, psi1r=psi1r, psi2r=psi2r, hr=t-tr)
                
            
            node_index = mesh.nodes_start_r_dict[i][j]
            mesh.rez_nodes_start_r[node_index][1][0]=psi1
            mesh.rez_nodes_start_r[node_index][1][1]=psi2

        for i, j, s, t, sl, tl, psi1l, psi2l, p2l in start_l_nodes:
            s2, t2, psi12, psi22, _ = mesh.get_right_conj_node_stxy(i, j)
            sr, tr, psi1r, psi2r = mesh.get_stxy_c_3node(s2, t2, psi12, psi22, sl, tl, psi1l, psi2l,  s, t, hyp_problem.C2)
            psi1, psi2, p2 = self.left_conj_solve(hyp_problem, s=s, t=t,
                            sl=sl, tl=tl, psi1l=psi1l, psi2l=psi2l, p2l=p2l, hl=t-tl, 
                            sr=sr, tr=tr, psi1r=psi1r, psi2r=psi2r, hr=t-tr)
            node_index = mesh.nodes_start_l_dict[i][j]
            mesh.rez_nodes_start_l[node_index][1][0]=psi1
            mesh.rez_nodes_start_l[node_index][1][1]=psi2
            mesh.rez_nodes_start_l[node_index][1][2]=p2
            left_p=p2

        for node in mesh.nodes_start_l.tolist() :
            node_index = mesh.nodes_start_l_dict[node[0]][ node[1]] 
            if node[2] == mesh.S0:
                mesh.rez_nodes_start_l[node_index][1][2] = left_p
            if node[2] == mesh.S1:
                mesh.rez_nodes_start_l[node_index][1][2] = right_p

        for node in mesh.nodes_start_r.tolist() :
            node_index = mesh.nodes_start_r_dict[node[0]][ node[1]] 
            if node[2] == mesh.S0:
                mesh.rez_nodes_start_r[node_index][1][2] = left_p
            if node[2] == mesh.S1:
                mesh.rez_nodes_start_r[node_index][1][2] = right_p

        
    def center_solve(self, problem: HypProblem, s:float, t:float,
                    sl:float, tl:float, xl:float, yl:float, hl:float, 
                    sr:float, tr:float, xr:float, yr:float, hr:float) -> Tuple[float, float]:

        B11, B12, B21, B22 = problem.B11, problem.B12, problem.B21, problem.B22,
        F1, F2 = problem.F1, problem.F2
        
        A = [[1 - hr/2*B11(s, t), -hr/2*B12(s, t)],
             [-hl/2*B21(s, t), 1-hl/2*B22(s, t)]]
        b = [xr + hr/2*(B11(sr, tr)*xr+B12(sr, tr)*yr + F1(s, t) + F1(sr, tr)),
             yl + hl/2*(B21(sl, tl)*xl+B22(sl, tl)*yl + F2(s, t) + F2(sl, tl))]
        return np.linalg.solve(A, b)
    
    def center_conj_solve(self, problem: HypProblem, s:float, t:float,
                    sl:float, tl:float, psi1l:float, psi2l:float, hl:float, 
                    sr:float, tr:float, psi1r:float, psi2r:float, hr:float) -> Tuple[float, float]:

        B11, B12, B21, B22 = problem.B11, problem.B12, problem.B21, problem.B22,
        F1, F2 = problem.F1, problem.F2
        
        A = [[1 + hl/2*B11(s, t), hl/2*B21(s, t)],
             [hr/2*B12(s, t), 1+hr/2*B22(s, t)]]
        b = [psi1l + hl/2*(-B11(sl, tl)*psi1l-B21(sl, tl)*psi2l + F1(s, t) + F1(sl, tl)),
             psi2r + hr/2*(-B12(sr, tr)*psi1r-B22(sr, tr)*psi2r + F2(s, t) + F2(sr, tr))]
        return np.linalg.solve(A, b)

    def left_solve(self, problem: HypProblem, s:float, t:float,
                   sl:float, tl:float, xl:float, yl:float, hl:float, 
                   sr:float, tr:float, xr:float, yr:float, hr:float) -> Tuple[float, float]:
        
        B11 = problem.B11
        B12 = problem.B12
        F1 = problem.F1
        G21 = problem.G21
        G22 = problem.G22

        A = [[1 - hr / 2 * B11(s, t), -hr / 2 * B12(s, t)],
                [-hl / 2 * G21(t), 1 - hl / 2 * G22(t)]]
        b = [xr + hr / 2 * (B11(sr, tr) * xr + B12(sr, tr) * yr + F1(s, t) + F1(sr, tr)),
                yl + hl / 2 * (G21(tl) * xl + G22(tl) * yl)]
        return np.linalg.solve(A, b)
    
    def left_conj_solve(self, problem: HypProblem, s:float, t:float,
                    sl:float, tl:float, psi1l:float, psi2l:float, p2l: float,hl:float, 
                    sr:float, tr:float, psi1r:float, psi2r:float, hr:float) -> Tuple[float, float]:
        
        B22 = problem.B22
        B12 = problem.B12
        
        G22 = problem.G22
        C2 = problem.C2
        psi_to_P = 1/problem.C1*G22(t)

        A = [[1 - hl/2*G22(t), hl/2*C2],
             [hr/2*B12(s, t)*psi_to_P, 1+hr/2*B22(s, t)]]
        b = [p2l +   hl/2*(G22(tl)*p2l-C2*psi2l),
             psi2r + hr/2*(-B12(sr, tr)*psi1r-B22(sr, tr)*psi2r)]
        p2, psi2 = np.linalg.solve(A, b)
        psi1 = psi_to_P*p2
        
        return psi1, psi2, p2
    
    
    def right_solve(self, problem: HypProblem, s:float, t:float,
                   sl:float, tl:float, xl:float, yl:float, hl:float, 
                   sr:float, tr:float, xr:float, yr:float, hr:float) -> Tuple[float, float]:
        
        B21 = problem.B21
        B22 = problem.B22
        F2 = problem.F2
        G12 = problem.G12
        G11 = problem.G11

        A = [[1 - hr / 2 * G11(t), -hr / 2 * G12(t)],
                [-hl / 2 * B21(s, t), 1 - hl / 2 * B22(s, t)]]
        b = [xr + hr / 2 * (G11(tr) * xr + G12(tr) * yr),
                yl + hl / 2 * (B21(sl, tl) * xl + B22(sl, tl) * yl + F2(s, t) + F2(sl, tl))]
        return np.linalg.solve(A, b)
    
    def right_conj_solve(self, problem: HypProblem, s:float, t:float,
                    sl:float, tl:float, psi1l:float, psi2l:float, hl:float, 
                    sr:float, tr:float, psi1r:float, psi2r:float, p1r: float, hr:float) -> Tuple[float, float]:
        
        B11 = problem.B11
        B21 = problem.B21
        
        G11 = problem.G11
        C1 = problem.C1
        psi_to_P = 1/problem.C2*G11(t)

        A = [[1 + hl/2*B11(s, t), hl/2*B21(s, t)*psi_to_P],
             [hr/2*C1, 1-hr/2*G11(t)]]
        b = [psi1l + hl/2*(-B11(sl, tl)*psi1l-B21(sl, tl)*psi2l),
             p1r+hr/2*(G11(tr)*p1r-C1*psi1r)]
        psi1, p1 = np.linalg.solve(A, b)
        psi2 = psi_to_P*p1
        
        return psi1, psi2, p1
    