import numpy as np
import scipy

from .problem import HypProblem
from .mesh import Mesh
from .solver import Solver
from typing import List, Callable

MAX_STEP_ALPHA = 20
MAX_ITERATION = 20

class OCProblem:
    def __init__(self, hyp_problem: HypProblem, mesh: Mesh, xs, ys) -> None:
        self.hyp_problem = hyp_problem
        self.mesh = mesh
        self.solver = Solver()
        self.iteration_solv = 0
        self.iteration_conj_solv = 0
        self.rezid = []

        self.xs = xs
        self.ys = ys

        self.u_min = None 
        self.u_max = None

        self.min_delta = 0.001

        nodes = mesh.get_border(type_border="left", sort_t=True)
        t_mesh = [node[0][3] for node in nodes]
        self.t_index = []
        self.t_hash = []
        for i, e in enumerate(t_mesh):
            if not e in self.t_hash:
                self.t_hash.append(e)
                self.t_index.append(i)

    def solve(self):
        self.iteration_solv += 1
        self.solver.solve_initial(self.mesh, self.hyp_problem)
        self.solver.solver_center(self.mesh, self.hyp_problem)
        self.solver.solver_final(self.mesh, self.hyp_problem)

    def solve_conj(self):
        self.iteration_conj_solv += 1
        self.solver.solver_initial_conj(self.mesh, self.hyp_problem)
        self.solver.solver_center_conj(self.mesh, self.hyp_problem)
        self.solver.solver_final_conj(self.mesh, self.hyp_problem) 

    def J(self, v):
        v_ = [v[ti] for ti in self.t_index]
        self.set_new_control(lambda ti: np.interp(ti, self.t_hash, v_))
        self.solve()

        nodes = self.mesh.get_border(type_border="final", sort_s=True)
        s_final = [node[0][2] for i, node in enumerate(nodes) if i in self.t_index]
        x_final = [node[1][0][0] for i, node in enumerate(nodes)if i in self.t_index]
        y_final = [node[1][0][1] for i, node in enumerate(nodes) if i in self.t_index]

        f = [(xi-self.xs(si))**2+(yi-self.ys(si))**2 for xi, yi, si in zip(x_final, y_final, s_final)]
        return scipy.integrate.trapezoid(f, s_final)

    def set_ulim(self, u_lim):
        self.u_min = u_lim[0]
        self.u_max = u_lim[1]

    def set_min_delta(self, min_delta):
        self.min_delta = min_delta

    def set_new_control(self, U):
        G22_0 = lambda t: U(t)
        G21_0 = lambda t: - G22_0(t)
        G11_0 = self.hyp_problem.G11
        G12_0 = self.hyp_problem.G12
        self.hyp_problem.set_G([[G11_0, G12_0], [G21_0, G22_0]])


def solve_oc(hyp_problem: HypProblem, mesh: Mesh, 
             U0: Callable[[float], float], xs: Callable[[float], float], ys: Callable[[float], float], 
             u_lim: List, eps:float=0.000001, debug=True, method:str="CGM", **params):
    """
    Solve problem:
    J(U) = int_S (x(s, t1)-xs(s))**2 ds + int_S (y(s, t1)-ys(s))**2 ds -> min
    xs, ys - functions

    U0 - start control
    U_lim = [u0, u1] - control limit 
    hyp_problem and mesh are problem
    
    stopping criteria
    int_T H(psi1^k, psi2^k, x^k, y^k, u^k, t)(u^{k+1}-u^k) dt < eps
    """
    oc_problem = OCProblem(hyp_problem, mesh, xs, ys)
    oc_problem.set_ulim(u_lim)
    oc_problem.set_min_delta(eps)
    oc_problem.set_new_control(U0)
    if method.upper() == "CGM":
        return cgm_solver(oc_problem, debug, **params)
    elif method.upper() == "IMPM":
        return impm_solver(oc_problem, debug, **params)
    elif method.upper() == "MPM":
        return mpm_solver(oc_problem, debug, **params)
    

