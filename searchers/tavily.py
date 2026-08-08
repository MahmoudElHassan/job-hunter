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
from typing import Any
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
import requests

TAVILY_URL = "https://api.tavily.com/search"
MAX_RESULTS_PER_QUERY = 8


def tavily_search(
    query: str,
    api_key: str,
    max_results: int = MAX_RESULTS_PER_QUERY,
    freshness_days: int | None = None,
) -> list[dict[str, Any]]:
    """Call Tavily Search API and return raw results list.

    Returns an empty list on error and prints a warning to stderr. The
    searcher wrapper is responsible for converting this to RawResult.

    `freshness_days` maps to Tavily `time_range` per docs:
      <= 1   → "day"
      <= 7   → "week"
      <= 31  → "month"
      else   → "year"
    `time_range` and `start_date` must not be combined.
    """
    payload: dict[str, Any] = {
        "api_key": api_key,
        "query": query,
        "max_results": max_results,
        "search_depth": "basic",
        "include_raw_content": False,
        "topic": "general",
    }
    if freshness_days is not None:
        try:
            days = int(freshness_days)
        except (TypeError, ValueError):
            days = None
        if days is not None and days > 0:
            if days <= 1:
                payload["time_range"] = "day"
            elif days <= 7:
                payload["time_range"] = "week"
            elif days <= 31:
                payload["time_range"] = "month"
            else:
                payload["time_range"] = "year"
    try:
        resp = requests.post(TAVILY_URL, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        return data.get("results", [])
    except requests.RequestException as e:
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

