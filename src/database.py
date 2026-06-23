"""SQLite persistence + new-opportunity detection.

The DB is the source of truth for the dashboard. upsert_records() returns only
the rows that were genuinely new this run (i.e. an id we'd never seen before),
which is what feeds the digest.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from .config import DB_PATH

_SCHEMA = """
CREATE TABLE IF NOT EXISTS opportunities (
    id          TEXT PRIMARY KEY,
    company     TEXT,
    title       TEXT,
    location    TEXT,
    url         TEXT,
    source      TEXT,
    category    TEXT,
    date_posted TEXT,
    deadline    TEXT,
    description TEXT,
    first_seen  TEXT,
    last_seen   TEXT,
    active      INTEGER DEFAULT 1,
    applied     INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS runs (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    ran_at  TEXT,
    found   INTEGER,
    new     INTEGER
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with connect() as conn:
        conn.executescript(_SCHEMA)


def upsert_records(records: list[dict]) -> list[dict]:
    """Insert/update records. Return the list of brand-new records."""
    init_db()
    new: list[dict] = []
    now = _now()
    seen_ids: list[str] = []
    with connect() as conn:
        for r in records:
            seen_ids.append(r["id"])
            row = conn.execute(
                "SELECT id FROM opportunities WHERE id = ?", (r["id"],)
            ).fetchone()
            if row is None:
                conn.execute(
                    """INSERT INTO opportunities
                       (id, company, title, location, url, source, category,
                        date_posted, deadline, description, first_seen, last_seen,
                        active, applied)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,1,0)""",
                    (r["id"], r["company"], r["title"], r["location"], r["url"],
                     r["source"], r["category"], r["date_posted"], r["deadline"],
                     r["description"], now, now),
                )
                r = dict(r)
                r["first_seen"] = now
                new.append(r)
            else:
                conn.execute(
                    """UPDATE opportunities
                       SET last_seen=?, active=1, location=?, url=?, source=?,
                           category=?, date_posted=COALESCE(?, date_posted),
                           deadline=COALESCE(?, deadline),
                           description=CASE WHEN ?<>'' THEN ? ELSE description END
                       WHERE id=?""",
                    (now, r["location"], r["url"], r["source"], r["category"],
                     r["date_posted"], r["deadline"], r["description"],
                     r["description"], r["id"]),
                )
        # Mark anything we manage but didn't see this run as inactive.
        if seen_ids:
            placeholders = ",".join("?" * len(seen_ids))
            conn.execute(
                f"UPDATE opportunities SET active=0 WHERE id NOT IN ({placeholders})",
                seen_ids,
            )
        conn.execute(
            "INSERT INTO runs (ran_at, found, new) VALUES (?,?,?)",
            (now, len(records), len(new)),
        )
    return new


def get_opportunities(active_only: bool = True) -> list[dict]:
    init_db()
    q = "SELECT * FROM opportunities"
    if active_only:
        q += " WHERE active=1"
    q += " ORDER BY first_seen DESC"
    with connect() as conn:
        return [dict(row) for row in conn.execute(q).fetchall()]


def get_stats() -> dict:
    init_db()
    with connect() as conn:
        total = conn.execute("SELECT COUNT(*) FROM opportunities WHERE active=1").fetchone()[0]
        by_cat = {
            row[0]: row[1]
            for row in conn.execute(
                "SELECT category, COUNT(*) FROM opportunities WHERE active=1 GROUP BY category"
            ).fetchall()
        }
        last_run = conn.execute(
            "SELECT ran_at, found, new FROM runs ORDER BY id DESC LIMIT 1"
        ).fetchone()
        new_7d = conn.execute(
            "SELECT COUNT(*) FROM opportunities WHERE active=1 AND first_seen >= datetime('now','-7 days')"
        ).fetchone()[0]
    return {
        "total_active": total,
        "by_category": by_cat,
        "new_last_7d": new_7d,
        "last_run": dict(last_run) if last_run else None,
    }


def set_applied(opp_id: str, applied: bool) -> None:
    init_db()
    with connect() as conn:
        conn.execute(
            "UPDATE opportunities SET applied=? WHERE id=?",
            (1 if applied else 0, opp_id),
        )
