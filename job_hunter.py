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
    """Append one row to Job_Listings.csv (creates with header if needed)."""
    is_new = not LISTINGS_CSV.exists() or LISTINGS_CSV.stat().st_size == 0
    with LISTINGS_CSV.open("a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "id", "date_found", "score", "source_type", "company", "role",
            "location", "remote", "sponsorship", "stack_match", "board",
            "url", "salary_range", "contact_email", "status", "notes",
        ])
        if is_new:
            writer.writeheader()
        writer.writerow(row)


def send_telegram(text: str, bot_token: str, chat_id: str) -> bool:
    """Send a message via Telegram Bot API. Returns True on success."""
    if not bot_token or not chat_id:
        print(f"⚠️  Telegram not configured; would have sent:\n{text[:200]}...")
        return False
    try:
        url = TELEGRAM_API.format(token=bot_token)
        resp = requests.post(url, json={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True,
        }, timeout=15)
        resp.raise_for_status()
        return True
    except requests.RequestException as e:
        print(f"⚠️  Telegram send failed: {e}", file=sys.stderr)
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

        results = tavily_search(query_text, tavily_key)
        stats["results"] += len(results)

        for r in results:
            url = r.get("url", "")
            title = r.get("title", "")
            content = r.get("content", "")

            if not url or not title:
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
