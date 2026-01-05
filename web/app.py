import os
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    send_file,
    flash,
)
from werkzeug.utils import secure_filename

from config_manager import (
    load_config,
    save_config,
    verify_dashboard_pin,
    set_dashboard_pin,
    export_config,
    import_config,
)
from watchdog import CameraWatchdog
from utils.logger import get_logger

logger = get_logger("web_dashboard")

app = Flask(__name__)
app.secret_key = os.environ.get("ME_CAMERA_SECRET_KEY", "dev-secret-key")

EXPORT_DIR = "exports"
os.makedirs(EXPORT_DIR, exist_ok=True)

watchdog = CameraWatchdog()


def is_authenticated() -> bool:
    return session.get("logged_in", False)


@app.before_first_request
def start_pipeline():
    watchdog_thread = os.environ.get("ME_CAMERA_NO_PIPELINE", "0")
    if watchdog_thread == "0":
        from threading import Thread
        t = Thread(target=watchdog.supervise, daemon=True)
        t.start()
        logger.info("Camera watchdog started from Flask app.")


@app.route("/login", methods=["GET", "POST"])
def login():
    config = load_config()
    if request.method == "POST":
        pin = request.form.get("pin", "")
        if not config.get("dashboard_pin_hash"):
            # First time: set PIN
            if not pin:
                flash("PIN required.")
            else:
                set_dashboard_pin(pin)
                session["logged_in"] = True
                return redirect(url_for("index"))
        else:
            if verify_dashboard_pin(pin):
                session["logged_in"] = True
                return redirect(url_for("index"))
            else:
                flash("Invalid PIN.")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
def index():
    if not is_authenticated():
        return redirect(url_for("login"))

    from camera_pipeline import CameraPipeline
    from threading import Event

    # temporary pipeline for status only (you may want a shared instance)
    temp_pipeline = CameraPipeline(Event())
    battery = temp_pipeline.get_battery_status()

    config = load_config()
    return render_template(
        "index.html",
        battery=battery,
        alerts=config["alerts"],
        motion=config["motion"],
    )


@app.route("/config", methods=["GET", "POST"])
def config_page():
    if not is_authenticated():
        return redirect(url_for("login"))

    config = load_config()
    if request.method == "POST":
        sensitivity = float(request.form.get("sensitivity", 0.5))
        config["motion"]["sensitivity"] = sensitivity
        save_config(config)
        flash("Configuration updated.")
        return redirect(url_for("config_page"))

    return render_template("config.html", config=config)


@app.route("/config/export")
def config_export():
    if not is_authenticated():
        return redirect(url_for("login"))

    export_path = os.path.join(EXPORT_DIR, "config_export.json")
    export_config(export_path)
    return send_file(export_path, as_attachment=True)


@app.route("/config/import", methods=["POST"])
def config_import():
    if not is_authenticated():
        return redirect(url_for("login"))

    file = request.files.get("file")
    if not file:
        flash("No file provided.")
        return redirect(url_for("config_page"))

    filename = secure_filename(file.filename)
    path = os.path.join(EXPORT_DIR, filename)
    file.save(path)
    import_config(path)
    flash("Configuration imported.")
    return redirect(url_for("config_page"))


@app.route("/shutdown", methods=["POST"])
def shutdown():
    if not is_authenticated():
        return redirect(url_for("login"))

    # Safe shutdown: stop pipeline and then power off OS
    watchdog.stop()
    os.system("sudo shutdown -h now")
    return "Shutting down...", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
