"""Scraping layer.

Two source types, both fail-soft (any single source erroring is logged and
skipped rather than killing the run):

1. Company ATS APIs (Greenhouse / Lever) for a curated set of quant & trading
   firms. These are official JSON endpoints, so they're reliable and structured.
2. The SimplifyJobs / vanshb03 community internship aggregators (raw GitHub
   JSON), filtered down to quant-relevant roles. This gives broad coverage of
   firms that don't expose a public ATS API.

Every source is normalized into the same record dict (see normalize()).
"""
from __future__ import annotations

import hashlib
import html
import json
import os
import re
import time
import urllib.request
from datetime import datetime, timezone

from . import suggestions
from .config import MANUAL_ROLES_PATH

UA = {"User-Agent": "Mozilla/5.0 (QuantInternshipTracker; personal job tracker)"}

# Phrases that hint at an application deadline inside a job description.
_DEADLINE_PATTERNS = [
    r"appl(?:y|ication)[^.\n]{0,40}?(?:by|before|deadline|closes?|due)\D{0,15}"
    r"((?:\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})|"
    r"(?:(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2}(?:st|nd|rd|th)?,?\s*\d{0,4}))",
    r"deadline\D{0,15}((?:\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})|"
    r"(?:(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2}(?:st|nd|rd|th)?,?\s*\d{0,4}))",
]
_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"[ \t ]+")


def _get(url: str, timeout: int = 25) -> bytes:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def _get_json(url: str, timeout: int = 25):
    return json.loads(_get(url, timeout))


def strip_html(raw: str) -> str:
    if not raw:
        return ""
    text = html.unescape(raw)
    text = _TAG_RE.sub(" ", text)
    text = _WS_RE.sub(" ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    return text.strip()


def extract_deadline(text: str):
    if not text:
        return None
    low = text[:4000]
    for pat in _DEADLINE_PATTERNS:
        m = re.search(pat, low, re.IGNORECASE)
        if m:
            return m.group(1).strip().rstrip(".")
    return None


def make_id(company: str, title: str) -> str:
    key = f"{(company or '').strip().lower()}|{(title or '').strip().lower()}"
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]


def _ts_to_date(ts):
    try:
        return datetime.fromtimestamp(int(ts), tz=timezone.utc).date().isoformat()
    except (TypeError, ValueError, OSError):
        return None


def normalize(company, title, url, source, location="", date_posted=None,
              description="", deadline=None) -> dict:
    description = (description or "").strip()
    return {
        "id": make_id(company, title),
        "company": (company or "").strip(),
        "title": (title or "").strip(),
        "location": (location or "").strip(),
        "url": (url or "").strip(),
        "source": source,
        "category": suggestions.categorize(title),
        "date_posted": date_posted,
        "deadline": deadline or extract_deadline(description),
        "description": description[:1200],
    }


# --------------------------------------------------------------------------- #
# Relevance filtering
# --------------------------------------------------------------------------- #
# Word-boundary match so "intern" does NOT fire on "INTERNational" / "INTERNal".
_INTERN_RE = re.compile(
    r"\b(?:intern(?:ship)?s?|co-?op|summer\s+analyst|industrial\s+placement|"
    r"placement|trainee|discovery)\b",
    re.IGNORECASE,
)


def is_internship(title: str, cfg) -> bool:
    t = title or ""
    if _INTERN_RE.search(t):
        return True
    # Allow multi-word terms added via config (e.g. "summer associate").
    tl = t.lower()
    return any(" " in term and term in tl for term in cfg.get("internship_terms", []))


def is_quant_relevant(company: str, title: str, cfg) -> bool:
    c = (company or "").lower()
    t = (title or "").lower()
    blob = c + " " + t
    if any(x and x in blob for x in cfg.get("exclude_keywords", [])):
        return False
    if any(f in c for f in cfg["known_firms"]):
        return True
    return any(k in blob for k in cfg["keywords"])


