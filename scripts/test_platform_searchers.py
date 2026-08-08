#!/usr/bin/env python3
"""Offline tests for the per-platform searcher registry, freshness
mapping, closed-posting filter, live-check stub, canonical URL
normalisation, and the global `is_likely_job` allow-list.

No network — only build_query, accept_url, registry behaviour, and
small helper functions are exercised.
Run: `python3 scripts/test_platform_searchers.py`
Exits non-zero on any failed assertion.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Allow running from the project root or from scripts/
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from searchers import (
    get_searcher,
    LinkedInJobsSearcher,
    LinkedInPostsSearcher,
    UpworkSearcher,
    MostaqlSearcher,
    GenericBoardSearcher,
    canonicalize_url,
    normalize_url,
)
from searchers.tavily import tavily_search
import job_hunter

PASS = 0
FAIL = 0


def check(name: str, actual, expected):
    global PASS, FAIL
    if actual == expected:
        PASS += 1
        print(f"  ✅ {name}")
    else:
        FAIL += 1
        print(f"  ❌ {name}")
        print(f"     actual:   {actual!r}")
        print(f"     expected: {expected!r}")


def section(title: str):
    print(f"\n=== {title} ===")


# ---- 1. registry ----
section("1. Registry — get_searcher()")
check("linkedin_jobs → LinkedInJobsSearcher",
      get_searcher("linkedin_jobs").__class__.__name__,
      "LinkedInJobsSearcher")
check("linkedin_posts → LinkedInPostsSearcher",
      get_searcher("linkedin_posts").__class__.__name__,
      "LinkedInPostsSearcher")
check("upwork → UpworkSearcher",
      get_searcher("upwork").__class__.__name__,
      "UpworkSearcher")
check("mostaql → MostaqlSearcher",
      get_searcher("mostaql").__class__.__name__,
      "MostaqlSearcher")
check("linkedin (alias) → LinkedInJobsSearcher",
      get_searcher("linkedin").__class__.__name__,
      "LinkedInJobsSearcher")
check("linkedin (case-insensitive) → LinkedInJobsSearcher",
      get_searcher("LinkedIn").__class__.__name__,
      "LinkedInJobsSearcher")
check("bayt → GenericBoardSearcher (no dedicated)",
      get_searcher("bayt").__class__.__name__,
      "GenericBoardSearcher")
check("indeed → GenericBoardSearcher (no dedicated)",
      get_searcher("indeed").__class__.__name__,
      "GenericBoardSearcher")
check("'' (empty) → GenericBoardSearcher",
      get_searcher("").__class__.__name__,
      "GenericBoardSearcher")
check("'unknown_board' → GenericBoardSearcher",
      get_searcher("unknown_board").__class__.__name__,
      "GenericBoardSearcher")
check("get_searcher('bayt').board == 'bayt'",
      get_searcher("bayt").board, "bayt")
check("get_searcher('indeed').board == 'indeed'",
      get_searcher("indeed").board, "indeed")
check("get_searcher('google').board == 'google'",
      get_searcher("google").board, "google")
check("get_searcher('').board == 'unknown'",
      get_searcher("").board, "unknown")

# ---- 2. build_query ----
section("2. build_query — site: scoping")
check("LinkedInJobs adds site:linkedin.com/jobs",
      "site:linkedin.com/jobs" in LinkedInJobsSearcher().build_query(
          {"board": "linkedin_jobs", "query": ".NET backend remote"}),
      True)
check("LinkedInPosts adds site:linkedin.com/posts + hiring signals",
      "site:linkedin.com/posts" in LinkedInPostsSearcher().build_query(
          {"board": "linkedin_posts", "query": ".NET"}),
      True)
check("LinkedInPosts adds hiring keywords in default case",
      "hiring" in LinkedInPostsSearcher().build_query(
          {"board": "linkedin_posts", "query": ".NET"}).lower(),
      True)
check("Upwork adds site:upwork.com/jobs",
      "site:upwork.com/jobs" in UpworkSearcher().build_query(
          {"board": "upwork", "query": "ASP.NET Core"}),
      True)
check("Mostaql adds site:mostaql.com (Arabic passes through)",
      "site:mostaql.com" in MostaqlSearcher().build_query(
          {"board": "mostaql", "query": "تطوير مواقع"}),
      True)
check("GenericBayt adds site:bayt.com",
      "site:bayt.com" in GenericBoardSearcher("bayt").build_query(
          {"board": "bayt", "query": ".NET developer"}),
      True)
check("Google row (already has site:) passes through unchanged",
      GenericBoardSearcher("google").build_query(
          {"board": "google", "query": "site:greenhouse.io .NET backend"}),
      "site:greenhouse.io .NET backend")

# ---- 3. accept_url ----
section("3. accept_url — URL allow filter")

# LinkedIn Jobs
lj = LinkedInJobsSearcher()
check("LI Jobs: /jobs/view/<id> → True",
      lj.accept_url("https://www.linkedin.com/jobs/view/3829384729"),
      True)
check("LI Jobs: /jobs/search?keywords=... → False",
      lj.accept_url("https://www.linkedin.com/jobs/search?keywords=.net"),
      False)
check("LI Jobs: /jobs/collections/recommended → False",
      lj.accept_url("https://www.linkedin.com/jobs/collections/recommended"),
      False)
check("LI Jobs: /company/microsoft/about → False",
      lj.accept_url("https://www.linkedin.com/company/microsoft/about"),
      False)
check("LI Jobs: empty URL → False",
      lj.accept_url(""),
      False)
check("LI Jobs: /goto?url=... → False",
      lj.accept_url("https://example.com/goto?url=CAESabcdef"),
      False)

# LinkedIn Posts
lp = LinkedInPostsSearcher()
check("LI Posts: /posts/abc-activity-9876 → True",
      lp.accept_url("https://www.linkedin.com/posts/abc-activity-9876"),
      True)
check("LI Posts: /feed/update/urn:li:activity:9876 → True",
      lp.accept_url("https://www.linkedin.com/feed/update/urn:li:activity:9876"),
      True)
check("LI Posts: /in/john-doe → False",
      lp.accept_url("https://www.linkedin.com/in/john-doe"),
      False)
check("LI Posts: /jobs/view/... → False (not a post path)",
      lp.accept_url("https://www.linkedin.com/jobs/view/12345"),
      False)

# Upwork
up = UpworkSearcher()
check("Upwork: /jobs/~<hash> → True",
      up.accept_url("https://www.upwork.com/jobs/~0123456789"),
      True)
check("Upwork: /jobs/<slug> → True",
      up.accept_url("https://www.upwork.com/jobs/asp-net-developer"),
      True)
check("Upwork: bare /jobs/ → False",
      up.accept_url("https://www.upwork.com/jobs/"),
      False)
check("Upwork: /freelance-jobs/<cat> → False (category landing)",
      up.accept_url("https://www.upwork.com/freelance-jobs/aspnet-core/"),
      False)
check("Upwork: / (homepage) → False",
      up.accept_url("https://www.upwork.com/"),
      False)

# Mostaql
mq = MostaqlSearcher()
check("Mostaql: /projects/<slug> → True",
      mq.accept_url("https://mostaql.com/projects/12345-تطوير-موقع"),
      True)
check("Mostaql: /project/<slug> (singular) → True",
      mq.accept_url("https://mostaql.com/project/67890"),
      True)
check("Mostaql: / (homepage) → False",
      mq.accept_url("https://mostaql.com/"),
      False)
check("Mostaql: /blog/something → False",
      mq.accept_url("https://mostaql.com/blog/post-name"),
      False)
check("Mostaql: /categories/<cat> → False",
      mq.accept_url("https://mostaql.com/categories/web-development"),
      False)

# Generic
gn = GenericBoardSearcher("bayt")
check("Generic Bayt: detail URL accepted",
      gn.accept_url("https://www.bayt.com/en/job/senior-backend-developer-12345"),
      True)
check("Generic Bayt: rejects /goto?url=",
      gn.accept_url("https://www.bayt.com/goto?url=xxx"),
      False)

# ---- 4. ORDER 1 acceptance: per-board detail regexes reject category/search ----
section("4. ORDER 1 — Generic per-board detail regexes")

# Toptal category page must be rejected
toptal_s = GenericBoardSearcher("toptal")
check("Toptal: /freelance-jobs/developers/dot-net → False (category)",
      toptal_s.accept_url("https://www.toptal.com/freelance-jobs/developers/dot-net"),
      False)
check("Toptal: /freelance-jobs/ → False (root category)",
      toptal_s.accept_url("https://www.toptal.com/freelance-jobs/"),
      False)

# Indeed/Glassdoor/Arc category / search indexes must be rejected
indeed_s = GenericBoardSearcher("indeed")
check("Indeed: /q-net-developer-remote-jobs → False (search index)",
      indeed_s.accept_url("https://www.indeed.com/q-net-developer-remote-jobs.html"),
      False)
check("Indeed: /jobs? → False (search index)",
      indeed_s.accept_url("https://www.indeed.com/jobs?q=net+developer"),
      False)

glassdoor_s = GenericBoardSearcher("glassdoor")
check("Glassdoor: /Job/net-developer-jobs-SRCH_IL → False (search index)",
      glassdoor_s.accept_url("https://www.glassdoor.com/Job/net-developer-jobs-SRCH_IL.htm"),
      False)
check("Glassdoor: /Job/Company/jobs → False (search index)",
      glassdoor_s.accept_url("https://www.glassdoor.com/Job/microsoft-net-jobs-SRCH_KO0.htm"),
      False)

arc_s = GenericBoardSearcher("arcdev")
check("Arc.dev: /remote-jobs/ ← category landing → False",
      arc_s.accept_url("https://arc.dev/remote-jobs"),
      False)
check("Arc.dev: /remote-jobs/backend/ ← category landing → False",
      arc_s.accept_url("https://arc.dev/remote-jobs/backend/"),
      False)

# Detail URLs that MUST still be accepted
check("LinkedIn: /jobs/view/<id> accepted",
      LinkedInJobsSearcher().accept_url("https://www.linkedin.com/jobs/view/3829384729"),
      True)
check("Upwork: /jobs/<slug> accepted",
      UpworkSearcher().accept_url("https://www.upwork.com/jobs/~01abc23456789"),
      True)
check("Mostaql: /projects/<id> accepted",
      MostaqlSearcher().accept_url("https://mostaql.com/projects/12345-some-slug"),
      True)
# Greenhouse job URL is checked at the global is_likely_job level too
check("is_likely_job: greenhouse job URL accepted",
      job_hunter.is_likely_job(
          "Senior Backend Developer at Acme",
          "https://boards.greenhouse.io/acme/jobs/12345",
          ""),
      True)

# ---- 5. ORDER 1 acceptance: toptal allow-list removed from is_likely_job ----
section("5. ORDER 1.1 — is_likely_job allow-list no longer trusts Toptal category")
check("is_likely_job: toptal.com/freelance-jobs/developers/dot-net → False",
      job_hunter.is_likely_job(
          "Dot Net Developer Jobs in UAE",
          "https://www.toptal.com/freelance-jobs/developers/dot-net",
          ""),
      False)
check("is_likely_job: toptal category landing → False",
      job_hunter.is_likely_job(
          "Freelance Asp Net Developer Jobs",
          "https://www.toptal.com/freelance-jobs/asp-net",
          ""),
      False)

# ---- 6. ORDER 1.4: canonicalize_url ----
section("6. ORDER 1.4 — canonicalize_url")
check("canonicalize: strips trailing slash",
      canonicalize_url("https://example.com/path/"),
      "https://example.com/path")
check("canonicalize: lowercases host",
      canonicalize_url("https://EXAMPLE.COM/Path"),
      "https://example.com/Path")
check("canonicalize: strips utm_* params",
      "utm_source" not in canonicalize_url("https://example.com/p?a=1&utm_source=x"),
      True)
check("canonicalize: strips fbclid",
      "fbclid" not in canonicalize_url("https://example.com/p?fbclid=abc&keep=1"),
      True)
check("canonicalize: strips ref but keeps keep",
      "keep=1" in canonicalize_url("https://example.com/p?ref=foo&keep=1"),
      True)
check("canonicalize: rejects empty",
      canonicalize_url(""), "")
check("canonicalize: rejects non-http",
      canonicalize_url("ftp://example.com"), "")
check("canonicalize: keeps query when present",
      canonicalize_url("https://example.com/p?a=1&b=2"),
      "https://example.com/p?a=1&b=2")
check("canonicalize: same URL with different trackers dedupes",
      canonicalize_url("https://example.com/p?utm_source=x") ==
      canonicalize_url("https://example.com/p?utm_source=y"),
      True)

# ---- 7. ORDER 2.1: freshness_days maps to time_range ----
section("7. ORDER 2.1 — freshness_days → time_range")

import requests as _req  # noqa: E402

# Patch requests.post to capture payloads instead of hitting the API.
captured: list[dict] = []
class _FakeResp:
    status_code = 200
    def raise_for_status(self): pass
    def json(self):
        return {"results": []}

def _fake_post(url, json=None, timeout=None, **kw):
    captured.append({"url": url, "json": dict(json or {})})
    return _FakeResp()

# days -> time_range expectations
expected_time_range = [(1, "day"), (2, "week"), (3, "week"), (7, "week"),
                       (8, "month"), (31, "month"), (32, "year"),
                       (200, "year"), (0, None), (-1, None), (None, None),
                       ("abc", None)]
_orig_post = _req.post
_req.post = _fake_post  # type: ignore
try:
    for days, expected in expected_time_range:
        captured.clear()
        tavily_search("test", "fake-key", freshness_days=days)
        assert captured, f"no captured payload for days={days!r}"
        payload = captured[0]["json"]
        actual = payload.get("time_range")
        check(f"freshness_days={days!r} → time_range={expected!r}",
              actual, expected)
finally:
    _req.post = _orig_post  # type: ignore

# Also confirm time_range is absent (no start_date) when freshness_days is None
_req.post = _fake_post  # type: ignore
try:
    captured.clear()
    tavily_search("test", "fake-key")
    payload = captured[0]["json"]
    check("freshness_days=None → no time_range in payload",
          "time_range" in payload, False)
    check("freshness_days=None → no start_date in payload",
          "start_date" in payload, False)
finally:
    _req.post = _orig_post  # type: ignore

# ---- 8. ORDER 2.2: is_closed_posting ----
section("8. ORDER 2.2 — is_closed_posting")
check("Closed EN: 'no longer available' → True",
      job_hunter.is_closed_posting("", "This role is no longer available."),
      True)
check("Closed EN: 'job is closed' → True",
      job_hunter.is_closed_posting("", "Sorry, this job is closed."),
      True)
check("Closed EN: 'position has been filled' → True",
      job_hunter.is_closed_posting("", "The position has been filled."),
      True)
check("Closed EN: 'application deadline has passed' → True",
      job_hunter.is_closed_posting("", "Sorry, the application deadline has passed."),
      True)
check("Closed AR: 'تم إغلاق' → True",
      job_hunter.is_closed_posting("", "تم إغلاق هذه الوظيفة"),
      True)
check("Closed AR: 'انتهى التقديم' → True",
      job_hunter.is_closed_posting("", "عذراً انتهى التقديم على هذه الفرصة"),
      True)
check("Open: 'apply now' → False",
      job_hunter.is_closed_posting("Backend Developer", "Apply now to join our team!"),
      False)
check("Open: empty content → False",
      job_hunter.is_closed_posting("Backend Developer", ""),
      False)

# ---- 9. ORDER 3: url_looks_alive with mocked responses ----
section("9. ORDER 3 — url_looks_alive (mocked)")

class _FakeHTTPResp:
    def __init__(self, status_code, url=""):
        self.status_code = status_code
        self.url = url
    def raise_for_status(self): pass
    def close(self): pass

captured_head = []
captured_get = []

def _fake_head(url, headers=None, timeout=None, allow_redirects=None, **kw):
    captured_head.append(url)
    return _FakeHTTPResp(200, url)

def _fake_get(url, headers=None, timeout=None, allow_redirects=None, stream=None, **kw):
    captured_get.append(url)
    return _FakeHTTPResp(200, url)

_orig_head = _req.head
_orig_get = _req.get
job_hunter._LIVE_CHECK_CALLS = 0
_req.head = _fake_head  # type: ignore
_req.get = _fake_get   # type: ignore
try:
    res = job_hunter.url_looks_alive("https://example.com/job/123")
    check("200 → True", res, True)
finally:
    _req.head = _orig_head  # type: ignore
    _req.get = _orig_get   # type: ignore

# 404 → False
def _fake_head_404(url, headers=None, timeout=None, allow_redirects=None, **kw):
    return _FakeHTTPResp(404, url)
job_hunter._LIVE_CHECK_CALLS = 0
_req.head = _fake_head_404  # type: ignore
_req.get = _fake_get         # type: ignore
try:
    res = job_hunter.url_looks_alive("https://example.com/job/gone")
    check("404 → False", res, False)
finally:
    _req.head = _orig_head  # type: ignore
    _req.get = _orig_get   # type: ignore

# timeout → True (fail-open)
def _fake_head_timeout(url, headers=None, timeout=None, allow_redirects=None, **kw):
    raise _req.exceptions.Timeout("simulated")
job_hunter._LIVE_CHECK_CALLS = 0
_req.head = _fake_head_timeout  # type: ignore
_req.get = _fake_get            # type: ignore
try:
    res = job_hunter.url_looks_alive("https://example.com/job/slow")
    check("timeout → True (fail-open)", res, True)
finally:
    _req.head = _orig_head  # type: ignore
    _req.get = _orig_get   # type: ignore

# 405 → falls back to GET
class _Calls:
    def __init__(self): self.head = 0; self.get = 0
_calls = _Calls()
def _fake_head_405(url, headers=None, timeout=None, allow_redirects=None, **kw):
    _calls.head += 1
    return _FakeHTTPResp(405, url)
def _fake_get_200(url, headers=None, timeout=None, allow_redirects=None, stream=None, **kw):
    _calls.get += 1
    return _FakeHTTPResp(200, url)
job_hunter._LIVE_CHECK_CALLS = 0
_req.head = _fake_head_405  # type: ignore
_req.get = _fake_get_200     # type: ignore
try:
    res = job_hunter.url_looks_alive("https://example.com/job/ok")
    check("405 head falls back to GET → True", res, True)
    check("GET was actually called on 405", _calls.get, 1)
finally:
    _req.head = _orig_head  # type: ignore
    _req.get = _orig_get   # type: ignore

# Closed-path URL → False without even hitting network
def _fake_head_should_not_call(url, **kw):
    raise AssertionError("should not be called for closed-path URL")
job_hunter._LIVE_CHECK_CALLS = 0
_req.head = _fake_head_should_not_call  # type: ignore
_req.get = _fake_head_should_not_call   # type: ignore
try:
    res = job_hunter.url_looks_alive("https://example.com/jobs/search?q=foo")
    check("closed-path hint in URL → False", res, False)
finally:
    _req.head = _orig_head  # type: ignore
    _req.get = _orig_get   # type: ignore

# ---- 10. ORDER 1.3: toptal row disabled ----
section("10. ORDER 1.3 — toptal disabled in config")
import csv
cfg = ROOT / "data" / "search_config.csv"
with cfg.open() as f:
    rows = list(csv.DictReader(f))
toptal_rows = [r for r in rows if (r.get("board") or "").lower() == "toptal"]
check("at least one toptal row in config",
      len(toptal_rows) >= 1, True)
check("all toptal rows enabled=false",
      all((r.get("enabled") or "").lower() == "false" for r in toptal_rows),
      True)

# ---- 11. Searchers wire into config rows correctly ----
section("11. build_query on actual search_config.csv rows")
if cfg.exists():
    with cfg.open() as f:
        rows = list(csv.DictReader(f))
    enabled = [r for r in rows if (r.get("enabled") or "").lower() == "true"]
    for r in enabled:
        board = r["board"]
        searcher = get_searcher(board)
        q = searcher.build_query(r)
        ok = "site:" in q.lower() or board == "google"
        check(f"build_query({board!r}) contains site: or is google",
              ok, True)
else:
    print("  (skip — search_config.csv not found)")

# ---- summary ----
print()
print("=" * 50)
print(f"  PASS: {PASS}")
print(f"  FAIL: {FAIL}")
print("=" * 50)
sys.exit(0 if FAIL == 0 else 1)
