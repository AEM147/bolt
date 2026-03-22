# Pre-Plan Part 2: Coding Methods vs Actual Code

Comparison of the coding patterns and architectural rules from `bolt_preplan(1).md` (sections 11-17) against the actual implementation.

---

## Section 11: Architecture in Layers

| Layer | Pre-Plan Rule | Actual Code | Status |
|-------|--------------|-------------|--------|
| **Layer 1 -- Config** | Loads once at startup. Every other layer receives config as parameter. Nothing loads config independently. | `shared_config.py` caches config. But modules like `news_aggregator.py`, `script_generator.py`, `video_pipeline.py` each have a `load_config()` function that can be called independently (they delegate to `shared_config.get_config()` now, but they can still load config on their own). `content_automation_master.py` loads config at module level into a global `CONFIG`. | **Partial** -- Config is cached centrally but still loaded as a module-level global in the orchestrator, not always passed as a parameter |
| **Layer 2 -- Database** | Single SQLite file. All state lives here. No layer shares state with another directly. | `database.py` with SQLite WAL mode. All pipeline modules write to DB. Cost tracker also uses a separate JSON file (`data/analytics/cost_tracking.json`). | **Partial** -- DB is primary state store, but `cost_tracker.py` maintains its own JSON file alongside the DB `cost_events` table |
| **Layer 3 -- Pipeline modules** | Each reads from DB, writes to DB, returns. Nothing else. | Modules generally follow this pattern. However `news_aggregator.py` also writes queue JSON files to `data/queue/` in addition to DB. | **Partial** -- JSON file writes in `news_aggregator.write_queue()` are redundant with DB storage |
| **Layer 4 -- Orchestrator** | Reads DB state, decides which module to call next, passes config. Only place that knows pipeline sequence. | `content_automation_master.py` does this correctly. However it also contains `CircuitBreaker` logic that arguably belongs in its own module. | **Yes** |
| **Layer 5 -- Job worker** | Polls DB for pending jobs. Runs in own process. | `job_worker.py` runs as separate Docker service. Polls DB. | **Yes** |
| **Layer 6 -- API server** | Reads DB for dashboard data. Writes human decisions to DB. Never imports pipeline modules. | `api.py` imports `content_automation_master` to trigger pipeline runs via `BackgroundTasks`. This violates "never imports pipeline modules". | **Violation** -- `api.py` imports `content_automation_master` for `run_full_pipeline()` and individual step functions |
| **Layer 7 -- Dashboard** | Calls API endpoints only. No direct DB access. Shows real state, not demo data. | Dashboard calls API via `api.ts`. Has static JSON fallbacks and DEMO_ITEMS in `ContentManagement.tsx` (now with API as primary, demo as fallback). | **Partial** -- Static fallbacks still exist, DEMO_ITEMS still in source as last resort |

### Layer replaceability test
> "Can you replace any one layer without touching any other?"

| Layer | Replaceable? | Blocker |
|-------|-------------|---------|
| Config | Yes | -- |
| Database | Mostly | `cost_tracker.py` has its own JSON file |
| Pipeline modules | Yes | Each is independent |
| Orchestrator | Mostly | `api.py` imports it directly |
| Job worker | Yes | -- |
| API server | Yes | -- |
| Dashboard | Yes | -- |

---

## Section 12: The Two Processes

| Pre-Plan Rule | Actual Code | Status |
|--------------|-------------|--------|
| Process A (pipeline scheduler) fires at 06:00 UTC, runs news + script, creates job if auto-approved, exits, never waits | `content_automation_master.py` `run_scheduler()` uses the `schedule` library. Full pipeline at 06:00. The HITL `wait_for_approval()` function polls with a timeout, which technically waits (up to 12h) inside the scheduler process. | **Violation** -- `wait_for_approval()` blocks the scheduler process with a polling loop instead of creating a job and exiting |
| Process B (job worker) polls DB every 30 seconds | `job_worker.py` polls every 60 seconds (not 30). | **Minor deviation** -- 60s vs 30s poll interval |
| They never call each other | Correct. Separate processes sharing only the DB. | **Yes** |

---

## Section 13: Module Contracts

### shared_config.py

