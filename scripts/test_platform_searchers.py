#!/usr/bin/env python3
"""Offline tests for the per-platform searcher registry.

No network — only build_query, accept_url, and registry behaviour.
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
)

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
# Board name must be preserved for CSV tagging (MiniMax bug: was always "unknown")
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
check("Generic: passes http(s) URL through (filtered later by is_likely_job)",
      gn.accept_url("https://www.bayt.com/en/job/12345"),
      True)
check("Generic: rejects /goto?url=",
      gn.accept_url("https://www.bayt.com/goto?url=xxx"),
      False)

# ---- 4. Searchers wire into config rows correctly ----
section("4. build_query on actual search_config.csv rows")
import csv
cfg = ROOT / "data" / "search_config.csv"
if cfg.exists():
    with cfg.open() as f:
        rows = list(csv.DictReader(f))
    enabled = [r for r in rows if (r.get("enabled") or "").lower() == "true"]
    for r in enabled:
        board = r["board"]
        searcher = get_searcher(board)
        q = searcher.build_query(r)
        ok = "site:" in q.lower() or "google" == board
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
