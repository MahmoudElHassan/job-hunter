#!/usr/bin/env python3
"""One-shot repair for data/Job_Listings.csv.

The old `append_listing` in job_hunter.py wrote 16 fields into a 20-column
header. Every new row shifted left by 4 positions, so:

    writer wrote: ..., salary_range, contact_email, status, notes
    header had:    ..., salary_range, recruiter_name, recruiter_email,
                       hiring_manager, hiring_manager_email, contact_email,
                       status, notes

Result on every existing row:
  * `recruiter_email`  = the old "status" value (almost always "new")
  * `hiring_manager`   = the old "notes" text (the actual listing snippet)
  * `status`           = "" (empty)
  * `notes`            = "" (empty)
  * 4 contact fields   = "" (never written)

This script:
  1. Reads all rows with the current (broken) mapping.
  2. Shifts the 3 misplaced values back: notes->hiring_manager (via content),
     status->recruiter_email, and "new"->status. Actually, the simplest model:
     - `recruiter_email` -> `status` (if it matches a known status word)
     - `hiring_manager`  -> `notes`
     - Clear `recruiter_name`, `recruiter_email`, `hiring_manager`,
       `hiring_manager_email`, `contact_email` (they were never written).
  3. (optional) Drops rows that fail the new is_likely_job noise filter
     so the dashboard / digest don't have to filter them later. Use
     `--keep-noise` to skip that step.
  4. Rewrites the file with the canonical LISTING_FIELDS header and every
     row having all 20 keys (filled with "" where unknown).
  5. Prints a short report.

Usage:
    python3 scripts/repair_listings_csv.py
    python3 scripts/repair_listings_csv.py --keep-noise
    python3 scripts/repair_listings_csv.py --in data/Job_Listings.csv.bak
"""

import argparse
import csv
import shutil
import sys
from datetime import datetime
from pathlib import Path

# Allow running as a script from the project root
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from job_hunter import LISTING_FIELDS, KNOWN_STATUSES, is_likely_job  # noqa: E402

DEFAULT_CSV = ROOT / "data" / "Job_Listings.csv"


def is_email(s: str) -> bool:
    return bool(s) and "@" in s and "." in s.split("@")[-1] and " " not in s


def repair(rows: list[dict]) -> list[dict]:
    """Shift the 3 misplaced values back into the correct columns."""
    fixed = []
    for raw in rows:
        r = {k: (raw.get(k) or "").strip() for k in raw.keys()}

        misplaced_status = r.get("recruiter_email", "")
        misplaced_notes = r.get("hiring_manager", "")

        # Build the clean row with the canonical 20 keys, defaulting to "".
        clean = {k: "" for k in LISTING_FIELDS}
        for k in (
            "id", "date_found", "score", "source_type", "company", "role",
            "location", "remote", "sponsorship", "stack_match", "board",
            "url", "salary_range",
        ):
            clean[k] = r.get(k, "")

        # Move misplaced values into their correct columns.
        if misplaced_status in KNOWN_STATUSES:
            clean["status"] = misplaced_status
        # `notes` was always written (sometimes empty). If it's empty but we
        # have text in the misplaced hiring_manager slot, treat that as notes.
        if not clean.get("notes") and misplaced_notes:
            clean["notes"] = misplaced_notes

        # If the original writer DID set a notes field that landed at
        # `contact_email` (writer wrote: ..., contact_email, status, notes),
        # then r.get("contact_email") actually holds the old status, and
        # r.get("status") holds the old notes. Handle that case:
        if not clean.get("notes"):
            old_notes = r.get("status", "")
            if old_notes and old_notes not in KNOWN_STATUSES:
                clean["notes"] = old_notes

        # All contact fields stay "" unless they actually look like emails
        # (the old writer never populated them, so this is a no-op today).
        for ck in (
            "recruiter_name", "recruiter_email",
            "hiring_manager", "hiring_manager_email", "contact_email",
        ):
            v = r.get(ck, "")
            if is_email(v):
                clean[ck] = v
            elif v and ck in ("recruiter_name", "hiring_manager"):
                # If it ever WAS a real name, keep it. (Today this branch is
                # never hit because the old writer skipped these fields.)
                clean[ck] = v

        # Sanity: recruiter_email must not contain a status word.
        if clean["recruiter_email"] in KNOWN_STATUSES:
            clean["recruiter_email"] = ""

        fixed.append(clean)
    return fixed


def main():
    parser = argparse.ArgumentParser(description="Repair Job_Listings.csv schema drift")
    parser.add_argument("--in", dest="in_path", type=Path, default=DEFAULT_CSV,
                        help=f"Path to the broken CSV (default: {DEFAULT_CSV})")
    parser.add_argument("--keep-noise", action="store_true",
                        help="Don't drop noise rows; just repair schema")
    parser.add_argument("--out", dest="out_path", type=Path, default=None,
                        help="Write to a different path (default: overwrite input)")
    parser.add_argument("--backup-suffix", default=".bak-before-repair",
                        help="Backup file suffix (default: .bak-before-repair)")
    args = parser.parse_args()

    src: Path = args.in_path
    dst: Path = args.out_path or src

    if not src.exists():
        sys.exit(f"❌ {src} not found")

    # Read raw rows
    with src.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        raw_rows = list(reader)
        raw_header = reader.fieldnames or []

    print(f"📄 {src}")
    print(f"   header fields: {len(raw_header)}  rows: {len(raw_rows)}")

    if raw_header != LISTING_FIELDS:
        print(f"   ⚠️  header on disk: {raw_header}")
        print(f"   expected:         {LISTING_FIELDS}")
        if sorted(raw_header) != sorted(LISTING_FIELDS):
            sys.exit(
                "❌ Header columns don't match even by name. "
                "Manual review needed before running this script."
            )
        print("   (column order differs but names match — proceeding with repair)")

    fixed = repair(raw_rows)
    # The old writer never set status for many rows (the "new" value got
    # written into recruiter_email). After shifting, most rows have an empty
    # status. Default any empty status to "new" so the dashboard / digest
    # "by status" / "new today" filters keep working.
    for r in fixed:
        if not r.get("status"):
            r["status"] = "new"
    print(f"   repaired rows: {len(fixed)}")

    # Optional: drop noise rows
    kept = fixed
    dropped = []
    if not args.keep_noise:
        kept, dropped = [], []
        for r in fixed:
            if is_likely_job(r.get("role", ""), r.get("url", ""), r.get("notes", "")):
                kept.append(r)
            else:
                dropped.append(r)
        print(f"   noise rows dropped: {len(dropped)}")
        print(f"   clean rows kept:    {len(kept)}")

    # Status distribution report
    status_counts: dict[str, int] = {}
    for r in kept:
        s = r.get("status", "") or "(empty)"
        status_counts[s] = status_counts.get(s, 0) + 1
    print("   status distribution (after repair):")
    for s, c in sorted(status_counts.items(), key=lambda x: -x[1]):
        print(f"     {s}: {c}")

    # Backup
    if dst == src:
        backup = src.with_name(src.name + args.backup_suffix)
        shutil.copy2(src, backup)
        print(f"   💾 backup: {backup}")

    # Write cleaned CSV with the canonical header
    with dst.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=LISTING_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for r in kept:
            writer.writerow(r)

    print(f"   ✅ wrote {dst}  ({dst.stat().st_size} bytes, {len(kept)} rows)")
    print("   done.")


if __name__ == "__main__":
    main()
