#!/usr/bin/env python3
"""
find_contacts.py — discover recruiter, hiring manager, and similar-role peers for a company.

Inputs:
    --company "Microsoft"               # required
    --role "Senior .NET Developer"      # optional, helps narrow hiring manager search
    --url "https://..."                 # optional, job listing URL (preferred — most specific)

Output:
    data/Applications/<Company>/contacts.md
    Also updates Job_Listings.csv if the company matches a known row.

Methods (in order of preference):
    1. Hunter.io API (if HUNTER_API_KEY set) — finds email patterns + verifies
    2. Tavily search (always available) — finds LinkedIn profiles, public emails
    3. Pattern guessing — firstname.lastname@company.com (if domain known)

Usage:
    python3 scripts/find_contacts.py --company "Microsoft" --role "Senior .NET"
    python3 scripts/find_contacts.py --url "https://linkedin.com/jobs/view/..."
"""

import argparse
import csv
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).parent.parent
DATA = ROOT / "data"
APPS_DIR = DATA / "Applications"
LISTINGS_CSV = DATA / "Job_Listings.csv"
APPS_DIR.mkdir(parents=True, exist_ok=True)

HUNTER_URL = "https://api.hunter.io/v2/domain-search"
TAVILY_URL = "https://api.tavily.com/search"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def tavily_search(query: str, api_key: str, max_results: int = 5) -> list[dict]:
    try:
        resp = requests.post(TAVILY_URL, json={
            "api_key": api_key,
            "query": query,
            "max_results": max_results,
            "search_depth": "basic",
            "topic": "general",
        }, timeout=30)
        resp.raise_for_status()
        return resp.json().get("results", [])
    except requests.RequestException as e:
        print(f"⚠️  Tavily error: {e}", file=sys.stderr)
        return []


