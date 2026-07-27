#!/usr/bin/env python3
"""
Job Hunter — main scanner

Scans job boards (Tavily search API) for matching roles, scores them, dedupes,
appends to data/Job_Listings.csv, and notifies via Telegram.

Sources covered: main jobs (LinkedIn, Bayt, GulfTalent, Indeed, Glassdoor,
RemoteOK, Arc.dev) + freelance (Upwork, Toptal, Mostaql, Contra, Braintrust,
HackerNews Who's Hiring) + OSS bounties (Algora, Gitcoin).

Usage:
    python3 job_hunter.py                  # full scan from search_config.csv
    python3 job_hunter.py --quick          # quick scan (priority 1 only)
    python3 job_hunter.py --digest         # daily digest mode (no new scans, just summary)
    python3 job_hunter.py --dry-run        # no writes, no Telegram
    python3 job_hunter.py --query "..."    # one-off query
"""

import argparse
import csv
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

# ---------- Paths ----------
ROOT = Path(__file__).parent
DATA = ROOT / "data"
CONFIG_CSV = DATA / "search_config.csv"
LISTINGS_CSV = DATA / "Job_Listings.csv"
DAILY_DIR = DATA / "daily"
APPS_DIR = DATA / "Applications"

DAILY_DIR.mkdir(parents=True, exist_ok=True)
APPS_DIR.mkdir(parents=True, exist_ok=True)

# ---------- Constants ----------
# Single source of truth for the Job_Listings.csv column layout.
# Every reader + writer (job_hunter.append_listing, run_scan, scripts/find_contacts.py,
# scripts/generate_application.py) MUST go through this list. If a script writes
# to Job_Listings.csv without using these fields, the next scanner run will shift
# columns again. Run scripts/repair_listings_csv.py if the header ever drifts.
LISTING_FIELDS = [
    "id", "date_found", "score", "source_type", "company", "role",
    "location", "remote", "sponsorship", "stack_match", "board",
    "url", "salary_range",
    "recruiter_name", "recruiter_email",
    "hiring_manager", "hiring_manager_email",
    "contact_email", "status", "notes",
]

# Status values that may appear in `status` (used by repair + guard + filter).
KNOWN_STATUSES = {"new", "tailored", "applied", "rejected"}

TAVILY_URL = "https://api.tavily.com/search"
TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"
MAX_RESULTS_PER_QUERY = 8
MAX_NOTIFICATIONS_PER_SCAN = 5  # avoid spam

# Mahmoud's profile (baked-in scoring weights)
PROFILE = {
    "name": "Mahmoud ElHassan",
    "role_keywords": [
        ".net", "asp.net", "c#", "c sharp", "backend", "back-end",
        "software engineer", "full stack", "fullstack", "developer",
    ],
    "negative_keywords": [
        "junior", "intern", "ios", "android native", "frontend-only",
        "front-end only", "design", "marketing", "sales",
    ],
    "preferred_locations": [
        "remote", "uae", "dubai", "abu dhabi", "qatar", "doha",
        "ksa", "saudi", "riyadh", "jeddah", "makkah",
        "gulf", "europe", "eu", "uk", "germany", "netherlands",
        "ireland", "malaysia", "singapore", "asia",
    ],
    "excluded_locations": [
        "cairo only", "egypt onsite", "iran", "north korea",
    ],
    "sponsorship_keywords": [
        "visa sponsorship", "sponsorship available", "relocation",
        "visa provided", "work permit",
    ],
    "tech_stack_keywords": [
        "asp.net core", ".net core", "entity framework", "ef core",
        "sql server", "postgresql", "mongo", "redis",
        "azure", "docker", "ci/cd",
        "clean architecture", "microservices", "rest api", "restful",
        "jwt", "multi-tenant",
    ],
    "freelance_indicators": [
        "upwork", "toptal", "freelancer.com", "contra", "braintrust",
        "mostaql", "khamsat", "peopleperhour", "fiverr",
        "contract", "hourly", "fixed price",
    ],
}


