from flask import Flask, jsonify, request, send_from_directory, session, redirect, render_template_string
from functools import wraps
import sqlite3
import json
import os

app = Flask(__name__)
app.secret_key   = os.environ.get('SECRET_KEY', 'krin-dev-secret-key')
VIEW_PASSWORD    = os.environ.get('VIEW_PASSWORD',  'KG12345678')
ADMIN_PASSWORD   = os.environ.get('ADMIN_PASSWORD', 'KG123456789')
DATABASE         = os.environ.get('DATABASE_PATH',  'trips.db')


# ── Auth decorators ───────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('role'):
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get('role') != 'admin':
            return jsonify({'error': 'View-only access'}), 403
        return f(*args, **kwargs)
    return decorated


# ── Login page ────────────────────────────────────────────────
LOGIN_HTML = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>KRIN Travelling Schedule – Login</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: Calibri, sans-serif;
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 30%, #0f3460 60%, #533483 100%);
  }
  .card {
    background: white;
    border-radius: 16px;
    padding: 40px 36px;
    width: 100%;
    max-width: 380px;
    box-shadow: 0 8px 32px rgba(0,0,0,0.3);
    text-align: center;
  }
  .logo { font-size: 2.5rem; margin-bottom: 10px; }
  h1 { font-size: 1.2rem; font-weight: 700; color: #2b6cb0; margin-bottom: 4px; }
  p  { font-size: 0.85rem; color: #718096; margin-bottom: 28px; }
  input[type=password] {
    width: 100%;
    padding: 11px 14px;
    border: 1.5px solid #e2e8f0;
    border-radius: 8px;
    font-size: 1rem;
    font-family: Calibri, sans-serif;
    margin-bottom: 14px;
    transition: border-color 0.2s;
  }
  input[type=password]:focus { outline: none; border-color: #63b3ed; }
  button {
    width: 100%;
    padding: 11px;
    background: linear-gradient(135deg, #2b6cb0, #2c7a7b);
    color: white;
    border: none;
    border-radius: 8px;
    font-size: 1rem;
    font-weight: 700;
    font-family: Calibri, sans-serif;
    cursor: pointer;
    transition: opacity 0.2s;
  }
  button:hover { opacity: 0.9; }
  .error {
    background: #fff5f5;
    color: #c53030;
    border: 1px solid #fed7d7;
    border-radius: 8px;
    padding: 9px 14px;
    font-size: 0.85rem;
    margin-bottom: 14px;
  }
</style>
</head>
<body>
<div class="card">
  <div class="logo">✈️</div>
  <h1>KRIN Travelling Schedule</h1>
  <p>ตารางการเดินทาง</p>
  {% if error %}
  <div class="error">Incorrect password. Please try again.</div>
  {% endif %}
  <form method="POST">
    <input type="password" name="password" placeholder="Enter password…" autofocus>
    <button type="submit">Sign In</button>
  </form>
</div>
</body>
</html>'''


@app.route('/login', methods=['GET', 'POST'])
def login():
    error = False
    if request.method == 'POST':
        pwd = request.form.get('password', '')
        if pwd == ADMIN_PASSWORD:
            session['role'] = 'admin'
            return redirect('/')
        elif pwd == VIEW_PASSWORD:
            session['role'] = 'viewer'
            return redirect('/')
        error = True
    return render_template_string(LOGIN_HTML, error=error)


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')


@app.route('/api/role')
@login_required
def get_role():
    return jsonify({'role': session.get('role')})


# ── DB ────────────────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS trips (
            id          TEXT PRIMARY KEY,
            start_date  TEXT NOT NULL,
            end_date    TEXT NOT NULL,
            dest        TEXT NOT NULL,
            details     TEXT DEFAULT '',
            staff       TEXT DEFAULT '[]',
            guests      TEXT DEFAULT '[]',
            color       TEXT DEFAULT '#3182ce'
        )
    ''')
    conn.commit()
    conn.close()


def row_to_dict(r):
    return {
        'id':      r['id'],
        'start':   r['start_date'],
        'end':     r['end_date'],
        'dest':    r['dest'],
        'details': r['details'],
        'staff':   json.loads(r['staff']),
        'guests':  json.loads(r['guests']),
        'color':   r['color'],
    }


# ── Routes ────────────────────────────────────────────────────
@app.route('/')
@login_required
def index():
    return send_from_directory('.', 'travel_dashboard.html')


@app.route('/api/trips', methods=['GET'])
@login_required
def get_trips():
    conn = get_db()
    rows = conn.execute('SELECT * FROM trips ORDER BY start_date').fetchall()
    conn.close()
    return jsonify([row_to_dict(r) for r in rows])


@app.route('/api/trips', methods=['POST'])
@login_required
@admin_required
def create_trip():
    d = request.get_json()
    conn = get_db()
    conn.execute(
        'INSERT INTO trips VALUES (?,?,?,?,?,?,?,?)',
        (d['id'], d['start'], d['end'], d['dest'],
         d.get('details', ''),
         json.dumps(d.get('staff', [])),
         json.dumps(d.get('guests', [])),
         d['color'])
    )
    conn.commit()
    conn.close()
    return jsonify({'ok': True}), 201


@app.route('/api/trips/<trip_id>', methods=['PUT'])
@login_required
@admin_required
def update_trip(trip_id):
    d = request.get_json()
    conn = get_db()
    conn.execute(
        '''UPDATE trips
           SET start_date=?, end_date=?, dest=?, details=?,
               staff=?, guests=?, color=?
           WHERE id=?''',
        (d['start'], d['end'], d['dest'],
         d.get('details', ''),
         json.dumps(d.get('staff', [])),
         json.dumps(d.get('guests', [])),
         d['color'], trip_id)
    )
    conn.commit()
    conn.close()
    return jsonify({'ok': True})


@app.route('/api/trips/<trip_id>', methods=['DELETE'])
@login_required
@admin_required
def delete_trip(trip_id):
    conn = get_db()
    conn.execute('DELETE FROM trips WHERE id=?', (trip_id,))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})


# ── Boot ──────────────────────────────────────────────────────
init_db()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
