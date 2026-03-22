# Bolt AI v2 -- What's Still Missing

Post-remediation status check. Two PRs have landed covering P1/P2 improvements and the pre-plan alignment remediation (phases A-E). This document catalogues what remains.

---

## Status: What's Been Fixed

| Area | Before | After |
|------|--------|-------|
| Video pipeline crash recovery | All-or-nothing write | Incremental DB writes: audio_ready -> avatar_ready -> assembled |
| HITL blocking | Scheduler polls for 12h | Scheduler exits, approval creates video job |
| API layer isolation | Imports pipeline modules | Creates DB jobs, job worker executes |
| Publication data model | No per-post metrics | views + engagement_rate columns added |
| Job worker backoff | Flat 5min retry | 5min -> 30min -> 2hr -> dead letter |
| Dead letter tracking | JSON files only | DB table + JSON + notifications |
| Content quality | 2 banned words | 30+ banned phrases + opening pattern regex |
| Script structure | Generic 5-part | Pre-plan 5-segment with timing |
| Article dedup | In-memory per-run | Persistent SQLite hashes across runs |
| API authentication | None | X-API-Key header auth |
| Dashboard API integration | Broken response handling | Fixed scripts endpoint unwrapping |
| Package structure | No init, no pyproject | __init__.py + pyproject.toml with ruff/mypy |

---

## Remaining: Coding Pattern Violations

These were identified in the gap analysis but not yet fixed because they require touching every module signature, which is a larger refactor.

### 1. Config as parameter (Pattern 1) -- NOT FIXED

Every module's `run()` function still calls `load_config()` internally instead of receiving config as a parameter. This is the most pervasive violation. It affects:
- `news_aggregator.run(config_path=...)`
- `script_generator.run(config_path=...)`
- `video_pipeline.run(config_path=...)`
- `platform_publisher.run(config_path=...)`
- `analytics_tracker.run(config_path=...)`

**What fixing this looks like:**
```python
# Every module changes from:
def run(config_path="code/config.json"):
    config = load_config(config_path)

# To:
def run(config: dict) -> dict:
    # config already loaded and secret-injected
```

The orchestrator becomes the only place that calls `get_config()`. Tests pass test config directly. This is high-value for testability but touches many files.

### 2. Modules return, never raise (Pattern 3) -- NOT FIXED

Pipeline modules can still raise exceptions. The orchestrator still wraps every step in broad `try/except Exception`. Fixing this requires:
- Each module returns `{"status": "success", ...}` or `{"status": "failed", "error": "...", "retriable": True}`
- Orchestrator checks `result["status"]` instead of catching exceptions
- A `ConfigurationError` exception class for missing keys (the one category that should propagate)

### 3. Orchestrator error categorization (Phase A3) -- PARTIALLY FIXED

The orchestrator still uses broad `try/except Exception`. The three-tier error handling (transient -> retry, config -> notify, programmer -> crash) is not yet implemented. This is tightly coupled with Pattern 3 above.

---

## Remaining: Pre-Plan Feature Gaps

### 4. Analytics feedback loop -- NOT IMPLEMENTED

The pre-plan says: "24 hours after posting, the analytics tracker fetches views, retention rate, likes, and comments from each platform. These update the Publication records and feed back into the Article scoring model over time."

