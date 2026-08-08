"""GenericBoardSearcher — fallback for boards without a dedicated searcher.

Adds a `site:` clause from a built-in map. If the board is unknown, the
query is used as-is (still subject to accept_url filter).

Per-board `accept_url` regexes reject category landing pages, search
indexes, and aggregator shells so only single, real postings get through.
The global `is_likely_job` gate in `run_scan` remains as a final safety
net for unknown boards.
"""
from __future__ import annotations

import re
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


# Per-board detail URL regexes. A URL must match `pattern` AND not match
# any `reject` entry to be accepted. Categories / search indexes / company
# marketing pages are rejected explicitly so they can never slip through.
_DETAIL_PATTERNS: dict[str, dict[str, tuple[str, ...]]] = {
    "bayt": {
        "pattern": r"bayt\.com/en/job/[^/?#]+",
        "reject":  (
            r"bayt\.com/en/jobs",
            r"bayt\.com/en/(?:companies|search|index|salary|career-advice)",
            r"bayt\.com/$",
        ),
    },
    "indeed": {
        "pattern": r"indeed\.com/(?:viewjob|rc/clk|pagead)",
        "reject":  (
            r"indeed\.com/(?:q-|[a-z]+\.l750|jobs\?|compare|salary|companies|reviews)",
            r"indeed\.com/$",
        ),
    },
    "glassdoor": {
        "pattern": r"glassdoor\.com/job-listing/",
        "reject":  (
            r"glassdoor\.com/Job/[a-zA-Z\-]+-jobs-(?:SRCH_KE|IL\.|IP\.)",
            r"glassdoor\.com/Job/[^/]+\.htm$",  # aggregate list page
            r"glassdoor\.com/(?:Job/|jobs|partner|salaries|reviews|employers|blog|listings|company)",
            r"glassdoor\.com/$",
        ),
    },
    "remoteok": {
        "pattern": r"remoteok\.com/remote-jobs/[0-9]+",
        "reject":  (
            r"remoteok\.com/remote-jobs/?$",
            r"remoteok\.com/(?:categories|companies|tags|locations)$",
        ),
    },
    "weworkremotely": {
        "pattern": r"weworkremotely\.com/(?:remote-jobs/[^/?#]+|listings/[0-9]+)",
        "reject":  (
            r"weworkremotely\.com/(?:remote-jobs/?$|categories|jobs-by-category|jobs-by-tag)",
            r"weworkremotely\.com/$",
        ),
    },
    "arcdev": {
        "pattern": r"arc\.dev/remote-jobs/[0-9]+",
        "reject":  (
            r"arc\.dev/remote-jobs/?$",
            r"arc\.dev/remote-jobs/[a-z][a-z\-]+/?$",  # category landing
            r"arc\.dev/$",
        ),
    },
    "toptal": {
        # Toptal exposes only category SERPs publicly; detail URLs are gated.
        # Accept the rare apply-style URL just in case, but reject everything else.
        "pattern": r"toptal\.com/(?:apply|jobs|talent|freelance-jobs)/[a-z0-9\-]+/?$",
        "reject":  (
            r"toptal\.com/freelance-jobs/?$",
            r"toptal\.com/(?:blog|core|company|careers|about|developers|designers|finance|product-managers|project-managers)/?$",
            r"toptal\.com/$",
        ),
    },
    "contra": {
        "pattern": r"contra\.com/(?:projects|jobs)/[a-z0-9\-]+/?$",
        "reject":  (
            r"contra\.com/(?:projects|jobs)/?$",
            r"contra\.com/(?:categories|tags)/",
            r"contra\.com/$",
        ),
    },
    "braintrust": {
        "pattern": r"braintrust\.dev/(?:jobs|hirers?)/[a-z0-9\-]+/?$",
        "reject":  (
            r"braintrust\.dev/(?:jobs|categories)/?$",
            r"braintrust\.dev/$",
        ),
    },
    "peopleperhour": {
        "pattern": r"peopleperhour\.com/(?:freelancer-jobs|jobs)/[a-z0-9\-]+/?$",
        "reject":  (
            r"peopleperhour\.com/(?:freelancer-jobs|jobs|categories|tags)/?$",
            r"peopleperhour\.com/$",
        ),
    },
    "github": {
        # GitHub repo, issue, or bounty — single, specific page.
        "pattern": (
            r"github\.com/[A-Za-z0-9_.\-]+/[A-Za-z0-9_.\-]+"
            r"(?:/(?:issues|pull|discussions|blob|tree)/[0-9]+|[/?#])?$"
        ),
        "reject":  (
            r"github\.com/(?:features|pricing|topics|trending|sponsors|search|orgs|users)/?$",
            r"github\.com/$",
        ),
    },
    "news.ycombinator": {
        # HN item detail: news.ycombinator.com/item?id=NNN
        "pattern": r"news\.ycombinator\.com/item\?id=[0-9]+",
        "reject":  (
            r"news\.ycombinator\.com/(?:jobs|ask|show|best|new|comments|submit|login|about)",
            r"news\.ycombinator\.com/$",
        ),
    },
    "google": {
        # 'google' board rows already include site:... — accept any http(s)
        # result that isn't a known aggregator shell. Run-scan still passes
        # the URL through is_likely_job.
        "pattern": r"https?://[^/?#]+/[^?#]+",
        "reject":  (
            r"toptal\.com/freelance-jobs/",
            r"jooble\.org/jobs",
            r"simplyhired\.com/search\?q=",
            r"ziprecruiter\.com/Jobs-[A-Za-z]",
            r"randstadusa\.com/jobs/q-",
            r"jobleads\.com/",
            r"bebee\.com/[^/]+/jobs/$",
        ),
    },
}


def _compile(rules: dict[str, tuple[str, ...]]) -> tuple[re.Pattern[str] | None, tuple[re.Pattern[str], ...]]:
    pat = rules.get("pattern")
    rej = tuple(re.compile(p, re.IGNORECASE) for p in rules.get("reject", ()))
    compiled_pat = re.compile(pat, re.IGNORECASE) if pat else None
    return compiled_pat, rej


class GenericBoardSearcher:
    """Adds `site:` to the query and applies per-board detail URL regexes."""

    def __init__(self, board_name: str = "unknown") -> None:
        self._board = (board_name or "unknown").lower()
        rules = _DETAIL_PATTERNS.get(self._board, {})
        self._pattern, self._reject = _compile(rules)

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
        raw = tavily_search(query, api_key, freshness_days=_safe_int(row.get("freshness_days")))
        out: list[RawResult] = []
        for r in raw:
            url = normalize_url(r.get("url", ""))
            if not url:
                continue
            if not self.accept_url(url):
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
        if not normalize_url(url):
            return False
        url_l = url.lower()
        # If we have explicit deny rules for this board, enforce them first.
        for pat in self._reject:
            if pat.search(url_l):
                return False
        # If we have a positive pattern for this board, the URL must match it.
        if self._pattern is not None:
            if not self._pattern.search(url_l):
                return False
        return True

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


def _safe_int(v) -> int | None:
    try:
        return int(v)
    except (TypeError, ValueError):
        return None
