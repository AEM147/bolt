# Pre-Plan vs App Map: Gap Analysis

Comparison of the [pre-plan](../bolt_preplan.md) requirements against what's actually implemented per the [APP_MAP.md](../bolt_ai_v2/bolt_v2/APP_MAP.md).

---

## 1. Content Theory (Sections 1-6 of Pre-Plan)

These are editorial/strategy guidelines, not code features. The question is: are they encoded in the system?

| Pre-Plan Requirement | Implemented? | Where | Notes |
|---------------------|-------------|-------|-------|
| 5 attention triggers (specificity shock, threat, contradiction, free value, social proof) | Partial | `script_generator.py` BOLT_SYSTEM_PROMPT | The system prompt tells Claude to hook in first 3 seconds, but doesn't explicitly enumerate the 5 triggers |
| 3 hook formulas (consequence, violation, implicit threat) | Not explicit | -- | Not codified as templates or scoring criteria |
| 45-second structure (0-3s hook, 3-8s stakes, 8-30s payload, 30-40s punchline, 40-45s CTA) | Partial | `script_generator.py` SCRIPT_FORMAT | Uses [HOOK][STORY][IMPACT][CTA][CATCHPHRASE] -- close but not the exact 5-segment timing from pre-plan |
| 110 word target | Yes | `config.json` quality_gate | `max_words_per_script: 130`, `min_script_words: 80`. Pre-plan says 110 target; config allows 80-135 range |
| Retention benchmarks (70% at 30s) | No | -- | No analytics threshold checking against the 70% target |
| Visual cuts (1 per 3-4 seconds) | No | -- | No B-roll cut timing in video_pipeline |
| Forbidden list (greetings, logo intros, hedged openings, multiple CTAs, undefined jargon, verbatim text, >3 facts, vague sourcing) | Partial | `content_validator.py`, `quality_gate` | `banned_words` list exists but only has "allegedly", "reportedly". The full forbidden list from pre-plan is not encoded |
| Character rules (one emotional register, slight robot humor, sides with audience, consistent catchphrase) | Yes | `script_generator.py` BOLT_SYSTEM_PROMPT, `config.json` character | Catchphrases, personality, voice rules are all in the system prompt |
| Body language (eyes on camera, hands visible, forward lean, never static, open posture) | No | -- | No avatar configuration parameters in video_pipeline for these |
| Topic make/skip decision criteria | No | -- | No automated topic filtering based on the make/skip rules |
| Content pillar schedule (Mon=news, Tue=tools, etc.) | Yes | `config.json` content_pillars | Matches pre-plan exactly |
| Niche decision / pivot plan | No | -- | No analytics-driven pivot logic |

---

## 2. Generation Stack (Section 7 of Pre-Plan)

| Pre-Plan Component | Implemented? | Where | Gap |
|-------------------|-------------|-------|-----|
| Claude for script generation | Yes | `script_generator.py` | Matches |
| Multi-key API pool for Claude | Partial | `llm_pool.py` | Module exists but pre-plan describes comma-separated keys in .env with auto-rotation on credit exhaustion |
| Edge-TTS (primary voice, free) | Yes | `local_tts.py`, `video_pipeline.py` | en-US-GuyNeural, rate/pitch/volume settings |
| Google Cloud TTS (fallback) | Yes | `video_pipeline.py` | Tier 2 fallback |
| ElevenLabs (paid upgrade) | Yes | `video_pipeline.py` | Tier 3 fallback |
| Vidnoz (primary avatar, free) | Yes | `video_pipeline.py` | Tier 1 |
| D-ID (fallback avatar) | Yes | `video_pipeline.py` | Tier 2 |
| HeyGen (paid upgrade avatar) | No | -- | Pre-plan mentions HeyGen at $29/month as the paid upgrade, not implemented |
| Kling AI for B-roll | No | -- | Pre-plan specifies Kling AI for background clips, no implementation |
| FFmpeg assembly | Yes | `video_pipeline.py` | 1080x1920, logo, lower third, captions |
| Pillow thumbnails (3 templates: 16:9, 9:16) | Partial | `video_pipeline.py` | Thumbnail generation exists but pre-plan specifies 3 templates (YouTube 16:9, TikTok 9:16, Instagram 9:16) |
| Buffer for scheduling (free, 3 channels) | Yes | `platform_publisher.py` | Buffer API integration present |

