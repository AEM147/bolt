# ⚡ Bolt AI Content Creator v2

**Fully automated AI-powered robot content creator** for YouTube Shorts, TikTok, and Instagram Reels.

Built from scratch with modern Python, real API integrations, and an intelligent quality gate powered by Claude.

---

## What's New in v2

| Feature | v1 (old) | v2 (this) |
|---|---|---|
| Script generation | Template-based | Claude AI — adapts per story |
| News scoring | Heuristic only | Claude editorially ranks stories |
| Voice synthesis | Placeholder | ElevenLabs + Google TTS fallback |
| Avatar video | Placeholder | HeyGen real API |
| Video branding | Placeholder | Creatomate templated render |
| Publishing | Placeholder | Buffer + direct YouTube/Instagram APIs |
| Analytics | Mock data | Real platform API data → live dashboard |
| Quality gate | None | Auto-retry with Claude scoring (8.5/10 threshold) |
| Notifications | None | Discord webhook at every step |
| Scheduler | Basic | Full daemon with PM2 or Docker |
| Setup | Manual | One-command `setup.sh` |

---

## Architecture

```
NEWS SOURCES (17 RSS feeds)
        ↓  every 6h
news_aggregator.py   ←→  Claude AI scoring
        ↓  top 5 stories to queue
script_generator.py  ←→  Claude writes Bolt script
        ↓  quality gate (8.5/10, auto-retry x3)
video_pipeline.py    →  ElevenLabs voice → HeyGen avatar → Creatomate render
        ↓  final MP4
platform_publisher.py →  YouTube (direct API) + TikTok & Instagram (Buffer)
        ↓  published
analytics_tracker.py  →  Pull real metrics → update dashboard JSON
        ↓
Bolt Dashboard (bolt-dashboard/)  — live data, real stats
```

---

## Quick Start

### Option A — Local (recommended for testing)

```bash
# 1. Clone / unzip this project
cd bolt_v2

# 2. One-command setup
chmod +x scripts/setup.sh && ./scripts/setup.sh

# 3. Add your API keys
nano code/config.json   # Replace all YOUR_* values

# 4. Test each step manually
python3 code/content_automation_master.py --step news
python3 code/content_automation_master.py --step script
python3 code/content_automation_master.py --step video
python3 code/content_automation_master.py --step publish

# 5. Run full pipeline once
python3 code/content_automation_master.py

# 6. Start the 24/7 scheduler
python3 code/content_automation_master.py --schedule
```

### Option B — Docker (recommended for production)

```bash
# 1. Build
docker build -t bolt-ai .

# 2. Create config with your API keys on host
cp code/config.json ./config.json
nano ./config.json

# 3. Run
docker run -d \
  --name bolt-ai \
  --restart unless-stopped \
  -v $(pwd)/config.json:/app/code/config.json \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/content:/app/content \
  -v $(pwd)/logs:/app/logs \
  bolt-ai
```

### Option C — DigitalOcean VPS ($6/month)

```bash
# On your droplet (Ubuntu 22.04)
git clone https://github.com/yourusername/bolt-ai.git
cd bolt-ai/bolt_v2
chmod +x scripts/setup.sh && ./scripts/setup.sh
nano code/config.json
python3 code/content_automation_master.py --schedule &
```

---

## API Keys Required

### Minimum (for script generation + news)
| Service | Free tier | Link |
|---|---|---|
| Anthropic (Claude) | $5 credit | console.anthropic.com |
| ElevenLabs (voice) | 10K chars/month | elevenlabs.io |

### For full automation
| Service | Cost | Link |
|---|---|---|
| HeyGen (avatar) | Free trial | heygen.com |
| Buffer (scheduling) | Free (3 channels) | buffer.com |
| Google Cloud TTS | 1M chars/month free | cloud.google.com |
| YouTube Data API v3 | Free | console.cloud.google.com |

### Optional but recommended
| Service | Cost | Link |
|---|---|---|
| Creatomate (branding) | Free trial | creatomate.com |
| Discord webhook | Free | discord.com |

---

## Pipeline Steps Explained

### `--step news` — News Aggregation
- Concurrently fetches 17 RSS feeds
- Filters for AI-relevant content published in the last 72 hours
- Deduplicates by title hash
- Scores with heuristics (reliability × timeliness × title impact)
- Sends top 15 candidates to Claude for editorial scoring (0–10)
- Writes top 5 stories to `data/queue/`

