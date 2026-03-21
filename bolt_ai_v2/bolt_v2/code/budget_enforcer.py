#!/usr/bin/env python3
"""
Bolt AI — Budget Enforcer (budget_enforcer.py)
===============================================
Hard stops the pipeline BEFORE expensive API calls if budget is exceeded.

The cost tracker records what was spent. The budget enforcer decides
whether to ALLOW or BLOCK the next step based on configured limits.

Limits (all in config.json → cost_tracking):
  monthly_budget_alert:    Soft warning (notification sent)
  monthly_budget_hard_stop: Hard stop (pipeline halted)
  per_video_budget_alert:  Soft warning per video
  per_video_budget_hard_stop: Hard stop per video
  daily_budget_hard_stop:  Hard stop for today's spending

Usage (in pipeline steps before expensive calls):
  from budget_enforcer import BudgetEnforcer
  budget = BudgetEnforcer(config)
  budget.check_or_raise("video")   # Raises BudgetExceededError if over limit
  budget.check_or_raise("publish")

Why this matters:
  A runaway loop or misconfigured retry can trigger hundreds of
  ElevenLabs/HeyGen calls in minutes. Without a hard stop, that's
  real money. This module is the safety net.
"""

import json
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("bolt.budget")


class BudgetExceededError(Exception):
    """Raised when a hard budget limit is exceeded."""
    def __init__(self, message: str, limit_type: str, spent: float, limit: float):
        self.limit_type = limit_type
        self.spent = spent
        self.limit = limit
        super().__init__(message)