def cgm_solver(oc_problem, debug, **params):
    global ALPHA_HYSTORY
    ALPHA_HYSTORY = 0
    
    for k in range(1, MAX_ITERATION):
        oc_problem.solve()
        oc_problem.solve_conj()
        nodes = oc_problem.mesh.get_border(type_border="left", sort_t=True)
        t = [node[0][3] for node in nodes]
        
        hu = [node[1][1][2]*(node[1][0][0]-node[1][0][1]) for node in nodes]
        
        uk = [oc_problem.hyp_problem.G22(ti) for ti in t]
        # new_uk = []
        # for uki, hui in zip(uk, hu):
        #     if hui == 0:
        #         new_uk.append(uki)
        #     elif hui > 0:
        #         new_uk.append(oc_problem.u_max)
        #     else:
        #         new_uk.append(oc_problem.u_min)
        over_uk, over_W, Theta_uk = _get_over(nodes, uk, t, oc_problem.u_min, oc_problem.u_max)

        oc_problem.rezid.append(Theta_uk)
        if debug:
            print("Оптимально" if Theta_uk <= oc_problem.min_delta else "Не оптимально")
            print(f"Невязка составляет: {Theta_uk:.6f}")
            print(40*"*")  
        if Theta_uk <= oc_problem.min_delta:
            if debug:
                print(f"Невязка составляет: {Theta_uk:.6f}")
                print( f"Решено на {k}-й итерации")
            break
          
        a = _alpha_test(oc_problem, uk, over_uk) 
        uk_a_min = _get_uki(a, uk, over_uk)
        oc_problem.set_new_control(lambda ti: np.interp(ti, t, uk_a_min))
        if debug:
            print("результат минимизации a = ", a)
    return oc_problem


def mpm_solver(oc_problem, debug, **params):
    nodes = oc_problem.mesh.get_border(type_border="left", sort_t=True)
    t_mesh = [node[0][3] for node in nodes]
    U0 = [oc_problem.hyp_problem.G22(ti) for ti in t_mesh]
    rez = scipy.optimize.minimize(oc_problem.J, U0, method="BFGS", tol=oc_problem.min_delta)
    oc_problem.set_new_control( lambda t: np.interp(t, t_mesh, rez.x))
    oc_problem.solve()
    oc_problem.rez_oc_solver = rez
    if debug:
        print(rez)
    return oc_problem


def impm_solver(oc_problem, debug, **params):
    global ALPHA_HYSTORY
    ALPHA_HYSTORY = 0
    for k in range(1, MAX_ITERATION):
        oc_problem.solve()
        oc_problem.solve_conj()
        nodes = oc_problem.mesh.get_border(type_border="left", sort_t=True)
        t = [node[0][3] for node in nodes]
        uk = [oc_problem.hyp_problem.G22(ti) for ti in t]
        over_uk, over_W, Theta_uk = _get_over(nodes, uk, t, oc_problem.u_min, oc_problem.u_max)
        
        oc_problem.rezid.append(Theta_uk)
        if debug:
            print("Оптимально" if Theta_uk <= oc_problem.min_delta else "Не оптимально")
            print(f"Невязка составляет: {Theta_uk:.6f}")
            print(40*"*")  
        if Theta_uk <= oc_problem.min_delta:
            if debug:
                print(f"Невязка составляет: {Theta_uk:.6f}")
                print( f"Решено на {k}-й итерации")
            break
        T = _get_interval_T(over_W, Theta_uk, beta=params["beta"], delta=params["delta"])
        a = _alpha_eps_test(oc_problem, uk, over_uk, T, params["eps_count_max"]) 
        uk_a_min = _get_uki_variation(uk, over_uk, T, a)
        oc_problem.set_new_control(lambda ti: np.interp(x=ti, xp=t, fp=uk_a_min))
        if debug:
            print("результат минимизации a = ", a)
    return oc_problem

def _get_over(nodes, uk, t, u_min, u_max):
    hu = [node[1][1][2]*(node[1][0][0]-node[1][0][1]) for node in nodes]
    new_uk = []
    for uki, hui in zip(uk, hu):
        if hui == 0:
            new_uk.append(uki)
        elif hui > 0:
            new_uk.append(u_max)
        else:
            new_uk.append(u_min)
    
    over_W, Theta_uk = _get_resid(t, hu, new_uk, uk) 
    over_uk = np.array(new_uk)
    return over_uk, over_W, Theta_uk


