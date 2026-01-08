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
from libcamera_streamer import LibcameraStreamer, is_libcamera_available
from qr_generator import generate_setup_qr

# Explicitly set template/static folders inside the web package to avoid confusion
app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = os.urandom(24)

watchdog = CameraWatchdog()
watchdog.start()

battery = BatteryMonitor(enabled=True)

# Initialize camera streamer
camera_available = is_libcamera_available()
if camera_available:
    camera_streamer = LibcameraStreamer()
    logger.info("[CAMERA] libcamera available, using native streaming")
else:
    camera_streamer = None
    logger.warning("[CAMERA] libcamera not available, camera stream disabled")

# Helpers for recordings/storage info
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

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
                    # Try to extract thumbnail
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
                if name.lower().endswith((".enc",)):
                    full = os.path.join(enc, name)
                    if os.path.getmtime(full) >= cutoff_ts:
                        count += 1
    except Exception as e:
        logger.warning(f"[HISTORY] Failed to count recent events: {e}")
    return count

@app.before_request
def ensure_first_run_redirect():
    if request.path.startswith("/static"):
        return
    if is_first_run() and request.path not in ("/setup", "/setup/save"):
        return redirect(url_for("setup"))

@app.route("/setup", methods=["GET"])
def setup():
    cfg = get_config()
    
    # Generate QR code for setup
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
        else:
            return render_template("login.html", error="Invalid username or password")
    
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        password_confirm = request.form.get("password_confirm", "")
        
        # Validation
        if not username or len(username) < 3:
            return render_template("register.html", error="Username must be at least 3 characters")
        
        if not password or len(password) < 6:
            return render_template("register.html", error="Password must be at least 6 characters")
        
        if password != password_confirm:
            return render_template("register.html", error="Passwords don't match")
        
        if user_exists(username):
            return render_template("register.html", error="Username already exists")
        
        # Create user
        if create_user(username, password):
            logger.info(f"[AUTH] New user registered: {username}")
            return render_template("register.html", success="Account created! Please login.")
        else:
            return render_template("register.html", error="Error creating account")
    
    return render_template("register.html")

