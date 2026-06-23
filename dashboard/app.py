"""Flask dashboard for the Quant Internship Tracker.

Run:  py "dashboard/app.py"   (or use scripts/start_dashboard.ps1)
Then open the printed http://127.0.0.1:<port> URL.

Reads the same SQLite DB the scanner writes, so it always reflects the latest
scan. Includes a "Scan now" button that kicks off a scrape in the background.
"""
from __future__ import annotations

import os
import sys
import threading
from datetime import datetime, timezone

from flask import Flask, jsonify, render_template, request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src import database, suggestions  # noqa: E402
from src.config import load_config  # noqa: E402

app = Flask(__name__)

_scan_lock = threading.Lock()
_scan_state = {"running": False, "finished_at": None}

TRACK_ORDER = ["trader", "researcher", "developer", "data", "general"]


def _days_ago(iso: str | None):
    if not iso:
        return None
    try:
        dt = datetime.fromisoformat(iso)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - dt).days
    except ValueError:
        return None


@app.route("/")
def index():
    cfg = load_config()
    scope = "US · undergrad-eligible" if cfg.get("us_undergrad_only", True) else "all roles"
    opps = database.get_opportunities(active_only=True)
    for o in opps:
        o["track_label"] = suggestions.label_for(o["category"])
        o["days_ago"] = _days_ago(o.get("first_seen"))
        blob = " ".join(str(o.get(k, "")) for k in
                        ("company", "title", "location", "source", "track_label"))
        o["search"] = blob.lower()
    stats = database.get_stats()
    tracks = [
        {"key": k, "label": suggestions.label_for(k),
         "tips": suggestions.suggestions_for(k),
         "count": stats["by_category"].get(k, 0)}
        for k in TRACK_ORDER
    ]
    return render_template(
        "index.html",
        opps=opps,
        stats=stats,
        tracks=tracks,
        checklist=suggestions.GENERAL_CHECKLIST,
        scan_running=_scan_state["running"],
        scope=scope,
        generated=datetime.now().strftime("%Y-%m-%d %H:%M"),
    )


@app.route("/api/opportunities")
def api_opportunities():
    return jsonify(database.get_opportunities(active_only=request.args.get("active", "1") == "1"))


@app.route("/api/applied", methods=["POST"])
def api_applied():
    data = request.get_json(force=True, silent=True) or {}
    if "id" not in data:
        return jsonify({"ok": False, "error": "missing id"}), 400
    database.set_applied(data["id"], bool(data.get("applied")))
    return jsonify({"ok": True})


@app.route("/api/scan", methods=["POST"])
def api_scan():
    if _scan_state["running"]:
        return jsonify({"started": False, "running": True})

    def job():
        with _scan_lock:
            _scan_state["running"] = True
            try:
                from src import run as runner
                runner.main()
            finally:
                _scan_state["running"] = False
                _scan_state["finished_at"] = datetime.now().isoformat(timespec="seconds")

    threading.Thread(target=job, daemon=True).start()
    return jsonify({"started": True})


@app.route("/api/scan/status")
def api_scan_status():
    return jsonify(_scan_state)


def main():
    cfg = load_config()
    port = int(cfg.get("dashboard_port", 5050))
    database.init_db()
    url = f"http://127.0.0.1:{port}"
    print(f"\n  Quant Internship Tracker dashboard -> {url}\n  (Ctrl+C to stop)\n")
    app.run(host="127.0.0.1", port=port, debug=False)


if __name__ == "__main__":
    main()
