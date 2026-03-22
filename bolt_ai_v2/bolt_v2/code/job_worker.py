#!/usr/bin/env python3
"""
Bolt AI — Job Worker (job_worker.py)
=====================================
Processes the SQLite `jobs` table — the retry queue used when pipeline
steps fail. This is the lightweight alternative to Celery + Redis that's
appropriate for Bolt's scale (1–3 videos/day).

Architecture:
  Pipeline step fails
       ↓
  db.enqueue_job("video", content_id, max_attempts=3)
       ↓
  job_worker polls every 60s
       ↓
  Picks up pending/retrying jobs
       ↓
  Runs the failed step again
       ↓
  Marks done or increments attempt count

Worker states:
  pending   → not yet started
  running   → currently executing
  retrying  → failed, scheduled for retry with exponential backoff
  done      → completed successfully
  dead      → exceeded max_attempts (moved to dead-letter log)

Run alongside the scheduler:
  python job_worker.py               # foreground
  python job_worker.py --once        # process queue once and exit
  pm2 start job_worker.py --name bolt-worker

Or via docker-compose (already configured as 'worker' service).
"""

import asyncio
import json
import logging
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from observability import get_logger, setup_logging
from secrets_manager import load_all_secrets
from database import get_db

setup_logging(log_dir="logs", level="INFO")
logger = get_logger("bolt.worker")

POLL_INTERVAL_SECONDS = 60
MAX_CONCURRENT_JOBS   = 2   # Don't run more than 2 jobs at once (API rate limits)


def load_config(path: str = "code/config.json") -> dict:
    """Load config with secrets injected via shared_config."""
    from shared_config import get_config
    return get_config(path)


# ── Job handlers ───────────────────────────────────────────────────────────

async def run_job(job: dict, config: dict) -> bool:
    """
    Execute a single job. Returns True on success, False on failure.
    Each job_type maps to a pipeline step function.
    """
    job_type   = job["job_type"]
    content_id = job.get("content_id", "")
    logger.info(f"Running job", extra={
        "job_id": job["id"], "type": job_type, "attempt": job["attempts"] + 1,
        "content_id": content_id,
    })

    try:
        from notifications import NotificationManager, Notification, NotificationLevel
        from cost_tracker import CostTracker
        from budget_enforcer import BudgetEnforcer, BudgetExceededError

        notifier = NotificationManager(config)
        tracker  = CostTracker()

        class _NullCB:
            def is_open(self, s): return False
            def record_failure(self, s): pass
            def record_success(self, s): pass

        cb = _NullCB()

        from content_automation_master import (
            step_news, step_script, step_video, step_publish, step_analytics
        )

        if job_type == "news":
            return await step_news(notifier, cb, tracker)

        elif job_type == "script":
            result = step_script(notifier, cb, tracker)
            return result is not None

        elif job_type == "video":
            # Budget check before video (the expensive step)
            try:
                BudgetEnforcer(config).check_or_raise("video_retry")
            except BudgetExceededError as e:
                logger.error("Budget exceeded — skipping video retry", extra={"error": str(e)})
                return False
            result = step_video(notifier, cb, tracker)
            return result is not None and result.get("video_ready") or result.get("audio_path")

        elif job_type == "publish":
            try:
                BudgetEnforcer(config).check_or_raise("publish_retry")
            except BudgetExceededError as e:
                logger.error("Budget exceeded — skipping publish retry")
                return False
            result = step_publish(notifier, cb, tracker)
            return result is not None

        elif job_type == "analytics":
            result = step_analytics(notifier, tracker)
            return result is not None

        elif job_type == "backup":
            from backup_system import BackupSystem
            backup = BackupSystem()
            result = backup.create_backup("retry")
            return bool(result)

        elif job_type == "pipeline_full":
            # Full pipeline triggered from API -- run all steps in sequence
            ok = await step_news(notifier, cb, tracker)
            if ok:
                result = step_script(notifier, cb, tracker)
                if result and result.get("auto_approved"):
                    try:
                        BudgetEnforcer(config).check_or_raise("video")
                    except BudgetExceededError:
                        logger.warning("Budget exceeded in pipeline_full -- deferring video")
                        db = get_db()
                        db.enqueue_job("video", content_id=result["content_id"], max_attempts=3)
                        return True
                    video = step_video(notifier, cb, tracker)
                    if video and (video.get("video_ready") or video.get("audio_path")):
                        step_publish(notifier, cb, tracker)
                    step_analytics(notifier, tracker)
            return ok

        else:
            logger.warning(f"Unknown job type: {job_type}")
            return False

    except Exception as e:
        logger.error(f"Job execution error", extra={
            "job_id": job["id"], "type": job_type, "error": str(e)
        }, exc_info=True)
        return False


# ── Backoff schedule ───────────────────────────────────────────────────────

def get_retry_delay(attempt: int) -> int:
    """
    Pre-plan escalating backoff:
      Attempt 1 -> 5 min
      Attempt 2 -> 30 min
      Attempt 3 -> 2 hours
      Beyond    -> 2 hours (will hit max_attempts and dead-letter)
    """
    base_delays = [300, 1800, 7200]   # 5m, 30m, 2h per pre-plan
    import random
    delay = base_delays[min(attempt, len(base_delays) - 1)]
    jitter = random.randint(-30, 30)
    return delay + jitter


