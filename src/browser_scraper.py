"""Optional Playwright scraper for JS-only career sites.

Some firms render their job lists with client-side JavaScript and expose no public
API, so a plain HTTP fetch sees nothing. This module drives a headless Chromium to
render + paginate them. Currently covers **Two Sigma** (Avature).

(Citadel is *not* here on purpose: its careers site sits behind Cloudflare
anti-bot, which blocks its pagination/AJAX for automated clients. Citadel roles are
maintained in manual_roles.json instead.)

Heavy + best-effort. Requires a one-time:
    py -m pip install playwright
    py -m playwright install chromium

Fail-soft by design: if Playwright (or the site) is unavailable, it logs a skip and
the rest of the scan proceeds. Gated by config "enable_browser_scraper" (default
true). The normal ATS / aggregator / curated / D. E. Shaw sources never depend on it.
"""
from __future__ import annotations

import re

from .scraper import (
    is_internship,
    is_quant_relevant,
    normalize,
    passes_term_filter,
    passes_us_undergrad,
)

_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

# Map a country token in a Two Sigma job-slug to a display location.
_TS_LOC = [
    ("united-states", "United States"), ("united-kingdom", "London, UK"),
    ("singapore", "Singapore"), ("hong-kong", "Hong Kong"),
    ("japan", "Tokyo, Japan"), ("china", "Shanghai, China"),
]


def _twosigma(browser, cfg, log):
    """Two Sigma (Avature) paginates via ?jobOffset=N — loop until no new roles."""
    collected: dict[str, str] = {}
    pg = browser.new_page(user_agent=_UA)
    try:
        for off in range(0, 600, 10):
            pg.goto(
                f"https://careers.twosigma.com/careers/OpenRoles/?jobRecordsPerPage=10&jobOffset={off}",
                wait_until="domcontentloaded", timeout=30000,
            )
            try:
                pg.wait_for_selector("a[href*='JobDetail/']", timeout=10000)
            except Exception:  # noqa: BLE001 - no roles on this page -> done
                break
            pg.wait_for_timeout(400)
            pairs = pg.eval_on_selector_all(
                "a", "els=>els.map(e=>[e.getAttribute('href'),(e.innerText||'').trim()])")
            page_links = {h: t for h, t in pairs if h and "JobDetail/" in h}
            if not page_links or not (set(page_links) - set(collected)):
                break
            collected.update(page_links)
    finally:
        pg.close()

    out = []
    for href, title in collected.items():
        title = re.sub(r"\s+", " ", title or "").strip()
        if not title:
            continue
        slug = href.split("JobDetail/")[1].rsplit("/", 1)[0].lower()
        loc = next((v for k, v in _TS_LOC if k in slug), "")
        url = href if href.startswith("http") else "https://careers.twosigma.com" + href
        if (is_internship(title, cfg) and is_quant_relevant("Two Sigma", title, cfg)
                and passes_us_undergrad(title, loc, None, cfg)
                and passes_term_filter(title, None, cfg)):
            out.append(normalize("Two Sigma", title, url, "Two Sigma (site)", loc))
    log(f"  Two Sigma site — {len(out)} role(s) of {len(collected)} listings")
    return out


def fetch_browser_sources(cfg, log=print):
    if not cfg.get("enable_browser_scraper", True):
        return []
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        log("  [skip] browser scraper — playwright not installed "
            "(py -m pip install playwright; py -m playwright install chromium)")
        return []

    out = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                for src in (lambda b: _twosigma(b, cfg, log),):
                    try:
                        out += src(browser)
                    except Exception as exc:  # noqa: BLE001 - per-site fail-soft
                        log(f"  [skip] browser source — {type(exc).__name__}: {str(exc)[:60]}")
            finally:
                browser.close()
    except Exception as exc:  # noqa: BLE001 - Playwright/browser unavailable
        log(f"  [skip] browser scraper — {type(exc).__name__}: {str(exc)[:80]}")
    return out
