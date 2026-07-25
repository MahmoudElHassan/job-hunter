#!/usr/bin/env python3
"""
generate_application.py — for a given JOB-ID, generate a complete ready-to-apply package.

Outputs (in data/Applications/<Company>/):
    - cover_letter.md       (formal email body for direct application)
    - proposal.md           (Upwork-style proposal if source=freelance)
    - linkedin_message.md   (short DM if source=linkedin)
    - bid_suggestion.md     (market-rate analysis)
    - application_summary.md (full package overview)

Usage:
    python3 scripts/generate_application.py --job JOB-2026-07-25-001
    python3 scripts/generate_application.py --job JOB-2026-07-25-001 --regenerate
"""

import argparse
import csv
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent.parent
DATA = ROOT / "data"
LISTINGS_CSV = DATA / "Job_Listings.csv"
APPS_DIR = DATA / "Applications"
APPS_DIR.mkdir(parents=True, exist_ok=True)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def load_job(job_id: str) -> dict:
    """Find the job row by ID."""
    if not LISTINGS_CSV.exists():
        sys.exit(f"❌ {LISTINGS_CSV} not found")
    with LISTINGS_CSV.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("id") == job_id:
                return row
    sys.exit(f"❌ Job {job_id} not found in Job_Listings.csv")


def read_master_resume() -> str:
    """Read the English master resume."""
    p = DATA / "master_resume_en.md"
    if not p.exists():
        sys.exit(f"❌ {p} not found")
    return p.read_text(encoding="utf-8")


def extract_relevant_skills(job: dict) -> list[str]:
    """Pick the skills from the job's stack_match field."""
    raw = job.get("stack_match", "")
    if not raw:
        return []
    return [s.strip() for s in raw.split(",") if s.strip()]


def extract_relevant_projects(master_resume: str, skills: list[str]) -> list[str]:
    """Pick the 2-3 most relevant projects based on skill overlap."""
    # Naive: pick projects that mention overlapping skills
    projects_section = re.search(
        r"## Selected Projects(.*?)## Education",
        master_resume, re.DOTALL
    )
    if not projects_section:
        return ["Khzama", "NumeriiSoft", "Matrix"]
    section = projects_section.group(1)
    # Split by ### (project header)
    chunks = re.split(r"###\s+", section)
    scored = []
    for chunk in chunks:
        if not chunk.strip():
            continue
        score = sum(1 for s in skills if s.lower() in chunk.lower())
        name = chunk.split("\n", 1)[0].strip()
        if score > 0:
            scored.append((score, name))
    scored.sort(reverse=True)
    return [name for _, name in scored[:3]] or ["Khzama", "NumeriiSoft"]


