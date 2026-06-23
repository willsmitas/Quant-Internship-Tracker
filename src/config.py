"""Configuration loader.

Built-in DEFAULTS are merged with the user-editable config.json at the project
root (config.json wins). This keeps a sane out-of-the-box setup while letting the
user add firms / keywords / settings without editing code.
"""
from __future__ import annotations

import json
import os

# Project root = parent of this file's directory (src/..)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data")
CONFIG_PATH = os.path.join(ROOT, "config.json")
DB_PATH = os.path.join(DATA_DIR, "opportunities.db")

DEFAULTS = {
    "internship_terms": [
        "intern", "internship", "co-op", "coop", "summer analyst", "placement",
    ],
    "keywords": [
        "quant", "quantitative", "trading", "trader", "systematic", "market mak",
        "market-mak", "derivativ", "hedge fund", "high frequency", "hft",
        "algorithmic", "low latency", "low-latency",
    ],
    "known_firms": [
        "jane street", "citadel", "two sigma", "hudson river", "jump trading", "drw",
        "imc", "optiver", "susquehanna", "akuna", "five rings", "old mission",
        "point72", "cubist", "tower research", "pdt partners", "virtu", "de shaw",
        "aqr", "worldquant", "voleon",
    ],
    "greenhouse_boards": {
        "IMC Trading": "imc",
        "DRW": "drweng",
        "Point72 / Cubist": "point72",
        "Jump Trading": "jumptrading",
        "Akuna Capital": "akunacapital",
        "Old Mission Capital": "oldmissioncapital",
        "Virtu Financial": "virtu",
        "Tower Research Capital": "towerresearchcapital",
        "PDT Partners": "pdtpartners",
        "Optiver": "optiver",
    },
    "exclude_keywords": [
        "trading card", "collectible", "networking event", "tax/accounting",
        "tax intern", "accounting intern", "auditor", "barista", "retail sales",
        "quantum",
    ],
    "lever_companies": {},
    "github_listing_urls": [
        "https://raw.githubusercontent.com/SimplifyJobs/Summer2026-Internships/dev/.github/scripts/listings.json",
    ],
    "us_undergrad_only": True,
    "lookback_days": 400,
    "dashboard_port": 5050,
}


def load_config() -> dict:
    """Return DEFAULTS deep-merged with config.json (file values win)."""
    cfg = json.loads(json.dumps(DEFAULTS))  # cheap deep copy
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as fh:
                user = json.load(fh)
        except (json.JSONDecodeError, OSError) as exc:  # pragma: no cover
            print(f"[config] WARNING: could not read config.json ({exc}); using defaults")
            user = {}
        for key, value in user.items():
            if key.startswith("_"):
                continue
            if isinstance(value, dict) and isinstance(cfg.get(key), dict):
                cfg[key].update(value)
            else:
                cfg[key] = value
    os.makedirs(DATA_DIR, exist_ok=True)
    return cfg