# --- US-undergrad eligibility ------------------------------------------------
_US_STATES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA", "HI", "ID", "IL",
    "IN", "IA", "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS", "MO", "MT",
    "NE", "NV", "NH", "NJ", "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI",
    "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY", "DC",
}
_US_CITY_HINTS = (
    "united states", "usa", "u.s.", "nyc", "new york", "manhattan", "chicago",
    "boston", "miami", "greenwich", "stamford", "austin", "houston", "dallas",
    "san francisco", "palo alto", "seattle", "los angeles", "philadelphia",
    "washington", "atlanta", "princeton", "west palm beach", "villanova",
    "ardmore", "bala cynwyd", "jupiter", "santa clara", "milpitas", "irving",
)
_STATE_RE = re.compile(r",\s*([A-Za-z]{2})\b")
_PHD_RE = re.compile(r"\bph\.?\s?d\b", re.IGNORECASE)
_MASTERS_RE = re.compile(r"\bmaster'?s\b", re.IGNORECASE)


def is_us_location(location: str) -> bool:
    """True if any part of the (possibly multi-city) location string is in the US.

    Unknown/empty location is treated as US (can't rule it out) so we don't
    silently drop a genuinely-US role that just lacks a location field.
    """
    if not location or not location.strip():
        return True
    low = location.lower()
    if any(h in low for h in _US_CITY_HINTS):
        return True
    return any(code.upper() in _US_STATES for code in _STATE_RE.findall(location))


def is_undergrad_eligible(title: str, degrees, description: str = "") -> bool:
    """Keep roles open to undergraduates; drop Master's/PhD-only ones.

    When the source lists eligible degrees (the aggregator does), that's
    authoritative — keep only if Bachelor's is among them. Otherwise scan the
    title + description: keep if it mentions Bachelor's/undergrad, drop if it
    requires a Master's or PhD with no Bachelor's option.
    """
    if degrees:
        degs = [str(d).lower() for d in degrees]
        return any("bachelor" in d or "undergrad" in d for d in degs)
    text = (title or "") + " " + (description or "")
    low = text.lower()
    if "bachelor" in low or "undergrad" in low:
        return True
    if _PHD_RE.search(text) or _MASTERS_RE.search(text):
        return False
    return True


def passes_us_undergrad(title: str, location: str, degrees, cfg,
                        description: str = "") -> bool:
    if not cfg.get("us_undergrad_only", True):
        return True
    return is_us_location(location) and is_undergrad_eligible(title, degrees, description)


def passes_term_filter(title: str, terms, cfg) -> bool:
    """Keep only roles for an internship cycle in cfg['min_intern_year'] (default
    2027) or later — i.e. after Summer 2026. Roles with no detectable year are
    kept (a freshly posted role can't be for a summer that already started). The
    Fall/Autumn of the prior year counts as "after" that year's summer.
    """
    min_year = cfg.get("min_intern_year")
    if not min_year:
        return True
    blob = ((title or "") + " " + " ".join(terms or [])).lower()
    years = [int(y) for y in re.findall(r"\b(20\d{2})\b", blob) if 2024 <= int(y) <= 2035]
    if not years:
        return True
    if max(years) >= int(min_year):
        return True
    return f"fall {int(min_year) - 1}" in blob or f"autumn {int(min_year) - 1}" in blob


