import base64
import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import time
import uuid
from collections import deque
from datetime import datetime, timezone
from functools import wraps
from io import BytesIO
from pathlib import Path
from threading import Lock

from flask import (
    Flask, Response, abort, current_app, g, jsonify, redirect, render_template,
    request, send_file, session, url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from cryptography.fernet import Fernet, InvalidToken


BASE_DIR = Path(__file__).resolve().parent
_STREAM_LOCK = Lock()
_STREAM_FRAMES = {}
_STREAM_VIEWERS = {}
_AUDIO_LOCK = Lock()
_TALK_QUEUES = {}
_LISTENERS = {}
_LISTEN_CHUNKS = {}
_LISTEN_SEQUENCE = {}
_ALLOWED_VIDEO_SUFFIXES = {'.mp4', '.mov', '.mkv', '.avi'}


def _utc_now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def _token_hash(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def _db():
    if 'db' not in g:
        g.db = sqlite3.connect(current_app.config['DATABASE'])
        g.db.row_factory = sqlite3.Row
        g.db.execute('PRAGMA foreign_keys = ON')
    return g.db


def _init_db(app):
    db = sqlite3.connect(app.config['DATABASE'])
    try:
        db.execute('PRAGMA journal_mode = WAL')
        db.executescript('''
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS devices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                token_hash TEXT NOT NULL UNIQUE,
                activation_hash TEXT NOT NULL,
                camera_mode TEXT NOT NULL DEFAULT 'security',
                status_json TEXT NOT NULL DEFAULT '{}',
                stream_url TEXT,
                last_seen TEXT,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS enrollments (
                code_hash TEXT PRIMARY KEY,
                camera_name TEXT NOT NULL,
                expires_at REAL NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS events (
                id TEXT PRIMARY KEY,
                device_id INTEGER NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
                event_type TEXT NOT NULL,
                filename TEXT,
                mime_type TEXT,
                created_at TEXT NOT NULL,
                duration_seconds INTEGER,
                has_audio INTEGER NOT NULL DEFAULT 0,
                metadata_json TEXT NOT NULL DEFAULT '{}'
            );
            CREATE TABLE IF NOT EXISTS shares (
                token_hash TEXT PRIMARY KEY,
                device_id INTEGER NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
                expires_at REAL NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS wifi_changes (
                device_id INTEGER PRIMARY KEY REFERENCES devices(id) ON DELETE CASCADE,
                change_id TEXT NOT NULL,
                ssid_cipher BLOB NOT NULL,
                password_cipher BLOB NOT NULL,
                expires_at REAL NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS events_device_created
                ON events(device_id, created_at DESC);
        ''')
    finally:
        db.close()


def _csrf_token():
    token = session.get('_csrf_token')
    if not token:
        token = secrets.token_urlsafe(24)
        session['_csrf_token'] = token
    return token


def _check_csrf():
    supplied = request.form.get('_csrf_token') or request.headers.get('X-CSRF-Token')
    expected = session.get('_csrf_token', '')
    if not supplied or not expected or not hmac.compare_digest(supplied, expected):
        abort(400, description='Invalid CSRF token')


def _login_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if not session.get('username'):
            if request.path.startswith('/api/'):
                return jsonify({'error': 'authentication_required'}), 401
            return redirect(url_for('login'))
        return fn(*args, **kwargs)
    return wrapped


def _device_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        auth = request.headers.get('Authorization', '')
        token = auth[7:] if auth.startswith('Bearer ') else ''
        if not token:
            return jsonify({'error': 'unauthorized'}), 401
        row = _db().execute(
            'SELECT * FROM devices WHERE token_hash = ?', (_token_hash(token),)
        ).fetchone()
        if row is None:
            return jsonify({'error': 'unauthorized'}), 401
        g.device = row
        return fn(*args, **kwargs)
    return wrapped


def _device_reply(device):
    with _STREAM_LOCK:
        stream_requested = _STREAM_VIEWERS.get(device['id'], 0) > time.time()
    return {
        'ok': True,
        'camera_id': device['id'],
        'device_id': device['device_id'],
        'camera_name': device['name'],
        'camera_mode': device['camera_mode'],
        'armed': device['camera_mode'] == 'security',
        'stream_requested': stream_requested,
    }


def _device_matches_ref(device, reference):
    return str(device['id']) == str(reference) or device['device_id'] == str(reference)


def _audio_device(camera_ref):
    row = _db().execute(
        'SELECT * FROM devices WHERE id = ?',
        (int(camera_ref),),
    ).fetchone() if str(camera_ref).isdigit() else None
    if row is None:
        row = _db().execute(
            'SELECT * FROM devices WHERE device_id = ?', (str(camera_ref),)
        ).fetchone()
    return row


def _listen_requested(device_id):
    with _AUDIO_LOCK:
        return _LISTENERS.get(device_id, 0.0) > time.time()


def _active_share(token):
    row = _db().execute(
        '''SELECT shares.*, devices.name AS camera_name, devices.device_id
           FROM shares JOIN devices ON devices.id = shares.device_id
           WHERE shares.token_hash = ? AND shares.expires_at > ?''',
        (_token_hash(token), time.time()),
    ).fetchone()
    return row


def _wifi_change_payload(device):
    change = _db().execute(
        'SELECT * FROM wifi_changes WHERE device_id = ? AND expires_at > ?',
        (device['id'], time.time()),
    ).fetchone()
    if change is None:
        return {}
    try:
        status = json.loads(device['status_json'] or '{}')
    except (TypeError, ValueError):
        status = {}
    if (status.get('wifi_change_id') == change['change_id']
            and status.get('wifi_change_result') in ('applied', 'rolled_back')):
        return {
            'wifi_change_id': change['change_id'],
            'wifi_change_result': status['wifi_change_result'],
            'wifi_change_target': status.get('wifi_change_target'),
            'wifi_change_reason': status.get('wifi_change_reason'),
        }
    try:
        return {
            'wifi_change_id': change['change_id'],
            'wifi_ssid': current_app.config['MEDIA_CIPHER'].decrypt(
                change['ssid_cipher']).decode('utf-8'),
            'wifi_password': current_app.config['MEDIA_CIPHER'].decrypt(
                change['password_cipher']).decode('utf-8'),
        }
    except (InvalidToken, UnicodeDecodeError):
        current_app.logger.error('Unable to decrypt a queued Wi-Fi change')
        return {'wifi_change_id': change['change_id']}


def _update_device_status(device, payload):
    status = {}
    try:
        status = json.loads(device['status_json'] or '{}')
    except (TypeError, ValueError):
        pass
    if isinstance(payload, dict):
        status.update(payload)
    _db().execute(
        'UPDATE devices SET status_json = ?, last_seen = ? WHERE id = ?',
        (json.dumps(status, separators=(',', ':')), _utc_now(), device['id']),
    )
    _db().commit()


def _save_event(device, event_type, content, mime_type, filename, duration=None,
                has_audio=False, metadata=None):
    if content is not None and len(content) > current_app.config['MAX_EVENT_BYTES']:
        return None, 'event_too_large'
    event_id = uuid.uuid4().hex
    stored_name = None
    if content is not None:
        suffix = Path(secure_filename(filename or '')).suffix.lower()
        if suffix not in _ALLOWED_VIDEO_SUFFIXES and event_type == 'motion':
            suffix = '.mp4'
        elif suffix not in {'.jpg', '.jpeg', '.png'} and event_type == 'snapshot':
            suffix = '.jpg'
        stored_name = f'{event_id}{suffix}.enc'
        target = Path(current_app.config['MEDIA_DIR']) / stored_name
        temp = target.with_suffix(target.suffix + '.tmp')
        temp.write_bytes(current_app.config['MEDIA_CIPHER'].encrypt(content))
        temp.replace(target)
    _db().execute(
        '''INSERT INTO events
           (id, device_id, event_type, filename, mime_type, created_at,
            duration_seconds, has_audio, metadata_json)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        (event_id, device['id'], event_type, stored_name, mime_type,
         _utc_now(), duration, int(bool(has_audio)),
         json.dumps(metadata or {}, separators=(',', ':'))),
    )
    _db().commit()
    stale = _db().execute(
        '''SELECT id, filename FROM events WHERE device_id = ?
           ORDER BY created_at DESC, rowid DESC LIMIT -1 OFFSET 10''',
        (device['id'],),
    ).fetchall()
    for old_event in stale:
        if old_event['filename']:
            try:
                (Path(current_app.config['MEDIA_DIR']) / old_event['filename']).unlink(missing_ok=True)
            except OSError:
                pass
        _db().execute('DELETE FROM events WHERE id = ?', (old_event['id'],))
    if stale:
        _db().commit()
    return event_id, None


def _event_json(row):
    metadata = {}
    try:
        metadata = json.loads(row['metadata_json'] or '{}')
    except (TypeError, ValueError):
        pass
    return {
        'id': row['id'],
        'device_id': row['device_id'],
        'type': row['event_type'],
        'created_at': row['created_at'],
        'duration_seconds': row['duration_seconds'],
        'has_audio': bool(row['has_audio']),
        'metadata': metadata,
        'has_clip': bool(row['filename']),
    }


def create_app(test_config=None):
    app = Flask(__name__, template_folder='web/templates', static_folder='web/static')
    data_dir = Path(os.environ.get('MECAM_DATA_DIR', BASE_DIR / 'cloud_data')).resolve()
    app.config.from_mapping(
        SECRET_KEY=os.environ.get('MECAM_SECRET_KEY') or secrets.token_hex(32),
        DATABASE=str(data_dir / 'mecam.sqlite3'),
        MEDIA_DIR=str(data_dir / 'events'),
        MAX_CONTENT_LENGTH=100 * 1024 * 1024,
        MAX_EVENT_BYTES=90 * 1024 * 1024,
        STREAM_VIEW_TTL=12,
        SETUP_KEY=os.environ.get('MECAM_SETUP_KEY', ''),
        STORAGE_SECRET=os.environ.get('MECAM_STORAGE_KEY') or os.environ.get('MECAM_SECRET_KEY'),
        COOKIE_SECURE=os.environ.get('MECAM_COOKIE_SECURE', '0') == '1',
    )
    if test_config:
        app.config.update(test_config)
    storage_secret = app.config['STORAGE_SECRET'] or app.config['SECRET_KEY']
    storage_key = base64.urlsafe_b64encode(hashlib.sha256(
        str(storage_secret).encode('utf-8')
    ).digest())
    app.config['MEDIA_CIPHER'] = Fernet(storage_key)
    Path(app.config['DATABASE']).parent.mkdir(parents=True, exist_ok=True)
    Path(app.config['MEDIA_DIR']).mkdir(parents=True, exist_ok=True)
    _init_db(app)
    app.config.update(
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax',
        SESSION_COOKIE_SECURE=app.config['COOKIE_SECURE'],
    )

    @app.teardown_appcontext
    def close_db(_error=None):
        db = g.pop('db', None)
        if db is not None:
            db.close()

    @app.after_request
    def security_headers(response):
        response.headers.setdefault('X-Content-Type-Options', 'nosniff')
        response.headers.setdefault('X-Frame-Options', 'DENY')
        response.headers.setdefault('Referrer-Policy', 'same-origin')
        response.headers.setdefault('Cache-Control', 'no-store')
        return response

    @app.get('/healthz')
    def healthz():
        return jsonify({'ok': True})

    @app.route('/setup', methods=['GET', 'POST'])
    def setup():
        if _db().execute('SELECT 1 FROM users LIMIT 1').fetchone():
            return redirect(url_for('login'))
        error = None
        setup_key = current_app.config['SETUP_KEY']
        if request.method == 'POST':
            _check_csrf()
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '')
            if setup_key and not hmac.compare_digest(
                    request.form.get('setup_key', ''), setup_key):
                error = 'Invalid setup key.'
            elif len(username) < 3 or len(password) < 12:
                error = 'Use a username of at least 3 characters and a password of at least 12.'
            else:
                _db().execute(
                    'INSERT INTO users(username, password_hash, created_at) VALUES (?, ?, ?)',
                    (username, generate_password_hash(password), _utc_now()),
                )
                _db().commit()
                session.clear()
                session['username'] = username
                return redirect(url_for('dashboard'))
        return render_template('cloud_setup.html', error=error, csrf_token=_csrf_token())

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if not _db().execute('SELECT 1 FROM users LIMIT 1').fetchone():
            return redirect(url_for('setup'))
        error = None
        if request.method == 'POST':
            _check_csrf()
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '')
            user = _db().execute(
                'SELECT * FROM users WHERE username = ?', (username,)
            ).fetchone()
            if user and check_password_hash(user['password_hash'], password):
                session.clear()
                session['username'] = username
                return redirect(url_for('dashboard'))
            error = 'Invalid username or password.'
        return render_template('cloud_setup.html', login=True, error=error,
                               csrf_token=_csrf_token())

    @app.post('/logout')
    @_login_required
    def logout():
        _check_csrf()
        session.clear()
        return redirect(url_for('login'))

    @app.route('/account', methods=['GET', 'POST'])
    @_login_required
    def account():
        error = None
        notice = session.pop('account_notice', None)
        if request.method == 'POST':
            _check_csrf()
            current_password = request.form.get('current_password', '')
            new_password = request.form.get('new_password', '')
            user = _db().execute(
                'SELECT * FROM users WHERE username = ?', (session['username'],)
            ).fetchone()
            if not user or not check_password_hash(user['password_hash'], current_password):
                error = 'Current password is incorrect.'
            elif len(new_password) < 12:
                error = 'New password must be at least 12 characters.'
            else:
                _db().execute(
                    'UPDATE users SET password_hash = ? WHERE username = ?',
                    (generate_password_hash(new_password), session['username']),
                )
                _db().commit()
                session['account_notice'] = 'Password updated.'
                return redirect(url_for('account'))
        return render_template('cloud_account.html', username=session['username'],
                               csrf_token=_csrf_token(), error=error, notice=notice)

    @app.route('/config', methods=['GET'])
    @_login_required
    def config_page():
        devices = _db().execute('SELECT * FROM devices ORDER BY name').fetchall()
        device_status = {}
        for device in devices:
            try:
                status = json.loads(device['status_json'] or '{}')
            except (TypeError, ValueError):
                status = {}
            change = _db().execute(
                'SELECT change_id, expires_at FROM wifi_changes WHERE device_id = ?',
                (device['id'],),
            ).fetchone()
            device_status[device['id']] = {
                'ssid': status.get('wifi_ssid'),
                'result': status.get('wifi_change_result'),
                'reason': status.get('wifi_change_reason'),
                'pending': bool(change and change['expires_at'] > time.time()
                                and status.get('wifi_change_id') != change['change_id']),
            }
        return render_template(
            'cloud_config.html', devices=devices, device_status=device_status,
            csrf_token=_csrf_token(), notice=session.pop('config_notice', None),
        )

    @app.post('/config/wifi')
    @_login_required
    def queue_wifi_change():
        _check_csrf()
        try:
            device_id = int(request.form.get('device_id', ''))
        except (TypeError, ValueError):
            abort(400, description='Select a camera')
        ssid = request.form.get('ssid', '').strip()
        password = request.form.get('wifi_password', '')
        if not ssid or len(ssid) > 32 or not password or len(password) > 128:
            abort(400, description='Enter a valid network name and password')
        if _db().execute('SELECT 1 FROM devices WHERE id = ?', (device_id,)).fetchone() is None:
            abort(404)
        change_id = uuid.uuid4().hex
        cipher = current_app.config['MEDIA_CIPHER']
        _db().execute(
            '''INSERT INTO wifi_changes
               (device_id, change_id, ssid_cipher, password_cipher, expires_at, created_at)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(device_id) DO UPDATE SET
                 change_id=excluded.change_id,
                 ssid_cipher=excluded.ssid_cipher,
                 password_cipher=excluded.password_cipher,
                 expires_at=excluded.expires_at,
                 created_at=excluded.created_at''',
            (device_id, change_id, cipher.encrypt(ssid.encode()),
             cipher.encrypt(password.encode()), time.time() + 24 * 3600, _utc_now()),
        )
        _db().commit()
        session['config_notice'] = 'Wi-Fi update queued. The camera will apply it when online.'
        return redirect(url_for('config_page'))

    @app.get('/events')
    @_login_required
    def events_page():
        rows = _db().execute(
            '''SELECT events.*, devices.name AS camera_name
               FROM events JOIN devices ON devices.id = events.device_id
               ORDER BY events.created_at DESC, events.rowid DESC LIMIT 100'''
        ).fetchall()
        return render_template(
            'cloud_events.html', events=[dict(_event_json(row), camera_name=row['camera_name'])
                                          for row in rows],
            csrf_token=_csrf_token(),
        )

    @app.post('/events/<event_id>/delete')
    @_login_required
    def delete_event(event_id):
        _check_csrf()
        row = _db().execute('SELECT filename FROM events WHERE id = ?', (event_id,)).fetchone()
        if row is None:
            abort(404)
        if row['filename']:
            path = (Path(app.config['MEDIA_DIR']) / row['filename']).resolve()
            if Path(app.config['MEDIA_DIR']).resolve() not in path.parents:
                abort(404)
            try:
                path.unlink(missing_ok=True)
            except OSError:
                abort(503, description='Could not remove event media')
        _db().execute('DELETE FROM events WHERE id = ?', (event_id,))
        _db().commit()
        return redirect(url_for('events_page'))

    @app.get('/')
    @app.get('/dashboard')
    @_login_required
    def dashboard():
        devices = _db().execute(
            'SELECT * FROM devices ORDER BY created_at DESC'
        ).fetchall()
        event_rows = _db().execute(
            '''SELECT events.*, devices.name AS camera_name
               FROM events JOIN devices ON devices.id = events.device_id
             ORDER BY events.created_at DESC, events.rowid DESC LIMIT 10'''
        ).fetchall()
        event_data = []
        for row in event_rows:
            item = _event_json(row)
            item['camera_name'] = row['camera_name']
            event_data.append(item)
        status_by_device = {}
        for device in devices:
            try:
                status_by_device[device['id']] = json.loads(device['status_json'] or '{}')
            except (TypeError, ValueError):
                status_by_device[device['id']] = {}
        online_by_device = {}
        now = time.time()
        for device in devices:
            try:
                seen_at = datetime.fromisoformat(device['last_seen']).timestamp()
                online_by_device[device['id']] = now - seen_at < 120
            except (TypeError, ValueError, OSError):
                online_by_device[device['id']] = False
        return render_template(
            'cloud_dashboard.html', username=session['username'], devices=devices,
            events=event_data, status_by_device=status_by_device,
            online_by_device=online_by_device,
            csrf_token=_csrf_token(), activation_code=session.pop('activation_code', None),
            share_url=session.pop('share_url', None),
        )

    @app.post('/cameras')
    @_login_required
    def create_camera():
        _check_csrf()
        name = request.form.get('name', '').strip()[:80]
        if not name:
            abort(400, description='Camera name is required')
        code = secrets.token_urlsafe(24)
        _db().execute(
            'INSERT INTO enrollments(code_hash, camera_name, expires_at, created_at) VALUES (?, ?, ?, ?)',
            (_token_hash(code), name, time.time() + 48 * 3600, _utc_now()),
        )
        _db().commit()
        session['activation_code'] = code
        return redirect(url_for('dashboard'))

    @app.post('/cameras/<int:camera_id>/share')
    @_login_required
    def create_camera_share(camera_id):
        _check_csrf()
        if _db().execute('SELECT 1 FROM devices WHERE id = ?', (camera_id,)).fetchone() is None:
            abort(404)
        try:
            hours = int(request.form.get('hours', '24'))
        except (TypeError, ValueError):
            abort(400, description='Access duration must be a number of hours')
        if not 1 <= hours <= 168:
            abort(400, description='Temporary access must be between 1 and 168 hours')
        token = secrets.token_urlsafe(32)
        _db().execute(
            'INSERT INTO shares(token_hash, device_id, expires_at, created_at) VALUES (?, ?, ?, ?)',
            (_token_hash(token), camera_id, time.time() + hours * 3600, _utc_now()),
        )
        _db().commit()
        session['share_url'] = url_for('shared_camera', token=token, _external=True)
        return redirect(url_for('dashboard'))

    @app.post('/cameras/<int:camera_id>/share/revoke')
    @_login_required
    def revoke_camera_shares(camera_id):
        _check_csrf()
        _db().execute('DELETE FROM shares WHERE device_id = ?', (camera_id,))
        _db().commit()
        return redirect(url_for('dashboard'))

    @app.post('/cameras/<int:camera_id>/mode')
    @_login_required
    def set_camera_mode(camera_id):
        _check_csrf()
        mode = request.form.get('mode')
        if mode not in ('security', 'standby'):
            abort(400, description='Mode must be security or standby')
        cursor = _db().execute(
            'UPDATE devices SET camera_mode = ? WHERE id = ?', (mode, camera_id)
        )
        _db().commit()
        if cursor.rowcount == 0:
            abort(404)
        return redirect(url_for('dashboard'))

    @app.get('/events/<event_id>/clip')
    @_login_required
    def event_clip(event_id):
        row = _db().execute(
            'SELECT filename, mime_type FROM events WHERE id = ?', (event_id,)
        ).fetchone()
        if row is None or not row['filename']:
            abort(404)
        path = (Path(app.config['MEDIA_DIR']) / row['filename']).resolve()
        if Path(app.config['MEDIA_DIR']).resolve() not in path.parents or not path.is_file():
            abort(404)
        try:
            content = app.config['MEDIA_CIPHER'].decrypt(path.read_bytes())
        except (InvalidToken, OSError):
            abort(503, description='Stored event is temporarily unavailable')
        filename = Path(row['filename']).stem
        return send_file(BytesIO(content), mimetype=row['mime_type'] or 'video/mp4',
                         as_attachment=request.args.get('download') == '1',
                         download_name=filename)

    @app.get('/api/cameras/<int:camera_id>/events')
    @_login_required
    def camera_events(camera_id):
        rows = _db().execute(
            '''SELECT * FROM events WHERE device_id = ?
             ORDER BY created_at DESC, rowid DESC LIMIT 10''', (camera_id,)
        ).fetchall()
        return jsonify({'events': [_event_json(row) for row in rows]})

    @app.post('/camera/<int:camera_id>/listen')
    @_login_required
    def set_listen(camera_id):
        _check_csrf()
        if _db().execute('SELECT 1 FROM devices WHERE id = ?', (camera_id,)).fetchone() is None:
            abort(404)
        enabled = request.form.get('enabled') == '1'
        with _AUDIO_LOCK:
            was_active = _LISTENERS.get(camera_id, 0.0) > time.time()
            _LISTENERS[camera_id] = time.time() + 15 if enabled else 0
            if enabled and not was_active:
                _LISTEN_CHUNKS[camera_id] = deque(maxlen=40)
                _LISTEN_SEQUENCE[camera_id] = 0
            elif not enabled:
                _LISTEN_CHUNKS.pop(camera_id, None)
        return jsonify({'listen_requested': enabled})

    @app.get('/api/cameras/<int:camera_id>/listen-audio')
    @_login_required
    def listen_audio(camera_id):
        if _db().execute('SELECT 1 FROM devices WHERE id = ?', (camera_id,)).fetchone() is None:
            abort(404)
        after = request.args.get('after', default=0, type=int)
        with _AUDIO_LOCK:
            active = _LISTENERS.get(camera_id, 0.0) > time.time()
            if active:
                _LISTENERS[camera_id] = time.time() + 15
            chunks = list(_LISTEN_CHUNKS.get(camera_id, ()))
        return jsonify({
            'listen_requested': active,
            'chunks': [item for item in chunks if item['sequence'] > after],
        })

    @app.post('/api/cameras/<camera_ref>/listen-chunk')
    @_device_required
    def listen_chunk(camera_ref):
        if not _device_matches_ref(g.device, camera_ref):
            return jsonify({'error': 'device_mismatch'}), 403
        content_type = request.headers.get('Content-Type', '')
        chunk = request.get_data(cache=False)
        if not content_type.startswith('audio/pcm') or not chunk or len(chunk) > 64_000 or len(chunk) % 2:
            return jsonify({'error': 'invalid_pcm_chunk'}), 400
        camera_id = g.device['id']
        with _AUDIO_LOCK:
            sequence = _LISTEN_SEQUENCE.get(camera_id, 0) + 1
            _LISTEN_SEQUENCE[camera_id] = sequence
            chunks = _LISTEN_CHUNKS.setdefault(camera_id, deque(maxlen=40))
            chunks.append({
                'sequence': sequence,
                'pcm_b64': base64.b64encode(chunk).decode('ascii'),
                'sample_rate': 16000,
                'channels': 1,
            })
            active = _LISTENERS.get(camera_id, 0.0) > time.time()
        return jsonify({'listen_requested': active})

    @app.post('/api/cameras/<int:camera_id>/speak')
    @_login_required
    def queue_speak(camera_id):
        _check_csrf()
        device = _db().execute('SELECT * FROM devices WHERE id = ?', (camera_id,)).fetchone()
        if device is None:
            abort(404)
        content = request.get_data(cache=False)
        content_type = request.headers.get('Content-Type', 'audio/webm').split(';', 1)[0]
        if not content or len(content) > 8 * 1024 * 1024 or not content_type.startswith('audio/'):
            return jsonify({'error': 'invalid_audio_payload'}), 400
        item = {
            'item_id': uuid.uuid4().hex,
            'kind': 'talk',
            'audio_b64': base64.b64encode(content).decode('ascii'),
            'content_type': content_type,
        }
        with _AUDIO_LOCK:
            queue = _TALK_QUEUES.setdefault(camera_id, deque(maxlen=3))
            if len(queue) == queue.maxlen:
                return jsonify({'error': 'talk_queue_full'}), 429
            queue.append(item)
        return jsonify({'ok': True, 'item_id': item['item_id']}), 202

    @app.get('/api/cameras/<int:camera_id>/speak-queue')
    @_device_required
    def speak_queue(camera_id):
        if camera_id != g.device['id']:
            return jsonify({'error': 'device_mismatch'}), 403
        with _AUDIO_LOCK:
            queue = _TALK_QUEUES.setdefault(camera_id, deque())
            item = queue.popleft() if queue else None
            listening = _LISTENERS.get(camera_id, 0.0) > time.time()
        if item:
            return jsonify({'has_audio': True, 'listen_requested': listening, **item})
        return jsonify({'has_audio': False, 'listen_requested': listening})

    @app.post('/api/device/audio-report')
    @_device_required
    def audio_report():
        payload = request.get_json(silent=True) or {}
        return jsonify({'ok': True, 'item_id': str(payload.get('item_id') or '')[:64]})

    @app.get('/camera/<int:camera_id>/stream.mjpg')
    @_login_required
    def cloud_stream(camera_id):
        device = _db().execute('SELECT id FROM devices WHERE id = ?', (camera_id,)).fetchone()
        if device is None:
            abort(404)
        with _STREAM_LOCK:
            _STREAM_VIEWERS[camera_id] = time.time() + app.config['STREAM_VIEW_TTL']

        def generate():
            last_sequence = -1
            while True:
                with _STREAM_LOCK:
                    _STREAM_VIEWERS[camera_id] = time.time() + app.config['STREAM_VIEW_TTL']
                    frame = _STREAM_FRAMES.get(camera_id)
                if frame and frame[0] != last_sequence:
                    last_sequence, jpeg = frame
                    yield b'--frame\r\nContent-Type: image/jpeg\r\nContent-Length: ' + str(len(jpeg)).encode() + b'\r\n\r\n' + jpeg + b'\r\n'
                else:
                    yield b'\r\n'
                    time.sleep(0.2)
        return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame',
                        headers={'X-Accel-Buffering': 'no'})

    @app.get('/share/<token>')
    def shared_camera(token):
        share = _active_share(token)
        if share is None:
            abort(404)
        rows = _db().execute(
            '''SELECT * FROM events WHERE device_id = ?
               ORDER BY created_at DESC, rowid DESC LIMIT 10''', (share['device_id'],)
        ).fetchall()
        return render_template(
            'shared_camera.html', share=share, token=token,
            events=[_event_json(row) for row in rows],
            expires_at=datetime.fromtimestamp(share['expires_at'], timezone.utc),
        )

    @app.get('/share/<token>/stream.mjpg')
    def shared_stream(token):
        share = _active_share(token)
        if share is None:
            abort(404)
        camera_id = share['device_id']
        with _STREAM_LOCK:
            _STREAM_VIEWERS[camera_id] = time.time() + app.config['STREAM_VIEW_TTL']

        def generate():
            last_sequence = -1
            while _active_share(token):
                with _STREAM_LOCK:
                    _STREAM_VIEWERS[camera_id] = time.time() + app.config['STREAM_VIEW_TTL']
                    frame = _STREAM_FRAMES.get(camera_id)
                if frame and frame[0] != last_sequence:
                    last_sequence, jpeg = frame
                    yield b'--frame\r\nContent-Type: image/jpeg\r\nContent-Length: ' + str(len(jpeg)).encode() + b'\r\n\r\n' + jpeg + b'\r\n'
                else:
                    yield b'\r\n'
                    time.sleep(0.2)
        return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame',
                        headers={'X-Accel-Buffering': 'no'})

    @app.get('/share/<token>/events/<event_id>/clip')
    def shared_event_clip(token, event_id):
        share = _active_share(token)
        if share is None:
            abort(404)
        row = _db().execute(
            'SELECT filename, mime_type FROM events WHERE id = ? AND device_id = ?',
            (event_id, share['device_id']),
        ).fetchone()
        if row is None or not row['filename']:
            abort(404)
        path = (Path(app.config['MEDIA_DIR']) / row['filename']).resolve()
        if Path(app.config['MEDIA_DIR']).resolve() not in path.parents or not path.is_file():
            abort(404)
        try:
            content = app.config['MEDIA_CIPHER'].decrypt(path.read_bytes())
        except (InvalidToken, OSError):
            abort(503, description='Stored event is temporarily unavailable')
        return send_file(BytesIO(content), mimetype=row['mime_type'] or 'video/mp4',
                         as_attachment=request.args.get('download') == '1',
                         download_name=Path(row['filename']).stem)

    @app.get('/api/cameras/<camera_ref>/stream-command')
    @_device_required
    def stream_command(camera_ref):
        if not _device_matches_ref(g.device, camera_ref):
            return jsonify({'error': 'device_mismatch'}), 403
        device = _db().execute(
            'SELECT * FROM devices WHERE id = ?', (g.device['id'],)
        ).fetchone()
        result = _device_reply(device)
        return jsonify({
            'camera_mode': device['camera_mode'],
            'stream_requested': result['stream_requested'],
            'listen_requested': _listen_requested(device['id']),
            'speak_pending': bool(_TALK_QUEUES.get(device['id'])),
            **_wifi_change_payload(device),
            'stream_fps': 10,
            'stream_fps_set': False,
        })

    @app.post('/api/cameras/<camera_ref>/live-frame')
    @_device_required
    def live_frame(camera_ref):
        if not _device_matches_ref(g.device, camera_ref):
            return jsonify({'error': 'device_mismatch'}), 403
        jpeg = request.get_data(cache=False)
        if not jpeg or len(jpeg) > 500_000 or not jpeg.startswith(b'\xff\xd8'):
            return jsonify({'error': 'invalid_jpeg_frame'}), 400
        with _STREAM_LOCK:
            camera_id = g.device['id']
            previous = _STREAM_FRAMES.get(camera_id)
            sequence = (previous[0] + 1) if previous else 1
            _STREAM_FRAMES[camera_id] = (sequence, jpeg)
            stream_requested = _STREAM_VIEWERS.get(camera_id, 0) > time.time()
        return jsonify({'stream_requested': stream_requested})

    @app.post('/api/device/activate')
    def activate_device():
        payload = request.get_json(silent=True) or {}
        code = str(payload.get('activation_code') or '')
        device_id = str(payload.get('device_id') or '').strip()[:128]
        if not code or not device_id:
            return jsonify({'error': 'activation_code_and_device_id_required'}), 400
        code_hash = _token_hash(code)
        db = _db()
        enrollment = db.execute(
            'SELECT * FROM enrollments WHERE code_hash = ? AND expires_at > ?',
            (code_hash, time.time()),
        ).fetchone()
        existing = db.execute(
            'SELECT * FROM devices WHERE activation_hash = ?', (code_hash,)
        ).fetchone()
        if enrollment is None and (existing is None or existing['device_id'] != device_id):
            return jsonify({'error': 'activation_code_invalid_or_expired'}), 403
        if existing is not None and existing['device_id'] != device_id:
            return jsonify({'error': 'device_mismatch'}), 403
        token = secrets.token_urlsafe(32)
        if existing:
            db.execute('UPDATE devices SET token_hash = ?, last_seen = ? WHERE id = ?',
                       (_token_hash(token), _utc_now(), existing['id']))
            device_name = existing['name']
        else:
            device_name = enrollment['camera_name']
            db.execute(
                '''INSERT INTO devices
                   (device_id, name, token_hash, activation_hash, camera_mode, last_seen, created_at)
                   VALUES (?, ?, ?, ?, 'security', ?, ?)''',
                (device_id, device_name, _token_hash(token), code_hash, _utc_now(), _utc_now()),
            )
            db.execute('DELETE FROM enrollments WHERE code_hash = ?', (code_hash,))
        db.commit()
        return jsonify({'device_token': token, 'camera_name': device_name}), 200

    @app.route('/api/device/status', methods=['GET', 'POST'])
    @_device_required
    def device_status():
        if request.method == 'POST':
            _update_device_status(g.device, request.get_json(silent=True) or {})
            device = _db().execute('SELECT * FROM devices WHERE id = ?', (g.device['id'],)).fetchone()
        else:
            _db().execute('UPDATE devices SET last_seen = ? WHERE id = ?', (_utc_now(), g.device['id']))
            _db().commit()
            device = g.device
        result = _device_reply(device)
        try:
            result.update(json.loads(device['status_json'] or '{}'))
        except (TypeError, ValueError):
            pass
        result.update({'camera_id': device['id'], 'device_id': device['device_id'],
                       'camera_mode': device['camera_mode'],
                       'armed': device['camera_mode'] == 'security'})
        result.update(_wifi_change_payload(device))
        return jsonify(result)

    @app.post('/api/device/heartbeat')
    @_device_required
    def device_heartbeat():
        payload = request.get_json(silent=True) or {}
        _update_device_status(g.device, payload.get('capabilities') or {})
        return jsonify({'ok': True, 'camera_id': g.device['id'],
                        'camera_mode': g.device['camera_mode']})

    @app.post('/api/stream/update')
    @_device_required
    def stream_update():
        payload = request.get_json(silent=True) or {}
        stream_url = str(payload.get('stream_url') or '')[:512]
        _db().execute('UPDATE devices SET stream_url = ?, last_seen = ? WHERE id = ?',
                      (stream_url, _utc_now(), g.device['id']))
        _db().commit()
        return jsonify({'ok': True})

    @app.post('/api/motion/with-clip')
    @_device_required
    def motion_with_clip():
        if g.device['camera_mode'] != 'security':
            return jsonify({'error': 'camera_disarmed'}), 409
        upload = request.files.get('video')
        if upload is None:
            return jsonify({'error': 'video_required'}), 400
        filename = secure_filename(upload.filename or 'motion.mp4')
        content = upload.read(current_app.config['MAX_EVENT_BYTES'] + 1)
        form_meta = {key: request.form.get(key) for key in ('category', 'confidence', 'motion_peak_pct', 'ghost_verdict') if request.form.get(key) is not None}
        try:
            duration = max(0, min(3600, int(request.form.get('duration_seconds', 0))))
        except (TypeError, ValueError):
            duration = None
        event_id, error = _save_event(
            g.device, 'motion', content, upload.mimetype or 'video/mp4', filename,
            duration, request.form.get('has_audio', '').lower() == 'true', form_meta,
        )
        if error:
            return jsonify({'error': error}), 413
        return jsonify({'ok': True, 'event_id': event_id}), 201

    @app.post('/api/motion')
    @_device_required
    def motion_alert():
        if g.device['camera_mode'] != 'security':
            return jsonify({'error': 'camera_disarmed'}), 409
        payload = request.get_json(silent=True) or {}
        event_id, _error = _save_event(g.device, 'motion', None, None, None,
                                       metadata=payload)
        return jsonify({'ok': True, 'event_id': event_id}), 201

    @app.post('/api/snapshot')
    @_device_required
    def snapshot_upload():
        content = None
        filename = request.files.get('snapshot') or request.files.get('image')
        if filename:
            content = filename.read(current_app.config['MAX_EVENT_BYTES'] + 1)
            mime_type = filename.mimetype or 'image/jpeg'
            name = filename.filename or 'snapshot.jpg'
        else:
            payload = request.get_json(silent=True) or {}
            encoded = payload.get('image_b64') or payload.get('snapshot_b64')
            if encoded:
                try:
                    content = base64.b64decode(encoded, validate=True)
                except (ValueError, TypeError):
                    return jsonify({'error': 'invalid_image'}), 400
            mime_type = 'image/jpeg'
            name = 'snapshot.jpg'
        if not content:
            return jsonify({'error': 'snapshot_required'}), 400
        event_id, error = _save_event(g.device, 'snapshot', content, mime_type,
                                      name, metadata=request.form.to_dict())
        if error:
            return jsonify({'error': error}), 413
        return jsonify({'ok': True, 'event_id': event_id}), 201

    @app.errorhandler(sqlite3.IntegrityError)
    def integrity_error(_error):
        return jsonify({'error': 'conflict'}), 409

    return app


app = create_app()


if __name__ == '__main__':
    app.run(
        host=os.environ.get('MECAM_HOST', '127.0.0.1'),
        port=int(os.environ.get('PORT', '8081')),
        threaded=True,
    )