| Contract Rule | Actual Code | Status |
|--------------|-------------|--------|
| Receives: optional path override | `get_config(path?, force_reload?)` | **Yes** |
| Returns: one config dict with all secrets injected, module-level cached | Uses `_CONFIG_CACHE` and calls `load_all_secrets()` | **Yes** |
| Forbidden: making any API call, writing anything | Pure read-only | **Yes** |
| Forbidden: being called more than once per module | Module-level cache prevents redundant loads, but no enforcement -- any code can call `get_config()` multiple times | **Partial** |

### news_aggregator.py

| Contract Rule | Actual Code | Status |
|--------------|-------------|--------|
| Receives: config dict | `run()` accepts `config_path` string and calls `load_config()` internally | **Violation** -- Should receive config dict as parameter, not load it itself |
| Returns: list of Article dicts saved to DB | Returns list of article dicts. Saves to DB via orchestrator (`step_news` calls `db.save_articles()`), not within the module itself. | **Partial** -- Module returns articles but doesn't write to DB directly; orchestrator does |
| Side effect: writes Article rows to DB with status=scored | Orchestrator handles DB writes, not the module | **Deviation** -- DB writing is in orchestrator, not module. Pre-plan says module writes to DB. |
| Async rule: this is the one async module | `run()` is async, uses `aiohttp` for concurrent feeds | **Yes** |
| Forbidden: calling script_generator | Does not import script_generator | **Yes** |

### script_generator.py

| Contract Rule | Actual Code | Status |
|--------------|-------------|--------|
| Receives: config dict | `run()` accepts `config_path` and calls `load_config()` internally | **Violation** -- Same as news_aggregator |
| Returns: Script dict with content_id, script text, quality scores, captions, status. Returns None if no article. | Returns a package dict with these fields | **Yes** |
| content_id generated here, format bolt_YYYYMMDD_HHMMSS | Generated in `run()` | **Yes** |
| Forbidden: calling video_pipeline, waiting for human input | Does not import video_pipeline or wait | **Yes** |

### content_validator.py

| Contract Rule | Actual Code | Status |
|--------------|-------------|--------|
| Receives: script text, article dict, config dict | `ContentValidator.validate()` takes script and article | **Yes** |
| Returns: ValidationResult with passed bool, score, failures list, warnings list | Returns `ValidationResult` dataclass | **Yes** |
| Forbidden: writing to DB, making API calls, modifying the script | Pure validation functions | **Yes** |

### video_pipeline.py

| Contract Rule | Actual Code | Status |
|--------------|-------------|--------|
| Receives: content_id string, config dict | `run()` accepts a full package dict and config | **Deviation** -- receives package dict, not just content_id |
| Incremental writes: after audio write audio_path + status=audio_ready; after avatar write avatar_path + status=avatar_ready | No incremental DB writes. Module returns a complete result dict. DB write happens in orchestrator after full completion. | **Violation** -- No incremental status updates. If process crashes after audio but before avatar, progress is lost. |
| Forbidden: using asyncio.run() internally | Uses `_run_async()` helper that calls `asyncio.run()` inside a thread pool when called from async context | **Violation** -- `asyncio.run()` is used internally for Edge-TTS calls |
| Forbidden: raising exceptions | Uses try/except but some paths could still raise | **Partial** |

### platform_publisher.py

| Contract Rule | Actual Code | Status |
|--------------|-------------|--------|
| Receives: content_id string, config dict | `run()` accepts a full package dict and config | **Deviation** -- receives package dict, not just content_id |
| Returns: dict keyed by platform with success and url/error | Returns results dict matching this shape | **Yes** |
| Forbidden: raising on platform failure | Uses try/except per platform, returns error dict | **Yes** |

### analytics_tracker.py

| Contract Rule | Actual Code | Status |
|--------------|-------------|--------|
| Receives: config dict | `run()` loads config internally via `load_config()` | **Violation** -- Same config loading pattern |
| Side effect: updates Publication rows | Writes to `analytics_snapshots` table. Does NOT update Publication rows with views/engagement_rate | **Violation** -- Per-publication metrics not written back to publications table |
| Forbidden: running during pipeline hours, blocking other pipeline steps | Scheduled at 09:00 UTC, separate from 06:00 pipeline | **Yes** |

---

## Section 14: Decision Trees

### Decision tree 1 -- after script scoring

