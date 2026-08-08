"""LinkedIn searchers — jobs and posts.

LinkedInJobsSearcher scopes Tavily to `site:linkedin.com/jobs` and only
accepts `linkedin.com/jobs/view/<id>` detail URLs (rejects search pages,
company about pages, aggregate -jobs landing pages).

LinkedInPostsSearcher is a lead source: scoped to `site:linkedin.com/posts`
plus hiring-signal keywords. The CSV row gets `source_type=post` and a
score cap in run_scan, so posts never become 5★ applies. Comment deep-links
and weak "looking for" engagement noise are rejected.
"""
from __future__ import annotations

import re
from urllib.parse import urlparse, parse_qs, unquote
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

# Comment / reply deep-link markers in query or path.
_COMMENT_MARKERS = (
    "commenturn",
    "dashcommenturn",
    "replyurn",
    "commentid",
    "/comments/",
)

# Strong hiring-signal keywords for posts (lowercase). Bare "looking for"
# is intentionally excluded — it matches mentor/advice comments.
_HIRING_SIGNALS = (
    "hiring", "we're hiring", "were hiring", "we are hiring",
    "open role", "open position", "join our team",
    "job opening", "vacancy", "now hiring", "#hiring",
    "مطلوب", "توظيف", "نبحث عن", "فرصة عمل",
)

# Engagement / comment noise that is not a hiring post.
_ENGAGEMENT_NOISE = (
    "commenting for",
    "commenting to",
    "interested",
    "dm me for referral",
    "dm me for",
    "please refer",
    "for reach",
    "following for",
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
        # Force strong hiring-signal keywords unless the config already has them.
        ql = q.lower()
        if any(sig in ql for sig in ("hiring", "we're hiring", "#hiring", "مطلوب", "توظيف", "نبحث عن")):
            base = q
        else:
            base = (
                f"({q}) (hiring OR \"we're hiring\" OR \"we are hiring\" "
                f"OR #hiring OR \"open role\" OR مطلوب OR توظيف OR \"نبحث عن\")"
            )
        return f"site:linkedin.com/posts {base}".strip()

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
            title = r.get("title", "")
            content = r.get("content", "")
            if not self._is_hiring_post(title, content):
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
        if self._is_comment_deeplink(url):
            return False
        return bool(_LINKEDIN_POST_PATH.search(url))

    @staticmethod
    def _is_comment_deeplink(url: str) -> bool:
        """True if URL points at a comment/reply rather than the post itself."""
        url_l = (url or "").lower()
        if any(m in url_l for m in _COMMENT_MARKERS):
            return True
        try:
            parsed = urlparse(url)
            # Decode query values (URN params are often percent-encoded).
            qs = parse_qs(parsed.query, keep_blank_values=True)
            for key, vals in qs.items():
                kl = key.lower()
                if any(m in kl for m in ("comment", "reply")):
                    return True
                for v in vals:
                    vl = unquote(v or "").lower()
                    if any(m in vl for m in _COMMENT_MARKERS):
                        return True
            frag = unquote(parsed.fragment or "").lower()
            if any(m in frag for m in _COMMENT_MARKERS):
                return True
        except Exception:
            pass
        return False

    @classmethod
    def _is_hiring_post(cls, title: str, content: str) -> bool:
        """Require a strong hiring signal; drop engagement-only noise."""
        combined = f"{title or ''} {content or ''}".lower()
        has_signal = any(sig in combined for sig in _HIRING_SIGNALS)
        if not has_signal:
            return False
        # If the text is dominated by engagement noise and lacks an explicit
        # company-style hiring phrase beyond a weak hit, drop it.
        noise_hits = sum(1 for n in _ENGAGEMENT_NOISE if n in combined)
        strong = any(
            s in combined
            for s in (
                "we're hiring", "we are hiring", "were hiring",
                "#hiring", "now hiring", "open role", "open position",
                "job opening", "join our team", "مطلوب", "توظيف", "نبحث عن",
            )
        )
        if noise_hits >= 1 and not strong:
            return False
        return True


def _safe_int(v) -> int | None:
    try:
        return int(v)
    except (TypeError, ValueError):
        return None
