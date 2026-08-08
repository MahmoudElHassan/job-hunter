"""Per-platform searcher registry.

Each searcher handles a specific job board (LinkedIn, Upwork, Mostaql, etc.)
and knows how to:
  - build a Tavily `site:`-scoped query from a config row
  - filter Tavily results to only the URLs that look like a real posting on
    that platform (reject category landings, search indexes, etc.)
  - tag the result with the right `board` and `source_type` so downstream
    scoring / Telegram / CSV use the right values.

Boards without a dedicated searcher fall back to GenericBoardSearcher, which
adds a `site:` clause from a built-in map.
"""
from __future__ import annotations

from .base import Searcher, RawResult
from .tavily import tavily_search, normalize_url, canonicalize_url
from .linkedin import LinkedInJobsSearcher, LinkedInPostsSearcher
from .upwork import UpworkSearcher
from .mostaql import MostaqlSearcher
from .generic import GenericBoardSearcher


# Registry: board name -> Searcher class
_SEARCHERS: dict[str, type[Searcher]] = {
    "linkedin_jobs":  LinkedInJobsSearcher,
    "linkedin_posts": LinkedInPostsSearcher,
    "upwork":         UpworkSearcher,
    "mostaql":        MostaqlSearcher,
}

# Aliases: the legacy `linkedin` board is treated as jobs.
_ALIASES: dict[str, str] = {
    "linkedin": "linkedin_jobs",
}


def get_searcher(board: str) -> Searcher:
    """Return a Searcher instance for the given board name.

    Unknown boards (and 'google' which already contains site:) fall back to
    GenericBoardSearcher with the original board name preserved for CSV tagging.
    """
    if not board:
        return GenericBoardSearcher("unknown")
    key = _ALIASES.get(board.lower().strip(), board.lower().strip())
    cls = _SEARCHERS.get(key)
    if cls is not None:
        return cls()
    # Pass the resolved board name so RawResult.board / logs are not "unknown".
    return GenericBoardSearcher(key)


__all__ = [
    "Searcher",
    "RawResult",
    "tavily_search",
    "normalize_url",
    "canonicalize_url",
    "get_searcher",
]
