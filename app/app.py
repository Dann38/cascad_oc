import sys
import os

_here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_here, '..', 'src'))
sys.path.insert(0, _here)

from flask import Flask, render_template, request, jsonify, session as flask_session, send_file
import uuid
from io import BytesIO
import base64

from solver_service import (
    get_session, build_problem_and_mesh, solve_forward,
    solve_optimal_control, generate_mesh_plot,
    generate_3d_surface_plots, generate_oc_plots,
    DEFAULT_CONFIG
)

app = Flask(__name__)
app.secret_key = 'cascad-oc-secret-key-2024'
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'


@app.before_request
def ensure_session():
    if 'session_id' not in flask_session:
        flask_session['session_id'] = uuid.uuid4().hex


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/solver/hyperbolic')
def solver_page():
    sess = get_session(flask_session['session_id'])
    return render_template('solver.html', config=sess['config'])


@app.route('/api/config', methods=['POST'])
def api_config():
    data = request.get_json()
    sid = flask_session['session_id']
    config = {k: data.get(k, DEFAULT_CONFIG[k]) for k in DEFAULT_CONFIG}
    try:
        build_problem_and_mesh(sid, config)
        mesh_img = generate_mesh_plot(sid)
        return jsonify({'status': 'ok', 'mesh_img': mesh_img})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400


@app.route('/api/solve_forward', methods=['POST'])
def api_solve_forward():
    sid = flask_session['session_id']
    try:
        solve_forward(sid)
        img_x, img_y = generate_3d_surface_plots(sid)
        return jsonify({
            'status': 'ok',
            'img_x': img_x,
            'img_y': img_y,
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400


@app.route('/api/solve_oc', methods=['POST'])
def api_solve_oc():
    sid = flask_session['session_id']
    data = request.get_json() or {}
    sess = get_session(sid)
    config = sess['config']

    if 'u_min' in data:
        config['u_min'] = float(data['u_min'])
    if 'u_max' in data:
        config['u_max'] = float(data['u_max'])
    if 'eps' in data:
        config['eps'] = float(data['eps'])
    if 'method' in data:
        config['method'] = data['method']
    if 'functional' in data:
        config['functional'] = data['functional']
    if 'beta' in data:
        config['beta'] = float(data['beta'])
    if 'delta' in data:
        config['delta'] = float(data['delta'])
    if 'eps_count_max' in data:
        config['eps_count_max'] = int(data['eps_count_max'])

    sess['config'] = config
    build_problem_and_mesh(sid, config)

    try:
        solve_optimal_control(sid)
        img_xf, img_yf, img_u, iterations = generate_oc_plots(sid)
        return jsonify({
            'status': 'ok',
            'img_xf': img_xf,
            'img_yf': img_yf,
            'img_u': img_u,
            'iterations': iterations,
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400


@app.route('/api/download/<plot_type>')
def api_download(plot_type):
    sid = flask_session['session_id']
    sess = get_session(sid)
    if not sess['forward_solved'] and plot_type not in ('mesh',):
        return 'Not solved yet', 400

    img = None
    if plot_type == 'mesh':
        img = generate_mesh_plot(sid)
    elif plot_type == 'x_surface':
        img_x, _ = generate_3d_surface_plots(sid)
        img = img_x
    elif plot_type == 'y_surface':
        _, img = generate_3d_surface_plots(sid)
    elif plot_type == 'x_final':
        img, _, _, _ = generate_oc_plots(sid)
    elif plot_type == 'y_final':
        _, img, _, _ = generate_oc_plots(sid)
    elif plot_type == 'control':
        _, _, img, _ = generate_oc_plots(sid)

    if img is None:
        return 'Plot not available', 400

    img_bytes = base64.b64decode(img)
    return send_file(BytesIO(img_bytes), mimetype='image/png',
                     download_name=f'{plot_type}.png')


if __name__ == '__main__':
    app.run(debug=True, port=5000)