class BudgetEnforcer:
    """
    Checks spending against configured limits before each pipeline step.

    Hard stops (raise BudgetExceededError):
      - monthly_budget_hard_stop  default: $20
      - daily_budget_hard_stop    default: $5
      - per_video_budget_hard_stop default: $1

    Soft alerts (log warning + send notification, but continue):
      - monthly_budget_alert      default: $10
      - per_video_budget_alert    default: $0.50
    """

    # Defaults — config.json overrides these
    _DEFAULTS = {
        "monthly_budget_alert":      10.0,
        "monthly_budget_hard_stop":  20.0,
        "daily_budget_alert":         3.0,
        "daily_budget_hard_stop":     5.0,
        "per_video_budget_alert":     0.50,
        "per_video_budget_hard_stop": 1.00,
    }

    def __init__(self, config: dict):
        self.config    = config
        self._ct_config = config.get("cost_tracking", {})
        self._limits   = {**self._DEFAULTS, **self._ct_config}
        self._tracker  = None

    def _get_tracker(self):
        if self._tracker is None:
            from cost_tracker import CostTracker
            self._tracker = CostTracker()
        return self._tracker

    def _get_spending(self) -> dict:
        t = self._get_tracker()
        daily   = t.get_daily_summary()
        monthly = t.get_monthly_summary()
        total   = t.get_total_summary()
        avg_per_video = total.get("avg_cost_per_video", 0)
        return {
            "daily":         daily.get("total_cost", 0),
            "monthly":       monthly.get("total_cost", 0),
            "avg_per_video": avg_per_video,
            "total_videos":  total.get("total_videos", 0),
        }

    def check_or_raise(self, step: str = "general") -> None:
        """
        Check all budget limits. Raises BudgetExceededError if any hard limit
        is exceeded. Logs warnings for soft limits.

        Call this BEFORE any expensive step (video rendering, voice synthesis).
        Cheap steps (news fetch, script generation) can be called without checking.

        Args:
            step: Which pipeline step is about to run (for logging context).
        """
        if not self._ct_config.get("enabled", True):
            return  # Budget tracking disabled

        spending = self._get_spending()
        alerts   = []

        # ── Daily hard stop ──────────────────────────────────────────────
        daily_limit = self._limits["daily_budget_hard_stop"]
        daily_spent = spending["daily"]
        if daily_limit > 0 and daily_spent >= daily_limit:
            msg = (
                f"Daily budget hard stop: spent ${daily_spent:.4f} today "
                f"(limit: ${daily_limit:.2f}). "
                f"Pipeline blocked for '{step}'. Resets at midnight UTC."
            )
            logger.error(msg, extra={"step": step, "daily_spent": daily_spent, "limit": daily_limit})
            self._notify(f"🛑 Daily Budget Hard Stop", msg, "critical")
            raise BudgetExceededError(msg, "daily", daily_spent, daily_limit)

        # ── Monthly hard stop ────────────────────────────────────────────
        monthly_limit = self._limits["monthly_budget_hard_stop"]
        monthly_spent = spending["monthly"]
        if monthly_limit > 0 and monthly_spent >= monthly_limit:
            msg = (
                f"Monthly budget hard stop: spent ${monthly_spent:.4f} "
                f"(limit: ${monthly_limit:.2f}). "
                f"Pipeline blocked for '{step}'."
            )
            logger.error(msg, extra={"step": step, "monthly_spent": monthly_spent, "limit": monthly_limit})
            self._notify("🛑 Monthly Budget Hard Stop", msg, "critical")
            raise BudgetExceededError(msg, "monthly", monthly_spent, monthly_limit)

        # ── Per-video hard stop ──────────────────────────────────────────
        avg_limit  = self._limits["per_video_budget_hard_stop"]
        avg_spent  = spending["avg_per_video"]
        total_vids = spending["total_videos"]
        if avg_limit > 0 and total_vids >= 5 and avg_spent >= avg_limit:
            msg = (
                f"Per-video budget hard stop: avg cost ${avg_spent:.4f}/video "
                f"(limit: ${avg_limit:.2f}). "
                f"Check which service is expensive."
            )
            logger.error(msg, extra={"step": step, "avg_per_video": avg_spent})
            self._notify("🛑 Per-Video Budget Hard Stop", msg, "critical")
            raise BudgetExceededError(msg, "per_video", avg_spent, avg_limit)

        # ── Soft warnings (log + notify but don't stop) ──────────────────
        if self._limits["daily_budget_alert"] > 0 and daily_spent >= self._limits["daily_budget_alert"]:
            alerts.append(f"⚠️ Daily spending ${daily_spent:.4f} approaching limit ${daily_limit:.2f}")

        if self._limits["monthly_budget_alert"] > 0 and monthly_spent >= self._limits["monthly_budget_alert"]:
            alerts.append(f"⚠️ Monthly spending ${monthly_spent:.4f} approaching limit ${monthly_limit:.2f}")

        for alert in alerts:
            logger.warning(alert, extra={"step": step})
            self._notify("⚠️ Budget Alert", alert, "warning")

    def check_all(self) -> dict:
        """
        Return full budget status without raising.
        Used by /api/status and the dashboard to show budget health.
        """
        spending = self._get_spending()
        alerts   = []
        overall  = "ok"

        checks = [
            ("daily",        spending["daily"],         "daily_budget_hard_stop",  "daily_budget_alert"),
            ("monthly",      spending["monthly"],        "monthly_budget_hard_stop","monthly_budget_alert"),
            ("per_video_avg",spending["avg_per_video"],  "per_video_budget_hard_stop","per_video_budget_alert"),
        ]

        for name, spent, hard_key, soft_key in checks:
            hard = self._limits.get(hard_key, 0)
            soft = self._limits.get(soft_key, 0)
            pct  = (spent / hard * 100) if hard > 0 else 0

            if hard > 0 and spent >= hard:
                overall = "blocked"
                alerts.append({"type": "hard_stop", "metric": name, "spent": spent, "limit": hard, "pct": pct})
            elif soft > 0 and spent >= soft:
                if overall == "ok":
                    overall = "warning"
                alerts.append({"type": "warning",   "metric": name, "spent": spent, "limit": hard, "pct": pct})

        return {
            "overall":  overall,
            "spending": spending,
            "limits":   {k: v for k, v in self._limits.items()},
            "alerts":   alerts,
        }

    def _notify(self, title: str, message: str, level: str) -> None:
        """Send budget alert via notification system."""
        try:
            from notifications import NotificationManager, Notification, NotificationLevel
            lmap = {"warning": NotificationLevel.WARNING, "critical": NotificationLevel.CRITICAL}
            nm = NotificationManager(self.config)
            nm.send(Notification(title=title, message=message, level=lmap.get(level, NotificationLevel.WARNING)))
        except Exception as e:
            logger.debug(f"Budget notify failed: {e}")


# ── Wire budget checks into pipeline ──────────────────────────────────────
# Add these calls in content_automation_master.py before each expensive step:
#
#   budget = BudgetEnforcer(CONFIG)
#   try:
#       budget.check_or_raise("video")     # before video_pipeline.run()
#       budget.check_or_raise("publish")   # before platform_publisher.run()
#   except BudgetExceededError as e:
#       notify(notifier, "🛑 Pipeline Blocked", str(e), "error")
#       return
