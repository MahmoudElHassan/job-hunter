# Job Hunter — Mahmoud ElHassan

> Personal AI job search worker. Scans job boards + freelance platforms 4×/day, scores matches, notifies via Telegram, and tailors CVs on demand. **100% free, runs on GitHub Actions.**

## What it does

- **Scans 30+ queries** across main boards (LinkedIn, Bayt, GulfTalent, Indeed, Glassdoor, RemoteOK, Arc.dev) + **freelance** (Upwork, Toptal, Mostaql, Contra, Braintrust, HackerNews Who's Hiring) + OSS bounties
- **Scores each result 1–5** using keyword + location + sponsorship heuristics
- **Notifies via Telegram** on score 4–5 finds
- **Stores everything** in `data/Job_Listings.csv` (deduped) + `data/daily/`
- **Runs on GitHub Actions** for free (2000 min/month, scheduled cron)
- **Tailors CVs** on demand via Mavis (in-chat) — no LLM key needed

## File layout

```
job-hunter/
├── job_hunter.py                 # Main scanner
├── requirements.txt
├── .env.example                  # Secrets template
├── .github/workflows/
│   ├── scan.yml                  # 4×/day scan cron
│   └── digest.yml                # Daily digest at 21:00 Makkah
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

The static dashboard in `docs/` is deployed as-is via the included `vercel.json`:

1. Go to [vercel.com/new](https://vercel.com/new) and import `MahmoudElHassan/job-hunter`.
2. Vercel reads `vercel.json` at the repo root — **no framework selection, no build command, no output override needed**.
3. Click **Deploy**. Every push to `main` redeploys automatically.
4. Visit your URL:
   - `/` → `docs/index.html` (dashboard with filters)
   - `/cover-letter/` → `docs/cover-letter/index.html`
5. The dashboard still fetches the CSV directly from the GitHub raw URL, so it picks up every scheduled scan automatically — no rebuild required.

If you have the `vercel` CLI authenticated, you can also deploy from the terminal:

```bash
npm i -g vercel
vercel --prod
```

## License

MIT