---

## 3. Pipeline Architecture (Section 8 of Pre-Plan)

| Pre-Plan Requirement | Implemented? | Where | Gap |
|---------------------|-------------|-------|-----|
| Article -> Script -> Video -> Publication flow | Yes | `content_automation_master.py` | Matches |
| Article states: fetched -> scored -> queued -> used/skipped | Partial | `database.py` articles table | Status field only has `pending`, `used`, `skipped`. Missing `fetched`, `scored`, `queued` |
| Script states: generating -> draft -> pending_review -> approved/rejected -> published | Partial | `database.py` scripts table | Has `pending_review`, `approved`, `rejected`, `published`. Missing `generating`, `draft` |
| Video states: pending -> audio_ready -> avatar_ready -> assembled/failed | Partial | `database.py` videos table | Has `pending`, `assembled`, `failed`. Missing `audio_ready`, `avatar_ready` intermediate states |
| Publication states: scheduled -> posted/failed -> retrying/dead | Partial | `database.py` publications table | Has `success`/`error_msg` but not the full state machine |
| Job states: pending -> running -> done/failed -> retrying/dead | Yes | `database.py` jobs table | Matches well |
| Modules communicate only through DB | Yes | Architecture | Modules read/write DB, no direct imports between pipeline modules |
| HITL gate between script and video | Yes | `hitl.py` | Flag file + dashboard + CLI approval |
| Two separate processes (script gen + video/publish) | Yes | `docker-compose.yml` | Pipeline scheduler + job worker as separate services |
| Scheduled run at 06:00 UTC | Yes | `content_automation_master.py` | Schedule library config |
| News fetch every 6h | Yes | `content_automation_master.py` | Configured |
| Claude scores each article 0-10 | Yes | `news_aggregator.py` | `claude_batch_score()` |
| Top 5 articles written to DB | Yes | `news_aggregator.py` | Queues top 5 |
| Score >= 9.0 auto-approve | Partial | `script_generator.py` | Config has `auto_approve_above: 9.0` but code uses `auto_publish_threshold: 8.5` |
| Score 6.0-9.0 pending_review | Yes | Quality gate logic | Matches |
| Score < 6.0 rejected | Yes | Quality gate logic | Matches |
| Budget check before video stage | Yes | `budget_enforcer.py` | `check_or_raise()` called before expensive steps |
| Platform post times (Instagram 12:00, YouTube 14:00, TikTok 19:00) | Yes | `config.json` platforms | Configured per platform |
| Analytics feedback loop (24h after posting) | Partial | `analytics_tracker.py` | Fetches metrics but no automated feedback into article scoring model |

---

## 4. Data Models (Section 9 of Pre-Plan)

### Article Model

| Pre-Plan Field | In DB? | DB Column | Notes |
|---------------|--------|-----------|-------|
| content_id | No | -- | Pre-plan says "Not set yet -- assigned when Script is created". DB has `id` (auto-increment) |
| source | Yes | `source` | |
| title | Yes | `title` | |
| summary | Yes | `summary` | |
| link | Yes | `link` | |
| pillar | Yes | `pillar` | |
| claude_score | Yes | `claude_score` | |
| heuristic_score | Yes | `heuristic_score` | |
| age_hours | Yes | `age_hours` | |
| published_iso | Yes | `published_iso` | |
| fetched_at | Yes | `fetched_at` | |
| status | Yes | `status` | Values differ from pre-plan (see pipeline states above) |

### Script Model

| Pre-Plan Field | In DB? | DB Column | Notes |
|---------------|--------|-----------|-------|
| content_id | Yes | `content_id` | `bolt_YYYYMMDD_HHMMSS` format |
| article_id | Yes | `article_id` | FK to articles |
| pillar | Yes | `pillar` | |
| script | Yes | `script` | |
| word_count | Yes | `word_count` | |
| overall_score | Yes | `overall_score` | |
| hook_strength | Yes | `hook_strength` | |
| simplicity | Yes | `simplicity` | |
| bolt_voice | Yes | `bolt_voice` | |
| pacing | Yes | `pacing` | |
| captions | Yes | `captions_json` | JSON blob |
| status | Yes | `status` | |
| auto_approved | Yes | `auto_approved` | |
| review_decision | Yes | `review_decision` | |
| generated_at | Yes | `generated_at` | |
| approved_at | Yes | `approved_at` | |