| Rule | Actual Code | Status |
|------|-------------|--------|
| Validator failed -> status=pending_review regardless of score | Validator is called but its result doesn't override the score-based decision in all cases | **Partial** |
| Score < 6.0 -> rejected, mark article skipped, try next article | Implemented in orchestrator | **Yes** |
| Score 6.0-9.0 -> pending_review, send notification, exit, no video job | Implemented | **Yes** |
| Score > 9.0 AND validator passed -> approved, create Job(type=video), exit | Auto-approve creates a job | **Yes** |
| Thresholds are config values, never hardcoded | Thresholds come from `config.json quality_gate` section | **Yes** |

### Decision tree 2 -- voice synthesis fallback chain

| Rule | Actual Code | Status |
|------|-------------|--------|
| Edge-TTS -> Google Cloud TTS -> ElevenLabs -> all failed = status=failed + retry Job | Fallback chain exists in `synthesize_voice()` | **Yes** |
| "File exists and size > 0 bytes" check | Basic file existence check, may not verify size > 0 | **Partial** |

### Decision tree 3 -- avatar generation fallback chain

| Rule | Actual Code | Status |
|------|-------------|--------|
| Vidnoz -> D-ID -> FFmpeg text card (always available) | Three-tier fallback exists | **Yes** |
| FFmpeg fallback means video production can never completely fail | `create_text_card_video()` is the last resort | **Yes** |

### Decision tree 4 -- job worker on failure

| Rule | Actual Code | Status |
|------|-------------|--------|
| Attempt 1 fails: retry in 5 min | `fail_job()` uses `retry_after_seconds=300` (5 min) | **Yes** |
| Attempt 2 fails: retry in 30 min | Same 5-min default for all attempts -- no escalating backoff | **Violation** -- Pre-plan says 5m/30m/2h escalation, code uses flat 5m |
| Attempt 3 fails: retry in 2h + error notification | Not implemented | **Violation** |
| Attempt 4 (max) fails: status=dead, dead_letter, critical notification | Max attempts reached -> job stays in retrying state. No dead_letter log or critical notification. | **Violation** |
| Budget exceeded: status=deferred, next_run_at=midnight | No deferred status. `BudgetExceededError` is raised and caught, but job is just failed, not deferred to midnight. | **Missing** |

---

## Section 15: Coding Patterns

| Pattern | Pre-Plan Rule | Actual Code | Status |
|---------|--------------|-------------|--------|
| **Pattern 1 -- Config as parameter** | Every function receives config as parameter. No function calls `get_config()` internally. No module-level config variable. | `content_automation_master.py` has module-level `CONFIG = load_config()`. Module `run()` functions load config internally via `load_config()`. | **Violated across the codebase** -- Config is loaded internally in every module's `run()` function, not passed as parameter |
| **Pattern 2 -- Sync everywhere except news_aggregator** | `asyncio.run()` called exactly once per pipeline run. | `video_pipeline.py` uses `_run_async()` which calls `asyncio.run()` in a thread. Multiple async contexts exist. | **Violated** -- `asyncio.run()` used in video_pipeline via thread pool |
| **Pattern 3 -- Modules return, never raise** | Every module catches exceptions, returns result with status field. Orchestrator checks status, never wraps in try/except. | Orchestrator (`content_automation_master.py`) wraps every step in try/except blocks. Modules can raise. | **Violated** -- Orchestrator uses try/except on every step call rather than checking returned status dicts |
| **Pattern 4 -- State always in DB, never in memory** | Every step writes result to DB before returning. Kill and restart = continues from last DB write. Video pipeline writes incrementally. | Video pipeline returns a complete dict; DB write happens after all sub-steps complete. If killed mid-video, all progress lost. | **Violated** for video_pipeline -- No incremental DB writes |
| **Pattern 5 -- One responsibility per file** | Can describe in one sentence without "and" | Most files follow this. `content_automation_master.py` is orchestrator AND scheduler AND CLI tool -- could be split. | **Mostly yes** |
| **Pattern 6 -- Every external call has a timeout** | RSS=10s, Claude=30s, Voice=60s, Avatar=5min, Publish=30s, DB=30s | RSS feeds have 10s timeout. Claude calls use default timeout. Voice/avatar have timeouts. DB connections have 30s timeout. | **Mostly yes** -- Specific timeout values vary slightly from pre-plan |

---

