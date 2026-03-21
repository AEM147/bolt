#!/usr/bin/env python3
"""
Bolt AI — Human-in-the-Loop (HITL) Approval System
====================================================
Pauses the pipeline after script generation and waits for explicit human
approval before spending API credits on video rendering and publishing.

Three ways to approve/reject:
  1. CLI:       python hitl.py approve bolt_20260321_063000
  2. Flag file: touch data/queue/bolt_20260321_063000_APPROVED.flag
  3. Dashboard: Click Approve/Reject in the Content Queue page

The pipeline daemon polls every 60 seconds for flag files.
If no decision is made within timeout_hours, the script is auto-rejected
and a notification is sent explaining why.

Why this matters:
  - Video rendering (Vidnoz/D-ID) and voice (ElevenLabs) cost real money/quota
  - A bad script that slips past the quality gate should be caught by a human
  - The pipeline runs unattended at 6am — you review at your own pace
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

logger = logging.getLogger("bolt.hitl")

QUEUE_DIR = Path("data/queue")
FLAG_SUFFIX_APPROVED = "_APPROVED.flag"
FLAG_SUFFIX_REJECTED = "_REJECTED.flag"
POLL_INTERVAL_SECONDS = 60


# ── Core approval waiter ───────────────────────────────────────────────────

async def wait_for_approval(
    script_id: str,
    timeout_hours: float = 12.0,
    config: dict = None,
    notifier=None,
) -> bool:
    """
    Block the pipeline until a human approves or rejects a script,
    or until the timeout expires.

    Args:
        script_id:     The content_id from the script package (e.g. "bolt_20260321_063000").
        timeout_hours: Max hours to wait before auto-rejecting. Default 12h.
        config:        Full config dict for sending notifications.
        notifier:      NotificationManager instance (optional).

    Returns:
        True  — approved, continue to video rendering.
        False — rejected or timed out, abort pipeline.

    Usage:
        approved = await wait_for_approval(script["content_id"], timeout_hours=12, config=config)
        if not approved:
            return  # stop the pipeline
    """
    approved_flag = QUEUE_DIR / f"{script_id}{FLAG_SUFFIX_APPROVED}"
    rejected_flag = QUEUE_DIR / f"{script_id}{FLAG_SUFFIX_REJECTED}"
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)

    deadline = time.time() + (timeout_hours * 3600)
    started_at = datetime.now(timezone.utc)
    expires_at = started_at + timedelta(hours=timeout_hours)

    logger.info("━" * 60)
    logger.info("⏸️  PIPELINE PAUSED — WAITING FOR HUMAN REVIEW")
    logger.info(f"   Script ID:  {script_id}")
    logger.info(f"   Expires:    {expires_at.strftime('%Y-%m-%d %H:%M UTC')}")
    logger.info(f"   Approve:    python hitl.py approve {script_id}")
    logger.info(f"   Reject:     python hitl.py reject {script_id}")
    logger.info(f"   Or touch:   data/queue/{script_id}_APPROVED.flag")
    logger.info("━" * 60)

    # Send notification with approval instructions
    _send_hitl_notification(
        title="👁️ Script Review Required",
        message=(
            f"Script `{script_id}` is waiting for your approval.\n"
            f"Expires: {expires_at.strftime('%H:%M UTC')} ({timeout_hours:.0f}h window)\n\n"
            f"**To approve:** `python hitl.py approve {script_id}`\n"
            f"**To reject:**  `python hitl.py reject {script_id}`\n"
            f"**Or use the dashboard** → Content Queue → Approve"
        ),
        color=0xFFAA00,
        config=config,
        notifier=notifier,
    )

    # Poll loop
    check_count = 0
    while time.time() < deadline:
        if approved_flag.exists():
            approved_flag.unlink(missing_ok=True)
            logger.info(f"✅ APPROVED: {script_id} — continuing to video rendering")
            _send_hitl_notification(
                title="✅ Script Approved",
                message=f"`{script_id}` approved after {_elapsed(started_at)}. Video rendering starting now.",
                color=0x00E5A0, config=config, notifier=notifier,
            )
            return True

        if rejected_flag.exists():
            rejected_flag.unlink(missing_ok=True)
            logger.warning(f"❌ REJECTED: {script_id} — pipeline aborted")
            _send_hitl_notification(
                title="❌ Script Rejected",
                message=f"`{script_id}` was rejected. A new script will be generated at the next pipeline run.",
                color=0xFF4560, config=config, notifier=notifier,
            )
            return False

        # Periodic reminder every 4 hours
        check_count += 1
        if check_count % (4 * 3600 // POLL_INTERVAL_SECONDS) == 0:
            remaining = (deadline - time.time()) / 3600
            logger.info(f"⏸️  Still waiting for approval. {remaining:.1f}h remaining.")

        await asyncio.sleep(POLL_INTERVAL_SECONDS)

    # Timeout
    logger.error(f"⏰ TIMEOUT: {script_id} — no decision made in {timeout_hours}h")
    _send_hitl_notification(
        title="⏰ Review Timed Out",
        message=f"`{script_id}` was not reviewed within {timeout_hours:.0f}h and has been skipped. It remains in the queue for tomorrow's run.",
        color=0xFF8C42, config=config, notifier=notifier,
    )
    return False


# ── Dashboard-compatible approve/reject (writes to queue JSON) ─────────────

def approve_from_dashboard(script_id: str) -> bool:
    """
    Called by the dashboard API when the user clicks Approve.
    Updates the script package status AND creates the flag file.
    """
    flag = QUEUE_DIR / f"{script_id}{FLAG_SUFFIX_APPROVED}"
    flag.touch()
    logger.info(f"Dashboard approved: {script_id}")
    return _update_queue_status(script_id, "approved")


def reject_from_dashboard(script_id: str, reason: str = "") -> bool:
    """
    Called by the dashboard API when the user clicks Reject.
    """
    flag = QUEUE_DIR / f"{script_id}{FLAG_SUFFIX_REJECTED}"
    flag.touch()
    logger.info(f"Dashboard rejected: {script_id} — {reason}")
    return _update_queue_status(script_id, "rejected", reason)


def _update_queue_status(script_id: str, status: str, reason: str = "") -> bool:
    """Update the status field in the script's queue JSON file."""
    matches = list(QUEUE_DIR.glob(f"script_{script_id}*.json"))
    if not matches:
        matches = list(QUEUE_DIR.glob(f"*{script_id}*.json"))
    if not matches:
        logger.warning(f"Queue file not found for {script_id}")
        return False
    pkg = json.loads(matches[0].read_text())
    pkg["status"] = status
    pkg["review_decision"] = {
        "status": status, "reason": reason,
        "decided_at": datetime.now(timezone.utc).isoformat(),
    }
    matches[0].write_text(json.dumps(pkg, indent=2))
    return True