# ── Dead-letter log ────────────────────────────────────────────────────────

def write_dead_letter(job: dict) -> None:
    """Write permanently failed jobs to a dead-letter log for manual review."""
    dead_dir = Path("data/dead_letters")
    dead_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out = dead_dir / f"dead_{job['job_type']}_{job['id']}_{ts}.json"
    job["dead_lettered_at"] = datetime.now(timezone.utc).isoformat()
    out.write_text(json.dumps(job, indent=2))
    logger.error(
        "Job moved to dead letter queue",
        extra={"job_id": job["id"], "type": job["job_type"], "path": str(out)}
    )


# ── Main worker loop ───────────────────────────────────────────────────────

async def process_queue(config: dict) -> int:
    """
    Poll the jobs table and process any pending/retrying jobs.
    Returns the number of jobs processed.
    """
    db = get_db()
    jobs = db.get_pending_jobs()

    if not jobs:
        return 0

    logger.info(f"Found {len(jobs)} job(s) to process")
    processed = 0

    for job in jobs[:MAX_CONCURRENT_JOBS]:
        job_id = job["id"]
        attempt = job["attempts"]

        # Mark as running
        now = datetime.now(timezone.utc).isoformat()
        with db._get_conn_ctx() as conn:
            conn.execute(
                "UPDATE jobs SET status='running', attempts=attempts+1, updated_at=? WHERE id=?",
                (now, job_id)
            )

        success = await run_job(job, config)

        if success:
            db.complete_job(job_id)
            logger.info("Job completed", extra={"job_id": job_id, "type": job["job_type"]})
        else:
            next_attempt = attempt + 1
            if next_attempt >= job["max_attempts"]:
                # Dead-letter it -- write to both DB table and JSON file
                with db._get_conn_ctx() as conn:
                    conn.execute(
                        "UPDATE jobs SET status='dead', updated_at=? WHERE id=?",
                        (datetime.now(timezone.utc).isoformat(), job_id)
                    )
                db.save_dead_letter(job)
                write_dead_letter(job)

                # Notify
                try:
                    from notifications import NotificationManager, Notification, NotificationLevel
                    nm = NotificationManager(config)
                    nm.send(Notification(
                        title="💀 Job Dead-Lettered",
                        message=f"Job `{job['job_type']}` (id:{job_id}) failed {job['max_attempts']} times and was moved to dead letters. Manual review required.",
                        level=NotificationLevel.ERROR,
                    ))
                except Exception:
                    pass
            else:
                delay = get_retry_delay(next_attempt)
                db.fail_job(job_id, job.get("error_msg", "execution failed"), retry_after_seconds=delay)
                logger.warning(
                    "Job failed, scheduling retry",
                    extra={"job_id": job_id, "attempt": next_attempt, "retry_in_seconds": delay}
                )

        processed += 1

    return processed


async def run_worker(once: bool = False, config_path: str = "code/config.json") -> None:
    """
    Main worker entry point.
    Polls the jobs queue in a loop (or once if --once flag is set).
    """
    config = load_config(config_path)
    logger.info("Job worker starting", extra={"mode": "once" if once else "daemon"})

    if once:
        count = await process_queue(config)
        logger.info(f"Processed {count} job(s)")
        return

    logger.info(f"Polling every {POLL_INTERVAL_SECONDS}s")
    while True:
        try:
            count = await process_queue(config)
            if count:
                logger.info(f"Worker cycle done — processed {count} job(s)")
        except Exception as e:
            logger.error("Worker cycle error", extra={"error": str(e)}, exc_info=True)

        await asyncio.sleep(POLL_INTERVAL_SECONDS)


# ── Worker status CLI ──────────────────────────────────────────────────────

def print_worker_status() -> None:
    """Print current job queue status."""
    db = get_db()
    with db._get_conn_ctx() as conn:
        rows = conn.execute(
            "SELECT status, COUNT(*) as count, job_type FROM jobs GROUP BY status, job_type ORDER BY status"
        ).fetchall()
        dead = conn.execute(
            "SELECT COUNT(*) FROM jobs WHERE status='dead'"
        ).fetchone()[0]

    print(f"\n{'═'*50}\n  ⚡ BOLT — JOB QUEUE STATUS\n{'═'*50}")
    if not rows:
        print("  Queue is empty — no pending jobs")
    else:
        for r in rows:
            icon = {"pending":"⏳","running":"🔄","retrying":"♻️","done":"✅","dead":"💀"}.get(r[0],"·")
            print(f"  {icon} {r[0]:10s} | {r[2]:12s} | {r[1]} job(s)")
    if dead:
        print(f"\n  ⚠️  {dead} dead-lettered job(s) in data/dead_letters/")
        print(f"  Manual review required — check dead letter files")
    print(f"{'═'*50}\n")


# ── CLI ────────────────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Bolt AI Job Worker")
    parser.add_argument("--once",    action="store_true", help="Process queue once and exit")
    parser.add_argument("--status",  action="store_true", help="Show queue status and exit")
    parser.add_argument("--config",  default="code/config.json")
    args = parser.parse_args()

    if args.status:
        print_worker_status()
        return

    asyncio.run(run_worker(once=args.once, config_path=args.config))


if __name__ == "__main__":
    main()
