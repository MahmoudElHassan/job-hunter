# Job Hunter — Mahmoud ElHassan

> Personal AI job search worker. Scans job boards + freelance platforms 3×/week (Sun/Tue/Thu at 17:00 Makkah), scores matches, notifies via Telegram, and tailors CVs on demand. **100% free, runs on GitHub Actions.**

## What it does

- **Scans focused boards** — LinkedIn jobs + hiring posts, Bayt / GulfTalent / Indeed, and freelance (Upwork, Mostaql, Contra, Braintrust, PeoplePerHour). Last **48 hours** only.
- **Scores each result 1–5** and keeps only .NET/C# stack fits that are **remote or visa-friendly**
- **Fail-closed open checks** on LinkedIn job pages and Gulf/freelance URLs (drops closed / unreachable)
- **Notifies via Telegram** with the top 5 by score (5★ before 4★)
- **Stores everything** in `data/Job_Listings.csv` (deduped) + `data/daily/`
- **Runs on GitHub Actions** for free (2000 min/month, scheduled cron)
- **Tailors CVs** on demand via Mavis (in-chat) — no LLM key needed
- **Delete from cover-letter board** (Yes/No + delete key) or `python3 scripts/delete_listing.py JOB-xxx`

## File layout

```
job-hunter/
├── job_hunter.py                 # Main scanner
├── requirements.txt
├── .env.example                  # Secrets template
├── .github/workflows/
│   ├── scan.yml                  # 3×/week scan cron (Sun/Tue/Thu 17:00 Makkah)
│   └── digest.yml                # Digest at 21:00 Makkah on scan days
├── scripts/
│   ├── daily_digest.py           # Telegram digest generator
│   └── push_cv_to_portfolio.sh   # Manual CV push
├── data/
│   ├── search_config.csv         # Editable query list
│   ├── Job_Listings.csv          # Deduped, scored jobs
│   ├── Dream_Companies.csv       # Target companies
│   ├── master_resume_en.md       # English CV (source)
│   ├── master_resume_ar.md       # Arabic CV (source)
│   ├── daily/YYYY-MM-DD.md       # Daily scan logs
│   └── Applications/<Company>/   # Per-company tailored materials
└── docs/
    ├── PROFILE.md                # Mahmoud's profile (baked-in heuristics)
    └── SETUP.md                  # Detailed setup
```

## Limitations

- **Web search is keyword-based** (Tavily). If a job is poorly tagged on the board, it might be missed.
- **Scoring is rule-based** (no LLM in the scanner). Good enough for filtering, but Mavis does the deep tailoring.
- **Telegram is one-way** (notifications). Commands are handled by Mavis in chat, not by the bot directly. (Could be added via Cloudflare Worker if needed.)
- **Public repo** — your scan data is visible. Don't put personal notes in `Job_Listings.csv` notes field.

## Deploy on Vercel

The static dashboard in `docs/` is deployed as-is via the included `vercel.json`
(`framework: null` + `outputDirectory: docs` so Vercel does **not** treat the
repo as a Python app because of `requirements.txt` / `job_hunter.py`):

1. Go to [vercel.com/new](https://vercel.com/new) and import `MahmoudElHassan/job-hunter`.
2. Leave Root Directory as `.` (repo root). Framework Preset should show **Other** from `vercel.json`.
3. Click **Deploy**. Every push to `main` redeploys automatically.
4. Visit your URL:
   - `/` → `docs/index.html` (dashboard with filters)
   - `/cover-letter/` → `docs/cover-letter/index.html`
5. The dashboard still fetches the CSV directly from the GitHub raw URL, so it picks up every scheduled scan automatically — no rebuild required.

### Cover-letter delete (optional)

To delete a listing from the cover-letter board into `data/Job_Listings.csv`:

1. In Vercel → Project → Settings → Environment Variables, add:
   - `DELETE_KEY` — a passphrase only you know
   - `GITHUB_TOKEN` — fine-grained PAT with **Contents: Read and write** on this repo
2. Redeploy.
3. On `/cover-letter/`, click **Delete** → confirm Yes → enter the delete key once per session.

If the API URL is not `https://job-hunter.vercel.app`, set it in the browser console:
`localStorage.setItem('cl_delete_api', 'https://YOUR-PROJECT.vercel.app/api/delete-listing')`

Local alternative (no Vercel):

```bash
python3 scripts/delete_listing.py JOB-xxx
```

If an old project still has Framework = Python in Vercel Project Settings, set it to **Other** (or clear Override) and redeploy.

If you have the `vercel` CLI authenticated, you can also deploy from the terminal:

```bash
npm i -g vercel
vercel --prod
```

## License

MIT