def _get_index_interval(index, delta):
    max_T = np.sum(index)
    intervals = []
    start = False
    for i, iss in enumerate(index):
        if iss and not start:
            start = True
            len_ = 0
            intervals.append([i, 0])
        if start and not iss:
            start = False
        if start:
            intervals[-1][1] += 1
    len_ = np.array([inter[1] for inter in intervals])
    index_interval = reversed(np.argsort(len_))
    
    sum_ = 0
    T = []
    for i in index_interval:
        sum_+=len_[i]
        T.append(intervals[i])
        if sum_ > delta*max_T:
            return T
    return T

def _get_interval_T(over_W, Theta_uk, beta, delta):
    index = over_W >= Theta_uk*beta   
    M = _get_index_interval(index, delta)
    T = []
    for Ti in M:
        tau_index = np.argmax(over_W[Ti[0]:Ti[0]+Ti[1]])
        left_tau = tau_index - Ti[0]
        right_tau = Ti[1]-tau_index
        T.append((tau_index, left_tau, right_tau))
    return T


def _get_resid(t_h, h_u_k, uk_new, uk):
    f = [h*(uk_new_i-uk_i) for h, uk_new_i, uk_i in zip(h_u_k, uk_new, uk) ]
    return f, scipy.integrate.trapezoid(f, t_h) 

def _get_uki(a, uk, uk_new):
    return [ uk_i + a*(uk_new_i - uk_i) for uk_i, uk_new_i in zip(uk, uk_new)]

def _get_uki_variation(uk, over_uk, T, param):
    uk_new = uk.copy()
    for Ti in T:
        tau, left, right = Ti
        ind_l = tau - int(left*param[0])
        ind_r = tau + int(right*param[0])
        uk_new[ind_l:ind_r] = uk_new[ind_l:ind_r] + param[1]*(over_uk[ind_l:ind_r]-uk_new[ind_l:ind_r])
    return uk_new

def _alpha_test(oc_problem:OCProblem, uk, uk_new, const=10):
    nodes = oc_problem.mesh.get_border(type_border="left", sort_t=True)
    t_mesh = [node[0][3] for node in nodes]
    global ALPHA_HYSTORY
    def fun(a):
        uk_a = _get_uki(a, uk, uk_new)
        return oc_problem.J(uk_a)
    is_run = True
    is_run_2 = False
    J_old = oc_problem.J(uk)
    a = const/(const+ALPHA_HYSTORY)
    max_a = ALPHA_HYSTORY + MAX_STEP_ALPHA
    while is_run:
        J_new = fun(a)
        if is_run_2 and J_old < J_new:
            return a
        if J_old > J_new:
            J_old = J_new
            is_run_2 = True
        ALPHA_HYSTORY += 1
        a =  const/(const+ALPHA_HYSTORY)
        if ALPHA_HYSTORY > max_a:
            return a
        
def _alpha_eps_test(oc_problem:OCProblem, uk, uk_new, T, eps_count_max, const=10):
    global ALPHA_HYSTORY
    # n = int(len(oc_problem.mesh.get_border(type_border="left", sort_t=False))/len(T))
    # n = len(oc_problem.mesh.get_border(type_border="left", sort_t=False))
    # eps = np.linspace(0, 1, n if n < eps_count_max else eps_count_max)[1:] if n > 0 else [1]
    eps = np.array([const/(const+i) for i in range(0, eps_count_max+1)])
    a = [const/(const+i+ALPHA_HYSTORY) for i in range(1, MAX_STEP_ALPHA+1)]

    J_min = np.inf
    start = False

    uk_a = [_get_uki_variation(uk, uk_new, T, [e, a[0]]) for e in eps]
   
    J_ar = [oc_problem.J(uk_ai) for uk_ai in uk_a]
    i = np.argmin(J_ar)
    J_min = J_ar[i]
    a_min = a[0]
    eps_min = eps[i]

    for arg_a in a:
        J_ar = []
        for arg_eps in eps:  
            uk_a = _get_uki_variation(uk, uk_new, T, [arg_eps, arg_a])
            J_ar.append(oc_problem.J(uk_a))
        i = np.argmin(J_ar)
        J= J_ar[i]
        if J < J_min:
            J_min = J
            a_min = arg_a
            eps_min = eps[i]
            start = True
        elif start:
            break
    ALPHA_HYSTORY = int(const/a_min-const)
    return (eps_min, arg_a)

