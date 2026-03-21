# Bolt AI v2 -- Full Debug Scan Report

Systematic section-by-section scan for wiring issues, bugs, duplications, and missing connections.

**Severity levels:** CRASH (will fail at runtime), BUG (incorrect behavior), WARN (code smell / future issue)

---

## CRASH-LEVEL ISSUES

### 1. `asyncio.run()` inside running event loop -- video pipeline will crash when scheduled

**File:** `code/video_pipeline.py` lines 24, 39
**Section:** F (Video Pipeline)

When the scheduler runs `asyncio.run(run_full_pipeline())`, the event loop is already running. Then:
- `run_full_pipeline()` (async) calls `step_video()` (sync)
- `step_video()` calls `video_pipeline.run()` (sync)
- `run()` calls `synthesize_edge_tts()` (sync)
- `synthesize_edge_tts()` calls `asyncio.run()` -- **CRASH**: `RuntimeError: This event loop is already running`

This means the video step will always crash when run via the scheduler daemon (`--schedule`).

**Fix:** Replace `asyncio.run()` in `synthesize_edge_tts()` with `asyncio.get_event_loop().run_until_complete()` or make the entire voice synthesis chain async-aware. Alternatively, use `nest_asyncio` as a quick patch.

---

### 2. `content_automation_master.py` passes article title instead of content_id to database

**File:** `code/content_automation_master.py` line 169
**Section:** B (Pipeline Orchestrator) / K (Database)

```python
db.save_publish_results(result["article"]["title"][:20], res)
```

The first argument to `save_publish_results()` is `content_id` (see `database.py` line 355), but the orchestrator passes a truncated article title like `"OpenAI Releases GP"`. This means:
- The `publications` table gets garbled `content_id` values
- Foreign key to `scripts.content_id` won't match (scripts use `bolt_20260321_063000` format)
- Analytics queries joining on content_id will return nothing

**Fix:** Change to `db.save_publish_results(result["content_id"], res)`

---

### 3. Test suite calls non-existent database methods

**File:** `tests/test_database.py`
**Section:** S (Tests)

Two method calls that don't exist in `database.py`:

1. `temp_db.get_recent_articles(limit=10)` -- No `get_recent_articles()` method exists. Closest is `get_top_article()`.
2. `db.get_pending_jobs(limit=5)` -- `get_pending_jobs()` exists but does NOT accept a `limit` parameter (signature: `def get_pending_jobs(self, job_type=None)`).

Both tests will fail with `AttributeError` / `TypeError`.

**Fix:** Add `get_recent_articles()` to `database.py` or change tests to use existing methods. Remove `limit=5` from `get_pending_jobs()` call.

---

## BUG-LEVEL ISSUES

### 4. All paths in config.json are hardcoded to `/workspace/bolt_v2/`

**File:** `code/config.json` lines 204-215
**Section:** A (Configuration)

```json
"paths": {
    "base": "/workspace/bolt_v2",
    "queue": "/workspace/bolt_v2/data/queue",
    "audio": "/workspace/bolt_v2/content/audio",
    ...
}
```

Every module reads `config["paths"]["queue"]`, `config["paths"]["audio"]`, etc. These absolute paths break in:
- Docker (where the app lives at `/app/`)
- DigitalOcean VPS (cloned to user home)
- Any non-workspace environment

The `Dockerfile` creates directories at `/app/data/queue`, `/app/content/audio`, etc. -- but the config points to `/workspace/bolt_v2/`.

**Fix:** Change all paths to relative (`data/queue`, `content/audio`, etc.) or make them configurable via environment variables.

---

### 5. `api.py` monkeypatches a leaky database connection

**File:** `code/api.py` lines 456-461
**Section:** P (API Backend) / K (Database)

```python
def _get_conn_ctx(self):
    conn = sqlite3.connect(str(self.db_path), timeout=30)
    conn.row_factory = sqlite3.Row
    return conn
```

This returns a raw `sqlite3.Connection` object. When used as `with db._get_conn_ctx() as conn:`, Python's `sqlite3.Connection.__exit__` handles commit/rollback but does NOT close the connection. Every call to `/api/news` and `/api/jobs` leaks a connection.

