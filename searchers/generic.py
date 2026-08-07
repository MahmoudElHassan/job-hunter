"""GenericBoardSearcher — fallback for boards without a dedicated searcher.

Adds a `site:` clause from a built-in map. If the board is unknown, the
query is used as-is (still subject to accept_url filter).
"""
from __future__ import annotations

from typing import Any
from .base import RawResult, Searcher
from .tavily import normalize_url, tavily_search


# site: restrictions for the boards that don't have a dedicated searcher.
# Keep narrow — only the host that actually holds job postings, not the
# whole domain.
GENERIC_BOARD_SITE = {
    "linkedin":       "site:linkedin.com/jobs",  # alias handled by registry
    "bayt":           "site:bayt.com",
    "gulftalent":     "site:gulftalent.com",
    "indeed":         "site:indeed.com",
    "glassdoor":      "site:glassdoor.com",
    "remoteok":       "site:remoteok.com",
    "weworkremotely": "site:weworkremotely.com",
    "arcdev":         "site:arc.dev",
    "toptal":         "site:toptal.com",
    "contra":         "site:contra.com",
    "braintrust":     "site:braintrust.dev",
    "peopleperhour":  "site:peopleperhour.com",
    "news.ycombinator": "site:news.ycombinator.com",
    "github":         "site:github.com",
    # 'google' intentionally omitted — its query already contains site:
}


class GenericBoardSearcher:
    """Adds `site:` to the query and accepts any http(s) URL that isn't
    a /goto redirect. Real filtering for GenericBoardSearcher is still
    done by the global `is_likely_job` gate in run_scan."""

    def __init__(self, board_name: str = "unknown") -> None:
        self._board = board_name or "unknown"

    @property
    def board(self) -> str:
        """Canonical board name for logs + CSV (e.g. bayt, google)."""
        return self._board

    def build_query(self, row: dict) -> str:
        q = (row.get("query") or "").strip()
        board = (row.get("board") or self._board or "").strip().lower()
        # Trust the config: if it already contains site:, pass through.
        if "site:" in q.lower():
            return q
        site = GENERIC_BOARD_SITE.get(board)
        if site:
            return f"{site} {q}"
        return q

    def search(self, row: dict, api_key: str, *, dry_run: bool = False) -> list[RawResult]:
        query = self.build_query(row)
        if dry_run:
            return []
        raw = tavily_search(query, api_key)
        out: list[RawResult] = []
        for r in raw:
            url = normalize_url(r.get("url", ""))
            if not url:
                continue
            out.append(RawResult(
                title=r.get("title", ""),
                url=url,
                content=r.get("content", ""),
                board=self._board,
                source_type=self._infer_source(url),
            ))
        return out

    def accept_url(self, url: str) -> bool:
        # Generic: accept any non-redirect, http(s) URL. The global
        # is_likely_job gate does the heavy lifting for non-dedicated
        # boards.
        return bool(normalize_url(url))

    @staticmethod
    def _infer_source(url: str) -> str:
        url_l = url.lower()
        freelance_hosts = ("upwork.com", "toptal.com", "mostaql.com",
                            "contra.com", "braintrust.dev", "peopleperhour.com",
                            "freelancer.com")
        if any(h in url_l for h in freelance_hosts):
            return "freelance"
        if "github.com" in url_l:
            return "oss"
        return "main"