def generate_cover_letter(job: dict) -> str:
    """Generate a formal cover letter / email body."""
    company = job.get("company", "[Company]")
    role = job.get("role", "[Role]")
    location = job.get("location", "")
    skills = extract_relevant_skills(job)
    master = read_master_resume()
    projects = extract_relevant_projects(master, skills)

    skills_str = ", ".join(skills[:5]) if skills else "ASP.NET Core, Azure, multi-tenant SaaS"

    projects_block = "\n".join(f"- **{p}**" for p in projects)

    return f"""# Cover Letter — {company} ({role})

> Email body. Replace [bracketed] fields before sending. Subject line below.

**Subject:** Application: {role} — Mahmoud ElHassan (4+ yr .NET, Azure, multi-tenant SaaS)

---

Dear Hiring Team,

I'm writing to apply for the **{role}** position at **{company}**. With 4+ years of production experience building scalable SaaS platforms on ASP.NET Core and Azure — including multi-tenant systems, Clean Architecture, and production RESTful APIs for web and mobile — I'm confident I can contribute from week one.

**Why me, specifically for {company}:**

- ✅ **Stack match:** I've shipped production code with {skills_str}
- ✅ **Scale:** Built and maintained multi-tenant SaaS serving real charities in Makkah (Khzama project), handling payment processing, transaction recording, and automated email workflows on Azure App Service with auto-scaling.
- ✅ **Architecture:** Strong on Clean Architecture (Domain / Application / Infrastructure / API), Repository Pattern, and JWT/role-based auth — I've implemented these patterns across multiple production systems.
- ✅ **Delivery:** CI/CD pipelines on Azure + GitHub Actions, Docker containerisation, environment management — I ship continuously, not in big-bang releases.

**Recent work most relevant to {role}:**

{projects_block}

Each project lives in production today. I can share architecture diagrams, code samples, and live URLs on request.

**Practical details:**

- **Location:** Makkah, Saudi Arabia — open to remote worldwide or sponsorship in Gulf / Asia / Europe
- **Visa:** Currently require sponsorship (no active KSA iqama), but I handle all paperwork
- **Notice period:** 2 weeks (or immediate for the right role)
- **References:** Available on request

I'd love a 30-minute call to walk you through my work and learn more about {company}'s roadmap for this role. When works for a quick chat?

Best regards,
**Mahmoud ElHassan**
📞 +966 050 411 6526
✉️ mahmoudelhassan9@gmail.com
🔗 https://www.linkedin.com/in/mahmoud-elhassan-94r
💻 https://github.com/MahmoudElHassan
🌐 https://mahmoud-portofolio-eta.vercel.app

---
_Personal note: I read about {company}'s recent work and I'm excited about the {role} scope. Let me know if you'd like me to send a 1-page case study on a relevant project._
"""


def generate_upwork_proposal(job: dict) -> str:
    """Generate Upwork-style proposal (shorter, more direct)."""
    company = job.get("company", "your team")
    role = job.get("role", "your project")
    skills = extract_relevant_skills(job)
    master = read_master_resume()
    projects = extract_relevant_projects(master, skills)
    skills_str = ", ".join(skills[:4]) if skills else "ASP.NET Core, EF Core, Azure, Docker"

    return f"""# Upwork Proposal — {company} ({role})

> Short, direct, leads with proof. Aim: < 1500 chars. Upwork truncates around 1500.

---

Hi {company},

I read your job post carefully — the {role} matches my last 4 years of production work almost exactly.

**What I've shipped that's most relevant:**

- **Khzama** — multi-tenant SaaS donation platform on Azure, Clean Architecture, JWT + role-based auth, payment processing, CI/CD via GitHub Actions. Live in production for charities in Makkah.
- **Matrix** — social media ads platform integrating Meta + TikTok APIs, MongoDB, Redis, payment gateway.
- **NumeriiSoft** — content platform with 3rd-party API integration, course management, JWT auth.

All three are in production today with paying users.

**Stack I work in daily:**

{skills_str}, plus xUnit tests, Git, Swagger/OpenAPI, Linux CLI. I use Cursor and OpenCode for AI-assisted development to ship faster.

**How I'd approach your project:**

1. Day 1 — read your existing code/repo, run it locally, write a 1-page architecture summary
2. Day 2-3 — clarify the deliverable, agree on acceptance criteria
3. Day 4+ — ship in small PRs with tests, daily standup, written progress notes
4. Final — handover with README + runbook

**Practical:**

- Time zone: UTC+3 (Makkah) — overlaps well with EU morning + US morning
- Availability: 30-40 hrs/week
- Rate: [see bid_suggestion.md]
- Communication: Slack, Teams, or your preferred channel

I'd love to see a quick call before you commit. Free 20-min chat to scope the work and answer any questions.

Mahmoud ElHassan
"""


def generate_linkedin_message(job: dict) -> str:
    """Generate a short LinkedIn DM (under 300 chars)."""
    company = job.get("company", "your team")
    role = job.get("role", "the role")

    return f"""# LinkedIn DM — {company}

> Under 300 chars. Direct, no flattery.

---

Hi [First Name] — saw the {role} posting at {company}. 4+ yr ASP.NET Core + Azure here (Khzama, a multi-tenant SaaS on Azure, is my latest). Open to remote/sponsorship worldwide. Worth a 5-min chat? — Mahmoud
"""


