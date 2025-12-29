from flask import Flask, request
import json

app = Flask(__name__)

@app.route("/", methods=["GET","POST"])
def setup():
    if request.method == "POST":
        with open("config.json","w") as f:
            json.dump(request.form.to_dict(), f, indent=4)
        return "Saved. Reboot device."
    return """
    <form method="post">
    WiFi SSID:<input name="wifi_ssid"><br>
    WiFi Password:<input name="wifi_password"><br>
    <button>Save</button>
    </form>
    """

app.run(host="0.0.0.0", port=5000)