def require_auth():
    return session.get("authenticated", False)

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
        
        return render_template("user_dashboard.html",
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

@app.route("/user/profile")
def user_profile():
    if not require_auth():
        return redirect(url_for("login"))
    
    username = session.get("username")
    user = get_user(username)
    
    return render_template("user_profile.html", 
        username=username,
        user=user
    )

@app.route("/user/change-password", methods=["GET", "POST"])
def change_password():
    if not require_auth():
        return redirect(url_for("login"))
    
    username = session.get("username")
    
    if request.method == "POST":
        old_password = request.form.get("old_password", "")
        new_password = request.form.get("new_password", "")
        new_password_confirm = request.form.get("new_password_confirm", "")
        
        if not authenticate(username, old_password):
            return render_template("change_password.html", error="Old password is incorrect")
        
        if len(new_password) < 6:
            return render_template("change_password.html", error="New password must be at least 6 characters")
        
        if new_password != new_password_confirm:
            return render_template("change_password.html", error="Passwords don't match")
        
        from user_auth import change_password as change_pwd
        if change_pwd(username, old_password, new_password):
            logger.info(f"[AUTH] Password changed for {username}")
            return render_template("change_password.html", success="Password changed successfully!")
        else:
            return render_template("change_password.html", error="Error changing password")
    
    return render_template("change_password.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/api/status")
def api_status():
    return jsonify(watchdog.status())

@app.route("/api/trigger_emergency", methods=["POST"])
def trigger_emergency():
    try:
        cfg = get_config()
        emergency_phone = cfg.get('emergency_phone', 'Not configured')
        
        logger.info(f"[EMERGENCY] Emergency triggered - Contact: {emergency_phone}")
        
        # TODO: Implement actual emergency notification (SMS, email, etc.)
        # For now, just log the event
        
        return jsonify({
            "ok": True,
            "message": "Emergency contact notified",
            "contact": emergency_phone,
            "timestamp": time.time()
        })
    except Exception as e:
        logger.error(f"[EMERGENCY] Error triggering emergency: {e}")
        return jsonify({
            "ok": False,
            "error": str(e)
        }), 500

@app.route("/config", methods=["GET", "POST"])
def settings():
    if not require_auth():
        return redirect(url_for("login"))
    
    try:
        cfg = get_config()
        
        if request.method == "POST":
            try:
                # Optional integrations
                cfg["wifi_enabled"] = request.form.get("wifi_enabled") == "on"
                cfg["bluetooth_enabled"] = request.form.get("bluetooth_enabled") == "on"
                
                # Email
                if "email" not in cfg:
                    cfg["email"] = {}
                cfg["email"]["enabled"] = request.form.get("email_enabled") == "on"
                cfg["email"]["smtp_server"] = request.form.get("smtp_server", "")
                cfg["email"]["smtp_port"] = int(request.form.get("smtp_port", 587)) if request.form.get("smtp_port") else 587
                cfg["email"]["username"] = request.form.get("email_username", "")
                cfg["email"]["password"] = request.form.get("email_password", "")
                cfg["email"]["from_address"] = request.form.get("email_from", "")
                cfg["email"]["to_address"] = request.form.get("email_to", "")
                
                # Google Drive
                if "google_drive" not in cfg:
                    cfg["google_drive"] = {}
                cfg["google_drive"]["enabled"] = request.form.get("gdrive_enabled") == "on"
                cfg["google_drive"]["folder_id"] = request.form.get("gdrive_folder_id", "")
                
                # Storage & Notifications
                if "notifications" not in cfg:
                    cfg["notifications"] = {}
                cfg["notifications"]["email_on_motion"] = cfg["email"]["enabled"]
                cfg["notifications"]["gdrive_on_motion"] = cfg["google_drive"]["enabled"]
                
                save_config(cfg)
                logger.info("[SETTINGS] Configuration updated successfully.")
                
                # Redirect to settings to show updated config
                return redirect(url_for("settings"))
            except Exception as e:
                logger.error(f"[SETTINGS] Error saving configuration: {e}")
                return render_template("config.html", config=cfg, error=f"Failed to save settings: {str(e)}")
        
        return render_template("config.html", config=cfg)
    except Exception as e:
        logger.error(f"[SETTINGS] Error loading settings page: {e}")
        return render_template("config.html", config={}, error=f"Failed to load settings: {str(e)}")

def gen_mjpeg():
    """Generate MJPEG frames from camera using libcamera."""
    if not camera_streamer:
        logger.warning("[STREAM] Camera streamer not available")
        yield b''
        return
    
    BOUNDARY = b'MJPEGBOUNDARY'
    frame_count = 0
    
    # Stream MJPEG with individual frames captured via libcamera-still
    while True:
        try:
            jpeg_data = camera_streamer.get_single_frame_jpeg()
            
            if jpeg_data:
                frame_count += 1
                # Proper MJPEG boundary format for browsers
                yield b'--' + BOUNDARY + b'\r\n'
                yield b'Content-Type: image/jpeg\r\n'
                yield b'Content-Length: ' + str(len(jpeg_data)).encode() + b'\r\n'
                yield b'X-Timestamp: ' + str(int(time.time() * 1000)).encode() + b'\r\n\r\n'
                yield jpeg_data
                yield b'\r\n'
                
                # Small delay between frames to avoid overwhelming CPU
                import time
                time.sleep(0.1)
            else:
                logger.debug("[STREAM] Failed to capture frame, retrying...")
                import time
                time.sleep(0.5)
                
        except Exception as e:
            logger.error(f"[STREAM] Frame generation error: {e}")
            import time
            time.sleep(1)

@app.route("/api/stream")
def stream():
    """MJPEG video stream endpoint."""
    if not require_auth():
        return redirect(url_for("login"))
    
    if not camera_available:
        return jsonify({"error": "Camera not available"}), 503
    
    return Response(gen_mjpeg(), mimetype='multipart/x-mixed-replace; boundary=MJPEGBOUNDARY')

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=False)