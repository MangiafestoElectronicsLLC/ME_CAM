from flask import Flask, render_template_string
import os

app = Flask(__name__)

HTML = """
<h2>ME Camera Dashboard</h2>
<ul>
{% for f in files %}
<li>{{f}}</li>
{% endfor %}
</ul>
"""

@app.route("/")
def index():
    files = os.listdir("encrypted_videos")
    return render_template_string(HTML, files=files)

app.run(host="0.0.0.0", port=5000)
