from flask import Flask, render_template, request, redirect, url_for, session, jsonify, Response
from threading import Event
from loguru import logger
import os
from datetime import datetime
import time
import sys

# Add parent directory to path so we can import modules from the root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config_manager import get_config, save_config, is_first_run, mark_first_run_complete
from watchdog import CameraWatchdog
from camera_pipeline import CameraPipeline
from battery_monitor import BatteryMonitor
from thumbnail_gen import extract_thumbnail
from user_auth import authenticate, create_user, user_exists, get_user
from qr_generator import generate_setup_qr

# Flask app
app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = os.urandom(24)

# Core services
watchdog = CameraWatchdog()
watchdog.start()

battery = BatteryMonitor(enabled=True)

# NEW CAMERA PIPELINE (libcamera-vid MJPEG)
pipeline = CameraPipeline()

# Base directory
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


# ------------------------------
# Helpers
# ------------------------------

def _recordings_path(cfg):
    rec_dir = cfg.get("storage", {}).get("recordings_dir", "recordings")
    return os.path.join(BASE_DIR, rec_dir)


def get_recordings(cfg, limit=12):
    path = _recordings_path(cfg)
    thumb_dir = os.path.join(BASE_DIR, "web", "static", "thumbs")
    videos = []
    try:
        os.makedirs(thumb_dir, exist_ok=True)
        if os.path.isdir(path):
            for name in os.listdir(path):
                if name.lower().endswith((".mp4", ".mov", ".avi", ".mkv")):
                    full = os.path.join(path, name)
                    ts = os.path.getmtime(full)
                    thumb_path = extract_thumbnail(full, thumb_dir)
                    thumb_url = f"/static/thumbs/{os.path.basename(thumb_path)}" if thumb_path else None
                    videos.append({
                        "name": name,
                        "date": datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M"),
                        "thumb_url": thumb_url
                    })
        videos.sort(key=lambda v: v["date"], reverse=True)
    except Exception as e:
        logger.warning(f"[RECORDINGS] Failed to list recordings: {e}")
    return videos[:limit]


def get_storage_used_gb(cfg):
    paths = [
        _recordings_path(cfg),
        os.path.join(BASE_DIR, cfg.get("storage", {}).get("encrypted_dir", "recordings_encrypted"))
    ]
    total_bytes = 0
    try:
        for path in paths:
            if not os.path.isdir(path):
                continue
            for root, _, files in os.walk(path):
                for f in files:
                    try:
                        total_bytes += os.path.getsize(os.path.join(root, f))
                    except Exception:
                        pass
    except Exception as e:
        logger.warning(f"[STORAGE] Failed to compute size: {e}")
    return round(total_bytes / (1024 ** 3), 2)


def count_recent_events(cfg, hours=24):
    cutoff_ts = (datetime.now()).timestamp() - (hours * 3600)
    count = 0
    try:
        path = _recordings_path(cfg)
        if os.path.isdir(path):
            for name in os.listdir(path):
                if name.lower().endswith((".mp4", ".mov", ".avi", ".mkv")):
                    full = os.path.join(path, name)
                    if os.path.getmtime(full) >= cutoff_ts:
                        count += 1
        enc = os.path.join(BASE_DIR, cfg.get("storage", {}).get("encrypted_dir", "recordings_encrypted"))
        if os.path.isdir(enc):
            for name in os.listdir(enc):
                if name.lower().endswith(".enc"):
                    full = os.path.join(enc, name)
                    if os.path.getmtime(full) >= cutoff_ts:
                        count += 1
    except Exception as e:
        logger.warning(f"[HISTORY] Failed to count recent events: {e}")
    return count


# ------------------------------
# First-run redirect
# ------------------------------

@app.before_request
def ensure_first_run_redirect():
    if request.path.startswith("/static"):
        return
    if is_first_run() and request.path not in ("/setup", "/setup/save"):
        return redirect(url_for("setup"))


# ------------------------------
# Setup Wizard
# ------------------------------

@app.route("/setup", methods=["GET"])
def setup():
    cfg = get_config()
    qr_code = generate_setup_qr("raspberrypi")
    setup_url = f"http://raspberrypi.local:8080/setup"
    return render_template("first_run.html", config=cfg, qr_code=qr_code, setup_url=setup_url)


@app.route("/setup/save", methods=["POST"])
def setup_save():
    cfg = get_config()
    cfg["device_name"] = request.form.get("device_name", cfg["device_name"])
    cfg["pin_enabled"] = request.form.get("pin_enabled") == "on"
    cfg["pin_code"] = request.form.get("pin_code") or cfg["pin_code"]
    cfg["storage"]["retention_days"] = int(request.form.get("retention_days") or 7)
    cfg["storage"]["motion_only"] = request.form.get("motion_only") == "on"
    cfg["storage"]["encrypt"] = request.form.get("encrypt") == "on"
    cfg["detection"]["person_only"] = request.form.get("person_only") == "on"
    cfg["detection"]["sensitivity"] = float(request.form.get("sensitivity") or 0.6)
    cfg["emergency_phone"] = request.form.get("emergency_phone", "")
    save_config(cfg)
    mark_first_run_complete()
    logger.info("[SETUP] First run completed.")
    return redirect(url_for("index"))


