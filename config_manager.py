import json, os

CONFIG_PATH = "config.json"

DEFAULT_CONFIG = {
    "wifi_ssid": "",
    "wifi_password": "",
    "email": "",
    "send_email": False,
    "sensitivity": 0.2,
    "pin": "1234"
}

def load_config():
    if not os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "w") as f:
            json.dump(DEFAULT_CONFIG, f, indent=4)
    with open(CONFIG_PATH) as f:
        return json.load(f)
