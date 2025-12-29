from config_manager import load_config
import subprocess, os

config = load_config()

# Launch setup mode if unconfigured
if config["wifi_ssid"] == "":
    subprocess.Popen(["python3", "setup_mode/setup_server.py"])
    subprocess.Popen(["python3", "setup_mode/qr_display.py"])
    exit()

# Normal operation
os.makedirs("motion_videos", exist_ok=True)
os.makedirs("encrypted_videos", exist_ok=True)

subprocess.Popen(["python3", "web_dashboard.py"])
subprocess.Popen(["python3", "motion_detector.py"])