# ------------------------------
# Authentication
# ------------------------------

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        if authenticate(username, password):
            session["authenticated"] = True
            session["username"] = username
            logger.info(f"[AUTH] User {username} logged in")
            return redirect(url_for("index"))
        return render_template("login.html", error="Invalid username or password")
    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        password_confirm = request.form.get("password_confirm", "")

        if not username or len(username) < 3:
            return render_template("register.html", error="Username must be at least 3 characters")
        if not password or len(password) < 6:
            return render_template("register.html", error="Password must be at least 6 characters")
        if password != password_confirm:
            return render_template("register.html", error="Passwords don't match")
        if user_exists(username):
            return render_template("register.html", error="Username already exists")

        if create_user(username, password):
            logger.info(f"[AUTH] New user registered: {username}")
            return render_template("register.html", success="Account created! Please login.")
        return render_template("register.html", error="Error creating account")

    return render_template("register.html")


def require_auth():
    return session.get("authenticated", False)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ------------------------------
# Dashboard
# ------------------------------

@app.route("/")
@app.route("/dashboard")
def index():
    if not require_auth():
        return redirect(url_for("login"))

    username = session.get("username", "User")
    try:
        cfg = get_config()
        status = watchdog.status()
        battery_status = battery.get_status()
        videos = get_recordings(cfg, limit=12)
        storage_used = get_storage_used_gb(cfg)
        history_count = count_recent_events(cfg, hours=24)

        return render_template(
            "user_dashboard.html",
            username=username,
            device_name=cfg.get("device_name", "ME_CAM_1"),
            status=status,
            battery_percent=battery_status.get("percent"),
            battery_external=battery_status.get("external_power"),
            battery_low=battery_status.get("is_low"),
            storage_used=storage_used,
            video_count=len(videos),
            videos=videos,
            history_count=history_count,
            emergency_phone=cfg.get("emergency_phone", "Not configured")
        )
    except Exception as e:
        logger.warning(f"[DASHBOARD] Fallback: {e}")
        return render_template("fallback.html", message="Camera unavailable")


# ------------------------------
# MJPEG STREAMING (NEW)
# ------------------------------

def mjpeg_generator():
    for frame in pipeline.mjpeg_frames():
        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n" +
            frame +
            b"\r\n"
        )


@app.route("/stream.mjpg")
def stream_mjpg():
    if not require_auth():
        return redirect(url_for("login"))
    return Response(
        mjpeg_generator(),
        mimetype="multipart/x-mixed-replace; boundary=frame"
    )


# ------------------------------
# Settings (/config)
# ------------------------------

@app.route("/config", methods=["GET", "POST"])
def settings():
    if not require_auth():
        return redirect(url_for("login"))

    cfg = get_config()

    if request.method == "POST":
        try:
            # Existing settings
            cfg["wifi_enabled"] = request.form.get("wifi_enabled") == "on"
            cfg["bluetooth_enabled"] = request.form.get("bluetooth_enabled") == "on"

            if "email" not in cfg:
                cfg["email"] = {}
            cfg["email"]["enabled"] = request.form.get("email_enabled") == "on"
            cfg["email"]["smtp_server"] = request.form.get("smtp_server", "")
            cfg["email"]["smtp_port"] = int(request.form.get("smtp_port", 587))
            cfg["email"]["username"] = request.form.get("email_username", "")
            cfg["email"]["password"] = request.form.get("email_password", "")
            cfg["email"]["from_address"] = request.form.get("email_from", "")
            cfg["email"]["to_address"] = request.form.get("email_to", "")

            if "google_drive" not in cfg:
                cfg["google_drive"] = {}
            cfg["google_drive"]["enabled"] = request.form.get("gdrive_enabled") == "on"
            cfg["google_drive"]["folder_id"] = request.form.get("gdrive_folder_id", "")

            if "notifications" not in cfg:
                cfg["notifications"] = {}
            cfg["notifications"]["email_on_motion"] = cfg["email"]["enabled"]
            cfg["notifications"]["gdrive_on_motion"] = cfg["google_drive"]["enabled"]

            # NEW: Resolution + FPS
            cfg["stream_resolution"] = request.form.get("stream_resolution", "1536x864")
            cfg["stream_fps"] = int(request.form.get("stream_fps", 15))

            save_config(cfg)
            pipeline.update_stream_settings()

            logger.info("[SETTINGS] Configuration updated successfully.")
            return redirect(url_for("settings"))

        except Exception as e:
            logger.error(f"[SETTINGS] Error saving configuration: {e}")
            return render_template("config.html", config=cfg, error=f"Failed to save settings: {str(e)}")

    return render_template("config.html", config=cfg)


# ------------------------------
# API
# ------------------------------

@app.route("/api/status")
def api_status():
    return jsonify(watchdog.status())


@app.route("/api/trigger_emergency", methods=["POST"])
def trigger_emergency():
    try:
        cfg = get_config()
        emergency_phone = cfg.get('emergency_phone', 'Not configured')
        logger.info(f"[EMERGENCY] Emergency triggered - Contact: {emergency_phone}")
        return jsonify({
            "ok": True,
            "message": "Emergency contact notified",
            "contact": emergency_phone,
            "timestamp": time.time()
        })
    except Exception as e:
        logger.error(f"[EMERGENCY] Error triggering emergency: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500


# ------------------------------
# Main
# ------------------------------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=False)
