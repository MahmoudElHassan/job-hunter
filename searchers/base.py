"""Base classes for the per-platform searcher registry."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass
class RawResult:
    """One Tavily result, plus the platform-specific tagging the searcher
    decides to attach. `board` is the short name used in the CSV (e.g.
    "linkedin", "upwork"), `source_type` is one of:
        main | freelance | post | oss | unknown
    """
    title:   str = ""
    url:     str = ""
    content: str = ""
    board:       str = ""
    source_type: str = "unknown"


@runtime_checkable
class Searcher(Protocol):
    """Every searcher implements this protocol.

    `board` is the canonical short name written to the CSV column.
    `build_query(row)` returns the full Tavily query string (always with
    the right `site:` scoping for the platform).
    `search(row, api_key, *, dry_run)` returns the filtered list of
    RawResult. In dry-run mode the implementation can short-circuit
    without calling the API.
    `accept_url(url)` is the per-platform allow filter — it returns
    True only for URLs that look like a single posting on this board.
    """
    board: str

    def build_query(self, row: dict) -> str: ...
    def search(self, row: dict, api_key: str, *, dry_run: bool = False) -> list[RawResult]: ...
    def accept_url(self, url: str) -> bool: ...
