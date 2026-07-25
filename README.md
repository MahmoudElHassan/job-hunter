# Job Hunter — Mahmoud ElHassan

> Personal AI job search worker. Scans job boards + freelance platforms 4×/day, scores matches, notifies via Telegram, and tailors CVs on demand. **100% free, runs on GitHub Actions.**

## What it does

- **Scans 30+ queries** across main boards (LinkedIn, Bayt, GulfTalent, Indeed, Glassdoor, RemoteOK, Arc.dev) + **freelance** (Upwork, Toptal, Mostaql, Contra, Braintrust, HackerNews Who's Hiring) + OSS bounties
- **Scores each result 1–5** using keyword + location + sponsorship heuristics
- **Notifies via Telegram** on score 4–5 finds
- **Stores everything** in `data/Job_Listings.csv` (deduped) + `data/daily/`
- **Runs on GitHub Actions** for free (2000 min/month, scheduled cron)
- **Tailors CVs** on demand via Mavis (in-chat) — no LLM key needed

## Architecture

```
GitHub Actions (cron)          Mavis (Mavis)        You
        │                            │               │
        ▼                            │               │
   job_hunter.py ──scan──▶ Tavily ──results──▶ CSV  │
        │                                            │
        └────notify────▶ Telegram Bot API ─────▶ 📱 │
                                                     │
   (you say "tailor JOB-001") ──────────────────────▶│
        ▲                                            │
        │                                            │
   tailored_resume.md ◀──── Mavis (LLM) ─────────────┘
        │
        └─ (you say "push CV") ──▶ scripts/push_cv_to_portfolio.sh
                                       │
                                       ▼
                              My_Portofolio repo
                              (auto-deploys on Vercel)
```

**Cost: $0/month.** GitHub Actions free for public repos, Telegram Bot API free, Tavily free tier 1000 searches/month (≈ 30/day, more than enough for 4 scans × 8 queries).

## Quick start

### 1. Get free API keys (3 minutes)

| Service | URL | Notes |
|---|---|---|
| **Tavily** | https://app.tavily.com/home | 1000 free searches/month. Sign up with Google. |
| **Telegram bot token** | https://t.me/BotFather | Send `/newbot`, follow prompts. |
| **Telegram chat_id** | https://t.me/userinfobot | Send `/start`, get your chat_id. |

### 2. Bootstrap

```bash
cd ~/job-hunter

# Copy env template
cp .env.example .env
nano .env   # Fill in TAVILY_API_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

# Install deps
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Run a quick test
python job_hunter.py --quick --dry-run
```

### 3. Push to GitHub

```bash
# One-time: create the repo
gh repo create job-hunter --public --source=. --remote=origin --push

# OR with git directly:
git init
git add .
git commit -m "initial: job-hunter v1"
gh repo create job-hunter --public --source=. --remote=origin --push
```

### 4. Add secrets to GitHub

Go to https://github.com/MahmoudElHassan/job-hunter/settings/secrets/actions and add:

- `TAVILY_API_KEY`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

### 5. Test the workflow

Go to https://github.com/MahmoudElHassan/job-hunter/actions → "Job Hunter — Scheduled Scan" → Run workflow → choose `quick`.

You should see a Telegram message within 2 minutes.

## Day-to-day usage

| You say to Mavis | What happens |
|---|---|
| `tailor JOB-2026-07-25-001` | Mavis reads the JD + master resume, generates tailored CV in `data/Applications/<Company>/resume_tailored.md` |
| `cover JOB-2026-07-25-001` | Cover letter (under 400 words) for the JD |
| `apply JOB-2026-07-25-001` | Marks status=applied, sets 7-day follow-up reminder |
| `pipeline` | Lists all jobs by status |
| `today` | Today's findings |
| `recap` | Weekly summary |
| `set salary_min 18000` | Updates profile filter |

## CV → portfolio flow (manual approval)

When you want to publish the latest CV to your portfolio site:

```bash
# Step 1: Convert .md to .pdf (if you don't already have a PDF version)
cd ~/job-hunter
pandoc data/master_resume_en.md -o data/cv-en.pdf
pandoc data/master_resume_ar.md -o data/cv-ar.pdf

# Step 2: Push to portfolio
bash scripts/push_cv_to_portfolio.sh
```

Vercel will auto-deploy within ~30 seconds. The PDFs at `mahmoud-portofolio-eta.vercel.app/pdf/cv-en.pdf` and `cv-ar.pdf` will be updated.

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

## License

MIT
