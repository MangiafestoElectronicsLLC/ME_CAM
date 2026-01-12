from flask import (
    Flask, render_template, request, redirect,
    url_for, session, jsonify
)
from threading import Event
from loguru import logger
import os

from config_manager import get_config, save_config, is_first_run, mark_first_run_complete
from watchdog import CameraWatchdog
from camera_pipeline import CameraPipeline

app = Flask(__name__)
app.secret_key = os.urandom(24)

watchdog = CameraWatchdog()
watchdog.start()  # start pipeline thread on boot


@app.before_request
def ensure_first_run_redirect():
    if request.path.startswith("/static"):
        return
    if is_first_run() and request.path not in ("/setup", "/setup/save"):
        return redirect(url_for("setup"))


@app.route("/setup", methods=["GET"])
def setup():
    cfg = get_config()
    return render_template("first_run.html", config=cfg)


@app.route("/setup/save", methods=["POST"])
def setup_save():
    cfg = get_config()

    cfg["device_name"] = request.form.get("device_name", cfg["device_name"])

    pin_enabled = request.form.get("pin_enabled") == "on"
    pin_code = request.form.get("pin_code") or cfg["pin_code"]
    cfg["pin_enabled"] = pin_enabled
    cfg["pin_code"] = pin_code

    cfg["storage"]["retention_days"] = int(request.form.get("retention_days") or 7)
    cfg["storage"]["motion_only"] = (request.form.get("motion_only") == "on")

    cfg["detection"]["person_only"] = (request.form.get("person_only") == "on")
    cfg["detection"]["sensitivity"] = float(request.form.get("sensitivity") or 0.6)

    # (Hooks for email/gdrive can be added here later)

    save_config(cfg)
    mark_first_run_complete()
    logger.info("[SETUP] First run completed.")
    return redirect(url_for("index"))


@app.route("/login", methods=["GET", "POST"])
def login():
    cfg = get_config()
    if request.method == "POST":
        pin = request.form.get("pin")
        try:
            if not cfg.get("pin_enabled", True) or pin == cfg.get("pin_code"):
                session["authenticated"] = True
                return redirect(url_for("index"))
            else:
                return render_template("login.html", error="Invalid PIN")
        except Exception as e:
            logger.warning(f"[PIN] Crash during PIN check: {e}")
            return render_template("login.html", error="PIN error, check config.")
    return render_template("login.html")


def require_auth():
    cfg = get_config()
    if cfg.get("pin_enabled", True) and not session.get("authenticated"):
        return False
    return True


@app.route("/")
def index():
    if not require_auth():
        return redirect(url_for("login"))

    try:
        # lightweight pipeline check for dashboard
        temp_pipeline = CameraPipeline(Event(), preview_only=True)
        status = watchdog.status()
        return render_template("dashboard.html", status=status)
    except Exception as e:
        logger.warning(f"[DASHBOARD] Fallback triggered: {e}")
        return render_template(
            "fallback.html",
            message="Camera pipeline unavailable. Check camera, model file, or config."
        )


@app.route("/api/status")
def api_status():
    return jsonify(watchdog.status())


@app.route("/api/trigger_emergency", methods=["POST"])
def trigger_emergency():
    """
    Hook to send latest motion clip to 'first responders':
    - future: upload to GDrive, email link, hit webhook, etc.
    """
    try:
        last_clip = watchdog.get_last_motion_clip()
        # TODO: actual email/gdrive/webhook integration
        logger.info(f"[EMERGENCY] Triggered for clip: {last_clip}")
        return jsonify({"ok": True, "clip": last_clip})
    except Exception as e:
        logger.error(f"[EMERGENCY] Failed: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500


# -------- Multi-camera dashboard (central node) --------

@app.route("/multicam")
def multicam():
    """
    This is for a separate 'hub' Pi or PC that monitors multiple ME_CAM nodes.
    Devices are configured manually in a list for now.
    """
    devices = [
        {"name": "Front Door", "url": "http://10.2.1.4:8080"},
        {"name": "Back Door", "url": "http://10.2.1.5:8080"}
        # etc., pulled from a config later
    ]
    return render_template("multicam.html", devices=devices)
