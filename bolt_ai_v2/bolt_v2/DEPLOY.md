# ⚡ Bolt AI — Deployment Guide

Copy-paste commands. Three paths depending on where you're deploying.

---

## Option A — DigitalOcean VPS ($6/month) — Recommended

### 1. Provision the server

Create a DigitalOcean Droplet:
- **Image**: Ubuntu 22.04 LTS
- **Size**: Basic · 1 vCPU · 1 GB RAM ($6/month) — enough for start
- **Region**: New York or closest to your audience

### 2. SSH in and run setup

```bash
# SSH into your droplet
ssh root@YOUR_DROPLET_IP

# Install Docker
curl -fsSL https://get.docker.com | sh
systemctl enable docker

# Install Docker Compose
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" \
  -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Clone / upload your project
apt install -y git
git clone https://github.com/yourusername/bolt-ai.git /app/bolt
# OR: scp -r ./bolt_v2 root@YOUR_IP:/app/bolt

cd /app/bolt
```

### 3. Configure secrets

```bash
cp .env.example .env
nano .env          # Add your real API keys
```

Minimum required keys to start:
```
ANTHROPIC_API_KEY=sk-ant-your-key
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
```

### 4. Start all services

```bash
# Build and start everything
docker-compose up -d

# Check all services are healthy
docker-compose ps

# View logs
docker-compose logs -f api
docker-compose logs -f pipeline
docker-compose logs -f worker
```

### 5. Build the dashboard

```bash
# On your local machine
cd bolt-dashboard
echo "VITE_API_URL=http://YOUR_DROPLET_IP:8000" > .env
npm install && npm run build

# Copy built files to the server
scp -r dist/ root@YOUR_DROPLET_IP:/app/bolt/bolt-dashboard/dist
```

Dashboard is now served at `http://YOUR_DROPLET_IP:8000`  
API docs at `http://YOUR_DROPLET_IP:8000/api/docs`

### 6. Verify everything works

```bash
# Health check
curl http://YOUR_DROPLET_IP:8000/api/health

# Check pipeline status
curl http://YOUR_DROPLET_IP:8000/api/status

# Trigger a test news fetch
curl -X POST http://YOUR_DROPLET_IP:8000/api/pipeline/news

# Check job queue
docker-compose exec worker python3 code/job_worker.py --status
```

---

## Option B — Render.com (Free tier)

Render gives you a free web service and a free background worker.

### 1. Push to GitHub

```bash
git init && git add . && git commit -m "Bolt AI v2.2"
git remote add origin https://github.com/yourusername/bolt-ai.git
git push -u origin main
```

### 2. Create services on Render

**Web service (API):**
- Connect your GitHub repo
- Runtime: Docker
- Build command: *(leave empty — uses Dockerfile)*
- Start command: `uvicorn code.api:app --host 0.0.0.0 --port $PORT`
- Instance type: Free

**Background worker (Pipeline + Job Worker):**
- Same repo
- Start command: `python3 code/content_automation_master.py --schedule & python3 code/job_worker.py`
- Instance type: Free

### 3. Add environment variables

In Render dashboard → Environment, add all keys from `.env.example`.

**Important**: Set `PYTHON_VERSION=3.11` in environment variables.

---

## Option C — Railway.app (~$5/month)

Railway is the easiest platform for Docker deployments.

```bash
# Install Railway CLI
npm install -g @railway/cli
railway login

# Deploy
railway init
railway up

# Add environment variables
railway variables set ANTHROPIC_API_KEY=sk-ant-your-key
railway variables set DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
# ... add all others from .env.example
```

Railway auto-detects docker-compose.yml and runs all services.

---

## Post-deployment setup

### Set up the daily pipeline schedule

If not using Docker (running directly on VPS):

```bash
# Add to crontab
crontab -e

# Add these lines:
0 6    * * * cd /app/bolt && python3 code/content_automation_master.py --step news >> logs/cron.log 2>&1
0 7    * * * cd /app/bolt && python3 code/content_automation_master.py --step script >> logs/cron.log 2>&1
30 7   * * * cd /app/bolt && python3 code/content_automation_master.py --step video >> logs/cron.log 2>&1
0 8    * * * cd /app/bolt && python3 code/content_automation_master.py --step publish >> logs/cron.log 2>&1
0 9    * * * cd /app/bolt && python3 code/content_automation_master.py --step analytics >> logs/cron.log 2>&1
0 3    * * * cd /app/bolt && python3 code/content_automation_master.py --backup daily >> logs/cron.log 2>&1
*/60   * * * * cd /app/bolt && python3 code/job_worker.py --once >> logs/cron.log 2>&1
```

### Approve scripts via CLI (HITL)

```bash
# List pending scripts
python3 code/hitl.py list

# Approve a specific script
python3 code/hitl.py approve bolt_20260321_063000

# Reject a script
python3 code/hitl.py reject bolt_20260321_063000 --reason "Too generic"
```

### Monitor the system

```bash
# Real-time logs
docker-compose logs -f

# Cost summary
python3 code/content_automation_master.py --cost-summary

# Database stats
python3 code/content_automation_master.py --db-stats

# Secrets audit (checks which keys are configured)
python3 code/content_automation_master.py --secrets-audit

# Job queue status
python3 code/job_worker.py --status

# List backups
python3 code/content_automation_master.py --list-backups
```

---

## Architecture in production

```
Internet
    │
    ▼
┌─────────────────────────────────────────┐
│  DigitalOcean Droplet ($6/mo)           │
│                                         │
│  ┌──────────┐    ┌────────────────────┐ │
│  │  api     │    │  pipeline          │ │
│  │  :8000   │    │  --schedule        │ │
│  │  FastAPI │    │  Runs 06:00 UTC    │ │
│  └──────────┘    └────────────────────┘ │
│                                         │
│  ┌──────────┐    ┌────────────────────┐ │
│  │  worker  │    │  SQLite DB         │ │
│  │  job     │    │  data/bolt.db      │ │
│  │  queue   │    │  (shared volume)   │ │
│  └──────────┘    └────────────────────┘ │
│                                         │
└─────────────────────────────────────────┘
    │
    ▼ API calls (free tiers)
┌───────────────────────────────────────┐
│  External Services                    │
│  edge-tts (free) → voice              │
│  Google TTS (1M/mo free) → fallback   │
│  Vidnoz (free) → avatar               │
│  Buffer (free) → scheduling           │
│  YouTube/TikTok/Instagram APIs        │
└───────────────────────────────────────┘
```

---

## Troubleshooting

**`ModuleNotFoundError`** — Missing dependency  
```bash
pip install -r requirements.txt
```

**`Database is locked`** — SQLite concurrent access issue  
```bash
# Check what's holding the lock
lsof data/bolt.db
# Restart the blocking service
docker-compose restart api
```

**`Budget hard stop active`** — Monthly/daily limit hit  
```bash
# Check current spending
python3 code/content_automation_master.py --cost-summary
# Increase limit in config.json → cost_tracking → monthly_budget_hard_stop
# Or wait for the period to reset
```

**`HITL timed out`** — Script wasn't reviewed in time  
```bash
# Check what's waiting
python3 code/hitl.py list
# Approve it
python3 code/hitl.py approve <content_id>
```

**Dashboard shows "Offline" in header** — Backend not reachable  
```bash
# Check API is running
docker-compose ps api
docker-compose logs api --tail 20
# Check it's healthy
curl http://localhost:8000/api/health
```
