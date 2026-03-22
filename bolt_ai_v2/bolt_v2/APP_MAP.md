# Bolt AI v2 -- Complete Application Map

A full reference of every file, module, class, function, and data flow in the project.

---

## Table of Contents

1. [High-Level Architecture](#1-high-level-architecture)
2. [Directory Structure](#2-directory-structure)
3. [Section A: Configuration and Secrets](#section-a-configuration-and-secrets)
4. [Section B: Pipeline Orchestration](#section-b-pipeline-orchestration)
5. [Section C: News Aggregation](#section-c-news-aggregation)
6. [Section D: Script Generation](#section-d-script-generation)
7. [Section E: Content Validation](#section-e-content-validation)
8. [Section F: Video Pipeline](#section-f-video-pipeline)
9. [Section G: Publishing](#section-g-publishing)
10. [Section H: Analytics](#section-h-analytics)
11. [Section I: Human-in-the-Loop (HITL)](#section-i-human-in-the-loop-hitl)
12. [Section J: Cost Tracking and Budget Enforcement](#section-j-cost-tracking-and-budget-enforcement)
13. [Section K: Database Layer](#section-k-database-layer)
14. [Section L: Observability](#section-l-observability)
15. [Section M: Notifications](#section-m-notifications)
16. [Section N: Backup System](#section-n-backup-system)
17. [Section N2: HTTP Utilities](#section-n2-http-utilities)
18. [Section O: Job Worker (Retry Queue)](#section-o-job-worker-retry-queue)
19. [Section P: FastAPI Backend](#section-p-fastapi-backend)
20. [Section Q: React Dashboard (Frontend)](#section-q-react-dashboard-frontend)
21. [Section R: DevOps and Deployment](#section-r-devops-and-deployment)
22. [Section S: Tests](#section-s-tests)
23. [Section T: Documentation](#section-t-documentation)
24. [Data Flow Diagram](#data-flow-diagram)
25. [External Dependencies](#external-dependencies)

---

## 1. High-Level Architecture

```
+---------------------------+       +---------------------------+
|     CONTENT PIPELINE      |       |     WEB INTERFACE         |
|  (Python, runs on cron)   |       |  (React + FastAPI)        |
+---------------------------+       +---------------------------+
|                           |       |                           |
|  news_aggregator.py       |       |  api.py (FastAPI :8000)   |
|         |                 |       |         |                 |
|  script_generator.py      |       |  bolt-dashboard/          |
|         |                 |       |    (React/Vite :5173)     |
|  content_validator.py     |       |                           |
|         |                 |       +---------------------------+
|  hitl.py (approval gate)  |              |
|         |                 |              |
|  video_pipeline.py        |       +------+------+
|         |                 |       |  SQLite DB  |
|  platform_publisher.py    |       |  (bolt.db)  |
|         |                 |       +------+------+
|  analytics_tracker.py     |              |
|                           |       +------+------+
+---------------------------+       |  config.json|
        |                           |  .env       |
+-------+-------+                   +-------------+
| job_worker.py |
| (retry queue) |
+---------------+
```

---

## 2. Directory Structure

```
bolt_v2/
|-- .env.example              # Environment variable template (API keys)
|-- .gitignore                # Git ignore rules
|-- APP_MAP.md                # This file
|-- DEPLOY.md                 # Deployment guide
|-- Dockerfile                # Container build instructions
|-- README.md                 # Project overview and quick start
|-- docker-compose.yml        # Multi-service container orchestration
|-- pytest.ini                # Test runner configuration
|-- requirements.txt          # Python dependencies
|
|-- pyproject.toml             # Python project config (ruff, mypy, pytest)
|
|-- code/                     # ===== PYTHON BACKEND =====
|   |-- __init__.py           # Package init (enables clean imports)
|   |-- shared_config.py      # Centralized config loader
|   |-- secrets_manager.py    # .env / env var secret injection
|   |-- config.json           # Application configuration (non-secret)
|   |-- content_automation_master.py  # Main orchestrator + scheduler
|   |-- news_aggregator.py    # RSS fetching + Claude scoring
|   |-- script_generator.py   # Claude script writing + quality gate
|   |-- content_validator.py  # Post-generation content validation
|   |-- video_pipeline.py     # Voice + avatar + assembly pipeline
|   |-- local_tts.py          # Edge TTS wrapper (free voice)
|   |-- platform_publisher.py # YouTube / TikTok / Instagram publishing
|   |-- analytics_tracker.py  # Platform metrics pull
|   |-- hitl.py               # Human-in-the-loop approval system
|   |-- database.py           # SQLite schema + CRUD
|   |-- api.py                # FastAPI web server
|   |-- job_worker.py         # Retry queue worker daemon
|   |-- notifications.py      # Multi-channel notification system
|   |-- observability.py      # Structured logging + rate limiter
|   |-- cost_tracker.py       # API usage cost tracking
|   |-- budget_enforcer.py    # Spending hard stops
|   |-- backup_system.py      # Data backup / restore
|   |-- http_utils.py         # Shared HTTP client with disk caching, retries, rate limiting
|
|-- bolt-dashboard/           # ===== REACT FRONTEND =====
|   |-- src/
|   |   |-- App.tsx           # Router + layout shell
|   |   |-- main.tsx          # Entry point
|   |   |-- index.css         # Global styles
|   |   |-- App.css           # App-level styles
|   |   |-- lib/
|   |   |   |-- api.ts        # API client (all backend calls)
|   |   |   |-- utils.ts      # Utility functions
|   |   |-- components/
|   |   |   |-- Sidebar.tsx   # Navigation sidebar
|   |   |   |-- Header.tsx    # Top bar (SSE status + pipeline trigger)
|   |   |   |-- ErrorBoundary.tsx
|   |   |   |-- ui/           # shadcn/ui component library (40+ components)
|   |   |-- pages/
|   |   |   |-- Dashboard.tsx         # Overview + metrics + chart
|   |   |   |-- ContentManagement.tsx # Script queue + HITL approve/reject
|   |   |   |-- Analytics.tsx         # Platform analytics dashboard
|   |   |   |-- NewsMonitor.tsx       # RSS feed viewer
|   |   |   |-- PlatformManagement.tsx # YouTube/TikTok/Instagram config
|   |   |   |-- CostBackups.tsx       # Cost tracking + backup management
|   |   |   |-- Settings.tsx          # Configuration panel
|   |   |-- hooks/
|   |       |-- use-mobile.tsx
|   |       |-- use-toast.ts
|   |-- public/
|   |   |-- data/             # Static fallback JSON
|   |   |-- images/           # Logo, thumbnails, brand assets
|   |-- package.json, vite.config.ts, tailwind.config.js, tsconfig.json
|
|-- data/                     # ===== RUNTIME DATA =====
|   |-- bolt.db               # SQLite database (created at runtime)
|   |-- queue/                # Pending content packages (JSON)
|   |-- published/            # Published content archive
|   |-- analytics/            # Analytics snapshots + cost tracking
|   |-- backups/              # Compressed backup archives
|   |-- cache/http/           # HTTP response disk cache (managed by http_utils.py)
|
|-- content/                  # ===== GENERATED MEDIA =====
|   |-- audio/                # TTS MP3 files
|   |-- video/                # Avatar + assembled MP4 files
|   |-- thumbnails/           # Generated thumbnail images
|
|-- docs/                     # ===== RESEARCH AND STRATEGY =====
|   |-- character_persona.md
|   |-- voice_characteristics.md
|   |-- content_calendar.md
|   |-- script_templates.md
|   |-- quality_scoring_system.md
|   |-- ai_news_sources.md
|   |-- visual_design_and_brand_guidelines.md
|   |-- market_and_audience_analysis.md
|   |-- optimization_strategies.md
|   |-- research_plan_AI_Robot_Character.md
|   |-- research_plan_Content_Strategy.md
|   |-- final_report.md / .docx / .pdf
|   |-- final_report_content_strategy.md / .docx / .pdf
|
|-- scripts/
|   |-- setup.sh              # One-command project setup
|
|-- tests/                    # ===== TEST SUITE =====
|   |-- conftest.py           # Shared fixtures
|   |-- test_budget_enforcer.py
|   |-- test_database.py
|   |-- test_news_aggregator.py
|   |-- test_quality_gate.py
|
|-- logs/                     # Structured JSON logs (runtime)
```

---

## Section A: Configuration and Secrets

### `code/config.json` -- Application Configuration
Non-secret configuration. All API key fields contain pointers like `"set ANTHROPIC_API_KEY in .env"`.

| Section | Purpose | Key Fields |
|---------|---------|------------|
| `character` | Bolt's personality | `name`, `catchphrases`, `target_duration_seconds`, `max_words_per_script` |
| `apis` | API endpoint configuration | Provider names, model IDs, voice IDs (keys are in .env) |
| `platforms` | YouTube/TikTok/Instagram settings | `enabled`, `post_time`, `timezone` per platform |
| `content_pillars` | Day-of-week content themes | Mon=ai_news, Tue=ai_tools, Wed=ai_concepts, etc. |
| `automation` | Pipeline behavior | `auto_publish_threshold`, `auto_publish_enabled`, `max_retries` |
| `quality_gate` | Script scoring rules | `min_script_words`, `max_script_words`, `min_overall_score`, `banned_words` |
| `hashtags` | Per-pillar hashtag sets | `ai_news`, `ai_tools`, `ai_concepts`, `ai_daily_life` |
| `news_sources` | 17 RSS feeds | URL + reliability score (0.0-1.0) per source |

### `code/shared_config.py` -- Centralized Config Loader
- **`get_config(path?, force_reload?)`** -- Loads `config.json`, injects secrets via `secrets_manager.load_all_secrets()`, caches result
- **`reset_cache()`** -- Clears cache (for tests)
- All modules import config through this single entry point

### `code/secrets_manager.py` -- Secret Injection
- **`_load_dotenv()`** -- Parses `.env` file, injects into `os.environ` (does not override existing vars)
- **`get_secret(key, fallback?)`** -- Returns env var value, treats `YOUR_*` as placeholders
- **`get_secret_required(key)`** -- Raises if key missing
- **`load_all_secrets(config_dict)`** -- Walks config dict, replaces pointer strings with real env var values
- **`print_audit()`** -- CLI report showing which secrets are set/missing

### `.env.example` -- Environment Variable Template
Lists all required/optional env vars grouped by service:
- AI: `ANTHROPIC_API_KEY`
- Voice: `ELEVENLABS_API_KEY`, `GOOGLE_CLOUD_TTS_KEY`
- Avatar: `VIDNOZ_API_KEY`, `DID_API_KEY`
- Publishing: `BUFFER_ACCESS_TOKEN`, `YOUTUBE_CLIENT_*`, `TIKTOK_ACCESS_TOKEN`, `INSTAGRAM_*`
- Notifications: `DISCORD_WEBHOOK_URL`, `TELEGRAM_BOT_TOKEN`, `EMAIL_*`
- App: `BOLT_CORS_ORIGINS`, `BOLT_BASE_PATH`

---

## Section B: Pipeline Orchestration

### `code/content_automation_master.py` -- Master Orchestrator

**Entry point for the entire application.** Runs as CLI tool or 24/7 scheduler daemon.

#### Key Components

| Component | Purpose |
|-----------|---------|
| `CircuitBreaker` | In-memory circuit breaker per service. Opens after N failures, auto-resets after timeout. |
| `step_news()` | Async. Calls `news_aggregator.run()`, saves to DB, sends Discord notification. |
| `step_script()` | Calls `script_generator.run()`, applies quality gate, saves to DB. |
| `step_video()` | Calls `video_pipeline.run()`, tracks costs, saves to DB. |
| `step_publish()` | Calls `platform_publisher.run()`, records results, increments video count. |
| `step_analytics()` | Calls `analytics_tracker.run()`, saves snapshots per platform. |
| `run_full_pipeline()` | Async. Chains all steps: news -> script -> HITL gate -> budget check -> video -> publish -> analytics. |
| `run_scheduler()` | Uses `schedule` library. Full pipeline at 06:00 UTC, news every 6h, analytics at 09:00, backups at 03:00. |
| `main()` | CLI parser with `--step`, `--schedule`, `--backup`, `--cost-summary`, `--db-stats`, etc. |

#### CLI Commands

```
python content_automation_master.py                          # Full pipeline (once)
python content_automation_master.py --step news              # Just news aggregation
python content_automation_master.py --step script            # Just script generation
python content_automation_master.py --step video             # Just video rendering
python content_automation_master.py --step publish           # Just publishing
python content_automation_master.py --step analytics         # Just analytics pull
python content_automation_master.py --schedule               # 24/7 daemon mode
python content_automation_master.py --backup manual          # Create backup (daily|weekly|monthly|manual)
python content_automation_master.py --list-backups           # List all backups
python content_automation_master.py --restore BACKUP_ID      # Restore from a specific backup
python content_automation_master.py --cost-summary           # Show cost report
python content_automation_master.py --db-stats               # Database statistics
python content_automation_master.py --secrets-audit          # Check which secrets are configured
python content_automation_master.py --config path/to/cfg     # Use custom config.json path
```

---

## Section C: News Aggregation

### `code/news_aggregator.py` -- RSS Feed Processor

Fetches 17 RSS feeds concurrently, scores articles, sends top candidates to Claude for editorial ranking.

#### Functions

| Function | Signature | Purpose |
|----------|-----------|---------|
| `clean_html()` | `(raw: str) -> str` | Strip HTML tags and normalize whitespace |
| `article_age_hours()` | `(published_parsed) -> float` | Calculate article age; returns 999 if unknown |
| `timeliness_score()` | `(age_hours: float) -> float` | Score 1.0 (new) to 0.0 (>72h) |
| `deduplicate()` | `(articles, seen_hashes) -> list` | Remove duplicates by MD5 of lowercased title |
| `fetch_feed()` | `async (session, name, info) -> list` | Fetch single RSS feed with 10s timeout |
| `heuristic_score()` | -- | Combine reliability * timeliness * title impact |
| `claude_editorial_score()` | -- | Send top 15 to Claude for 0-10 editorial scoring |
| `run()` | `async () -> list` | Full pipeline: fetch all -> filter -> dedup -> score -> return top 5 |

#### Data Flow

```
17 RSS feeds --[concurrent fetch]--> raw articles
    --> filter by age (<72h) and AI relevance
    --> deduplicate by title hash
    --> heuristic scoring (reliability * timeliness)
    --> top 15 sent to Claude for editorial scoring (0-10)
    --> top 5 written to data/queue/ and returned
```

---

## Section D: Script Generation

### `code/script_generator.py` -- Claude Script Writer

Uses Claude to write 100-130 word scripts in Bolt's voice, with auto-scoring and retry.

#### Constants

| Constant | Purpose |
|----------|---------|
| `BOLT_SYSTEM_PROMPT` | Defines Bolt's personality, voice rules, catchphrases, word limits |
| `SCRIPT_FORMAT` | Template: [HOOK] -> [STORY] -> [IMPACT] -> [CTA] -> [CATCHPHRASE] |
| `PLATFORM_CAPTIONS_PROMPT` | Asks Claude to generate YouTube/TikTok/Instagram captions |
| `QUALITY_SCORING_PROMPT` | Asks Claude to score: hook_strength, simplicity, bolt_voice, pacing, overall_score |

#### Functions

| Function | Purpose |
|----------|---------|
| `get_todays_pillar(config)` | Maps current day-of-week to content pillar (ai_news, ai_tools, etc.) |
| `generate_script(article, pillar, config)` | Sends article + pillar to Claude, returns script text |
| `score_script(script, config)` | Sends script to Claude for quality scoring, returns JSON scores |
| `generate_captions(script, title, pillar, config)` | Generates platform-specific captions with hashtags |
| `run()` | Full flow: pick top article -> generate -> score -> retry if <8.5 -> save package |

#### Quality Gate Logic

```
Score >= 8.5  --> auto_approved = True, status = "approved"
Score >= 6.0  --> auto_approved = False, status = "pending_review" (needs HITL)
Score <  6.0  --> auto_rejected, discarded
```

Up to 3 retry attempts if score < 8.5. Each retry includes Claude's feedback from the previous attempt.

---

## Section E: Content Validation

### `code/content_validator.py` -- Post-Generation Quality Checks

Runs after Claude generates a script, before it enters the approval queue.

#### Class: `ContentValidator`

| Method | Purpose |
|--------|---------|
| `validate(script, article)` | Run all checks, return `ValidationResult` |
| `_check_banned_words()` | Scan for weasel words, misinformation phrases |
| `_check_word_count()` | Enforce 80-135 word range |
| `_check_duplicate()` | Compare against last 5 published scripts by similarity |
| `_check_structure()` | Verify hook, catchphrase, and CTA are present |
| `_check_misinformation()` | Flag phrases like "100% certain", "confirmed that" |
| `_check_repetition()` | TF-IDF similarity against recent scripts |

#### Dataclass: `ValidationResult`

| Field | Type | Purpose |
|-------|------|---------|
| `passed` | `bool` | Overall pass/fail |
| `score` | `float` | 0.0-10.0 combined penalty score |
| `failures` | `list[str]` | Human-readable failure descriptions |
| `warnings` | `list[str]` | Non-blocking issues |
| `checks` | `dict` | Per-check pass/fail detail |

---

## Section F: Video Pipeline

### `code/video_pipeline.py` -- Media Production

Tiered provider architecture: tries free options first, falls back to paid.

#### Voice Synthesis (3 tiers)

| Tier | Provider | Function | Cost |
|------|----------|----------|------|
| 1 | Edge TTS | `synthesize_edge_tts()` | Free, unlimited |
| 2 | Google Cloud TTS | `synthesize_google_tts()` | Free 1M chars/month |
| 3 | ElevenLabs | `synthesize_elevenlabs()` | Free 10K chars/month |

`synthesize_voice()` -- Tries all three in order, returns first success.

#### Avatar Video (3 tiers)

| Tier | Provider | Function | Cost |
|------|----------|----------|------|
| 1 | Vidnoz | `create_vidnoz_video()` | Free, 1900+ avatars |
| 2 | D-ID | `create_did_video()` | Free 20/month |
| 3 | FFmpeg | `create_text_card_video()` | Free, local fallback |

`create_avatar_video()` -- Tries all three in order.

#### Video Assembly

| Function | Purpose |
|----------|---------|
| `assemble_final_video()` | FFmpeg: combine audio + avatar + branding overlays |
| `generate_thumbnail()` | Pillow: create 1080x1920 thumbnail with title text |
| `run()` | Full flow: voice -> avatar -> assembly -> thumbnail -> return package |

### `code/local_tts.py` -- Edge TTS Dedicated Module

| Function | Purpose |
|----------|---------|
| `generate_audio(script, filename, config?)` | Generate MP3 using Edge TTS |
| `generate_with_retries(script, filename, config, max_retries)` | Retry wrapper |
| `list_voices()` | Print all available Edge TTS English voices |
| `preview_voice(voice_name)` | Generate a test clip with a given voice |

Recommended voices: `en-US-GuyNeural` (default), `en-US-ChristopherNeural`, `en-US-EricNeural`, `en-GB-RyanNeural`.

---

## Section G: Publishing

### `code/platform_publisher.py` -- Multi-Platform Publisher

#### Functions

| Function | Purpose |
|----------|---------|
| `notify_discord()` | Send rich Discord embed notification |
| `publish_youtube()` | Direct upload via YouTube Data API v3 (OAuth refresh + multipart upload) |
| `publish_tiktok_buffer()` | Schedule via Buffer API |
| `publish_tiktok_direct()` | Direct TikTok API upload (fallback) |
| `publish_instagram_buffer()` | Schedule via Buffer API |
| `publish_instagram_direct()` | Direct Instagram Graph API upload (fallback) |
| `run()` | Publish to all enabled platforms, move package to `data/published/`, return results |

#### Publishing Flow

```
approved package
    |
    +--> YouTube: OAuth token refresh -> download video -> multipart upload
    |
    +--> TikTok: Buffer API schedule (fallback: direct upload)
    |
    +--> Instagram: Buffer API schedule (fallback: Graph API)
    |
    +--> Move package to data/published/
    +--> Send Discord summary
```

---

## Section H: Analytics

### `code/analytics_tracker.py` -- Platform Metrics Collector

#### Functions

| Function | Purpose |
|----------|---------|
| `fetch_youtube_analytics()` | YouTube Data API: subscribers, views, likes, comments for last 30 videos |
| `fetch_tiktok_analytics()` | TikTok API: followers, likes, views, engagement rate |
| `fetch_instagram_analytics()` | Instagram Graph API: followers, impressions, reach |
| `calculate_engagement_rate()` | (likes + comments) / views * 100 |
| `calculate_growth_trends()` | Compare current vs previous period |
| `run()` | Fetch all platforms, calculate summary, write to `data/analytics/analytics.json` and dashboard static files |

#### Output Format

```json
{
  "platforms": {
    "youtube": { "subscribers": N, "total_channel_views": N, ... },
    "tiktok": { "followers": N, "likes": N, ... },
    "instagram": { "followers": N, "impressions": N, ... }
  },
  "summary": {
    "total_views_30d": N,
    "total_followers": N,
    "videos_published": N,
    "engagement_rate": N
  },
  "weekly_views": [ { "day": "Mon", "youtube": N, "tiktok": N, "instagram": N }, ... ]
}
```

---

## Section I: Human-in-the-Loop (HITL)

### `code/hitl.py` -- Approval Gate

Scripts that don't auto-approve (score < 9.0 but >= 6.0) enter the HITL queue.

#### Core Functions

| Function | Purpose |
|----------|---------|
| `wait_for_approval(script_id, timeout_hours, config, notifier)` | Async. Polls every 60s for flag files. Returns True (approved) or False (rejected/timeout). |
| `approve_from_dashboard(script_id)` | Creates `_APPROVED.flag` file + updates DB status |
| `reject_from_dashboard(script_id, reason?)` | Creates `_REJECTED.flag` file + updates DB status |
| `list_pending()` | Returns all scripts with `pending_review` status |

#### Approval Methods

1. **CLI**: `python hitl.py approve bolt_20260321_063000`
2. **Flag file**: `touch data/queue/bolt_20260321_063000_APPROVED.flag`
3. **Dashboard**: Click Approve/Reject in Content Queue page (calls API)

#### Timeout Behavior

Default 12 hours. After timeout:
- Script auto-rejected
- Notification sent explaining why
- Pipeline continues without this script

---

## Section J: Cost Tracking and Budget Enforcement

### `code/cost_tracker.py` -- Usage Tracking

#### Class: `CostTracker`

| Method | Purpose |
|--------|---------|
| `record_usage(service, operation, quantity, model?)` | Log an API call with calculated cost |
| `_calculate_cost()` | Look up price from config pricing table |
| `get_monthly_summary()` | Total cost, video count, per-service breakdown for current month |
| `get_daily_summary()` | Same for today |
| `get_total_summary()` | Lifetime totals |
| `get_current_video_cost()` | Cost accumulated for the video currently being processed |
| `increment_video_count()` | Called after successful publish |

Data stored in `data/analytics/cost_tracking.json`.

### `code/budget_enforcer.py` -- Spending Hard Stops

#### Class: `BudgetEnforcer`

| Method | Purpose |
|--------|---------|
| `check_or_raise(step)` | Check all limits. Raises `BudgetExceededError` if over hard stop. |
| `_check_monthly()` | Compare monthly spend vs `monthly_budget_hard_stop` (default $20) |
| `_check_daily()` | Compare daily spend vs `daily_budget_hard_stop` (default $5) |
| `_check_per_video()` | Compare current video cost vs `per_video_budget_hard_stop` (default $1) |

#### Class: `BudgetExceededError`

| Attribute | Type | Purpose |
|-----------|------|---------|
| `limit_type` | `str` | "monthly" / "daily" / "per_video" |
| `spent` | `float` | Amount actually spent |
| `limit` | `float` | The configured limit |

#### Default Limits

| Limit | Soft Alert | Hard Stop |
|-------|------------|-----------|
| Monthly | $10 | $20 |
| Daily | $3 | $5 |
| Per Video | $0.50 | $1.00 |

---

## Section K: Database Layer

### `code/database.py` -- SQLite Backend

WAL mode enabled, foreign keys enforced.

#### Tables

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `articles` | Fetched news articles | `source`, `title`, `claude_score`, `heuristic_score`, `status` |
| `scripts` | Generated scripts | `content_id` (unique), `script`, `overall_score`, `status`, `auto_approved` |
| `videos` | Video pipeline output | `content_id` (FK), `audio_path`, `avatar_path`, `final_path`, `video_ready` |
| `publications` | Per-platform publish results | `content_id`, `platform`, `success`, `url`, `error` |
| `analytics_snapshots` | Daily metric snapshots | `platform`, `fetched_at`, `followers`, `views_30d`, `engagement_rate`, `raw_json` |
| `cost_events` | Individual API cost events | `service`, `operation`, `cost`, `timestamp` |
| `jobs` | Retry queue | `job_type`, `content_id`, `status`, `attempts`, `max_attempts` |

#### Class: `BoltDB`

| Method Group | Methods |
|-------------|---------|
| Articles | `save_article()`, `save_articles()`, `get_recent_articles()`, `get_top_article()`, `mark_article_used()` |
| Scripts | `save_script()`, `get_scripts()`, `get_script_by_content_id()`, `get_pending_script()`, `approve_script()`, `reject_script()` |
| Videos | `save_video()` |
| Publications | `save_publication()`, `save_publish_results()` |
| Analytics | `save_analytics_snapshot()`, `get_latest_analytics()` |
| Costs | `record_cost()`, `get_cost_summary()` |
| Jobs | `enqueue_job()`, `get_pending_jobs()`, `fail_job()`, `complete_job()` |
| Dashboard | `get_dashboard_summary()` |

#### Singleton: `get_db()`
Returns a single `BoltDB` instance, creates the database and runs schema if it doesn't exist.

---

## Section L: Observability

### `code/observability.py` -- Logging + Rate Limiting

#### Structured Logging

| Class | Purpose |
|-------|---------|
| `JSONFormatter` | Formats log records as single-line JSON objects |
| `HumanFormatter` | Readable console output with level icons |

`init(config, log_dir, log_level)` -- Sets up dual-handler logging: JSON to file, human-readable to console.

`get_logger(name)` -- Returns a named logger instance.

#### API Rate Limiter (Token Bucket)

| Class | Purpose |
|-------|---------|
| `TokenBucket` | Per-service token bucket with configurable rate |
| `RateLimiter` | Manages buckets for all services |

`get_rate_limiter(config)` -- Creates limiter from config.

`await rate_limiter.acquire("claude")` -- Blocks until a token is available.

Default rates:
- Claude: 50 req/min
- ElevenLabs: 20 req/min
- Edge TTS: 200 req/min
- Vidnoz/D-ID: 10 req/min
- YouTube: 50 req/min
- Buffer: 20 req/min

---

## Section M: Notifications

### `code/notifications.py` -- Multi-Channel Alerts

#### Class: `NotificationLevel` (Enum)
`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`

#### Dataclass: `Notification`
`title`, `message`, `level`, `channel`, `metadata`

#### Class: `NotificationManager`

| Method | Purpose |
|--------|---------|
| `send(notification)` | Route to all enabled channels |
| `_send_discord()` | Rich embed via webhook |
| `_send_email()` | SMTP with HTML template |
| `_send_telegram()` | Telegram Bot API message |
| `_send_console()` | Formatted log output |

Channels auto-detected from config: Discord (webhook URL), Email (SMTP config), Telegram (bot token), Console (always on).

---

## Section N: Backup System

### `code/backup_system.py` -- Data Protection

#### Class: `BackupSystem`

| Method | Purpose |
|--------|---------|
| `create_backup(backup_type)` | Compress data dirs + config into timestamped gzip archive |
| `restore_backup(backup_id)` | Extract archive back to data directories |
| `list_backups()` | Return all backups with size, type, timestamp |
| `_rotate_backups()` | Enforce retention: 7 daily, 4 weekly, 12 monthly |

Backs up: `data/queue/`, `data/published/`, `data/analytics/`, `content/*`, `logs/`, `code/config.json`.

---

## Section N2: HTTP Utilities

### `code/http_utils.py` -- Shared HTTP Client

Centralized HTTP layer with disk caching, exponential-backoff retries, and per-host rate limiting. All outbound HTTP requests in the pipeline should route through this module for consistent behavior.

#### Classes

| Class | Purpose |
|-------|---------|
| `HTTPError` | Raised when a request fails after all retries. Attributes: `url`, `status_code`, `detail` |

#### Functions

| Function | Signature | Purpose |
|----------|-----------|---------|
| `cached_get()` | `(url, params?, headers?, cache_ttl_hours=1.0, max_retries=3, backoff_factor=2.0, timeout=15, cache_dir?)` | HTTP GET with disk caching and exponential-backoff retries |
| `cached_post()` | `(url, json_data?, data?, headers?, max_retries=3, backoff_factor=2.0, timeout=30)` | HTTP POST with retries (no caching) |
| `async_cached_get()` | `async (session, url, cache_ttl_hours=1.0, timeout_s=10, cache_dir?)` | Async HTTP GET using aiohttp with disk caching (for `news_aggregator`) |
| `get_request_log()` | `() -> list[dict]` | Return audit log of all HTTP requests made during the process |
| `clear_request_log()` | `()` | Clear the request audit log |

#### Internal Helpers

| Function | Purpose |
|----------|---------|
| `_cache_key()` | SHA-256 hash of URL + sorted params for deterministic cache keys |
| `_cache_path()` | Map cache key to file path in `data/cache/http/` |
| `_read_cache()` | Return cached response if fresh (within TTL), else None |
| `_write_cache()` | Persist JSON-serializable response to disk |
| `_extract_host()` | Parse hostname from URL for per-host rate limiting |
| `_rate_limit_wait()` | Sleep if needed to respect per-host minimum intervals |

#### Per-Host Rate Limits

Configured per hostname. Defaults to 0.5s between requests for unknown hosts. Examples:
- RSS feeds (openai.com, anthropic.com, etc.): 0.5--1.0s
- Anthropic API: 0.1s (50 req/min)
- ElevenLabs API: 3.0s (20 req/min)
- YouTube/Google APIs: 0.2--0.5s

#### Retry Behavior

- Retryable status codes: 429, 500, 502, 503, 504
- 429 responses honor the `Retry-After` header
- Exponential backoff: attempt 0 = immediate, attempt 1 = 2s, attempt 2 = 4s
- Connection errors and timeouts also trigger retries

---

## Section O: Job Worker (Retry Queue)

### `code/job_worker.py` -- Background Retry Processor

Polls the SQLite `jobs` table every 60 seconds. Processes failed pipeline steps.

#### States

```
pending --> running --> done
                   \-> retrying --> running (again)
                               \-> dead (max_attempts exceeded)
```

#### Functions

| Function | Purpose |
|----------|---------|
| `run_job(job, config)` | Execute a single job by type (news/script/video/publish) |
| `process_queue(config)` | Fetch pending/retrying jobs, run up to 2 concurrently |
| `main_loop()` | Infinite poll loop (60s interval) |

Exponential backoff: attempt 1 = immediate, attempt 2 = 2 min, attempt 3 = 8 min.

Max concurrent jobs: 2 (to respect API rate limits).

---

## Section P: FastAPI Backend

### `code/api.py` -- Web API Server

Runs on port 8000. Serves the React dashboard and all API endpoints.

#### Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/health` | Health check (for monitoring/Docker) |
| `GET` | `/api/status` | Pipeline health + system status |
| `GET` | `/api/analytics` | Platform metrics from DB |
| `GET` | `/api/scripts` | Content queue (all scripts, optional `?status=` filter) |
| `GET` | `/api/scripts/{id}` | Single script detail |
| `POST` | `/api/hitl/approve/{id}` | Approve a script |
| `POST` | `/api/hitl/reject/{id}` | Reject a script |
| `GET` | `/api/hitl/pending` | List scripts awaiting review |
| `POST` | `/api/pipeline/run` | Trigger full pipeline run (background task) |
| `POST` | `/api/pipeline/{step}` | Trigger specific step |
| `GET` | `/api/pipeline/status` | Current pipeline state |
| `GET` | `/api/costs` | Cost summary (optional `?month=` filter) |
| `GET` | `/api/backups` | List available backups |
| `POST` | `/api/backups` | Create manual backup |
| `POST` | `/api/backups/{id}/restore` | Restore from backup |
| `GET` | `/api/news` | Recent articles in DB |
| `GET` | `/api/jobs` | Job queue status |
| `GET` | `/api/stream/status` | SSE endpoint for real-time pipeline status (emits JSON every 5s) |

#### Static File Serving
If `bolt-dashboard/dist/` exists (built frontend), serves it at `/` with `/assets`, `/images`, `/data` mounts.

#### CORS
Configurable via `BOLT_CORS_ORIGINS` env var (comma-separated). Defaults to localhost dev ports.

---

## Section Q: React Dashboard (Frontend)

### Stack
- React 18 + TypeScript
- Vite (build tool)
- Tailwind CSS + shadcn/ui components
- React Router (client-side routing)
- TanStack React Query (data fetching with 30s auto-refresh)
- Recharts (charts)
- Lucide React (icons)

### `src/App.tsx` -- Router Layout

```
<QueryClientProvider>
  <Router>
    <Sidebar />
    <Header />
    <Routes>
      /          --> Dashboard
      /content   --> ContentManagement
      /analytics --> Analytics
      /news      --> NewsMonitor
      /platforms --> PlatformManagement
      /costs     --> CostBackups
      /settings  --> Settings
    </Routes>
  </Router>
</QueryClientProvider>
```

### Pages

| Page | Route | Description |
|------|-------|-------------|
| `Dashboard.tsx` | `/` | Overview: metric cards, weekly views chart, pipeline status, platform breakdown |
| `ContentManagement.tsx` | `/content` | Script queue with HITL approve/reject buttons, script preview, quality scores |
| `Analytics.tsx` | `/analytics` | Platform-level charts: views, engagement, growth trends |
| `NewsMonitor.tsx` | `/news` | RSS feed viewer with Claude scores, source reliability |
| `PlatformManagement.tsx` | `/platforms` | YouTube/TikTok/Instagram config, posting schedule, connection status |
| `CostBackups.tsx` | `/costs` | Monthly cost breakdown by service, backup list with restore buttons |
| `Settings.tsx` | `/settings` | Config editor, API key status, automation toggles (**local-only -- no backend save endpoint yet**) |

### `src/lib/api.ts` -- API Client

All backend calls in one object:

```typescript
api.health()                    // GET /api/health
api.status()                    // GET /api/status
api.analytics()                 // GET /api/analytics
api.scripts(status?)            // GET /api/scripts
api.script(id)                  // GET /api/scripts/{id}
api.approve(id)                 // POST /api/hitl/approve/{id}
api.reject(id, reason?)         // POST /api/hitl/reject/{id}
api.pending()                   // GET /api/hitl/pending
api.runPipeline()               // POST /api/pipeline/run
api.runStep(step)               // POST /api/pipeline/{step}
api.pipelineStatus()            // GET /api/pipeline/status
api.costs(month?)               // GET /api/costs
api.backups()                   // GET /api/backups
api.createBackup(type?)         // POST /api/backups
api.restoreBackup(id)           // POST /api/backups/{id}/restore
api.news()                      // GET /api/news
api.jobs()                      // GET /api/jobs
```

### `src/components/Header.tsx` -- Real-Time Status
Connects to SSE endpoint (`/api/stream/status`) for live pipeline state, pending review count, failed job count, and monthly cost.

### `src/components/Sidebar.tsx` -- Navigation
7 nav items with icons. Shows "Pipeline Active" status indicator at bottom.

---

## Section R: DevOps and Deployment

### `Dockerfile` -- Container Image
- Base: `python:3.11-slim`
- System deps: `ffmpeg`, `curl`, `git`
- Installs Python deps + NLTK data
- Exposes port 8000
- Default CMD: `uvicorn code.api:app`

### `docker-compose.yml` -- Multi-Service Setup

| Service | Container | Command | Port |
|---------|-----------|---------|------|
| `api` | bolt-api | `uvicorn code.api:app --reload` | 8000 |
| `pipeline` | bolt-pipeline | `python3 code/content_automation_master.py --schedule` | -- |
| `worker` | bolt-worker | `python3 code/job_worker.py` | -- |
| `dashboard` (dev profile) | bolt-dashboard | `pnpm dev` | 5173 |

Shared volumes: `bolt_data`, `bolt_content`, `bolt_logs`, `bolt_backups`.

### `scripts/setup.sh` -- One-Command Setup
Creates directories, installs Python deps, copies `.env.example`, downloads NLTK data.

---

## Section S: Tests

### `pytest.ini`
```ini
testpaths = tests
pythonpath = code
```

### Test Files

| File | Coverage |
|------|----------|
| `conftest.py` | Shared fixtures: `sample_config`, `sample_config_file`, `temp_db`, `sample_article`, `sample_script` |
| `test_budget_enforcer.py` | Default limits, config overrides, monthly/daily hard stop raises, under-budget passes |
| `test_news_aggregator.py` | `clean_html()`, `article_age_hours()`, `timeliness_score()`, `deduplicate()` |
| `test_database.py` | Article CRUD, script CRUD, job queue enqueue/fetch |
| `test_quality_gate.py` | Auto-approve threshold, auto-reject threshold, review range, word count, banned words |

---

## Section T: Documentation

| File | Content |
|------|---------|
| `docs/character_persona.md` | Bolt's personality, backstory, mannerisms |
| `docs/voice_characteristics.md` | Speaking style, pace, tone guidelines |
| `docs/content_calendar.md` | Weekly content pillar schedule |
| `docs/script_templates.md` | Script structure templates per pillar |
| `docs/quality_scoring_system.md` | Detailed scoring criteria and thresholds |
| `docs/ai_news_sources.md` | RSS feed list with reliability ratings |
| `docs/visual_design_and_brand_guidelines.md` | Colors, fonts, thumbnail templates |
| `docs/market_and_audience_analysis.md` | Target audience research |
| `docs/optimization_strategies.md` | Growth and engagement strategies |
| `docs/research_plan_AI_Robot_Character.md` | Character design research |
| `docs/research_plan_Content_Strategy.md` | Content strategy research |
| `docs/final_report.md` | Comprehensive project report |
| `docs/final_report_content_strategy.md` | Content strategy deep dive |

---

## Data Flow Diagram

```
                                    CONFIG
                                  .env + config.json
                                      |
                                shared_config.py
                                      |
            +-------------------------+-------------------------+
            |                         |                         |
     PIPELINE FLOW              API SERVER              JOB WORKER
            |                    (api.py)             (job_worker.py)
            |                         |                    |
    +-------+-------+          +------+------+       retry failed
    |               |          |             |       pipeline steps
    v               |          v             v
news_aggregator     |    React Dashboard   SQLite DB
    |               |     (bolt-dashboard)   (bolt.db)
    | RSS feeds     |          |
    | Claude score  |          | /api/*
    v               |          |
script_generator    |          +-- Dashboard.tsx     (overview)
    |               |          +-- ContentManagement (HITL)
    | Claude write  |          +-- Analytics.tsx     (charts)
    | quality gate  |          +-- NewsMonitor.tsx   (feeds)
    v               |          +-- PlatformManagement
content_validator   |          +-- CostBackups.tsx
    |               |          +-- Settings.tsx
    | banned words  |
    | structure     |
    v               |
  hitl.py           |
    |               |
    | approve?      |
    v               |
video_pipeline -----+
    |
    | Edge TTS -> Vidnoz -> FFmpeg
    v
platform_publisher
    |
    | YouTube API / Buffer / Instagram
    v
analytics_tracker
    |
    | Pull real metrics
    v
  [done]
```

---

## External Dependencies

### Python (requirements.txt)

| Package | Purpose | Free Tier |
|---------|---------|-----------|
| `anthropic` | Claude AI API | $5 credit |
| `aiohttp` | Async HTTP | Open source |
| `feedparser` | RSS parsing | Open source |
| `edge-tts` | Microsoft Edge TTS | Unlimited free |
| `Pillow` | Image generation | Open source |
| `nltk` | NLP tokenization | Open source |
| `scikit-learn` | TF-IDF similarity | Open source |
| `fastapi` | Web framework | Open source |
| `uvicorn` | ASGI server | Open source |
| `schedule` | Cron scheduler | Open source |
| `python-dotenv` | .env loading | Open source |
| `beautifulsoup4` | HTML parsing | Open source |
| `python-json-logger` | JSON logging | Open source |
| `sse-starlette` | Server-Sent Events | Open source |
| `requests-toolbelt` | Multipart uploads | Open source |

### System
- FFmpeg (video assembly)
- Python 3.11+
- Node.js 18+ (dashboard)
- pnpm (dashboard package manager)

### External APIs

| API | Used By | Free Tier |
|-----|---------|-----------|
| Anthropic Claude | news_aggregator, script_generator | $5 credit |
| Edge TTS | local_tts, video_pipeline | Unlimited |
| Google Cloud TTS | video_pipeline | 1M chars/month |
| ElevenLabs | video_pipeline | 10K chars/month |
| Vidnoz | video_pipeline | Free, 1900+ avatars |
| D-ID | video_pipeline | 20 videos/month |
| YouTube Data API v3 | platform_publisher, analytics_tracker | Free |
| TikTok API | platform_publisher, analytics_tracker | Free |
| Instagram Graph API | platform_publisher, analytics_tracker | Free |
| Buffer API | platform_publisher | Free (3 channels) |
| Discord Webhooks | notifications | Free |
| Telegram Bot API | notifications | Free |