## Section 16: Error Philosophy

| Category | Pre-Plan Response | Actual Code | Status |
|----------|------------------|-------------|--------|
| **Transient (429, 503, timeout)** | Catch, log WARNING, create retry job with exponential backoff, return status=failed, never raise | `http_utils.py` retries with backoff. Modules catch and return errors. But backoff is flat (5m) not exponential. | **Partial** -- Retry exists but backoff is flat, not escalating |
| **Configuration (missing key, wrong token)** | Catch, log ERROR with exact missing key, send notification, fallback if available, no retry | Secrets manager logs placeholders. Modules log errors and fall back. Notifications not always sent for config issues. | **Partial** |
| **Programmer (KeyError, TypeError)** | Let it raise. Do not catch. Must crash visibly. | Orchestrator's try/except catches everything, including programmer errors, which masks bugs. | **Violated** -- Broad try/except in orchestrator catches all error types |
| **Logging contract: WARNING+ includes content_id** | Every log at WARNING+ includes content_id if one exists | Structured logging exists but content_id is not consistently included in all WARNING+ messages. | **Partial** |

### Logging level contract

| Level | Pre-Plan "When" | Actual | Status |
|-------|----------------|--------|--------|
| DEBUG | Internal state transitions, every DB read/write, every fallback switch | Limited DEBUG logging | **Partial** |
| INFO | Every pipeline step start/completion, every job created/started/completed | Step start/end logged at INFO | **Yes** |
| WARNING | Every fallback triggered, every retry, every budget alert, every rejection | Fallbacks and retries logged | **Yes** |
| ERROR | Every caught transient failure, config failures, failed notifications | Errors logged | **Yes** |
| CRITICAL | Budget hard stop, dead letter, process-level failure | Budget hard stops logged. No dead letter logging. | **Partial** |

---

## Section 17: Build Sequence

| Phase | Pre-Plan Order | Actual State | Status |
|-------|---------------|--------------|--------|
| Phase 1 -- Foundation | shared_config, database, observability, budget_enforcer | All exist and work | **Done** |
| Phase 2 -- Pipeline (text) | news_aggregator, content_validator, script_generator, hitl | All exist and work | **Done** |
| Phase 3 -- Media | local_tts, video_pipeline, platform_publisher, analytics_tracker | All exist | **Done** |
| Phase 4 -- Orchestration | job_worker, content_automation_master, api, Dashboard | All exist | **Done** |
| Pre-plan rule: "no page ships with hardcoded demo data" | Dashboard pages have DEMO_ITEMS as last-resort fallback. API is primary data source. | **Partial** -- Demo data exists as fallback, not primary |

---

## Summary: Critical Coding Method Violations

| # | Violation | Severity | Description |
|---|-----------|----------|-------------|
| 1 | **Config as parameter (Pattern 1)** | High | Every module's `run()` loads config internally. Pre-plan mandates config be passed as parameter for testability. |
| 2 | **API server imports pipeline modules (Layer 6)** | High | `api.py` imports `content_automation_master` to trigger runs. Pre-plan says API should only read/write DB, never import pipeline modules. Should use job creation instead. |
| 3 | **Video pipeline no incremental DB writes (Pattern 4)** | High | Pre-plan requires writing `status=audio_ready` after audio, `status=avatar_ready` after avatar. Current code writes once after full completion. Crash mid-process = lost progress. |
| 4 | **Orchestrator catches all exceptions (Pattern 3 + Error Category 3)** | Medium | Broad try/except masks programmer errors. Pre-plan says modules return status dicts, orchestrator checks status, programmer errors must crash visibly. |
| 5 | **Job worker flat backoff** | Medium | Pre-plan specifies 5m/30m/2h/dead escalation. Code uses flat 5m retry with no dead letter or deferred status. |
| 6 | **HITL blocks scheduler process** | Medium | `wait_for_approval()` polls inside the scheduler. Pre-plan says scheduler creates job and exits, never waits. |
| 7 | **analytics_tracker doesn't update Publication rows** | Medium | Pre-plan says views/engagement_rate populate the Publication model 24h later. Code only writes to analytics_snapshots, not back to publications. |
| 8 | **Modules return, never raise (Pattern 3)** | Medium | Multiple modules can raise exceptions that the orchestrator catches. Should return failure dicts instead. |
