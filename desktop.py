"""Run the dashboard as a native desktop window (no web browser).

Starts the Flask dashboard on a background thread and renders it inside a native
window via pywebview (uses the Windows WebView2 runtime). Closing the window
stops the server and exits.

    py desktop.py
"""
from __future__ import annotations

import os
import sys
import threading
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.config import load_config  # noqa: E402
from dashboard.app import app  # noqa: E402


def _serve(port: int) -> None:
    # use_reloader=False is required when running Flask off the main thread.
    app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False)


def _wait_for_server(url: str, timeout: float = 15.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(url, timeout=1)
            return True
        except Exception:  # noqa: BLE001 - just polling until it's up
            time.sleep(0.15)
    return False


def main() -> int:
    cfg = load_config()
    port = int(cfg.get("dashboard_port", 5050))
    url = f"http://127.0.0.1:{port}"

    threading.Thread(target=_serve, args=(port,), daemon=True).start()
    if not _wait_for_server(url):
        print("Dashboard server did not start in time.")
        return 1

    import webview

    webview.create_window(
        "Quant Internship Tracker",
        url,
        width=1320,
        height=900,
        min_size=(900, 600),
    )
    webview.start()  # blocks until the window is closed
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
