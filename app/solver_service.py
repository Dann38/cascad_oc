import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from io import BytesIO
import base64
import uuid
import pickle
from cascadoc_old import HypProblem, Mesh, Solver, solve_oc

_sessions = {}

DEFAULT_CONFIG = {
    'S': [0, 1],
    'T': [0, 0.2],
    'C': [1, 2],
    'm': 100,
    'B11': '-2*s',
    'B12': '4/3*s**2',
    'B21': '-(3*s+1)/(4*(s**2+1)*(s+1))',
    'B22': '4/((s+1)*(3*s+1))',
    'F1': '4*s**3*np.sin(t)+2*np.cos(t)+4*s**2*np.cos(t)/(3*(s+1))',
    'F2': '0',
    'G11': '-4*np.cos(t)/(np.cos(t)-4*np.sin(t))',
    'G12': '4*np.cos(t)/(np.cos(t)-4*np.sin(t))',
    'G21': '-np.sin(t)/(np.cos(t)-4*np.sin(t))+1',
    'G22': 'np.sin(t)/(np.cos(t)-4*np.sin(t))-1',
    'x0': '0',
    'y0': '(3*s+1)/(2*(s+1))',
    'phi_dx': '-2*(x - 2*(s**2+1)*np.sin(T1))',
    'phi_dy': '-2*(y - (3*s+1)/(2*(s+1))*np.cos(T1))',
    'U0': 'np.sin(t)/(np.cos(t)-4*np.sin(t))-1',
    'xs': '2*(s**2+1)*np.sin(T1)',
    'ys': '(3*s+1)/(2*(s+1))*np.cos(T1)',
    'u_min': -2.5,
    'u_max': 1.0,
    'eps': 0.00001,
    'method': 'cgm',
    'beta': 0.0,
    'delta': 1.0,
    'eps_count_max': 6,
    'functional': 'quadratic',
}


def _make_function(expr, var_names, extra_globals=None):
    ns = {'np': np, 'sin': np.sin, 'cos': np.cos, 'tan': np.tan,
          'exp': np.exp, 'log': np.log, 'sqrt': np.sqrt, 'abs': np.abs,
          'pi': np.pi, 'e': np.e, '__builtins__': {}}
    if extra_globals:
        ns.update(extra_globals)
    if expr.strip() == '':
        return lambda *args: 0.0
    code = compile(f'lambda {",".join(var_names)}: {expr}', '<expr>', 'eval')
    return eval(code, ns)


def _parse_config(config):
    T0, T1 = config['T']
    S0, S1 = config['S']
    alphas = {'T0': T0, 'T1': T1, 'S0': S0, 'S1': S1}

    B11 = _make_function(config['B11'], ['s', 't'], alphas)
    B12 = _make_function(config['B12'], ['s', 't'], alphas)
    B21 = _make_function(config['B21'], ['s', 't'], alphas)
    B22 = _make_function(config['B22'], ['s', 't'], alphas)
    F1 = _make_function(config['F1'], ['s', 't'], alphas)
    F2 = _make_function(config['F2'], ['s', 't'], alphas)
    G11 = _make_function(config['G11'], ['t'], alphas)
    G12 = _make_function(config['G12'], ['t'], alphas)
    G21 = _make_function(config['G21'], ['t'], alphas)
    G22 = _make_function(config['G22'], ['t'], alphas)
    x0 = _make_function(config['x0'], ['s'], alphas)
    y0 = _make_function(config['y0'], ['s'], alphas)
    phi_dx = _make_function(config['phi_dx'], ['s', 'x', 'y'], alphas)
    phi_dy = _make_function(config['phi_dy'], ['s', 'x', 'y'], alphas)
    U0 = _make_function(config['U0'], ['t'], alphas)
    xs = _make_function(config['xs'], ['s'], alphas)
    ys = _make_function(config['ys'], ['s'], alphas)

    hyp_problem = HypProblem(
        T=config['T'], S=config['S'], C=config['C'],
        B=[[B11, B12], [B21, B22]],
        F=[F1, F2],
        G=[[G11, G12], [G21, G22]],
        X0=x0, Y0=y0,
        phi_dx=phi_dx, phi_dy=phi_dy
    )
    return hyp_problem, U0, xs, ys


