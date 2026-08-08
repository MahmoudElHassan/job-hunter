"""MostaqlSearcher — Arabic-language freelance platform.

Accepts `mostaql.com/project/<id>` or `mostaql.com/projects/<id>` detail
URLs. Rejects the homepage, blog, and static marketing pages.
"""
from __future__ import annotations

import re
from .base import RawResult
from .tavily import normalize_url, tavily_search


# Detail URL: mostaql.com/project/<id> or mostaql.com/projects/<id>
_MOSTAQL_DETAIL = re.compile(
    r"mostaql\.com/(?:projects|project)/[^/?#]+",
    re.IGNORECASE,
)
# Marketing / non-job paths
_MOSTAQL_REJECT = re.compile(
    r"mostaql\.com/(?:blog|categories|skills|users|about|home)?/?$",
    re.IGNORECASE,
)


class MostaqlSearcher:
    board = "mostaql"
    source_type = "freelance"

    def build_query(self, row: dict) -> str:
        q = (row.get("query") or "").strip()
        if "site:" in q.lower():
            return q
        return f"site:mostaql.com {q}".strip()

    def search(self, row: dict, api_key: str, *, dry_run: bool = False) -> list[RawResult]:
        if dry_run:
            return []
        query = self.build_query(row)
        raw = tavily_search(query, api_key, freshness_days=_safe_int(row.get("freshness_days")))
        out: list[RawResult] = []
        for r in raw:
            url = normalize_url(r.get("url", ""))
            if not self.accept_url(url):
                continue
            out.append(RawResult(
                title=r.get("title", ""),
                url=url,
                content=r.get("content", ""),
                board=self.board,
                source_type="freelance",
            ))
        return out

    def accept_url(self, url: str) -> bool:
        if not normalize_url(url):
            return False
        url_l = url.lower()
        if _MOSTAQL_REJECT.search(url_l):
            return False
        return bool(_MOSTAQL_DETAIL.search(url_l))


def _safe_int(v) -> int | None:
    try:
        return int(v)
    except (TypeError, ValueError):
        return None
