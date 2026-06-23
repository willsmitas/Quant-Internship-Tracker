# Quant Internship Tracker

An automated agent that scours the web for **quant / trading internships** every
6 hours, plus a local **dashboard** that compiles every opportunity with
deadlines and tailored suggestions for improving your chances.

Built for William Smitas (william_smitas@brown.edu).

---

## What it does

- **Scans every 6 hours** via a Windows Scheduled Task (already installed).
- Pulls from two kinds of sources, fail-soft (one source breaking never stops a run):
  - **Company ATS APIs** (Greenhouse / Lever) for major quant firms: IMC, DRW,
    Point72 / Cubist, Jump Trading, Akuna, Old Mission, Virtu, Tower Research,
    PDT Partners, Optiver.
  - **Community internship aggregators** (SimplifyJobs + vanshb03 GitHub lists),
    filtered to quant/trading-relevant roles — this covers Citadel, SIG, Jane
    Street, Walleye, AQR, Radix, and many more that don't expose a public API.
- **Filters to US, undergrad-eligible roles** — drops international-only postings
  and PhD/Master's-only roles (toggle with `us_undergrad_only` in `config.json`).
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
| `internship_terms` | Extra multi-word terms to count as an internship. |
| `github_listing_urls` | Aggregator JSON feeds (bump to the Summer 2027 repo when it's live). |
| `dashboard_port` | Port for the dashboard (default 5050). |

After editing, run a scan (or hit "Scan now") to apply.

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
requirements.txt
src/
  config.py              # defaults + config.json loader
  scraper.py             # Greenhouse/Lever + aggregator scraping, filtering
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