def get_session(session_id):
    if session_id not in _sessions:
        _sessions[session_id] = {
            'config': dict(DEFAULT_CONFIG),
            'hyp_problem': None,
            'mesh': None,
            'solver': None,
            'oc_result': None,
            'forward_solved': False,
            'oc_solved': False,
        }
    return _sessions[session_id]


def build_problem_and_mesh(session_id, config):
    session = get_session(session_id)
    session['config'] = dict(config)
    hyp_problem, U0, xs, ys = _parse_config(config)
    mesh = Mesh(hyp_problem, config['m'])
    session['hyp_problem'] = hyp_problem
    session['mesh'] = mesh
    session['U0'] = U0
    session['xs'] = xs
    session['ys'] = ys
    session['forward_solved'] = False
    session['oc_solved'] = False
    return hyp_problem, mesh


def solve_forward(session_id):
    session = get_session(session_id)
    hyp_problem = session['hyp_problem']
    mesh = session['mesh']
    solver = Solver()
    solver.solve_initial(mesh, hyp_problem)
    solver.solver_center(mesh, hyp_problem)
    solver.solver_final(mesh, hyp_problem)
    session['solver'] = solver
    session['forward_solved'] = True


def solve_optimal_control(session_id):
    session = get_session(session_id)
    if not session['forward_solved']:
        solve_forward(session_id)

    config = session['config']
    hyp_problem = session['hyp_problem']
    mesh = session['mesh']
    U0 = session['U0']
    xs = session['xs']
    ys = session['ys']

    hyp_problem2 = HypProblem(
        T=config['T'], S=config['S'], C=config['C'],
        B=[[hyp_problem.B11, hyp_problem.B12], [hyp_problem.B21, hyp_problem.B22]],
        F=[hyp_problem.F1, hyp_problem.F2],
        G=[[hyp_problem.G11, hyp_problem.G12], [hyp_problem.G21, hyp_problem.G22]],
        X0=hyp_problem.x0, Y0=hyp_problem.y0,
        phi_dx=hyp_problem.phi_dx, phi_dy=hyp_problem.phi_dy
    )
    mesh2 = Mesh(hyp_problem2, config['m'])

    kwargs = {}
    if config['method'].upper() == 'IMPM':
        kwargs = {'beta': config['beta'], 'delta': config['delta'],
                  'eps_count_max': config['eps_count_max']}

    oc_result = solve_oc(
        hyp_problem2, mesh2, U0, xs, ys,
        u_lim=[config['u_min'], config['u_max']],
        eps=config['eps'],
        method=config['method'],
        debug=False,
        **kwargs
    )
    session['oc_result'] = oc_result
    session['oc_mesh'] = mesh2
    session['oc_solved'] = True
    return oc_result


def fig_to_base64(fig):
    buf = BytesIO()
    fig.savefig(buf, format='png', dpi=100)
    buf.seek(0)
    result = base64.b64encode(buf.read()).decode('utf-8')
    plt.close(fig)
    return result


def generate_mesh_plot(session_id):
    session = get_session(session_id)
    mesh = session['mesh']
    if mesh is None:
        return None
    plt.close('all')
    fig, ax = plt.subplots(figsize=(7, 5))
    mesh.plot_mesh()
    ax.set_xlabel('s')
    ax.set_ylabel('t')
    ax.set_title('Characteristic Mesh')
    img = fig_to_base64(fig)
    return img


def generate_surface_plots(session_id):
    session = get_session(session_id)
    if not session['forward_solved']:
        return None, None

    mesh = session['mesh']
    solver = session['solver']

    nodes = mesh.get_border(type_border='final', sort_s=True)
    s_vals = np.array([n[0][2] for n in nodes])
    x_vals = np.array([n[1][0][0] for n in nodes])
    y_vals = np.array([n[1][0][1] for n in nodes])

    fig_x, ax_x = plt.subplots(figsize=(6, 4))
    ax_x.plot(s_vals, x_vals, 'r.-', markersize=3)
    ax_x.set_xlabel('s')
    ax_x.set_ylabel('x(s, T)')
    ax_x.set_title('x at final time')
    ax_x.grid(True)
    img_x = fig_to_base64(fig_x)

    fig_y, ax_y = plt.subplots(figsize=(6, 4))
    ax_y.plot(s_vals, y_vals, 'b.-', markersize=3)
    ax_y.set_xlabel('s')
    ax_y.set_ylabel('y(s, T)')
    ax_y.set_title('y at final time')
    ax_y.grid(True)
    img_y = fig_to_base64(fig_y)

    return img_x, img_y


