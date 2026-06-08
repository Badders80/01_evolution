"""
HLT Mission Control — Admin dev server.

Flask app on port 5000 serving static SPA from admin/static/.
SQLite auto-initialised on startup.
"""

import os
from flask import Flask, send_from_directory, jsonify
from flask_cors import CORS

from admin.db import init_db

app = Flask(__name__, static_folder="admin/static")
CORS(app)

# ─── Init DB ──────────────────────────────────────────────────────────────────

init_db()


# ─── Static SPA catch-all ─────────────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory("admin/static", "index.html")


@app.route("/<path:path>")
def static_files(path):
    return send_from_directory("admin/static", path)


# ─── Health ───────────────────────────────────────────────────────────────────

@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "service": "hlt-mission-control"})


# ─── Entrypoint ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True, use_reloader=False)