What exists: `analytics_tracker.py` fetches platform-level metrics and writes to `analytics_snapshots`. The `update_publication_metrics()` DB method now exists (added in PR #2), but nothing calls it yet. The feedback loop into article scoring doesn't exist.

**What's needed:**
- `analytics_tracker.py` needs to query publications older than 24h that haven't been metrics-updated yet
- For each, fetch per-video metrics from the platform API
- Call `db.update_publication_metrics(content_id, platform, views, engagement_rate)`
- Optionally: feed engagement data back to Claude scoring prompts over time

### 5. Kling AI B-roll integration -- NOT IMPLEMENTED

Pre-plan specifies Kling AI for generating tech-themed background clips (circuit boards, data flows, abstract AI imagery). Currently the video pipeline only uses avatar footage or FFmpeg text-card fallback. No B-roll layer exists.

### 6. HeyGen avatar (paid tier) -- NOT IMPLEMENTED

Pre-plan describes HeyGen at $29/month as the paid upgrade with best lip sync quality. Only Vidnoz -> D-ID -> FFmpeg fallback chain is implemented.

### 7. Three platform-specific thumbnail templates -- NOT IMPLEMENTED

Pre-plan says three templates: 16:9 for YouTube, 9:16 for TikTok and Instagram. Current `generate_thumbnail()` creates a single 1280x720 thumbnail. The template system isn't platform-aware.

### 8. Topic make/skip automated filtering -- NOT IMPLEMENTED

Pre-plan has detailed make/skip criteria (cover model releases with benchmarks, free tools, AI replacing professions; skip research papers without product outcomes, philosophy without events, unverified breaking news). This editorial logic isn't encoded in the article scoring or filtering.

### 9. Retention benchmark monitoring -- NOT IMPLEMENTED

Pre-plan sets a 70% retention at 30s as the quality threshold. Analytics are collected but there's no threshold-based alerting or content strategy adjustment when retention drops below target.

---

## Remaining: Operational Readiness

### 10. CI/CD pipeline -- NOT IMPLEMENTED

No GitHub Actions. No automated linting, type-checking, or test runs on PR. The `pyproject.toml` with ruff/mypy config exists but nothing runs it automatically.

### 11. Database migrations -- NOT IMPLEMENTED

Schema changes (like the new `views`/`engagement_rate` columns and `dead_letters` table) require dropping and recreating the DB on existing deployments. No alembic or version-based migration system.

### 12. Log rotation -- NOT IMPLEMENTED

Structured logs write to files unbounded. No logrotate config or max-size policy.

### 13. Cost tracker dual storage -- NOT FIXED

`cost_tracker.py` maintains its own JSON file (`data/analytics/cost_tracking.json`) alongside the DB `cost_events` table. The pre-plan says all state should be in the DB. The JSON file is redundant.

### 14. news_aggregator.write_queue() JSON files -- NOT FIXED

`news_aggregator.py` writes queue JSON files to `data/queue/` in addition to saving articles to the DB. The pre-plan says modules communicate only through the DB. The JSON queue files are legacy from before the DB existed.

---

## Priority Ranking

| Priority | Item | Rationale |
|----------|------|-----------|
| P1 | Config as parameter (item 1) | Most pervasive pattern violation. Blocks proper testability. |
| P1 | Modules return, never raise (item 2) | Coupled with error categorization. Makes error handling predictable. |
| P1 | CI/CD pipeline (item 10) | No safety net for future changes. The codebase is now complex enough that manual testing is insufficient. |
| P2 | Analytics feedback loop (item 4) | The DB method exists but nothing calls it. Completing this closes the most important data loop in the system. |
| P2 | Database migrations (item 11) | Required before any production deployment with schema changes. |
| P2 | Remove redundant JSON storage (items 13, 14) | Aligns with pre-plan "DB is the only state store" principle. |
| P3 | Kling AI B-roll (item 5) | Net new feature. Visual polish, not structural. |
| P3 | HeyGen avatar (item 6) | Paid tier upgrade. Only relevant when content strategy is proven. |
| P3 | Platform-specific thumbnails (item 7) | Polish. Single thumbnail works for MVP. |
| P3 | Topic make/skip filtering (item 8) | Editorial logic. Claude scoring partially covers this. |
| P3 | Retention monitoring (item 9) | Needs real analytics data first. |
| P3 | Log rotation (item 12) | Operational polish. |

---

## Summary

The structural integrity of the system is now solid. The three pre-plan invariant rules are respected. The pipeline is crash-recoverable, non-blocking, and uses the DB as the primary state store. The two highest-impact remaining items are the config-as-parameter refactor (testability) and CI/CD (safety net). After those, completing the analytics feedback loop would close the most valuable data cycle in the system.
