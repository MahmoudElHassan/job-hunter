#!/usr/bin/env python3
"""
Daily digest — sends a summary of today's finds + pipeline status to Telegram.
Designed to be run as a GitHub Action (digest.yml) at end of business day.
"""

import csv
import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import requests

# #region agent log
_DEBUG_LOG = Path(__file__).resolve().parent.parent / ".cursor" / "debug-08a199.log"


def _agent_log(hypothesis_id: str, location: str, message: str, data: dict, run_id: str = "digest-review") -> None:
    try:
        payload = {
            "sessionId": "08a199",
            "runId": run_id,
            "hypothesisId": hypothesis_id,
            "location": location,
            "message": message,
            "data": data,
            "timestamp": int(datetime.now(timezone.utc).timestamp() * 1000),
        }
        with _DEBUG_LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload) + "\n")
    except Exception:
        pass
# #endregion

ROOT = Path(__file__).parent.parent
LISTINGS = ROOT / "data" / "Job_Listings.csv"
DAILY_DIR = ROOT / "data" / "daily"


def today_str() -> str:
    # Match Job_Listings.csv date_found (UTC from job_hunter.now_iso).
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def send_telegram(text: str, token: str, chat_id: str) -> bool:
    if not token or not chat_id:
        print(f"⚠️  Telegram not configured. Message would be:\n{text[:300]}...")
        # #region agent log
        _agent_log("H3", "daily_digest.py:send_telegram", "telegram not configured", {"configured": False})
        # #endregion
        return False
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    base_payload = {
        "chat_id": chat_id,
        "text": text,
        "disable_web_page_preview": True,
    }
    try:
        resp = requests.post(url, json={**base_payload, "parse_mode": "Markdown"}, timeout=15)
        if resp.status_code == 200:
            # #region agent log
            _agent_log("H3", "daily_digest.py:send_telegram", "markdown send ok", {"status": 200})
            # #endregion
            return True
        print(
            f"⚠️  Telegram Markdown failed (status {resp.status_code}), retrying plain text",
            file=sys.stderr,
        )
    except requests.RequestException as e:
        print(f"⚠️  Telegram Markdown request error: {e}, retrying plain text", file=sys.stderr)

    try:
        resp = requests.post(url, json=base_payload, timeout=15)
        resp.raise_for_status()
        # #region agent log
        _agent_log("H3", "daily_digest.py:send_telegram", "plain-text fallback ok", {"status": resp.status_code})
        # #endregion
        return True
    except requests.RequestException as e:
        print(f"❌ Telegram send failed: {e}", file=sys.stderr)
        # #region agent log
        _agent_log("H3", "daily_digest.py:send_telegram", "send failed", {"error": type(e).__name__})
        # #endregion
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
    lines.append("_Next scan: Sun / Tue / Thu 17:00 Makkah_")
    return "\n".join(lines)


def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")

    # #region agent log
    _agent_log(
        "H1",
        "daily_digest.py:main",
        "requests imported; starting digest",
        {
            "requests_ok": True,
            "has_token": bool(token),
            "has_chat": bool(chat_id),
            "today_utc": today_str(),
        },
    )
    # #endregion

    stats = gather_today()
    # #region agent log
    _agent_log(
        "H4",
        "daily_digest.py:main",
        "gather_today",
        {"new_today": stats["new_today"], "total": stats["total"]},
    )
    # #endregion
    msg = format_digest(stats)
    print(msg)
    configured = bool(token and chat_id)
    ok = send_telegram(msg, token, chat_id)
    if configured and not ok:
        sys.exit("❌ Digest built but Telegram send failed.")


if __name__ == "__main__":
    main()
