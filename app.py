from flask import Flask, jsonify, request, send_from_directory
import sqlite3
import json
import os

app = Flask(__name__)

DATABASE = os.environ.get('DATABASE_PATH', 'trips.db')


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


# ── Serve dashboard ───────────────────────────────────────────
@app.route('/')
def index():
    return send_from_directory('.', 'travel_dashboard.html')


# ── API ───────────────────────────────────────────────────────
@app.route('/api/trips', methods=['GET'])
def get_trips():
    conn = get_db()
    rows = conn.execute('SELECT * FROM trips ORDER BY start_date').fetchall()
    conn.close()
    return jsonify([row_to_dict(r) for r in rows])


@app.route('/api/trips', methods=['POST'])
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