def hunter_domain_search(domain: str, api_key: str) -> dict:
    """Use Hunter.io to find email patterns + people at a domain."""
    try:
        resp = requests.get(HUNTER_URL, params={
            "domain": domain,
            "api_key": api_key,
            "limit": 10,
        }, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        print(f"⚠️  Hunter error for {domain}: {e}", file=sys.stderr)
        return {}


def extract_domain(url_or_company: str) -> str:
    """Extract likely company domain from URL or company name guess."""
    if url_or_company.startswith("http"):
        netloc = urlparse(url_or_company).netloc.lower()
        # Strip www.
        return netloc.replace("www.", "").split("/")[0]
    # Heuristic: "Microsoft" → "microsoft.com" (just a guess)
    return f"{url_or_company.lower().replace(' ', '')}.com"


def find_recruiter_via_tavily(company: str, role: str, api_key: str) -> list[dict]:
    """Search LinkedIn / public sources for recruiters at the company."""
    queries = [
        f"site:linkedin.com {company} recruiter technical",
        f"site:linkedin.com {company} engineering hiring manager",
        f"site:linkedin.com {company} talent acquisition",
    ]
    results = []
    for q in queries:
        for r in tavily_search(q, api_key, max_results=5):
            url = r.get("url", "")
            if "linkedin.com/in/" in url:
                results.append({
                    "name": extract_linkedin_name(url, r.get("title", "")),
                    "title": r.get("title", ""),
                    "linkedin": url,
                    "snippet": r.get("content", "")[:200],
                })
    # Dedupe by linkedin URL
    seen = set()
    unique = []
    for r in results:
        if r["linkedin"] not in seen:
            seen.add(r["linkedin"])
            unique.append(r)
    return unique[:5]


def extract_linkedin_name(url: str, title: str) -> str:
    """Try to extract person name from LinkedIn URL slug or title."""
    # URL pattern: /in/firstname-lastname-XXXXX/
    m = re.search(r"/in/([a-z0-9-]+)", url)
    if m:
        slug = m.group(1).rsplit("-", 1)[0]  # remove the random ID at end
        return slug.replace("-", " ").title()
    # Fallback: first 3 words of title
    return " ".join(title.split()[:3])


def find_email_patterns(company: str, domain: str, api_key: str) -> dict:
    """Use Hunter.io to get email pattern + a few verified emails."""
    data = hunter_domain_search(domain, api_key)
    if not data or "data" not in data:
        return {"pattern": None, "emails": [], "note": "Hunter.io returned no data"}

    pattern = data["data"].get("pattern")
    emails_raw = data["data"].get("emails", [])
    emails = [
        {
            "email": e.get("value"),
            "name": f"{e.get('first_name', '')} {e.get('last_name', '')}".strip(),
            "position": e.get("position", ""),
            "department": e.get("department", ""),
            "linkedin": e.get("linkedin", ""),
        }
        for e in emails_raw
    ]
    return {"pattern": pattern, "emails": emails, "note": "Hunter.io"}


def find_hiring_manager_via_tavily(company: str, role: str, api_key: str) -> list[dict]:
    """Search for the specific person managing this role's team."""
    queries = [
        f'site:linkedin.com "{company}" "head of engineering" OR "engineering manager" OR "VP engineering"',
        f'site:linkedin.com "{company}" "team lead" backend',
    ]
    results = []
    for q in queries:
        for r in tavily_search(q, api_key, max_results=3):
            url = r.get("url", "")
            if "linkedin.com/in/" in url:
                results.append({
                    "name": extract_linkedin_name(url, r.get("title", "")),
                    "title": r.get("title", ""),
                    "linkedin": url,
                })
    seen = set()
    unique = []
    for r in results:
        if r["linkedin"] not in seen:
            seen.add(r["linkedin"])
            unique.append(r)
    return unique[:3]


def generate_pattern_emails(first_names: list[str], last_names: list[str], pattern: str, domain: str) -> list[str]:
    """Generate email guesses using Hunter.io's pattern."""
    if not pattern or not first_names or not last_names:
        return []
    emails = []
    for fn in first_names[:3]:
        for ln in last_names[:3]:
            try:
                email = pattern.format(first=fn.lower(), last=ln.lower(), f=fn[0].lower())
                emails.append(f"{email}@{domain}")
            except (KeyError, IndexError):
                continue
    return list(set(emails))


def find_similar_role_peers(company: str, role: str, api_key: str) -> list[dict]:
    """Find 2 people in similar roles at the company (signals culture + comp)."""
    queries = [
        f'site:linkedin.com "{company}" "backend engineer" .NET OR "C#"',
        f'site:linkedin.com "{company}" "senior backend" OR "staff engineer"',
    ]
    results = []
    for q in queries:
        for r in tavily_search(q, api_key, max_results=4):
            url = r.get("url", "")
            if "linkedin.com/in/" in url:
                results.append({
                    "name": extract_linkedin_name(url, r.get("title", "")),
                    "title": r.get("title", ""),
                    "linkedin": url,
                })
    seen = set()
    unique = []
    for r in results:
        if r["linkedin"] not in seen:
            seen.add(r["linkedin"])
            unique.append(r)
    return unique[:4]


def update_job_listings(company: str, contacts: dict) -> bool:
    """Update Job_Listings.csv with contact info if company matches a row."""
    if not LISTINGS_CSV.exists():
        return False

    rows = []
    updated = False
    with LISTINGS_CSV.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("company", "").lower() == company.lower():
                if contacts.get("recruiter_email"):
                    row["contact_email"] = contacts["recruiter_email"]
                updated = True
            rows.append(row)

    if updated:
        with LISTINGS_CSV.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
    return updated


def write_contacts_md(company: str, role: str, contacts: dict) -> Path:
    """Write contacts.md for the company."""
    company_slug = slugify(company)
    app_dir = APPS_DIR / company_slug
    app_dir.mkdir(parents=True, exist_ok=True)

    out = app_dir / "contacts.md"

    lines = [
        f"# Contacts — {company}",
        f"_Generated {now_iso()}_",
        "",
        f"**Role targeted:** {role or 'N/A'}",
        f"**Company domain:** {contacts.get('domain', 'N/A')}",
        f"**Source method:** {contacts.get('source', 'tavily + hunter.io')}",
        "",
        "## Recruiter / Talent Acquisition",
        "",
    ]

    recruiters = contacts.get("recruiters", [])
    if recruiters:
        for r in recruiters:
            lines.append(f"### {r.get('name', 'Unknown')}")
            lines.append(f"- **Title:** {r.get('title', 'N/A')}")
            lines.append(f"- **LinkedIn:** {r.get('linkedin', 'N/A')}")
            if r.get("email"):
                lines.append(f"- **Email (verified):** `{r['email']}`")
            if r.get("position"):
                lines.append(f"- **Position (Hunter):** {r['position']}")
            lines.append(f"- **Snippet:** {r.get('snippet', 'N/A')[:150]}")
            lines.append("")
    else:
        lines.append("_No recruiter found. Try LinkedIn Recruiter search manually._")
        lines.append("")

    lines.extend([
        "## Hiring Manager / Team Lead",
        "",
    ])
    managers = contacts.get("hiring_managers", [])
    if managers:
        for m in managers:
            lines.append(f"### {m.get('name', 'Unknown')}")
            lines.append(f"- **Title:** {m.get('title', 'N/A')}")
            lines.append(f"- **LinkedIn:** {m.get('linkedin', 'N/A')}")
            lines.append("")
    else:
        lines.append("_No hiring manager found. Use company LinkedIn → People → Search._")
        lines.append("")

    lines.extend([
        "## Pattern Guesses (if Hunter.io pattern available)",
        "",
    ])
    pattern_emails = contacts.get("pattern_emails", [])
    if pattern_emails:
        for e in pattern_emails:
            lines.append(f"- `{e}` (verify with Hunter.io before sending)")
    else:
        lines.append("_No pattern available. Try: `firstname.lastname@{domain}`, `careers@{domain}`, `talent@{domain}`_")

    lines.extend([
        "",
        "## Similar-Role Peers (for culture + comp intel)",
        "",
    ])
    peers = contacts.get("peers", [])
    if peers:
        for p in peers:
            lines.append(f"- **{p.get('name', 'Unknown')}** — {p.get('title', 'N/A')} — {p.get('linkedin', 'N/A')}")
    else:
        lines.append("_No peers found._")

    lines.extend([
        "",
        "## Generic Catch-alls to Try",
        "",
        f"- `careers@{contacts.get('domain', 'company.com')}`",
        f"- `talent@{contacts.get('domain', 'company.com')}`",
        f"- `hr@{contacts.get('domain', 'company.com')}`",
        f"- `recruiting@{contacts.get('domain', 'company.com')}`",
        f"- `jobs@{contacts.get('domain', 'company.com')}`",
        "",
        "## Next Steps",
        "",
        "1. Pick the most relevant contact from above",
        "2. Verify the email with Hunter.io (free: 25/month) or NeverBounce",
        "3. Send the tailored cover letter (see cover_letter.md in this folder)",
        "4. Wait 3-5 business days; if no reply, follow up (see followup_email.md)",
    ])

    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def main():
    parser = argparse.ArgumentParser(description="Find recruiter, hiring manager, and peers at a company")
    parser.add_argument("--company", help="Company name (e.g. 'Microsoft')")
    parser.add_argument("--role", default="", help="Target role (helps narrow hiring manager)")
    parser.add_argument("--url", help="Job listing URL (alternative to --company)")
    args = parser.parse_args()

    load_dotenv(ROOT / ".env")
    tavily_key = os.environ.get("TAVILY_API_KEY", "")
    hunter_key = os.environ.get("HUNTER_API_KEY", "")

    if not tavily_key:
        sys.exit("❌ TAVILY_API_KEY not set. See .env.example.")

    if not args.company and not args.url:
        sys.exit("❌ Provide --company or --url")

    company = args.company or "Unknown"
    if args.url and not company:
        # Try to extract company from URL
        m = re.search(r"at-([^-/]+)", args.url)
        company = m.group(1).replace("-", " ").title() if m else "Unknown"

    print(f"🔍 Finding contacts for: {company}")
    print(f"   Role: {args.role or 'N/A'}")
    print()

    # 1. Try Hunter.io if domain known
    domain = extract_domain(company)
    pattern_data = {"pattern": None, "emails": [], "note": "No Hunter.io key"}
    if hunter_key:
        print(f"📧 Querying Hunter.io for {domain}...")
        pattern_data = find_email_patterns(company, domain, hunter_key)
        if pattern_data.get("emails"):
            print(f"   ✅ Found {len(pattern_data['emails'])} verified emails, pattern: {pattern_data.get('pattern')}")
        else:
            print(f"   ⚠️  No emails at {domain}")
    else:
        print("⏭️  HUNTER_API_KEY not set, skipping Hunter.io")

    # 2. Search LinkedIn via Tavily
    print(f"🔎 Searching LinkedIn via Tavily...")
    recruiters = find_recruiter_via_tavily(company, args.role, tavily_key)
    print(f"   Found {len(recruiters)} recruiter/hiring candidates")
    print(f"🔎 Finding hiring manager...")
    managers = find_hiring_manager_via_tavily(company, args.role, tavily_key)
    print(f"   Found {len(managers)} potential managers")
    print(f"🔎 Finding similar-role peers...")
    peers = find_similar_role_peers(company, args.role, tavily_key)
    print(f"   Found {len(peers)} peers")

    # 3. Generate pattern emails
    pattern_emails = []
    if pattern_data.get("pattern") and pattern_data.get("emails"):
        first_names = list({e["name"].split()[0] for e in pattern_data["emails"] if e.get("name")})
        last_names = list({e["name"].split()[-1] for e in pattern_data["emails"] if e.get("name")})
        pattern_emails = generate_pattern_emails(first_names, last_names, pattern_data["pattern"], domain)

    # 4. Merge Hunter.io emails into recruiters list
    for e in pattern_data.get("emails", []):
        if e.get("position") and any(kw in e["position"].lower() for kw in ["recruit", "talent", "hr", "people"]):
            recruiters.insert(0, {
                "name": e["name"],
                "title": e["position"],
                "linkedin": e.get("linkedin", ""),
                "email": e.get("email", ""),
                "snippet": "Hunter.io verified",
            })

    contacts = {
        "domain": domain,
        "source": "hunter.io + tavily" if hunter_key else "tavily-only",
        "recruiters": recruiters,
        "hiring_managers": managers,
        "peers": peers,
        "pattern_emails": pattern_emails,
        "recruiter_email": recruiters[0].get("email", "") if recruiters else "",
    }

    out_path = write_contacts_md(company, args.role, contacts)
    print(f"\n✅ Wrote: {out_path}")

    # Update Job_Listings.csv
    if update_job_listings(company, contacts):
        print(f"📝 Updated Job_Listings.csv with contact for {company}")


if __name__ == "__main__":
    main()
