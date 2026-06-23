"""Entry point for one scan cycle.

    py -m src.run        (from the project root)
    py src/run.py        (also works — see the path shim below)

Flow: scrape all sources -> upsert into SQLite -> write a digest of any new
opportunities -> (optionally) email them. Designed to be invoked every 6 hours
by Windows Task Scheduler; safe to run by hand any time.
"""
from __future__ import annotations

import os
import sys
from datetime import datetime

# Windows consoles default to cp1252; force UTF-8 so non-ASCII job titles
# (em-dashes, accented firm names) can never raise UnicodeEncodeError mid-scan.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except (AttributeError, ValueError):
        pass

# Allow `py src/run.py` by making the project root importable as a package parent.
if __package__ in (None, ""):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from src import database, digest, notifier, scraper  # type: ignore
    from src.config import DATA_DIR, load_config  # type: ignore
else:
    from . import database, digest, notifier, scraper
    from .config import DATA_DIR, load_config

LOG_PATH = os.path.join(DATA_DIR, "scan.log")


def _make_logger():
    os.makedirs(DATA_DIR, exist_ok=True)
    fh = open(LOG_PATH, "a", encoding="utf-8")

    def log(msg: str = ""):
        line = str(msg)
        print(line, flush=True)
        fh.write(line + "\n")
        fh.flush()

    return log, fh


def main() -> int:
    log, fh = _make_logger()
    try:
        cfg = load_config()
        log("=" * 64)
        log(f"Scan started: {datetime.now().isoformat(timespec='seconds')}")
        log("=" * 64)

        records = scraper.scrape_all(cfg, log)
        new_records = database.upsert_records(records)

        log("-" * 64)
        log(f"New opportunities since last run: {len(new_records)}")
        for r in new_records:
            log(f"  + {r['company']}: {r['title']}  ({r.get('location','')})")

        digest_path = digest.write_digest(new_records)
        if digest_path:
            log(f"Digest written: {digest_path}")

        if new_records:
            html = digest.build_html(new_records)
            subject = f"[Quant Tracker] {len(new_records)} new quant internship(s)"
            notifier.send_digest_email(subject, html, cfg, log)

        stats = database.get_stats()
        log("-" * 64)
        log(f"Active opportunities in tracker: {stats['total_active']} "
            f"(new in last 7d: {stats['new_last_7d']})")
        log(f"By track: {stats['by_category']}")
        log("Scan complete.\n")
        return 0
    except Exception as exc:  # noqa: BLE001 - top-level guard so the task never crashes silently
        log(f"FATAL: {type(exc).__name__}: {exc}")
        import traceback
        log(traceback.format_exc())
        return 1
    finally:
        fh.close()


if __name__ == "__main__":
    raise SystemExit(main())
