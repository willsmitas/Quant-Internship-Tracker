# Quant Internship Tracker

An automated agent that scours the web for **quant / trading internships** every
6 hours, plus a local **dashboard** that compiles every opportunity with
deadlines and tailored suggestions for improving your chances.

Built for William Smitas (william_smitas@brown.edu).

---

## What it does

- **Scans every 6 hours** via a Windows Scheduled Task (already installed).
- Pulls from five kinds of sources, fail-soft (one source breaking never stops a run):
  - **Company ATS APIs** (Greenhouse / Lever) for major quant firms: IMC, DRW,
    Point72 / Cubist, Jump Trading, Akuna, Old Mission, Virtu, Tower Research,
    PDT Partners, Optiver, Jane Street.
  - **Community internship aggregators** (SimplifyJobs + vanshb03 GitHub lists),
    filtered to quant/trading-relevant roles — covers SIG, Walleye, AQR, Radix,
    TransMarket, and many more that don't expose a public API.
  - **Own-site HTML scraper** for D. E. Shaw's server-rendered careers page.
  - **Headless-browser scraper** (optional, Playwright) for JS-only sites —
    currently Two Sigma. See [Browser scraper](#browser-scraper-optional).
  - **Hand-curated roles** in `manual_roles.json` for firms behind anti-bot
    protection (Citadel) — see [Adding roles by hand](#adding-roles-by-hand).
- **Filters to US, undergrad-eligible roles for Summer 2027+** — drops
  international-only postings, PhD/Master's-only roles, and any role for Summer 2026
  or earlier (toggle with `us_undergrad_only` / `min_intern_year` in `config.json`).
- **Includes early-career discovery / insight programs**, not just roles titled
  "intern".
- **De-duplicates** and stores everything in `data/opportunities.db` (SQLite).
- **Detects new postings** since the last run and writes a digest to
  `data/latest_digest.md` (+ a timestamped copy in `data/digests/`).
- **Dashboard** compiles all active roles with deadlines, lets you filter/sort,
  mark roles as applied, and shows prep suggestions per role track.
- **Cloud backup**: a Claude scheduled routine does the same web sweep every 6
  hours as redundancy in case your PC is asleep.

New opportunities surface in the dashboard and in the digest files
(`data/latest_digest.md` + `data/digests/`).

---

## One-time setup

Python 3.13 and the two dependencies are already installed. If you ever move the
project or set it up fresh:

```powershell
py -m pip install -r requirements.txt
```

The 6-hour scheduled task is **already registered**. To re-register (e.g. after
moving the folder) or remove it:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\install_scheduler.ps1
powershell -ExecutionPolicy Bypass -File scripts\uninstall_scheduler.ps1
```

---

## Daily use

### Open the dashboard

Two ways to view it:

- **As a desktop app (no browser)** — double-click **`Start Dashboard (App).bat`**.
  It opens the dashboard in a native window using `pywebview` (Windows WebView2).
  Requires the one-time `pip install -r requirements.txt` (which now includes
  `pywebview`). Closing the window quits it.
- **In your browser** — double-click **`Start Dashboard.bat`**, or run:
  ```powershell
  powershell -ExecutionPolicy Bypass -File scripts\start_dashboard.ps1
  ```
  then open **http://127.0.0.1:5050**.

Either way, the "Scan now" button kicks off a fresh scrape on demand; otherwise the
view reflects the latest 6-hourly scan. (If the desktop window ever fails to open,
run `py desktop.py` from a terminal to see the error.)

### Run a scan by hand
```powershell
powershell -ExecutionPolicy Bypass -File scripts\run_scan.ps1
```

### See what's new
- `data\latest_digest.md` — the most recent run's new opportunities.
- `data\digests\` — a timestamped digest per run that found something new.
- `data\scan.log` — full run history.

---

## Customizing

Edit **`config.json`** (no code changes needed) to tune what gets tracked:

| Key | What it controls |
|-----|------------------|
| `greenhouse_boards` | Firms scraped via Greenhouse — add `"Firm Name": "boardtoken"`. Find a firm's token in its careers page URL (`boards.greenhouse.io/<token>`). |
| `lever_companies` | Same idea for Lever (`jobs.lever.co/<company>`). |
| `keywords` | Words that mark a role as quant-relevant in the aggregator feed. |
| `known_firms` | Firm names always treated as quant (so even a "SWE Intern" there is kept). |
| `exclude_keywords` | Phrases that filter out noise (e.g. `trading card`, `quantum`). |
| `us_undergrad_only` | `true` (default) keeps only US-located roles open to undergrads. Set `false` to also include international + PhD/Master's-only roles. |
| `min_intern_year` | Keep only roles for this cycle year or later (default `2027` = after Summer 2026; Fall of the prior year still counts). Set to `null` to disable. Roles with no detectable year are kept. |
| `internship_terms` | Title words that qualify a role — includes `discovery program` / `insight` variants so early-career programs are caught, not just "intern". |
| `github_listing_urls` | Aggregator JSON feeds (bump to the Summer 2027 repo when it's live). |
| `dashboard_port` | Port for the dashboard (default 5050). |

After editing, run a scan (or hit "Scan now") to apply.

### Adding roles by hand

A few firms (Citadel, HRT) sit behind anti-bot protection or expose no API the
tracker can read. (Jane Street, D. E. Shaw, and Two Sigma are scraped
automatically — don't add those here.) Add the rest to **`manual_roles.json`** and
they'll appear on the dashboard (source `Manual`), bypassing the auto-filters since
you've already vetted them:

```json
{
  "roles": [
    {
      "company": "Citadel Securities",
      "title": "Software Engineer Intern (US)",
      "location": "New York, NY / Miami, FL",
      "url": "https://www.citadelsecurities.com/careers/details/software-engineer-intern-us/",
      "deadline": null
    }
  ]
}
```

Only `company`, `title`, and `url` are required. Re-run a scan to apply. (The
cloud backup routine also web-searches these own-site firms, so it can surface
roles to copy in here.)

### Browser scraper (optional)

Two Sigma renders its jobs with JavaScript, so the tracker scrapes it with a
headless browser (Playwright). This is optional and off the critical path — if
Playwright isn't installed, the scan simply skips it. To enable:

```powershell
py -m pip install playwright
py -m playwright install chromium
```

It adds ~20s per scan; turn it off with `"enable_browser_scraper": false` in
`config.json`. (Citadel also renders via JS but sits behind Cloudflare anti-bot, so
it can't be scraped reliably — keep Citadel roles in `manual_roles.json`.)

---

## Cloud backup routine

A Claude scheduled task, **quant-internship-cloud-backup**, runs the same web
sweep every 6 hours as redundancy. Manage it in the Claude app's **Scheduled**
sidebar. Two things to know:
- It runs while the Claude app is open (if closed when due, it runs on next launch).
- On its first run, click **Run now** once to pre-approve web search so future
  runs don't pause for permission.

---

## Project layout

```
config.json              # all user-tunable settings
manual_roles.json        # hand-added roles for own-site firms (D. E. Shaw, etc.)
requirements.txt
src/
  config.py              # defaults + config.json loader
  scraper.py             # Greenhouse/Lever + aggregator + D. E. Shaw scraping, filtering
  browser_scraper.py     # optional Playwright scraper for JS-only sites (Two Sigma)
  database.py            # SQLite storage + new-opportunity detection
  suggestions.py         # role classification + prep suggestions
  digest.py              # markdown digest builder
  run.py                 # one scan cycle (entry point)
dashboard/
  app.py                 # Flask dashboard server
  templates/index.html   # the dashboard UI
desktop.py               # native-window launcher (pywebview, no browser)
Start Dashboard (App).bat  # double-click: open as a desktop app
Start Dashboard.bat        # double-click: open in your browser
scripts/
  run_scan.ps1           # run one scan (Task Scheduler calls this)
  start_dashboard.ps1    # launch the dashboard
  install_scheduler.ps1  # register the 6-hour task
  uninstall_scheduler.ps1
cloud/agent_prompt.md    # reference prompt for the cloud backup
data/                    # DB, digests, logs (auto-created; git-ignored)
```

---

## Troubleshooting

- **A firm shows no roles** — its Greenhouse/Lever token may be wrong or it uses a
  different system (Workday, custom site). Those firms still come through the
  aggregator. Check `data\scan.log` for `[skip]` lines.
- **Dashboard won't start** — port 5050 may be busy; change `dashboard_port` in
  `config.json`.
- **Scheduled task didn't run** — it only runs while you're logged in. Open Task
  Scheduler, find `QuantInternshipTracker`, and check "Last Run Result" (0 = ok).
- **Scan found 0 new** — normal; it means nothing changed since the last run.
```
