#!/bin/bash
# ╔══════════════════════════════════════════════════════════╗
# ║        BOLT AI CONTENT CREATOR — SETUP SCRIPT v2         ║
# ║         One-command installation and configuration        ║
# ╚══════════════════════════════════════════════════════════╝

set -e  # Exit immediately on any error

BOLD="\033[1m"
YELLOW="\033[33m"
GREEN="\033[32m"
CYAN="\033[36m"
RED="\033[31m"
RESET="\033[0m"

echo ""
echo -e "${YELLOW}${BOLD}⚡ BOLT AI CONTENT CREATOR — SETUP v2 ⚡${RESET}"
echo -e "${CYAN}Automated multi-platform AI content pipeline${RESET}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# ── Check Python ─────────────────────────────────────────────
echo -e "${BOLD}[1/6] Checking Python version...${RESET}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 not found. Install Python 3.10+ first.${RESET}"
    exit 1
fi
PYVER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo -e "${GREEN}✅ Python $PYVER found${RESET}"

# ── Create directories ───────────────────────────────────────
echo -e "\n${BOLD}[2/6] Creating directory structure...${RESET}"
mkdir -p logs data/{queue,published,analytics} content/{audio,video,thumbnails}
echo -e "${GREEN}✅ Directories created${RESET}"

# Generate .env if it does not exist
if [ ! -f ".env" ]; then
  python3 code/secrets_manager.py --generate-env 2>/dev/null || true
  cp .env.example .env 2>/dev/null || true
  echo -e "${YELLOW}Created .env — add your API keys: nano .env${RESET}"
fi

# ── Install dependencies ─────────────────────────────────────
echo -e "\n${BOLD}[3/6] Installing Python dependencies...${RESET}"
pip install -q -r requirements.txt --break-system-packages 2>/dev/null || \
pip install -q -r requirements.txt
python3 -c "import nltk; nltk.download('punkt', quiet=True); nltk.download('stopwords', quiet=True); nltk.download('vader_lexicon', quiet=True)"
echo -e "${GREEN}✅ Dependencies installed${RESET}"

# ── Copy assets ──────────────────────────────────────────────
echo -e "\n${BOLD}[4/6] Setting up brand assets...${RESET}"
mkdir -p assets
if [ -d "../imgs" ]; then
    cp -r ../imgs/* assets/ 2>/dev/null || true
    echo -e "${GREEN}✅ Brand assets copied from workspace${RESET}"
else
    echo -e "${YELLOW}⚠️  No imgs folder found — add bolt_logo.png manually to assets/${RESET}"
fi

# ── API Key configuration ────────────────────────────────────
echo -e "\n${BOLD}[5/6] API Configuration${RESET}"
echo -e "${CYAN}You'll need these API keys to fully automate the pipeline:${RESET}"
echo ""
echo "  🔑 REQUIRED for automation:"
echo "    • Anthropic (Claude)  → https://console.anthropic.com"
echo "    • ElevenLabs (voice)  → https://elevenlabs.io"
echo "    • HeyGen (avatar)     → https://heygen.com"
echo "    • Buffer (scheduling) → https://buffer.com/developers"
echo ""
echo "  🔑 REQUIRED for publishing:"
echo "    • YouTube Data API v3 → https://console.cloud.google.com"
echo "    • TikTok API          → https://developers.tiktok.com"
echo "    • Instagram Graph API → https://developers.facebook.com"
echo ""
echo "  🔔 OPTIONAL (recommended):"
echo "    • Discord Webhook     → Server Settings → Integrations → Webhooks"
echo "    • Creatomate          → https://creatomate.com (video branding)"
echo "    • Google Cloud TTS    → https://console.cloud.google.com (free fallback voice)"
echo ""
echo -e "${YELLOW}Edit code/config.json and replace all 'YOUR_*' values with real keys.${RESET}"

# ── PM2 / Cron setup ─────────────────────────────────────────
echo -e "\n${BOLD}[6/6] Scheduler setup${RESET}"
if command -v pm2 &> /dev/null; then
    pm2 delete bolt-ai 2>/dev/null || true
    pm2 start code/content_automation_master.py \
        --name bolt-ai \
        --interpreter python3 \
        -- --schedule
    pm2 save
    echo -e "${GREEN}✅ Bolt running via PM2 (pm2 logs bolt-ai to view logs)${RESET}"
else
    echo -e "${YELLOW}PM2 not found. Setting up cron job instead...${RESET}"
    CRON_CMD="0 6 * * * cd $(pwd) && python3 code/content_automation_master.py >> logs/cron.log 2>&1"
    (crontab -l 2>/dev/null | grep -v "content_automation_master"; echo "$CRON_CMD") | crontab -
    echo -e "${GREEN}✅ Cron job added (runs daily at 06:00)${RESET}"
    echo -e "${CYAN}   Install PM2 for better process management: npm install -g pm2${RESET}"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${GREEN}${BOLD}⚡ BOLT IS READY!${RESET}"
echo ""
echo -e "${CYAN}Quick commands:${RESET}"
echo "  python3 code/content_automation_master.py             # Run full pipeline now"
echo "  python3 code/content_automation_master.py --step news # Only aggregate news"
echo "  python3 code/news_aggregator.py                       # Test news fetching"
echo "  python3 code/script_generator.py                      # Test script generation"
echo "  python3 code/analytics_tracker.py                     # Update dashboard data"
echo ""
echo -e "${YELLOW}Next step: Add your API keys to code/config.json then run:${RESET}"
echo "  python3 code/content_automation_master.py --step news"
echo ""