### `--step script` — Script Generation
- Reads #1 story from queue
- Detects today's content pillar (News/Tools/Concepts/Life by day of week)
- Asks Claude to write a 100–130 word Bolt script with hook, story, impact, CTA
- Auto-scores with Claude (hook strength, simplicity, Bolt voice, pacing)
- **Auto-retries up to 3 times** if score < 8.5/10
- Generates platform-specific captions for YouTube, TikTok, Instagram
- Saves complete package to queue with status `approved` or `pending_review`

### `--step video` — Video Production
1. **ElevenLabs API** — converts script to MP3 with Bolt's configured voice
2. **Google Cloud TTS** — auto-fallback if ElevenLabs quota is exceeded
3. **HeyGen API** — generates Bolt avatar talking video (9:16 vertical)
4. **Creatomate** — overlays branding (lower third, logo, captions, outro)
5. Saves final video URL and updates queue package

### `--step publish` — Publishing
- **YouTube** — direct upload via YouTube Data API v3 (Shorts-optimised metadata)
- **TikTok** — scheduled via Buffer API
- **Instagram** — scheduled via Buffer API (falls back to direct Graph API)
- Moves published package to `data/published/`
- Sends Discord summary

### `--step analytics` — Analytics Pull
- Fetches real metrics from all three platform APIs
- Calculates engagement rates, growth trends
- Updates `data/analytics/analytics.json`
- Writes to `bolt-dashboard/public/data/analytics.json` (live dashboard feed)

---

## Schedule

| Time (UTC) | Action |
|---|---|
| 00:00, 06:00, 12:00, 18:00 | News aggregation (queue refresh) |
| 06:00 | Full pipeline (news → script → video → publish) |
| 09:00 | Analytics pull |
| 12:00 (local) | Instagram post goes live (scheduled via Buffer) |
| 14:00 (local) | YouTube Short goes live |
| 19:00 (local) | TikTok video goes live |

---

## Quality Gate

Scripts are automatically scored by Claude on 5 criteria:
- **Hook strength** (0–10) — does it grab in 3 seconds?
- **Simplicity** (0–10) — understandable to a general audience?
- **Bolt voice** (0–10) — sounds like Bolt's robot personality?
- **Pacing** (0–10) — easy to deliver in 45 seconds?
- **Word count** — must be 100–130 words

**If overall score < 8.5**: Claude is asked to regenerate with specific feedback. Up to 3 attempts.  
**If all attempts fail**: Video is queued for human review in the dashboard.  
**Auto-publish**: Disabled by default. Enable in `config.json` → `automation.auto_publish_enabled: true`

---

## Dashboard

The Bolt dashboard at `bolt-dashboard/` now reads from `bolt-dashboard/public/data/analytics.json` which the analytics tracker updates daily with **real platform data**.

Access: `https://your-deploy-url.com`  
Refresh: Data updates daily at 09:00 UTC

---

## Troubleshooting

**"No articles in queue"** — Run `--step news` first. Check your internet connection and RSS feed URLs.

**"Voice synthesis failed"** — Check ElevenLabs API key and your monthly character quota. Enable Google TTS as fallback in config.

**"HeyGen unavailable"** — The pipeline continues without avatar video. Publishing will use audio + static thumbnail.

**"Publishing failed"** — Check your OAuth tokens (YouTube refresh token expires periodically). Re-authenticate and update config.

**Dashboard showing old data** — Run `--step analytics` to force a refresh.

---

## File Structure

```
bolt_v2/
├── code/
│   ├── config.json                   # All settings and API keys
│   ├── content_automation_master.py  # ← Main orchestrator (run this)
│   ├── news_aggregator.py            # RSS → Claude scoring → queue
│   ├── script_generator.py           # Claude script writing + scoring
│   ├── video_pipeline.py             # ElevenLabs + HeyGen + Creatomate
│   ├── platform_publisher.py         # YouTube + Buffer (TikTok/Instagram)
│   └── analytics_tracker.py         # Real platform metrics → dashboard
├── scripts/
│   └── setup.sh                      # One-command installer
├── data/
│   ├── queue/                        # Articles and scripts in progress
│   ├── published/                    # Completed content records
│   └── analytics/                    # Analytics snapshots
├── content/
│   ├── audio/                        # Generated MP3 files
│   ├── video/                        # Generated MP4 files
│   └── thumbnails/                   # Generated thumbnail images
├── logs/                             # Daily rotating log files
├── assets/                           # Brand assets (logo, templates)
├── Dockerfile                        # Docker deployment
└── requirements.txt                  # Python dependencies
```

---

*Bolt AI Content Creator v2 — Built for creators who want to scale without burning out.*  
*⚡ Let's get wired!*
