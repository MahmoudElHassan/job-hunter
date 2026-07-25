#!/usr/bin/env bash
# Push latest CVs from job-hunter repo to MahmoudElHassan/My_Portofolio
# Run this manually after approving a CV change.

set -euo pipefail

JOB_HUNTER_DIR="${1:-$HOME/job-hunter}"
PORTFOLIO_DIR="${2:-$HOME/My_Portofolio}"
LANG="${3:-en}"   # "en" or "ar" or "both"

cd "$JOB_HUNTER_DIR"

echo "📥 Pulling latest from job-hunter..."
git pull --rebase --autostash

if [ ! -d "$PORTFOLIO_DIR" ]; then
  echo "📥 Cloning portfolio repo to $PORTFOLIO_DIR..."
  git clone https://github.com/MahmoudElHassan/My_Portofolio.git "$PORTFOLIO_DIR"
fi

cd "$PORTFOLIO_DIR"
git pull --rebase --autostash

push_lang() {
  local lang="$1"
  local src="$JOB_HUNTER_DIR/data/master_resume_${lang}.md"
  # Need to convert MD → PDF. Two options:
  #   1. Have a pre-generated PDF in job-hunter/data/cv-${lang}.pdf (manual step)
  #   2. Convert on-the-fly using pandoc (if installed)
  local pdf_src="$JOB_HUNTER_DIR/data/cv-${lang}.pdf"
  local pdf_dst="public/pdf/cv-${lang}.pdf"

  if [ -f "$pdf_src" ]; then
    cp "$pdf_src" "$pdf_dst"
    echo "✅ Copied cv-${lang}.pdf"
  else
    echo "⚠️  No PDF found at $pdf_src. Convert .md → .pdf first:"
    echo "    pandoc $src -o $pdf_src"
  fi
}

case "$LANG" in
  en) push_lang en ;;
  ar) push_lang ar ;;
  both)
    push_lang en
    push_lang ar
    ;;
  *) echo "Usage: $0 [job-hunter-dir] [portfolio-dir] [en|ar|both]" ; exit 1 ;;
esac

git add public/pdf/
if git diff --staged --quiet; then
  echo "🟰 No changes to commit"
else
  git commit -m "cv: auto-update from job-hunter ($(date +%Y-%m-%d))"
  echo "🚀 Pushing to portfolio repo..."
  git push
  echo "✅ Vercel will redeploy automatically."
fi