def generate_3d_surface_plots(session_id):
    session = get_session(session_id)
    if not session['forward_solved']:
        return None, None

    mesh = session['mesh']

    center_nodes = mesh.nodes_center
    s_list, t_list, x_list, y_list = [], [], [], []
    for node in center_nodes:
        s_list.append(node[2])
        t_list.append(node[3])
        idx = mesh.nodes_center_dict[int(node[0])][int(node[1])]
        rez = mesh.rez_nodes_center[idx]
        x_list.append(rez[0][0])
        y_list.append(rez[0][1])

    s_arr = np.array(s_list)
    t_arr = np.array(t_list)
    x_arr = np.array(x_list)
    y_arr = np.array(y_list)

    plt.close('all')
    fig_x = plt.figure(figsize=(6, 5))
    ax = fig_x.add_subplot(111, projection='3d')
    ax.scatter(s_arr, t_arr, x_arr, c=x_arr, cmap='viridis', s=1, alpha=0.6)
    ax.set_xlabel('s')
    ax.set_ylabel('t')
    ax.set_zlabel('x')
    ax.set_title('x(s,t) surface')
    img_x = fig_to_base64(fig_x)

    plt.close('all')
    fig_y = plt.figure(figsize=(6, 5))
    ax = fig_y.add_subplot(111, projection='3d')
    ax.scatter(s_arr, t_arr, y_arr, c=y_arr, cmap='plasma', s=1, alpha=0.6)
    ax.set_xlabel('s')
    ax.set_ylabel('t')
    ax.set_zlabel('y')
    ax.set_title('y(s,t) surface')
    img_y = fig_to_base64(fig_y)

    return img_x, img_y


def generate_oc_plots(session_id):
    session = get_session(session_id)
    if not session['oc_solved']:
        return None, None, None, None

    oc_result = session['oc_result']
    oc_mesh = session['oc_mesh']
    config = session['config']

    nodes_final = oc_mesh.get_border(type_border='final', sort_s=True)
    s_f = np.array([n[0][2] for n in nodes_final])
    x_f = np.array([n[1][0][0] for n in nodes_final])
    y_f = np.array([n[1][0][1] for n in nodes_final])

    xs_fn = session['xs']
    ys_fn = session['ys']

    plt.close('all')
    fig_xf, ax = plt.subplots(figsize=(6, 4))
    ax.plot(s_f, x_f, 'r.-', markersize=3, label='x(s,T) found')
    ax.plot(s_f, [xs_fn(si) for si in s_f], 'b-', label='x target')
    ax.set_xlabel('s')
    ax.set_ylabel('x')
    ax.set_title('x at final time')
    ax.legend()
    ax.grid(True)
    img_xf = fig_to_base64(fig_xf)

    plt.close('all')
    fig_yf, ax = plt.subplots(figsize=(6, 4))
    ax.plot(s_f, y_f, 'r.-', markersize=3, label='y(s,T) found')
    ax.plot(s_f, [ys_fn(si) for si in s_f], 'b-', label='y target')
    ax.set_xlabel('s')
    ax.set_ylabel('y')
    ax.set_title('y at final time')
    ax.legend()
    ax.grid(True)
    img_yf = fig_to_base64(fig_yf)

    nodes_left = oc_mesh.get_border(type_border='left', sort_t=True)
    t_vals = np.array([n[0][3] for n in nodes_left])
    u_found = np.array([oc_result.hyp_problem.G22(ti) for ti in t_vals])
    u0_fn = session['U0']
    u_init = np.array([u0_fn(ti) for ti in t_vals])

    plt.close('all')
    fig_u, ax = plt.subplots(figsize=(6, 4))
    ax.plot(t_vals, u_init, 'g--', label='U0 (initial)')
    ax.plot(t_vals, u_found, 'r-', label='U (found)')
    ax.set_xlabel('t')
    ax.set_ylabel('u(t)')
    ax.set_title('Control function')
    ax.legend()
    ax.grid(True)
    img_u = fig_to_base64(fig_u)

    iterations = []
    for i, r in enumerate(oc_result.rezid):
        iterations.append({
            'iteration': i + 1,
            'residual': f'{r:.8f}',
        })

    return img_xf, img_yf, img_u, iterations
