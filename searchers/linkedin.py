"""LinkedIn searchers — jobs and posts.

LinkedInJobsSearcher scopes Tavily to `site:linkedin.com/jobs` and only
accepts `linkedin.com/jobs/view/<id>` detail URLs (rejects search pages,
company about pages, aggregate -jobs landing pages).

LinkedInPostsSearcher is a lead source: scoped to `site:linkedin.com/posts`
plus hiring-signal keywords. The CSV row gets `source_type=post` and a
score cap in run_scan, so posts never become 5★ applies.
"""
from __future__ import annotations

import re
from .base import RawResult
from .tavily import normalize_url, tavily_search


# Detail URL pattern: linkedin.com/jobs/view/<digits or slug>
_LINKEDIN_JOB_VIEW = re.compile(r"linkedin\.com/jobs/view/", re.IGNORECASE)
# Posts can live at either linkedin.com/posts/<id> or linkedin.com/feed/update/<id>
_LINKEDIN_POST_PATH = re.compile(
    r"linkedin\.com/(?:posts/[^/?#]+|feed/update/[^/?#]+)",
    re.IGNORECASE,
)
# Aggregate / search / company pages that look like jobs but aren't.
_LINKEDIN_AGGREGATE = re.compile(
    r"linkedin\.com/jobs/(?:search|collections|recommendations|api/|"
    r"[a-z\-]+-jobs(?:\?|$))",
    re.IGNORECASE,
)
_LINKEDIN_COMPANY_ABOUT = re.compile(
    r"linkedin\.com/(?:company|companies)/[^/]+(?:/about|/jobs/?)?$",
    re.IGNORECASE,
)

# Hiring-signal keywords for posts (lowercase).
_HIRING_SIGNALS = (
    "hiring", "we're hiring", "were hiring", "looking for",
    "open role", "open position", "we are hiring", "join our team",
    "job opening", "vacancy", "now hiring", "#hiring",
    "مطلوب", "توظيف", "نبحث عن", "فرصة عمل", "وظيفة",
)


class LinkedInJobsSearcher:
    """Real job postings on LinkedIn."""

    board = "linkedin"

    def build_query(self, row: dict) -> str:
        q = (row.get("query") or "").strip()
        if "site:" in q.lower():
            return q
        return f"site:linkedin.com/jobs {q}".strip()

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
                source_type="main",
            ))
        return out

    def accept_url(self, url: str) -> bool:
        if not normalize_url(url):
            return False
        url_l = url.lower()
        if _LINKEDIN_AGGREGATE.search(url_l):
            return False
        if _LINKEDIN_COMPANY_ABOUT.search(url_l):
            return False
        if not _LINKEDIN_JOB_VIEW.search(url_l):
            return False
        return True


class LinkedInPostsSearcher:
    """Hiring posts on LinkedIn (lead source, not direct apply links)."""

    board = "linkedin"
    source_type = "post"

    def build_query(self, row: dict) -> str:
        q = (row.get("query") or "").strip()
        if "site:" in q.lower():
            return q
        # Force the hiring-signal keywords unless the config already has them.
        ql = q.lower()
        if any(sig in ql for sig in ("hiring", "we're hiring", "looking for", "مطلوب", "توظيف")):
            base = q
        else:
            base = f"({q}) (hiring OR \"we're hiring\" OR \"looking for\" OR #hiring OR مطلوب OR توظيف)"
        return f"site:linkedin.com/posts {base}".strip()

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
            title = r.get("title", "")
            content = r.get("content", "")
            # Tavily already filters by our query keywords, but add a
            # belt-and-suspenders check on the actual content.
            combined = (title + " " + content).lower()
            if not any(sig in combined for sig in _HIRING_SIGNALS):
                continue
            out.append(RawResult(
                title=title,
                url=url,
                content=content,
                board=self.board,
                source_type="post",
            ))
        return out

    def accept_url(self, url: str) -> bool:
        if not normalize_url(url):
            return False
        return bool(_LINKEDIN_POST_PATH.search(url))
