from flask import Flask, render_template
import json

app = Flask(__name__)

@app.route("/")
def index():
    with open("hub_config.json") as f:
        devices = json.load(f)
    return render_template("multicam.html", devices=devices)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8090)