The database module already has a proper `_get_conn()` context manager that closes connections. This monkeypatch bypasses it.

**Fix:** Add a proper `get_recent_articles()` method to `BoltDB` and use it instead of raw SQL in api.py, or make `_get_conn_ctx` properly close connections.

---

### 6. `api.py` `get_script()` does a full table scan

**File:** `code/api.py` lines 235-236
**Section:** P (API Backend)

```python
scripts = db.get_scripts(limit=200)
match = next((s for s in scripts if s["content_id"] == content_id), None)
```

Fetches up to 200 scripts then does a linear search. This:
- Is O(n) instead of O(1)
- Misses any script past position 200
- Returns 404 for valid scripts that exist but are old

**Fix:** Add `get_script_by_content_id(content_id)` to `BoltDB` that queries by content_id directly.

---

### 7. Dead config: `quality_gate.auto_approve_above` is never read

**File:** `code/config.json` lines 86, 367-368
**Section:** A (Config) / D (Script Generator)

Two separate `auto_approve_above` values exist:
- `quality_gate.auto_approve_above: 9.0` (line 86)
- `hitl.auto_approve_above: 9.0` (line 367)

Neither is read by any code. The script generator uses `automation.auto_publish_threshold: 8.5` combined with `automation.auto_publish_enabled: false`. Since `auto_publish_enabled` defaults to `false`, ALL scripts get `pending_review` status regardless of score. The quality gate `auto_approve_above` has no effect.

**Fix:** Wire the `quality_gate.auto_approve_above` into `script_generator.save_script_to_queue()` so scripts scoring above 9.0 are auto-approved even when `auto_publish_enabled` is false. The HITL gate should only apply to the 8.5-9.0 range.

---

### 8. Rate limiter config keys don't match

**File:** `code/config.json` lines 330-334 vs `code/observability.py` lines 221-233
**Section:** A (Config) / L (Observability)

Config defines:
```json
"rate_limiting": {
    "enabled": true,
    "claude_requests_per_minute": 50,
    "voice_requests_per_minute": 100
}
```

But `RateLimiterRegistry._DEFAULTS` expects bare service names:
```python
_DEFAULTS = {"claude": 50, "elevenlabs": 20, "edge_tts": 200, ...}
```

The config override `{**self._DEFAULTS, **limits}` merges both dicts, but the config keys (`claude_requests_per_minute`) don't match the default keys (`claude`), so the config overrides are silently ignored. The `enabled` key also gets added as a bucket named "enabled" with rate 1.

**Fix:** Either change config keys to match (`"claude": 50`) or update `_load_from_config()` to parse the `_requests_per_minute` suffix.

---

### 9. Header.tsx hardcodes SSE URL

**File:** `bolt-dashboard/src/components/Header.tsx` line 28
**Section:** Q (Dashboard Frontend)

```typescript
const es = new EventSource('http://localhost:8000/api/stream/status')
```

Hardcoded to localhost:8000. Breaks in any non-local deployment. Should use `API_BASE` from `api.ts`.

**Fix:** `const es = new EventSource(\`\${API_BASE}/api/stream/status\`)`

---

## WARN-LEVEL ISSUES

### 10. Cost tracker reads config.json directly, bypassing shared_config

**File:** `code/cost_tracker.py` line 114
**Section:** J (Cost Tracking)

`_load_pricing()` opens `config.json` with `json.load()` directly, bypassing `shared_config.get_config()`. For pricing data this doesn't cause functional issues (no secrets in pricing), but it's inconsistent with the centralized config pattern and reads the file on every `record_usage()` call.

---

### 11. Cost tracker "monthly" dict is keyed by day, not month

**File:** `code/cost_tracker.py` line 72
**Section:** J (Cost Tracking)

```python
date = datetime.now().strftime("%Y-%m-%d")
self.costs["monthly"][date] = { ... }
```

The dict named "monthly" is actually keyed by daily date strings. `get_monthly_summary()` iterates all dates and filters by month prefix, which works but is misleading. This also means the "monthly" dict grows without bound (one key per day the pipeline runs).

---

### 12. `config.json` has `cost_tracking` missing `daily_budget_alert`

**File:** `code/config.json` lines 266-295
**Section:** A (Config) / J (Budget)

