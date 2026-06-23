"""Build human-readable digests of newly found opportunities.

Since email delivery is currently disabled, the digest is the primary
notification surface: each run writes a timestamped markdown file plus updates
data/latest_digest.md (and an HTML version the email path can reuse later).
"""
from __future__ import annotations

import os
from datetime import datetime

from . import suggestions
from .config import DATA_DIR

DIGEST_DIR = os.path.join(DATA_DIR, "digests")


def _group_by_category(records):
    groups: dict[str, list] = {}
    for r in records:
        groups.setdefault(r.get("category", "general"), []).append(r)
    return groups


def build_markdown(new_records: list[dict]) -> str:
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    if not new_records:
        return f"# Quant Internship Digest — {stamp}\n\nNo new opportunities this run.\n"

    lines = [f"# Quant Internship Digest — {stamp}",
             "",
             f"**{len(new_records)} new opportunit{'y' if len(new_records)==1 else 'ies'} found.**",
             ""]
    for track, items in _group_by_category(new_records).items():
        lines.append(f"## {suggestions.label_for(track)} ({len(items)})")
        lines.append("")
        for r in items:
            loc = f" — {r['location']}" if r.get("location") else ""
            lines.append(f"### {r['company']}: {r['title']}{loc}")
            if r.get("url"):
                lines.append(f"- Apply: {r['url']}")
            if r.get("deadline"):
                lines.append(f"- **Deadline:** {r['deadline']}")
            if r.get("date_posted"):
                lines.append(f"- Posted: {r['date_posted']}")
            lines.append(f"- Source: {r.get('source','')}")
            lines.append("")
        # One or two prep tips for this track.
        tips = suggestions.suggestions_for(track)[:2]
        if tips:
            lines.append(f"_To prep for {suggestions.label_for(track)} roles:_")
            for area, action, _res in tips:
                lines.append(f"- **{area}:** {action}")
            lines.append("")
    lines.append("---")
    lines.append("Open the dashboard for full details, deadlines, and prep suggestions.")
    return "\n".join(lines)


def build_html(new_records: list[dict]) -> str:
    """Minimal HTML version (used by the email path when enabled)."""
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    if not new_records:
        return f"<h2>Quant Internship Digest — {stamp}</h2><p>No new opportunities this run.</p>"
    parts = [f"<h2>Quant Internship Digest — {stamp}</h2>",
             f"<p><b>{len(new_records)} new opportunities found.</b></p>"]
    for track, items in _group_by_category(new_records).items():
        parts.append(f"<h3>{suggestions.label_for(track)} ({len(items)})</h3><ul>")
        for r in items:
            loc = f" — {r['location']}" if r.get("location") else ""
            dl = f" · <b>Deadline:</b> {r['deadline']}" if r.get("deadline") else ""
            url = r.get("url", "")
            link = f'<a href="{url}">{r["company"]}: {r["title"]}</a>' if url else f'{r["company"]}: {r["title"]}'
            parts.append(f"<li>{link}{loc}{dl}</li>")
        parts.append("</ul>")
    return "\n".join(parts)


def write_digest(new_records: list[dict]) -> str | None:
    """Write timestamped + latest digest files. Returns the timestamped path."""
    os.makedirs(DIGEST_DIR, exist_ok=True)
    md = build_markdown(new_records)
    latest = os.path.join(DATA_DIR, "latest_digest.md")
    with open(latest, "w", encoding="utf-8") as fh:
        fh.write(md)
    if not new_records:
        return None
    path = os.path.join(DIGEST_DIR, datetime.now().strftime("digest_%Y%m%d_%H%M.md"))
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(md)
    return path
