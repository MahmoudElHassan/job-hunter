"""Shared Tavily API call + URL normalization.

Every searcher goes through `tavily_search` so a future change to the API
(headers, payload shape, rate-limit handling) is done in one place.
`normalize_url` rejects URLs that are obviously not real pages — empty,
non-http(s), or /goto redirect paths.
"""
from __future__ import annotations

import re
import sys
from typing import Any
import requests

TAVILY_URL = "https://api.tavily.com/search"
MAX_RESULTS_PER_QUERY = 8


def tavily_search(query: str, api_key: str, max_results: int = MAX_RESULTS_PER_QUERY) -> list[dict[str, Any]]:
    """Call Tavily Search API and return raw results list.

    Returns an empty list on error and prints a warning to stderr. The
    searcher wrapper is responsible for converting this to RawResult.
    """
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


# Reject anything that obviously isn't a real landing page.
_BAD_PATH = re.compile(r"/goto\?")


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