# ── List scripts pending review ────────────────────────────────────────────

def list_pending() -> list[dict]:
    """Return all scripts currently waiting for human review."""
    pending = []
    for f in sorted(QUEUE_DIR.glob("script_*.json")):
        try:
            pkg = json.loads(f.read_text())
            if pkg.get("status") in ("pending_review", "approved"):
                pending.append({
                    "content_id": pkg.get("content_id", f.stem),
                    "status": pkg.get("status"),
                    "title": pkg.get("article", {}).get("title", "")[:60],
                    "score": pkg.get("quality", {}).get("overall_score", 0),
                    "generated_at": pkg.get("generated_at", ""),
                })
        except Exception:
            pass
    return pending


# ── Internal helpers ───────────────────────────────────────────────────────

def _elapsed(since: datetime) -> str:
    delta = datetime.now(timezone.utc) - since
    mins = int(delta.total_seconds() // 60)
    if mins < 60:
        return f"{mins}m"
    return f"{mins//60}h {mins%60}m"


def _send_hitl_notification(title: str, message: str, color: int,
                             config: Optional[dict], notifier=None) -> None:
    """Send notification via Discord webhook and/or notifier."""
    if notifier:
        try:
            from notifications import Notification, NotificationLevel
            notifier.send(Notification(title=title, message=message,
                                        level=NotificationLevel.WARNING))
        except Exception as e:
            logger.debug(f"Notifier send failed: {e}")

    if config:
        webhook = config.get("apis", {}).get("discord_webhook_url", "")
        if webhook and not webhook.startswith("YOUR_"):
            try:
                import requests
                requests.post(webhook, json={"embeds": [{
                    "title": title, "description": message, "color": color,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "footer": {"text": "Bolt HITL Approval System"},
                }]}, timeout=8)
            except Exception as e:
                logger.debug(f"Discord notify failed: {e}")


# ── CLI ────────────────────────────────────────────────────────────────────

def main():
    import argparse
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    parser = argparse.ArgumentParser(
        description="Bolt AI — Human-in-the-Loop Approval CLI",
        epilog="Example: python hitl.py approve bolt_20260321_063000"
    )
    sub = parser.add_subparsers(dest="command")

    app = sub.add_parser("approve", help="Approve a script to continue to video rendering")
    app.add_argument("script_id", help="Content ID from the queue (e.g. bolt_20260321_063000)")

    rej = sub.add_parser("reject", help="Reject a script — pipeline will abort")
    rej.add_argument("script_id")
    rej.add_argument("--reason", default="", help="Optional reason for rejection")

    sub.add_parser("list", help="List all scripts pending review")

    args = parser.parse_args()

    if args.command == "approve":
        ok = approve_from_dashboard(args.script_id)
        if ok:
            print(f"✅ Approved: {args.script_id}")
            print("   Pipeline will detect the flag within 60 seconds and continue.")
        else:
            print(f"⚠️  Could not find queue file for {args.script_id}")
            print(f"   Creating flag file directly...")
            flag = QUEUE_DIR / f"{args.script_id}{FLAG_SUFFIX_APPROVED}"
            QUEUE_DIR.mkdir(parents=True, exist_ok=True)
            flag.touch()
            print(f"✅ Flag created: {flag}")

    elif args.command == "reject":
        ok = reject_from_dashboard(args.script_id, args.reason)
        if ok:
            print(f"❌ Rejected: {args.script_id}")
        else:
            flag = QUEUE_DIR / f"{args.script_id}{FLAG_SUFFIX_REJECTED}"
            QUEUE_DIR.mkdir(parents=True, exist_ok=True)
            flag.touch()
            print(f"❌ Rejection flag created: {flag}")

    elif args.command == "list":
        pending = list_pending()
        if not pending:
            print("No scripts pending review.")
        else:
            print(f"\n{'─'*70}")
            print(f"  Scripts pending review ({len(pending)})")
            print(f"{'─'*70}")
            for p in pending:
                print(f"  [{p['status']:14s}] [{p['score']:4.1f}] {p['content_id']}")
                print(f"               {p['title']}")
            print(f"{'─'*70}")
            print(f"  python hitl.py approve <content_id>")
            print(f"  python hitl.py reject  <content_id>\n")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