def suggest_bid(job: dict) -> str:
    """Suggest bid / fee based on market data + Mahmoud's profile."""
    source = job.get("source_type", "main")
    score = int(job.get("score", 3))
    role = job.get("role", "")

    is_senior = "senior" in role.lower() or "lead" in role.lower() or "staff" in role.lower()

    if source == "freelance":
        if "upwork" in job.get("board", "").lower():
            hourly = "USD 35-50/hr" if is_senior else "USD 25-40/hr"
            fixed = "USD 800-2,500 (small project, 1-2 weeks)"
        elif "toptal" in job.get("board", "").lower():
            hourly = "USD 80-120/hr (Toptal premium rate)"
        elif "mostaql" in job.get("board", "").lower():
            hourly = "USD 15-25/hr"
            fixed = "USD 200-800 (small Arabic-market project)"
        elif "contra" in job.get("board", "").lower():
            hourly = "USD 40-60/hr (no platform fees = higher take-home)"
        else:
            hourly = "USD 30-45/hr"
    else:
        # Full-time roles
        if "uae" in job.get("location", "").lower() or "dubai" in job.get("location", "").lower():
            monthly = "AED 14,000 - 22,000 / month (mid-level .NET, 4 yr)"
        elif "ksa" in job.get("location", "").lower() or "saudi" in job.get("location", "").lower():
            monthly = "SAR 14,000 - 22,000 / month"
        elif "europe" in job.get("location", "").lower() or "eu" in job.get("location", "").lower():
            monthly = "EUR 60,000 - 85,000 / year"
        elif "remote" in job.get("location", "").lower():
            monthly = "USD 55,000 - 85,000 / year"
        else:
            monthly = "Negotiate based on local market"
        return f"""# Bid Suggestion — {role}

**Role type:** Full-time
**Seniority:** {'Senior' if is_senior else 'Mid-level'}

## Salary target

{monthly}

## Negotiation anchor

- Floor (accept): 90% of midpoint
- Target: midpoint
- Stretch: 110% of midpoint (only if other offers)

## What strengthens your ask

- 4+ yr production .NET (not just training)
- Real multi-tenant SaaS on Azure (Khzama)
- 3rd-party API integration experience (Matrix)
- Open source (arabic-fix) — rare signal for backend devs

## What to leave out of anchor

- BSc in Tourism & Hotels (bridge narrative instead — hospitality → customer obsession → backend)
- "Looking for sponsorship" (lead with "open to remote or sponsorship, both work")

## If they push back on comp

Counter with: "I can take slightly below midpoint if the role offers [learning / visa / remote flexibility / project impact]. What's your range flexibility?"
"""

    return f"""# Bid Suggestion — {role}

**Role type:** Freelance / Contract
**Source:** {source}
**Score:** {score}★

## Hourly rate (recommended)

**{hourly}**

## Why this range

- Mahmoud is mid-level (4+ yr), not junior — bottom of range is too low
- ASP.NET Core + Azure stack commands 20-30% premium over generic .NET
- Multi-tenant + Clean Architecture experience is rare in mid-level

## Fixed-price alternative

{fixed if 'fixed' in locals() else 'Estimate: hours × hourly + 20% buffer for scope creep'}

## If client pushes back

- "My rate reflects production Azure + multi-tenant experience. I'm happy to scope a fixed-price first milestone so you can evaluate the work before committing further."
- Never go below 80% of range without clear scope reduction
"""


