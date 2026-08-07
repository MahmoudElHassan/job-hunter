"""UpworkSearcher — only `/jobs/<id>` detail pages, never
`/freelance-jobs/<category>` category landings.
"""
from __future__ import annotations

import re
from .base import RawResult
from .tavily import normalize_url, tavily_search


# Detail URL: upwork.com/jobs/~<hash> (canonical) or upwork.com/jobs/<slug>
# with a real path segment. Reject bare /jobs/ and /freelance-jobs/ categories.
_UPWORK_JOB_DETAIL = re.compile(
    r"upwork\.com/jobs/(?:~[a-z0-9]+|[a-z0-9][\w\-]{3,})",
    re.IGNORECASE,
)
_UPWORK_CATEGORY = re.compile(r"upwork\.com/freelance-jobs/", re.IGNORECASE)


class UpworkSearcher:
    board = "upwork"
    source_type = "freelance"

    def build_query(self, row: dict) -> str:
        q = (row.get("query") or "").strip()
        if "site:" in q.lower():
            return q
        return f"site:upwork.com/jobs {q}".strip()

    def search(self, row: dict, api_key: str, *, dry_run: bool = False) -> list[RawResult]:
        if dry_run:
            return []
        query = self.build_query(row)
        raw = tavily_search(query, api_key)
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
        if _UPWORK_CATEGORY.search(url_l):
            return False
        return bool(_UPWORK_JOB_DETAIL.search(url_l))
