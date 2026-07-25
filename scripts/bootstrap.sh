#!/usr/bin/env bash
# One-time bootstrap: create GitHub repo, push code, set up.
# Run this ONCE after copying the project files locally.

set -euo pipefail

cd "$(dirname "$0")/.."
ROOT="$(pwd)"

echo "🚀 Job Hunter — bootstrap"
echo ""

# Pre-flight checks
command -v git >/dev/null || { echo "❌ git not found"; exit 1; }
command -v python3 >/dev/null || { echo "❌ python3 not found"; exit 1; }
command -v gh >/dev/null || { echo "❌ gh CLI not found. Install: brew install gh"; exit 1; }

# Check gh auth
if ! gh auth status >/dev/null 2>&1; then
  echo "❌ gh not authenticated. Run: gh auth login"
  exit 1
fi

# Check .env
if [ ! -f "$ROOT/.env" ]; then
  echo "⚠️  No .env file. Creating from template..."
  cp "$ROOT/.env.example" "$ROOT/.env"
  echo "👉 Edit .env with your TAVILY_API_KEY and TELEGRAM_BOT_TOKEN"
  echo "   Then re-run this script."
  exit 0
fi

# Install deps
echo "📦 Installing Python deps..."
python3 -m pip install -r requirements.txt --user --quiet

# Test scan
echo "🧪 Testing scanner (dry-run)..."
python3 job_hunter.py --quick --dry-run

# Init git
if [ ! -d "$ROOT/.git" ]; then
  echo "📝 Initializing git repo..."
  git init
  git add .
  git commit -m "initial: job-hunter v1"
fi

# Create GitHub repo
echo "🌐 Creating GitHub repo MahmoudElHassan/job-hunter (public)..."
if gh repo view MahmoudElHassan/job-hunter >/dev/null 2>&1; then
  echo "🟰 Repo already exists, will push to it"
else
  gh repo create job-hunter --public --description "Personal AI job search worker. Free, GitHub Actions, Telegram." --source=. --remote=origin
fi

# Push
echo "⬆️  Pushing to GitHub..."
git push -u origin main 2>/dev/null || git push -u origin master

echo ""
echo "✅ Bootstrap complete!"
echo ""
echo "👉 Next steps:"
echo "1. Go to https://github.com/MahmoudElHassan/job-hunter/settings/secrets/actions"
echo "2. Add these secrets:"
echo "   - TAVILY_API_KEY"
echo "   - TELEGRAM_BOT_TOKEN"
echo "   - TELEGRAM_CHAT_ID"
echo "3. Go to https://github.com/MahmoudElHassan/job-hunter/actions"
echo "4. Run 'Job Hunter — Scheduled Scan' with mode=quick to test"
echo "5. Check Telegram for the test message"