# --------------------------------------------------------------------------- #
# Source: Greenhouse
# --------------------------------------------------------------------------- #
def fetch_greenhouse(name: str, token: str, cfg, log) -> list[dict]:
    out: list[dict] = []
    try:
        listing = _get_json(f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs")
    except Exception as exc:  # noqa: BLE001 - fail soft per source
        log(f"  [skip] Greenhouse:{name} ({token}) — {type(exc).__name__}: {str(exc)[:60]}")
        return out

    jobs = listing.get("jobs", []) if isinstance(listing, dict) else []
    candidates = []
    for job in jobs:
        title = job.get("title", "")
        loc = (job.get("location") or {}).get("name", "")
        if (is_internship(title, cfg)
                and is_quant_relevant(name, title, cfg)
                and passes_us_undergrad(title, loc, None, cfg)
                and passes_term_filter(title, None, cfg)):
            candidates.append((job, title, loc))

    kept = 0
    for job, title, loc in candidates:
        url = job.get("absolute_url", "")
        date_posted = (job.get("updated_at") or "")[:10] or None
        description = ""
        # Pull detail for description + deadline (small number of intern roles).
        try:
            detail = _get_json(
                f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs/{job.get('id')}"
            )
            description = strip_html(detail.get("content", ""))
            date_posted = (detail.get("updated_at") or date_posted or "")[:10] or date_posted
        except Exception:  # noqa: BLE001
            pass
        # Final Master's/PhD-only check now that we have the full description.
        if not is_undergrad_eligible(title, None, description):
            continue
        out.append(normalize(name, title, url, f"Greenhouse:{name}", loc,
                             date_posted, description))
        kept += 1
        time.sleep(0.05)
    log(f"  Greenhouse:{name} — {kept} role(s) of {len(jobs)} postings")
    return out


# --------------------------------------------------------------------------- #
# Source: Lever
# --------------------------------------------------------------------------- #
def fetch_lever(name: str, company: str, cfg, log) -> list[dict]:
    out: list[dict] = []
    try:
        postings = _get_json(f"https://api.lever.co/v0/postings/{company}?mode=json")
    except Exception as exc:  # noqa: BLE001
        log(f"  [skip] Lever:{name} ({company}) — {type(exc).__name__}: {str(exc)[:60]}")
        return out
    if not isinstance(postings, list):
        return out
    for p in postings:
        title = p.get("text", "")
        if not is_internship(title, cfg):
            continue
        cats = p.get("categories", {}) or {}
        loc = cats.get("location", "")
        url = p.get("hostedUrl", "")
        date_posted = _ts_to_date((p.get("createdAt") or 0) / 1000) if p.get("createdAt") else None
        description = strip_html(p.get("descriptionPlain") or p.get("description", ""))
        out.append(normalize(name, title, url, f"Lever:{name}", loc,
                             date_posted, description))
    log(f"  Lever:{name} — {sum(1 for p in postings if is_internship(p.get('text',''), cfg))} intern role(s)")
    return out


# --------------------------------------------------------------------------- #
# Source: GitHub internship aggregators (SimplifyJobs / vanshb03)
# --------------------------------------------------------------------------- #
def fetch_github_listings(cfg, log) -> list[dict]:
    out: list[dict] = []
    seen_keys = set()
    for url in cfg["github_listing_urls"]:
        try:
            arr = _get_json(url, timeout=30)
        except Exception as exc:  # noqa: BLE001
            log(f"  [skip] aggregator {url.split('/')[4] if '/' in url else url} — "
                f"{type(exc).__name__}")
            continue
        if not isinstance(arr, list):
            continue
        kept = 0
        for e in arr:
            if not isinstance(e, dict):
                continue
            if not e.get("is_visible", True) or not e.get("active", True):
                continue
            company = e.get("company_name", "")
            title = e.get("title", "")
            if not is_internship(title, cfg) or not is_quant_relevant(company, title, cfg):
                continue
            locs = e.get("locations") or []
            loc = ", ".join(locs) if isinstance(locs, list) else str(locs)
            terms = e.get("terms") or []
            if not passes_us_undergrad(title, loc, e.get("degrees"), cfg):
                continue
            if not passes_term_filter(title, terms, cfg):
                continue
            key = make_id(company, title)
            if key in seen_keys:
                continue
            seen_keys.add(key)
            term_str = ", ".join(terms) if isinstance(terms, list) else str(terms)
            out.append(normalize(
                company, title, e.get("url", ""),
                f"Simplify ({term_str})" if term_str else "Simplify",
                loc, _ts_to_date(e.get("date_posted")),
                description=f"{term_str} internship. Category: {e.get('category','')}.",
            ))
            kept += 1
        label = url.split("/")[4] if url.count("/") >= 4 else url
        log(f"  aggregator {label} — {kept} quant intern role(s) kept")
    return out


# --------------------------------------------------------------------------- #
# Source: D. E. Shaw careers site (server-rendered HTML, no public API)
# --------------------------------------------------------------------------- #
_DESHAW_ANCHOR_RE = re.compile(
    r'<a[^>]+href="(/careers/[a-z0-9\-]+\-\d+)"[^>]*>(.*?)</a>', re.S
)


def fetch_deshaw(cfg, log) -> list[dict]:
    """Scrape D. E. Shaw's careers page (deshaw.com/careers), which renders all
    role links server-side. Each role's title/location come from the anchor text;
    the usual internship / quant / US / undergrad / term filters then apply.
    """
    out: list[dict] = []
    try:
        page = _get("https://www.deshaw.com/careers", timeout=20).decode("utf-8", "ignore")
    except Exception as exc:  # noqa: BLE001 - fail soft
        log(f"  [skip] D. E. Shaw site — {type(exc).__name__}: {str(exc)[:60]}")
        return out

    seen, kept, total = set(), 0, 0
    for href, inner in _DESHAW_ANCHOR_RE.findall(page):
        if href in seen:
            continue
        seen.add(href)
        total += 1
        title = html.unescape(_TAG_RE.sub(" ", inner))
        title = _WS_RE.sub(" ", title).replace("\n", " ").strip()
        title = re.sub(r"^icon\s+", "", title, flags=re.IGNORECASE).split(" : ")[0].strip()
        if not title:
            continue
        loc_m = re.search(r"\(([^)]+)\)", title)
        loc = loc_m.group(1).strip() if loc_m else ""
        if not is_internship(title, cfg):
            continue
        if not is_quant_relevant("D. E. Shaw Group", title, cfg):
            continue
        if not passes_us_undergrad(title, loc, None, cfg):
            continue
        if not passes_term_filter(title, None, cfg):
            continue
        out.append(normalize("D. E. Shaw Group", title,
                             "https://www.deshaw.com" + href, "D. E. Shaw (site)", loc))
        kept += 1
    log(f"  D. E. Shaw site — {kept} role(s) of {total} listings")
    return out


# --------------------------------------------------------------------------- #
# Source: hand-curated roles (manual_roles.json)
# --------------------------------------------------------------------------- #
def fetch_manual_roles(log) -> list[dict]:
    """Roles added by hand for firms the automated sources don't cover (own
    careers sites like D. E. Shaw, Jane Street, etc.). These are trusted as-is —
    the US / undergrad / term filters are NOT applied, since you've vetted them.
    """
    out: list[dict] = []
    if not os.path.exists(MANUAL_ROLES_PATH):
        return out
    try:
        with open(MANUAL_ROLES_PATH, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (json.JSONDecodeError, OSError) as exc:
        log(f"  [skip] manual_roles.json — {type(exc).__name__}: {str(exc)[:60]}")
        return out
    for r in data.get("roles", []):
        if not isinstance(r, dict):
            continue
        company, title = r.get("company", ""), r.get("title", "")
        if not company or not title:
            continue
        out.append(normalize(
            company, title, r.get("url", ""), r.get("source", "Manual"),
            r.get("location", ""), r.get("date_posted"),
            r.get("description", ""), r.get("deadline"),
        ))
    log(f"  manual_roles.json — {len(out)} curated role(s)")
    return out


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #
def scrape_all(cfg, log=print) -> list[dict]:
    records: dict[str, dict] = {}

    def add(items):
        for r in items:
            # Prefer a record that carries a real description/deadline.
            existing = records.get(r["id"])
            if existing is None:
                records[r["id"]] = r
            else:
                if not existing.get("description") and r.get("description"):
                    existing["description"] = r["description"]
                if not existing.get("deadline") and r.get("deadline"):
                    existing["deadline"] = r["deadline"]

    log("Scraping company ATS boards...")
    for name, token in cfg["greenhouse_boards"].items():
        add(fetch_greenhouse(name, token, cfg, log))
    for name, company in cfg.get("lever_companies", {}).items():
        add(fetch_lever(name, company, cfg, log))

    log("Scraping community internship aggregators...")
    add(fetch_github_listings(cfg, log))

    log("Scraping own-site firms...")
    add(fetch_deshaw(cfg, log))

    log("Scraping JS-only sites (headless browser)...")
    try:
        from .browser_scraper import fetch_browser_sources  # deferred: avoids import cycle
        add(fetch_browser_sources(cfg, log))
    except Exception as exc:  # noqa: BLE001 - never let the optional source break a scan
        log(f"  [skip] browser sources — {type(exc).__name__}: {str(exc)[:60]}")

    log("Loading hand-curated roles...")
    add(fetch_manual_roles(log))

    result = list(records.values())
    log(f"Total unique quant internships found this run: {len(result)}")
    return result
