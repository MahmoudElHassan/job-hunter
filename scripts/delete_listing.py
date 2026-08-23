#!/usr/bin/env python3
"""Delete one job row from data/Job_Listings.csv by id (local, with Yes/No).

Usage:
    python3 scripts/delete_listing.py JOB-2026-08-21-170000-001
    python3 scripts/delete_listing.py JOB-xxx --yes   # skip confirm
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from job_hunter import LISTING_FIELDS  # noqa: E402

DEFAULT_CSV = ROOT / "data" / "Job_Listings.csv"


def main() -> int:
    parser = argparse.ArgumentParser(description="Delete a listing from Job_Listings.csv")
    parser.add_argument("job_id", help="Job id column value, e.g. JOB-…")
    parser.add_argument(
        "--csv",
        type=Path,
        default=DEFAULT_CSV,
        help=f"Path to CSV (default: {DEFAULT_CSV})",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip interactive Yes/No confirmation",
    )
    args = parser.parse_args()
    job_id = args.job_id.strip()
    path: Path = args.csv

    if not path.exists():
        print(f"❌ CSV not found: {path}", file=sys.stderr)
        return 1

    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or LISTING_FIELDS)
        rows = list(reader)

    match = [r for r in rows if (r.get("id") or "").strip() == job_id]
    if not match:
        print(f"❌ No row with id={job_id}", file=sys.stderr)
        return 1

    row = match[0]
    company = row.get("company") or "?"
    role = row.get("role") or "?"
    print(f"About to delete: {job_id}")
    print(f"  {company} — {role}")
    print(f"  url: {row.get('url') or 'N/A'}")

    if not args.yes:
        answer = input("Delete this row from Job_Listings.csv? [Yes/No]: ").strip().lower()
        if answer not in ("y", "yes"):
            print("Cancelled.")
            return 0

    kept = [r for r in rows if (r.get("id") or "").strip() != job_id]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for r in kept:
            writer.writerow({k: r.get(k, "") for k in fieldnames})

    print(f"✅ Deleted {job_id}. Remaining rows: {len(kept)}")
    print("Commit and push when ready so GitHub Pages / jsDelivr update.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