The config defines `monthly_budget_alert: 10.0` and `per_video_budget_alert: 0.5` but NOT `daily_budget_alert`. The `BudgetEnforcer._DEFAULTS` provides `3.0` as fallback, but the config is incomplete -- the daily alert cannot be configured without editing code.

---

### 13. Duplicate Discord notification logic

**File:** `code/platform_publisher.py` lines 27-44 vs `code/notifications.py`
**Section:** G (Publisher) / M (Notifications)

`platform_publisher.py` has its own `notify_discord()` function that directly posts to the webhook. The `notifications.py` module has a full `NotificationManager` with Discord support. The publisher's function duplicates the Discord notification logic and doesn't use the centralized notification system.

---

### 14. `content_validator.py` is never called from the main pipeline

**File:** `code/content_validator.py`
**Section:** E (Content Validation)

The validator IS called from `script_generator.save_script_to_queue()` (line 227), but wrapped in a try/except that catches all exceptions and continues silently. If the validator fails to import or has any issue, it's completely bypassed with only a debug log. The validation results are used to downgrade the score but the try/except means validation failures are invisible.

---

### 15. `news_aggregator.run()` returns top stories but orchestrator expects specific format

**File:** `code/content_automation_master.py` line 98 vs `code/news_aggregator.py` line 251
**Section:** B (Orchestrator) / C (News)

The orchestrator does:
```python
articles = await news_aggregator.run()
if articles:
    db.save_articles(articles)
```

`news_aggregator.run()` returns `list[dict]` with keys like `title`, `summary`, `claude_score`, `content_pillar`, `claude_hook_idea`. But `db.save_article()` expects `pillar` (not `content_pillar`). The database method at line 207 handles both: `article.get("content_pillar", article.get("pillar", ""))` -- so this works, but the inconsistent key naming is fragile.

---

### 16. `platform_publisher.run()` looks for `final_video_url` but `video_pipeline` stores `final_video_path`

**File:** `code/platform_publisher.py` line 195 vs `code/video_pipeline.py` line 237
**Section:** F (Video) / G (Publisher)

The publisher checks:
```python
video_url = package.get("final_video_url") or package.get("avatar_video_url")
```

But the video pipeline stores:
```python
package["final_video_path"] = final   # local file path
package["avatar_video_path"] = avatar  # local file path  
```

The key names don't match (`_url` vs `_path`). `final_video_url` will be `None`, then `avatar_video_url` will also be `None`. The publisher will log "No video URL in package" and fail every time.

**This is effectively a CRASH bug** -- publishing will never work because the key names are mismatched between video pipeline output and publisher input.

---

## Summary Table

| # | Severity | Section | File | Issue |
|---|----------|---------|------|-------|
| 1 | CRASH | F | video_pipeline.py | `asyncio.run()` inside running event loop |
| 2 | CRASH | B/K | content_automation_master.py | Article title passed as content_id to DB |
| 3 | CRASH | S | test_database.py | Tests call non-existent DB methods |
| 4 | BUG | A | config.json | All paths hardcoded to `/workspace/bolt_v2/` |
| 5 | BUG | P/K | api.py | Monkeypatched DB connection never closes |
| 6 | BUG | P | api.py | `get_script()` full table scan, misses old scripts |
| 7 | BUG | A/D | config.json + script_generator | `auto_approve_above` config is dead/unused |
| 8 | BUG | A/L | config.json + observability | Rate limiter config keys don't match |
| 9 | BUG | Q | Header.tsx | Hardcoded SSE URL to localhost |
| 10 | WARN | J | cost_tracker.py | Bypasses shared_config |
| 11 | WARN | J | cost_tracker.py | "monthly" dict keyed by day |
| 12 | WARN | A/J | config.json | Missing `daily_budget_alert` config key |
| 13 | WARN | G/M | platform_publisher.py | Duplicate Discord notification logic |
| 14 | WARN | E | content_validator.py | Silently swallowed validation errors |
| 15 | WARN | B/C | orchestrator + aggregator | Inconsistent field names (`content_pillar` vs `pillar`) |
| 16 | CRASH | F/G | video_pipeline + publisher | Key mismatch: `_path` vs `_url` -- publishing never works |
