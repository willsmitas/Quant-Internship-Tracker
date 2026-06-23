"""Role classification + tailored prep suggestions.

categorize() maps a job title to one of five tracks. Each track has a curated
list of concrete prep actions (with a resource) so the dashboard can tell the
user what to work on to improve their odds for that specific kind of role.
"""
from __future__ import annotations

# Order matters: first matching track wins.
_TRACK_KEYWORDS = [
    ("trader", [
        "trader", "trading intern", "quant trading", "quantitative trading",
        "market making", "market maker", "execution trader", "trading analyst",
    ]),
    ("researcher", [
        "research", "quant research", "quantitative research", "alpha",
        "signal", "modeling", "statistician", "data scientist", "machine learning",
        "ml ", "ai ", "quantitative analyst", "quant analyst",
    ]),
    ("developer", [
        "software", "engineer", "developer", "swe", "c++", "infrastructure",
        "platform", "systems", "low latency", "low-latency", "devops", "sre",
        "fpga", "hardware",
    ]),
    ("data", [
        "data engineer", "data analyst", "analytics", "database", "pipeline",
        "data platform",
    ]),
]

TRACK_LABELS = {
    "trader": "Quant Trader",
    "researcher": "Quant Researcher",
    "developer": "Quant Developer / SWE",
    "data": "Data / Analytics",
    "general": "General / Other",
}

# Each suggestion: (focus area, concrete action, resource)
_SUGGESTIONS = {
    "trader": [
        ("Mental math", "Hit 20/20 on Zetamac (arithmetic) consistently under time pressure.", "arithmetic.zetamac.com"),
        ("Probability & EV", "Drill expected value, conditional probability, and combinatorics until reflexive.", "Heard on the Street; A Practical Guide to Quant Finance Interviews (Green Book)"),
        ("Market-making games", "Practice making two-sided markets and updating on new info (Figgie, estimation games).", "Jane Street Figgie; estimation/penny-jar games"),
        ("Sequential decisions", "Study optimal stopping, Kelly criterion, and simple game theory.", "Green Book ch. on games; Kelly criterion notes"),
        ("Brain teasers", "Work through classic trading-desk puzzles out loud, explaining your reasoning.", "Heard on the Street; Frederick Mosteller 'Fifty Challenging Problems'"),
        ("Poker / EV intuition", "Play low-stakes poker to internalize variance, pot odds, and reads.", "Any poker EV primer"),
    ],
    "researcher": [
        ("Statistics", "Master hypothesis testing, regression, MLE, and time-series (stationarity, autocorrelation).", "Wasserman 'All of Statistics'; Tsay 'Analysis of Financial Time Series'"),
        ("Python / data stack", "Be fluent in numpy/pandas/scikit-learn; build a clean research notebook end-to-end.", "pandas docs; scikit-learn user guide"),
        ("ML fundamentals", "Understand bias-variance, regularization, cross-validation, and overfitting on noisy data.", "ESL (Hastie); fast.ai"),
        ("Research project", "Ship one signal-research project: hypothesis -> data -> backtest -> writeup on GitHub.", "Kaggle dataset or free market data (yfinance)"),
        ("Probability theory", "Solidify distributions, expectations, Brownian motion basics, and stochastic intuition.", "Green Book; Shreve vol. 1 (light)"),
        ("Reading papers", "Read & summarize a few SSRN / arXiv q-fin papers; be able to critique methodology.", "ssrn.com (q-fin), arxiv.org/list/q-fin"),
    ],
    "developer": [
        ("Data structures & algos", "Grind LeetCode mediums/hards; target ~150 problems with patterns mastered.", "LeetCode; NeetCode 150"),
        ("C++ proficiency", "Learn modern C++ (move semantics, templates, RAII); most low-latency desks use it.", "cppreference; 'Effective Modern C++' (Meyers)"),
        ("Low-latency concepts", "Study cache behavior, memory layout, lock-free structures, and kernel-bypass basics.", "Mechanical sympathy blogs; CppCon talks"),
        ("Systems project", "Build something concrete: an order book, a backtester, or a market-data parser.", "Your GitHub"),
        ("Online assessments", "Practice timed HackerRank/CodeSignal — many quant firms gate on an OA first.", "CodeSignal; HackerRank"),
        ("Concurrency", "Understand threads, atomics, and async; be ready to reason about race conditions.", "C++ concurrency in action"),
    ],
    "data": [
        ("SQL fluency", "Be quick with window functions, joins, and query optimization.", "StrataScratch; DataLemur"),
        ("Pipelines", "Know how to move/clean large datasets reliably (pandas, Spark basics, schemas).", "pandas docs; Spark quickstart"),
        ("Python ETL", "Build a small reproducible pipeline from raw source to clean analytical table.", "Your GitHub"),
        ("Statistics", "Refresh distributions, A/B testing, and summary-stat intuition.", "Wasserman 'All of Statistics'"),
        ("Visualization", "Tell a clear story from data (matplotlib/plotly) — clarity beats decoration.", "Storytelling with Data"),
    ],
    "general": [
        ("Resume tailoring", "One page, quantified bullets, finance/quant keywords matched to the posting.", "Jobscan; your career center"),
        ("Probability & math", "Refresh core probability and mental math — nearly every quant loop tests it.", "Green Book; Zetamac"),
        ("Coding basics", "Be comfortable with Python and basic LeetCode-style problems.", "LeetCode; NeetCode"),
        ("Networking", "Reach out to alumni at the firm; attend info sessions; ask specific questions.", "LinkedIn; Brown CareerLAB / alumni"),
    ],
}

GENERAL_CHECKLIST = [
    "Keep a master resume + tailor a one-page version per firm (match the posting's keywords).",
    "Apply within days of a posting going live — many quant internships are reviewed on a rolling basis.",
    "Build a public GitHub with 1-2 polished quant projects (backtest, signal study, or order book).",
    "Get fast at mental math (Zetamac) and core probability (Green Book) — common across every track.",
    "Practice timed online assessments (CodeSignal / HackerRank) before you need them.",
    "Network: message Brown alumni at target firms, attend info sessions, ask thoughtful questions.",
    "Prepare 3-4 behavioral stories (challenge, failure, teamwork, why-this-firm) using STAR.",
    "Track every application + deadline (this dashboard) so nothing slips through the cracks.",
]


def categorize(title: str) -> str:
    t = (title or "").lower()
    for track, kws in _TRACK_KEYWORDS:
        if any(k in t for k in kws):
            return track
    return "general"


def suggestions_for(track: str):
    return _SUGGESTIONS.get(track, _SUGGESTIONS["general"])


def label_for(track: str) -> str:
    return TRACK_LABELS.get(track, TRACK_LABELS["general"])
