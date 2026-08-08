#!/usr/bin/env python3
"""
Daily digest — sends a summary of today's finds + pipeline status to Telegram.
Designed to be run as a GitHub Action (digest.yml) at end of business day.
"""

import csv
import os
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).parent.parent
LISTINGS = ROOT / "data" / "Job_Listings.csv"
DAILY_DIR = ROOT / "data" / "daily"


def today_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def send_telegram(text: str, token: str, chat_id: str) -> bool:
    if not token or not chat_id:
        print(f"⚠️  Telegram not configured. Message would be:\n{text[:300]}...")
        return False
    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown",
                  "disable_web_page_preview": True},
            timeout=15,
        )
        resp.raise_for_status()
        return True
    except requests.RequestException as e:
        print(f"❌ Telegram send failed: {e}", file=sys.stderr)
        return False


def gather_today() -> dict:
    """Gather stats about listings found today."""
    if not LISTINGS.exists() or LISTINGS.stat().st_size == 0:
        return {"new_today": 0, "score_5": 0, "score_4": 0, "total": 0,
                "by_status": {}, "by_source": {}, "top_companies": []}

    today = today_str()
    new_today = []
    by_status = Counter()
    by_source = Counter()
    companies = Counter()
    total = 0

    with LISTINGS.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            total += 1
            by_status[row.get("status", "unknown")] += 1
            by_source[row.get("source_type", "unknown")] += 1
            companies[row.get("company", "Unknown")] += 1
            if row.get("date_found", "").startswith(today):
                new_today.append(row)

    return {
        "new_today": len(new_today),
        "score_5": sum(1 for r in new_today if r.get("score") == "5"),
        "score_4": sum(1 for r in new_today if r.get("score") == "4"),
        "total": total,
        "by_status": dict(by_status),
        "by_source": dict(by_source),
        "top_companies": companies.most_common(5),
    }


def format_digest(stats: dict) -> str:
    today = today_str()
    by_status = stats["by_status"]
    by_source = stats["by_source"]
    lines = [
        f"📊 *Daily Digest — {today}*",
        "",
        f"🆕 New today: *{stats['new_today']}* "
        f"(5★: {stats['score_5']} · 4★: {stats['score_4']})",
        f"📦 Total in pipeline: *{stats['total']}*",
        "",
        "*By source:*",
    ]
    for src, n in sorted(by_source.items(), key=lambda x: -x[1]):
        lines.append(f"  • {src}: {n}")
    lines.append("")
    lines.append("*By status:*")
    for st, n in sorted(by_status.items(), key=lambda x: -x[1]):
        lines.append(f"  • {st}: {n}")

    if stats["new_today"] == 0:
        lines.append("")
        lines.append("😴 No new matches today. The market is quiet — keep applying to the warm leads.")

    lines.append("")
    lines.append("_Next scan: 08:00 Makkah (tomorrow)_")
    return "\n".join(lines)


def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")

    stats = gather_today()
    msg = format_digest(stats)
    print(msg)
    send_telegram(msg, token, chat_id)


if __name__ == "__main__":
    main()