### Video Model

| Pre-Plan Field | In DB? | DB Column | Notes |
|---------------|--------|-----------|-------|
| content_id | Yes | `content_id` | FK to scripts |
| audio_path | Yes | `audio_path` | |
| audio_provider | Yes | `audio_provider` | |
| avatar_path | Yes | `avatar_path` | |
| avatar_provider | Yes | `avatar_provider` | |
| final_path | Yes | `final_path` | |
| thumbnail_path | Yes | `thumbnail_path` | |
| video_ready | Yes | `video_ready` | |
| status | Yes | `status` | Missing intermediate states (audio_ready, avatar_ready) |
| completed_at | Yes | `completed_at` | |

### Publication Model

| Pre-Plan Field | In DB? | DB Column | Notes |
|---------------|--------|-----------|-------|
| content_id | Yes | `content_id` | |
| platform | Yes | `platform` | |
| success | Yes | `success` | |
| post_url | Yes | `post_url` | |
| post_id | Yes | `post_id` | |
| error_msg | Yes | `error_msg` | |
| scheduled_at | Yes | `scheduled_at` | |
| published_at | Yes | `published_at` | |
| views | **No** | -- | Pre-plan says "Populated 24h later by analytics tracker" -- not in schema |
| engagement_rate | **No** | -- | Pre-plan says "Populated 24h later" -- not in schema |

---

## 5. Three Invariant Rules (Section 10 of Pre-Plan)

| Rule | Status | Evidence |
|------|--------|----------|
| **Rule 1: content_id is immutable** -- format `bolt_YYYYMMDD_HHMMSS`, travels to every table | Yes | `content_id` used as FK across scripts, videos, publications, cost_events |
| **Rule 2: modules do not call modules** -- only shared state is DB | Yes | Modules read/write DB independently, orchestrator chains them |
| **Rule 3: pipeline never blocks** -- no stage waits for human, job worker connects stages async | Yes | HITL uses flag file polling (non-blocking), job_worker runs as separate process |

---

## 6. Appendices (Pre-Plan)

| Appendix | Implemented? | Where |
|----------|-------------|-------|
| Content Pillar Schedule (Mon-Sun mapping) | Yes | `config.json` content_pillars |
| Voice Parameters (en-US-GuyNeural, +8% rate, +5Hz pitch, +10% volume) | Yes | `local_tts.py`, `config.json` |
| Fallback voices (Christopher, Eric, Ryan) | Partial | `local_tts.py` | Only primary voice configured by default |
| Posting Schedule (Instagram 12:00, YouTube 14:00, TikTok 19:00) | Yes | `config.json` platforms |

---

## Summary: Key Gaps

| # | Gap | Severity | Description |
|---|-----|----------|-------------|
| 1 | Publication model missing views/engagement_rate columns | Medium | Pre-plan specifies these are populated 24h later by analytics tracker. The `analytics_snapshots` table captures platform-level metrics but per-publication metrics are missing |
| 2 | No B-roll generation (Kling AI) | Medium | Pre-plan specifies Kling AI for background clips; not implemented |
| 3 | Forbidden list not fully encoded | Medium | Only 2 banned words vs the full list of opening killers, content killers from pre-plan |
| 4 | Article/Video state machines incomplete | Low | Missing intermediate states (fetched/scored/queued for articles, audio_ready/avatar_ready for videos) |
| 5 | No HeyGen integration | Low | Pre-plan's paid avatar upgrade path not implemented |
| 6 | Analytics feedback loop not automated | Medium | Metrics are collected but don't feed back into article scoring |
| 7 | 5 attention triggers / 3 hook formulas not codified | Low | Content theory from pre-plan not encoded as scoring criteria |
| 8 | Avatar body language parameters not configured | Low | Pre-plan details eye direction, hand visibility, forward lean -- no avatar config for these |
| 9 | Thumbnail templates (3 platform-specific) | Low | Single thumbnail generation exists, pre-plan specifies 3 templates |
| 10 | Auto-approve threshold mismatch | Low | Pre-plan says 9.0, config has both 8.5 and 9.0 in different fields |