def write_summary(job: dict, files_written: list[Path]) -> str:
    return f"""# Application Package — {job.get('company', 'Unknown')}

_Generated {now_iso()}_

## Job Details

- **ID:** {job.get('id')}
- **Role:** {job.get('role')}
- **Company:** {job.get('company')}
- **Location:** {job.get('location', 'N/A')}
- **Source:** {job.get('source_type')} ({job.get('board')})
- **Score:** {job.get('score')}★
- **URL:** {job.get('url')}

## Stack match

{job.get('stack_match', 'N/A')}

## Files in this package

{chr(10).join(f"- `{f.name}`" for f in files_written)}

## Suggested next steps

1. Run `python3 scripts/find_contacts.py --company "{job.get('company')}" --role "{job.get('role')}"` to get recruiter/hiring manager info
2. Review `cover_letter.md` and tweak the [bracketed] sections
3. For freelance: review `proposal.md` (keep under 1500 chars on Upwork)
4. Send to the right contact (see contacts.md after running find_contacts)
5. Update Job_Listings.csv: change `status` from `new` to `applied`
6. Set 7-day follow-up reminder (cron once)

## Estimated effort to submit

- Review cover letter: 5 min
- Find contact + verify email: 5-10 min
- Send application: 2 min
- Update tracker: 1 min

**Total: ~15-20 min per application.** Plan to do 3-5/day for max output.
"""


def main():
    parser = argparse.ArgumentParser(description="Generate ready-to-apply package for a job")
    parser.add_argument("--job", required=True, help="Job ID (e.g. JOB-2026-07-25-001)")
    parser.add_argument("--regenerate", action="store_true", help="Overwrite existing files")
    args = parser.parse_args()

    job = load_job(args.job)
    company_slug = slugify(job.get("company", "unknown"))
    app_dir = APPS_DIR / company_slug
    app_dir.mkdir(parents=True, exist_ok=True)

    print(f"📦 Generating application package for: {job.get('company')} — {job.get('role')}")
    print(f"   Output dir: {app_dir}")
    print()

    written = []

    # Cover letter (always)
    p = app_dir / "cover_letter.md"
    if p.exists() and not args.regenerate:
        print(f"   ⏭️  {p.name} exists, skipping (use --regenerate to overwrite)")
    else:
        p.write_text(generate_cover_letter(job), encoding="utf-8")
        print(f"   ✅ {p.name}")
        written.append(p)

    # Upwork proposal (if freelance)
    if job.get("source_type") == "freelance":
        p = app_dir / "proposal.md"
        if p.exists() and not args.regenerate:
            print(f"   ⏭️  {p.name} exists, skipping")
        else:
            p.write_text(generate_upwork_proposal(job), encoding="utf-8")
            print(f"   ✅ {p.name}")
            written.append(p)

    # LinkedIn message (if from LinkedIn)
    if "linkedin" in job.get("board", "").lower():
        p = app_dir / "linkedin_message.md"
        if p.exists() and not args.regenerate:
            print(f"   ⏭️  {p.name} exists, skipping")
        else:
            p.write_text(generate_linkedin_message(job), encoding="utf-8")
            print(f"   ✅ {p.name}")
            written.append(p)

    # Bid suggestion (always)
    p = app_dir / "bid_suggestion.md"
    if p.exists() and not args.regenerate:
        print(f"   ⏭️  {p.name} exists, skipping")
    else:
        p.write_text(suggest_bid(job), encoding="utf-8")
        print(f"   ✅ {p.name}")
        written.append(p)

    # Summary (always, regenerates)
    p = app_dir / "application_summary.md"
    p.write_text(write_summary(job, written), encoding="utf-8")
    print(f"   ✅ {p.name}")

    # Job_Listings.csv: bump status
    if not args.regenerate:
        rows = []
        updated = False
        with LISTINGS_CSV.open(encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row.get("id") == args.job:
                    row["status"] = "tailored"
                    updated = True
                rows.append(row)
        if updated and rows:
            with LISTINGS_CSV.open("w", encoding="utf-8", newline="") as f:
                w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
                w.writeheader()
                w.writerows(rows)
            print(f"📝 Status updated to 'tailored' in Job_Listings.csv")

    print()
    print("✅ Done. Review the files, then send.")


if __name__ == "__main__":
    main()
