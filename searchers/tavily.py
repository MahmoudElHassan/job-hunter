"""Shared Tavily API call + URL normalization.

Every searcher goes through `tavily_search` so a future change to the API
(headers, payload shape, rate-limit handling) is done in one place.
`normalize_url` rejects URLs that are obviously not real pages — empty,
non-http(s), or /goto redirect paths.
`canonicalize_url` is the dedup-friendly form: lowercase host, strip
trailing slash, drop tracking query params.
"""
from __future__ import annotations

import re
import sys
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
import requests

TAVILY_URL = "https://api.tavily.com/search"
MAX_RESULTS_PER_QUERY = 8

# Set when Tavily returns 432 (monthly plan / key usage limit). Callers should
# abort the scan so we do not silently finish with 0 results and an empty CSV.
_PLAN_LIMIT_HIT = False


def tavily_plan_limit_hit() -> bool:
    """True if any call this process hit HTTP 432 plan/key limit."""
    return _PLAN_LIMIT_HIT


def reset_tavily_plan_limit_flag() -> None:
    """Reset the plan-limit flag (tests / new scan process)."""
    global _PLAN_LIMIT_HIT
    _PLAN_LIMIT_HIT = False


def tavily_search(
    query: str,
    api_key: str,
    max_results: int = MAX_RESULTS_PER_QUERY,
    freshness_days: int | None = None,
) -> list[dict[str, Any]]:
    """Call Tavily Search API and return raw results list.

    Returns an empty list on error and prints a warning to stderr. The
    searcher wrapper is responsible for converting this to RawResult.

    On HTTP 432 (plan limit exceeded), sets `tavily_plan_limit_hit()` and
    skips further network calls for the rest of the process.

    `freshness_days` maps to Tavily recency:
      <= 2   → start_date = now UTC minus N days (48h when N=2)
               (no time_range — API forbids combining them)
      <= 7   → time_range "week"
      <= 31  → time_range "month"
      else   → time_range "year"
    If start_date is rejected (4xx other than 432), falls back to time_range=day.
    """
    global _PLAN_LIMIT_HIT
    if _PLAN_LIMIT_HIT:
        return []

    payload: dict[str, Any] = {
        "api_key": api_key,
        "query": query,
        "max_results": max_results,
        "search_depth": "basic",
        "include_raw_content": False,
        "topic": "general",
    }
    used_start_date = False
    if freshness_days is not None:
        try:
            days = int(freshness_days)
        except (TypeError, ValueError):
            days = None
        if days is not None and days > 0:
            if days <= 2:
                # Exact window (e.g. 48h) via start_date instead of coarse "day".
                start = datetime.now(timezone.utc) - timedelta(days=days)
                payload["start_date"] = start.strftime("%Y-%m-%d")
                used_start_date = True
            elif days <= 7:
                payload["time_range"] = "week"
            elif days <= 31:
                payload["time_range"] = "month"
            else:
                payload["time_range"] = "year"
    try:
        resp = requests.post(TAVILY_URL, json=payload, timeout=30)
        if resp.status_code == 432:
            _PLAN_LIMIT_HIT = True
            print(
                "❌ Tavily plan/key limit exceeded (HTTP 432). "
                "Upgrade the plan or wait for the quota reset — aborting further queries.",
                file=sys.stderr,
            )
            return []
        # start_date rejected → fall back to time_range=day (stricter 24h).
        if used_start_date and resp.status_code >= 400 and resp.status_code != 432:
            print(
                f"⚠️  Tavily start_date rejected ({resp.status_code}); "
                "retrying with time_range=day",
                file=sys.stderr,
            )
            payload.pop("start_date", None)
            payload["time_range"] = "day"
            resp = requests.post(TAVILY_URL, json=payload, timeout=30)
            if resp.status_code == 432:
                _PLAN_LIMIT_HIT = True
                print(
                    "❌ Tavily plan/key limit exceeded (HTTP 432). "
                    "Upgrade the plan or wait for the quota reset — aborting further queries.",
                    file=sys.stderr,
                )
                return []
        resp.raise_for_status()
        data = resp.json()
        return data.get("results", [])
    except requests.RequestException as e:
        # Some adapters surface 432 only after raise_for_status.
        status = getattr(getattr(e, "response", None), "status_code", None)
        if status == 432:
            _PLAN_LIMIT_HIT = True
            print(
                "❌ Tavily plan/key limit exceeded (HTTP 432). "
                "Upgrade the plan or wait for the quota reset — aborting further queries.",
                file=sys.stderr,
            )
            return []
        print(f"⚠️  Tavily error for '{query[:50]}...': {e}", file=sys.stderr)
        return []


# Reject anything that obviously isn't a real landing page.
_BAD_PATH = re.compile(r"/goto\?")

# Tracking / referrer query params we strip from canonical URL.
_STRIPPED_QUERY_PREFIXES = ("utm_",)
_STRIPPED_QUERY_KEYS = {"fbclid", "ref", "ref_src", "refId"}


def normalize_url(url: str) -> str:
    """Return the URL if it's a real, fetchable page, else ''.

    Strips empty, non-http, and /goto redirect-style URLs. Per-platform
    searchers should call this before accept_url.
    """
    if not url:
        return ""
    url_l = url.lower()
    if not (url_l.startswith("http://") or url_l.startswith("https://")):
        return ""
    if _BAD_PATH.search(url_l):
        return ""
    return url


def canonicalize_url(url: str) -> str:
    """Return a canonical, dedup-friendly form of `url`.

    - empty / non-http(s) → ''
    - lowercases host (scheme stays lower too)
    - strips trailing slash from path
    - drops utm_*, fbclid, ref, ref_src, refId
    - drops empty query/fragment

    Used as the dedupe key in run_scan so the same posting surfaced via
    two different tracking URLs is not duplicated.
    """
    if not url:
        return ""
    raw = url.strip()
    if not (raw.lower().startswith("http://") or raw.lower().startswith("https://")):
        return ""
    parts = urlsplit(raw)
    scheme = (parts.scheme or "https").lower()
    netloc = parts.netloc.lower()
    # Strip default ports
    if netloc.endswith(":80") and scheme == "http":
        netloc = netloc[:-3]
    if netloc.endswith(":443") and scheme == "https":
        netloc = netloc[:-4]
    path = parts.path or ""
    if len(path) > 1 and path.endswith("/"):
        path = path.rstrip("/")
    if path == "":
        path = "/"
    # Filter query params
    query_pairs = parse_qsl(parts.query, keep_blank_values=True)
    keep = []
    for k, v in query_pairs:
        kl = k.lower()
        if any(kl.startswith(p) for p in _STRIPPED_QUERY_PREFIXES):
            continue
        if kl in _STRIPPED_QUERY_KEYS:
            continue
        keep.append((k, v))
    new_query = urlencode(keep)
    return urlunsplit((scheme, netloc, path, new_query, ""))