# ---------- Helpers ----------
def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def today_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def load_config() -> list[dict[str, str]]:
    """Read search_config.csv and return active queries."""
    if not CONFIG_CSV.exists():
        sys.exit(f"❌ {CONFIG_CSV} not found. Run from project root.")
    rows = []
    with CONFIG_CSV.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Skip comment lines (# ...) and rows with missing 'board' field
            board = row.get("board")
            if not board or board.strip().startswith("#"):
                continue
            # Skip rows with missing 'enabled' field
            enabled = row.get("enabled")
            if not enabled:
                continue
            if enabled.lower() == "true":
                rows.append(row)
    return rows


def load_existing_listings() -> set[str]:
    """Get set of dedup keys (URL + normalized company/role) from existing CSV."""
    if not LISTINGS_CSV.exists() or LISTINGS_CSV.stat().st_size == 0:
        return set()
    keys = set()
    with LISTINGS_CSV.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            url = (row.get("url") or "").strip().lower()
            company = (row.get("company") or "").strip().lower()
            role = (row.get("role") or "").strip().lower()
            if url:
                keys.add(f"url:{url}")
            if company and role:
                keys.add(f"cr:{company}|{role}")
    return keys


def tavily_search(query: str, api_key: str, max_results: int = MAX_RESULTS_PER_QUERY) -> list[dict[str, Any]]:
    """Call Tavily Search API and return results list."""
    payload = {
        "api_key": api_key,
        "query": query,
        "max_results": max_results,
        "search_depth": "basic",
        "include_raw_content": False,
        "topic": "general",
    }
    try:
        resp = requests.post(TAVILY_URL, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        return data.get("results", [])
    except requests.RequestException as e:
        print(f"⚠️  Tavily error for '{query[:50]}...': {e}", file=sys.stderr)
        return []


def is_likely_job(title: str, url: str, content: str) -> bool:
    """Return True if the result looks like a single, real job posting.

    Used as the first gate in run_scan (before scoring / dedupe / saving) so we
    never pollute the CSV with Reddit threads, Workday blogs, NaukriGulf index
    pages, MSDN magazine articles, etc.

    Rules are kept in this single place. Be conservative: when in doubt, allow
    (return True) and let score_result's <=2 gate do the rest. False-positives
    are recoverable; false-negatives (real jobs skipped) are not.
    """
    title_l = (title or "").lower()
    url_l = (url or "").lower()

    # ---- Allow list (high confidence ATS job pages) — checked first so a
    # ---- messy title on a known-good URL still passes.
    allow_hosts = (
        "linkedin.com/jobs/view/",
        "job-boards.greenhouse.io/",
        "boards.greenhouse.io/",
        "jobs.lever.co/",
        "jobs.ashbyhq.com/",
        "myworkdayjobs.com/",  # all *.myworkdayjobs.com host variants
        "bayt.com/en/job/",
        "gulftalent.com/job/",
        "wellfound.com/jobs/",
        "upwork.com/jobs/",
        "toptal.com/freelance-jobs/",
    )
    if any(h in url_l for h in allow_hosts):
        return True
    # Workday ATS specifically requires /job/ in the path (e.g. myworkdayjobs.com/en-US/job/...)
    if "myworkdayjobs.com" in url_l and "/job/" in url_l:
        return True

    # ---- Deny list: URL hosts / paths (high confidence) ----
    deny_hosts = (
        "reddit.com",
        "learn.microsoft.com",
        "devblogs.microsoft.com",
        "msdn.microsoft.com",
        "stackoverflow.blog",
        "hackernoon.com",
        "medium.com",  # articles
    )
    if any(h in url_l for h in deny_hosts):
        return False
    # blog.workday.com (and generally /blog/ on non-ATS hosts)
    if "workday.com" in url_l and "/blog" in url_l:
        return False
    if "/blog/" in url_l and not any(ats in url_l for ats in allow_hosts):
        return False
    # Pure discussion: title contains ": r/" (Reddit style)
    if ": r/" in title_l:
        return False

    # ---- Deny list: title patterns (case-insensitive) ----
    # Question-shaped: "Does X", "Should I Y", "What does Z", "Almost afraid ..."
    question_starts = (
        "does ", "should i ", "what does ", "almost afraid",
        "how to ", "is it worth ",
    )
    if title_l.startswith(question_starts):
        return False
    # Magazine / article style
    magazine_markers = (
        "msdn magazine", "devtalk", "community leadership",
        "magazine:", "by ", "interview with",
    )
    if any(m in title_l for m in magazine_markers):
        return False
    # Aggregate listing pages (e.g. "1000+ Asp.net Core Remote jobs",
    # NaukriGulf-style "Net Developer Jobs in UAE")
    if title_l.startswith("browse "):
        return False
    if re.search(r"\b1000\+ .* jobs\b", title_l):
        return False
    if re.search(r"jobs in (uae|saudi|gulf|egypt|europe|asia|qatar|kuwait|bahrain|oman)\b", title_l):
        return False
    # URL says "jobs?" search page (Indeed / generic aggregators)
    if re.search(r"/jobs\?", url_l):
        return False
    # URL ends with -jobs (e.g. ziprecruiter.com/Jobs/Remote-Backend-Net-Developer)
    if re.search(r"-jobs/?$", url_l):
        return False
    # Aggregator search-result URLs (Jooble, Indeed, SimplyHired, Glassdoor,
    # ZipRecruiter, NaukriGulf, etc.) — they look like job pages but are
    # actually a search-results index for "X role" with N matches.
    aggregator_url_patterns = (
        r"jooble\.org/jobs[-/]",          # ca.jooble.org/jobs-net-developer-...
        r"indeed\.com/q-[a-z0-9%+\-]+-jobs",  # indeed.com/q-...-jobs.html
        r"indeed\.com/jobs\?",             # alternate Indeed search
        r"simplyhired\.com/search\?q=",    # simplyhired.com/search?q=...
        r"glassdoor\.com/Job/.+-jobs-SRCH_",  # glassdoor search results
        r"glassdoor\.com/Job/.+-jobs-(?:SRCH|IL)",
        r"ziprecruiter\.com/Jobs-[A-Za-z]",  # ziprecruiter search-by-keyword
        r"linkedin\.com/jobs/search",       # linkedin search results
        r"linkedin\.com/jobs/.+-jobs\?",    # linkedin search with query
        r"linkedin\.com/jobs/(?:[a-z\-]+-)?jobs\?",
        r"randstadusa\.com/jobs/q-",        # randstad staffing search
        r"arc\.dev/remote-jobs/[a-z\-]+/?$",  # arc.dev category landing page
        r"toptal\.com/freelance-jobs/(?:[a-z\-]+/)?[a-z\-]+/?$",  # toptal category
    )
    if any(re.search(p, url_l) for p in aggregator_url_patterns):
        return False
    # Salary / overview pages (glassdoor, levels.fyi) — not jobs
    if re.search(r"/(Salaries|salary|compensation|overview)/?", url_l):
        return False
    if "salary-SRCH" in url_l or "compensation" in url_l:
        return False
    # URL contains URL-encoded space (+) — almost always a search query
    if "+" in url_l and any(kw in url_l for kw in ("jobs", "developer", "engineer", "net")):
        return False

    # ---- Title patterns: numeric / aggregate markers ----
    # Title is mostly a number: "937 Net developer ...", "$46", "1000+ ... jobs"
    if re.match(r"^\s*(\$?\d[\d,]*\s*$|\d[\d,]*\s)", title_l):
        # "937 jobs" / "$46" / "1000+ ..." → aggregate listing
        return False
    # Title contains " jobs" near the end as a noun (aggregate), not "X is hiring"
    if re.search(r"\b\d*\s*jobs?\b\s*(in\s+\w+)?\s*\.?$", title_l):
        return False
    # Title ends with " jobs" (without "hiring"/"available"/"open" after)
    if re.search(r"\bjobs?\s*\.?$", title_l):
        return False
    # "Browse" prefix (NaukriGulf / ZipRecruiter aggregator)
    if title_l.startswith("browse "):
        return False
    if re.search(r"\b1000\+ .* jobs\b", title_l):
        return False
    if re.search(r"jobs in (uae|saudi|gulf|egypt|europe|asia|qatar|kuwait|bahrain|oman|dubai|abu dhabi|riyadh|jeddah|makkah|new york|london)\b", title_l):
        return False
    # Category/archive page: title contains "[Month Year]" or "(Month Year)"
    if re.search(r"[\[\(]\s*(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{4}\s*[\]\)]", title_l):
        return False
    # Salary / pay trend article titles
    if re.search(r"\baverage salary\b", title_l) or re.search(r"\bpay trends?\b", title_l):
        return False
    # Generic role + "Jobs" as title (e.g. "Net Developer jobs in New York, NY")
    if re.match(r"^[a-z][\w\s\.#\+]+ jobs?( in [\w\s,]+)?[\.,]?$", title_l):
        # If the title is just "X jobs" (no specific company/role detail),
        # treat as aggregator. Real jobs usually have a specific company name.
        return False
    # Title is just a number (ZipRecruiter "salary snippet" preview)
    if re.match(r"^\s*\$?\d+(?:k|,000)?\s*$", title_l):
        return False

    # Default: let it through to score_result
    return True


def score_result(title: str, url: str, content: str) -> tuple[int, str]:
    """
    Score a search result 1-5 based on Mahmoud's profile.
    Returns (score, source_type) where source_type is 'main' | 'freelance' | 'oss' | 'unknown'.
    """
    text = f"{title} {url} {content}".lower()
    score = 0
    notes = []

    # Hard rejects
    for neg in PROFILE["negative_keywords"]:
        if neg in text:
            return (1, "unknown")

    # Role match
    role_hits = sum(1 for kw in PROFILE["role_keywords"] if kw in text)
    if role_hits >= 2:
        score += 2
        notes.append("role+")
    elif role_hits == 1:
        score += 1
        notes.append("role")

    # Tech stack match
    stack_hits = sum(1 for kw in PROFILE["tech_stack_keywords"] if kw in text)
    if stack_hits >= 3:
        score += 2
        notes.append(f"stack+{stack_hits}")
    elif stack_hits >= 1:
        score += 1
        notes.append(f"stack{stack_hits}")

    # Location
    loc_hits = sum(1 for kw in PROFILE["preferred_locations"] if kw in text)
    if loc_hits >= 1:
        score += 1
        notes.append("loc")
    for bad in PROFILE["excluded_locations"]:
        if bad in text:
            score -= 1
            notes.append(f"loc-:{bad}")

    # Sponsorship
    if any(kw in text for kw in PROFILE["sponsorship_keywords"]):
        score += 1
        notes.append("sponsor")

    # Source type
    source = "unknown"
    if any(fw in text for fw in PROFILE["freelance_indicators"]):
        source = "freelance"
        score += 1  # freelance roles count slightly higher (user wants emphasis)
        notes.append("freelance")
    elif "github.com" in url and ("bounty" in text or "issue" in text or "contribute" in text):
        source = "oss"
        notes.append("oss")
    elif any(board in url for board in [
        "linkedin.com", "bayt.com", "gulftalent.com", "indeed.com",
        "glassdoor.com", "remoteok.com", "arc.dev", "weworkremotely.com",
    ]):
        source = "main"
        notes.append("main")

    # Map to 1-5
    if score >= 5:
        return (5, source)
    if score >= 3:
        return (4, source)
    if score >= 2:
        return (3, source)
    if score >= 1:
        return (2, source)
    return (1, source)


def extract_company_role(title: str, url: str) -> tuple[str, str]:
    """Best-effort extract company and role from a search result."""
    # Heuristics: titles often have "Role at Company" or "Company - Role"
    title = title.strip()
    company = ""
    role = title

    patterns = [
        r"^(.+?)\s+at\s+(.+?)(?:\s*[-|]|\s*$)",
        r"^(.+?)\s*[-|]\s*(.+?)$",
    ]
    for pat in patterns:
        m = re.match(pat, title, re.IGNORECASE)
        if m:
            role = m.group(1).strip()
            company = m.group(2).strip()
            break

    # From URL: linkedin.com/jobs/view/ or indeed.com/q-...
    if not company:
        m = re.search(r"linkedin\.com/jobs/view/[^/]*-at-([^-/]+)", url)
        if m:
            company = m.group(1).replace("-", " ").title()

    if not company:
        company = "Unknown"

    return company, role


def append_listing(row: dict[str, str]) -> None:
    """Append one row to Job_Listings.csv (creates with header if needed).

    Hardened against schema drift:
    * Always writes the full LISTING_FIELDS header (never the old 16-col shape).
    * Normalises the row dict to LISTING_FIELDS keys (default "" for missing).
    * Refuses to append if the existing header on disk doesn't match
      LISTING_FIELDS (so we never silently shift columns again).
    """
    is_new = not LISTINGS_CSV.exists() or LISTINGS_CSV.stat().st_size == 0

    if not is_new:
        with LISTINGS_CSV.open(encoding="utf-8", newline="") as f:
            reader = csv.reader(f)
            existing_header = next(reader, None)
        if existing_header != LISTING_FIELDS:
            sys.exit(
                "❌ Job_Listings.csv header does not match LISTING_FIELDS.\n"
                f"   on disk: {existing_header}\n"
                f"   expected: {LISTING_FIELDS}\n"
                "   Run `python3 scripts/repair_listings_csv.py` to repair."
            )

    # Normalise: any extra keys are dropped, missing keys become "".
    safe_row = {k: ("" if row.get(k) is None else str(row.get(k, "")))
                for k in LISTING_FIELDS}

    with LISTINGS_CSV.open("a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=LISTING_FIELDS,
            extrasaction="ignore",
        )
        if is_new:
            writer.writeheader()
        writer.writerow(safe_row)


def send_telegram(text: str, bot_token: str, chat_id: str) -> bool:
    """Send a message via Telegram Bot API. Returns True on success.

    Strategy: try Markdown first, fall back to plain text on 400.
    Plain text is more robust against URLs/underscores/special chars in scraped data.
    """
    if not bot_token or not chat_id:
        print(f"⚠️  Telegram not configured; would have sent:\n{text[:200]}...")
        return False
    url = TELEGRAM_API.format(token=bot_token)
    base_payload = {
        "chat_id": chat_id,
        "text": text,
        "disable_web_page_preview": True,
    }
    # Try Markdown first (gives bold formatting)
    try:
        resp = requests.post(url, json={**base_payload, "parse_mode": "Markdown"}, timeout=15)
        if resp.status_code == 200:
            return True
        # Markdown parse failed — log and fall back
        print(f"⚠️  Telegram Markdown failed (status {resp.status_code}), retrying plain text",
              file=sys.stderr)
    except requests.RequestException as e:
        print(f"⚠️  Telegram Markdown request error: {e}, retrying plain text", file=sys.stderr)

    # Fall back to plain text (no parse_mode)
    try:
        resp = requests.post(url, json=base_payload, timeout=15)
        resp.raise_for_status()
        return True
    except requests.RequestException as e:
        print(f"❌ Telegram plain text also failed: {e}", file=sys.stderr)
        return False


def format_telegram(item: dict[str, str]) -> str:
    """Format a single listing for Telegram."""
    score = item["score"]
    emoji = {5: "🔥", 4: "🟢", 3: "⚪", 2: "🟡"}.get(int(score), "•")
    return (
        f"{emoji} **{item['company']}** — {item['role']}\n"
        f"📍 {item['location'] or 'N/A'}"
        f"{' · 🏠 Remote' if item['remote'] == 'yes' else ''}"
        f"{' · ✈️ Sponsorship' if item['sponsorship'] == 'yes' else ''}\n"
        f"💼 Stack: {item['stack_match'] or 'N/A'}\n"
        f"💰 {item['salary_range'] or 'Salary not listed'}\n"
        f"🔗 {item['url']}\n"
    )


def run_scan(
    queries: list[dict[str, str]],
    tavily_key: str,
    tg_token: str,
    tg_chat: str,
    dry_run: bool = False,
) -> dict[str, int]:
    """Run one scan pass. Returns stats dict."""
    stats = {"queries": 0, "results": 0, "new": 0, "score_5": 0, "score_4": 0, "notified": 0}
    existing = load_existing_listings()
    notified_buffer: list[dict[str, str]] = []
    scan_id = f"{today_str()}-{datetime.now().strftime('%H%M%S')}"

    for q in queries:
        stats["queries"] += 1
        query_text = q["query"]
        location_filter = q.get("location_filter", "")
        print(f"🔍 [{stats['queries']}] {query_text} ({location_filter or 'any'})")

        if dry_run:
            # Dry-run: skip network calls entirely
            print(f"   [dry-run] skipped API call")
            results = []
        else:
            results = tavily_search(query_text, tavily_key)
        stats["results"] += len(results)

        for r in results:
            url = r.get("url", "")
            title = r.get("title", "")
            content = r.get("content", "")

            if not url or not title:
                continue

            # Phase 2: drop non-job results (Reddit / blog / index pages) before
            # anything else. Log every skip so the rule list can be tuned from
            # Actions logs.
            if not is_likely_job(title, url, content):
                print(f"   skipped noise: {url}")
                continue

            # Dedup
            url_key = f"url:{url.lower()}"
            company_guess, role_guess = extract_company_role(title, url)
            cr_key = f"cr:{company_guess.lower()}|{role_guess.lower()}"
            if url_key in existing or cr_key in existing:
                continue

            score, source = score_result(title, url, content)
            if score <= 2:
                continue  # don't pollute the CSV with low-quality

            # Determine remote/sponsorship flags
            text_lower = f"{title} {content}".lower()
            remote = "yes" if "remote" in text_lower else "unknown"
            sponsorship = "yes" if any(kw in text_lower for kw in PROFILE["sponsorship_keywords"]) else "unknown"

            # Determine stack match keywords
            stack_match = ", ".join([
                kw for kw in PROFILE["tech_stack_keywords"] if kw in text_lower
            ][:5])

            # Board detection
            board = "unknown"
            for b in ["linkedin", "bayt", "gulftalent", "indeed", "glassdoor",
                      "remoteok", "arc.dev", "weworkremotely", "upwork", "toptal",
                      "mostaql", "contra", "braintrust", "github.com"]:
                if b in url:
                    board = b
                    break

            row = {
                "id": f"JOB-{scan_id}-{stats['new']+1:03d}",
                "date_found": now_iso(),
                "score": str(score),
                "source_type": source,
                "company": company_guess,
                "role": role_guess,
                "location": location_filter or "N/A",
                "remote": remote,
                "sponsorship": sponsorship,
                "stack_match": stack_match,
                "board": board,
                "url": url,
                "salary_range": "N/A",
                # 4 contact fields: empty by default; find_contacts.py fills them later.
                "recruiter_name": "",
                "recruiter_email": "",
                "hiring_manager": "",
                "hiring_manager_email": "",
                "contact_email": "",
                "status": "new",
                "notes": (content[:200] + "...") if len(content) > 200 else content,
            }

            if not dry_run:
                append_listing(row)
                existing.add(url_key)
                existing.add(cr_key)

            stats["new"] += 1
            if score == 5:
                stats["score_5"] += 1
                if len(notified_buffer) < MAX_NOTIFICATIONS_PER_SCAN:
                    notified_buffer.append(row)
            elif score == 4:
                stats["score_4"] += 1
                if len(notified_buffer) < MAX_NOTIFICATIONS_PER_SCAN:
                    notified_buffer.append(row)

    # Send notifications
    if notified_buffer and not dry_run:
        header = f"🎯 *Job Hunter — {stats['new']} new match{'es' if stats['new'] != 1 else ''}*\n"
        body = "\n".join(format_telegram(item) for item in notified_buffer)
        footer = f"\n_Generated at {now_iso()}_"
        msg = header + body + footer
        ok = send_telegram(msg, tg_token, tg_chat)
        if ok:
            stats["notified"] = len(notified_buffer)

    return stats


def write_daily_log(stats: dict[str, int], queries_run: int) -> None:
    """Write today's scan log."""
    log_path = DAILY_DIR / f"{today_str()}.md"
    is_new = not log_path.exists()
    with log_path.open("a", encoding="utf-8") as f:
        if is_new:
            f.write(f"# Daily Scan — {today_str()}\n\n")
        f.write(f"## Scan at {datetime.now().strftime('%H:%M:%S')}\n")
        f.write(f"- Queries run: {queries_run}\n")
        f.write(f"- Results fetched: {stats['results']}\n")
        f.write(f"- New listings added: **{stats['new']}**\n")
        f.write(f"- Score 5: {stats['score_5']} | Score 4: {stats['score_4']}\n")
        f.write(f"- Telegram notifications sent: {stats['notified']}\n\n")


def main():
    parser = argparse.ArgumentParser(description="Job Hunter scanner")
    parser.add_argument("--quick", action="store_true", help="Quick scan (priority 1 only)")
    parser.add_argument("--dry-run", action="store_true", help="Don't write or notify")
    parser.add_argument("--query", type=str, help="One-off query, skip config")
    args = parser.parse_args()

    load_dotenv(ROOT / ".env")
    tavily_key = os.environ.get("TAVILY_API_KEY", "")
    tg_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    tg_chat = os.environ.get("TELEGRAM_CHAT_ID", "")

    if not tavily_key:
        sys.exit("❌ TAVILY_API_KEY not set. See .env.example.")

    if args.query:
        queries = [{"query": args.query, "location_filter": "", "enabled": "true", "priority": "1"}]
    else:
        queries = load_config()
        if args.quick:
            queries = [q for q in queries if q.get("priority") == "1"]

    if not queries:
        sys.exit("❌ No enabled queries in search_config.csv")

    print(f"🚀 Starting scan: {len(queries)} queries")
    stats = run_scan(queries, tavily_key, tg_token, tg_chat, dry_run=args.dry_run)
    if not args.dry_run:
        write_daily_log(stats, len(queries))

    print(f"\n📊 Done: {stats['queries']} queries, {stats['results']} results, "
          f"{stats['new']} new (5★: {stats['score_5']}, 4★: {stats['score_4']}), "
          f"{stats['notified']} notifications.")


if __name__ == "__main__":
    main()
