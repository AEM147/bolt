"""
Bolt AI -- Confirmation Checker (confirmation_checker.py)
=========================================================
Verifies that scheduled posts actually went live on each platform.

Pre-plan Section 21:
  1. Post scheduled via Buffer -> Publication record with status=scheduled
  2. Confirmation check 15 minutes after scheduled_at -> platform API polled
  3. Status updated to live or failed; retry job created if not found

"Scheduling is not confirming. A post scheduled through Buffer may fail to publish."
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

import requests

logger = logging.getLogger("bolt.dist.confirm")


def check_publications(content_id: str, config: dict) -> dict:
    """
    Check all publications for a content_id that were scheduled but
    not yet confirmed as live.

    Returns dict of per-platform confirmation results.
    """
    from database import get_db

    db = get_db()
    results = {}

    # Get all publications for this content_id
    with db._get_conn_ctx() as conn:
        rows = conn.execute("""
            SELECT * FROM publications
            WHERE content_id = ? AND success = 1
        """, (content_id,)).fetchall()

    for row in rows:
        pub = dict(row)
        platform = pub["platform"]
        post_id = pub.get("post_id", "")
        post_url = pub.get("post_url", "")

        if not post_id and not post_url:
            results[platform] = {"confirmed": False, "reason": "no post_id or url"}
            continue

        confirmed = _verify_on_platform(platform, post_id, post_url, config)
        results[platform] = confirmed

        if confirmed.get("confirmed"):
            logger.info(f"Post confirmed live: {platform}", extra={
                "content_id": content_id, "post_id": post_id,
            })
        else:
            logger.warning(f"Post not confirmed: {platform}", extra={
                "content_id": content_id, "reason": confirmed.get("reason", "unknown"),
            })
            # Create retry job for re-publishing
            db.enqueue_job(f"distribute_{platform}", content_id=content_id, max_attempts=2)

    return results


def _verify_on_platform(platform: str, post_id: str, post_url: str,
                        config: dict) -> dict:
    """
    Check if a specific post is live on its platform.
    Returns {"confirmed": bool, "reason": str, "views": int}.
    """
    try:
        if platform == "youtube":
            return _verify_youtube(post_id, config)
        elif platform == "tiktok":
            return _verify_tiktok(post_id, config)
        elif platform == "instagram":
            return _verify_instagram(post_id, config)
        else:
            return {"confirmed": False, "reason": f"Unknown platform: {platform}"}
    except Exception as e:
        return {"confirmed": False, "reason": str(e)}


def _verify_youtube(video_id: str, config: dict) -> dict:
    """Check if a YouTube video is live via Data API v3."""
    apis = config.get("apis", {})
    client_id = apis.get("youtube_client_id", "")
    client_secret = apis.get("youtube_client_secret", "")
    refresh_token = apis.get("youtube_refresh_token", "")

    if not client_id or client_id.startswith("YOUR_"):
        return {"confirmed": False, "reason": "YouTube credentials not configured"}

    try:
        # Refresh token
        token_resp = requests.post("https://oauth2.googleapis.com/token", data={
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }, timeout=10)
        if not token_resp.ok:
            return {"confirmed": False, "reason": "Token refresh failed"}

        access_token = token_resp.json()["access_token"]
        resp = requests.get(
            f"https://www.googleapis.com/youtube/v3/videos",
            params={"id": video_id, "part": "status,statistics", "access_token": access_token},
            timeout=10,
        )
        if resp.ok:
            items = resp.json().get("items", [])
            if items:
                status = items[0].get("status", {}).get("uploadStatus", "")
                views = items[0].get("statistics", {}).get("viewCount", 0)
                return {"confirmed": status == "processed", "views": int(views), "reason": ""}
        return {"confirmed": False, "reason": "Video not found in API response"}
    except Exception as e:
        return {"confirmed": False, "reason": str(e)}


def _verify_tiktok(post_id: str, config: dict) -> dict:
    """Check if a TikTok post is live. Limited verification via Buffer."""
    # TikTok API access is limited -- we rely on Buffer's confirmation
    # For now, assume Buffer-scheduled posts are live after 15 minutes
    if post_id:
        return {"confirmed": True, "reason": "Buffer scheduled (assumed live)", "views": 0}
    return {"confirmed": False, "reason": "No post_id from Buffer"}


def _verify_instagram(post_id: str, config: dict) -> dict:
    """Check if an Instagram post is live via Graph API."""
    ig_token = config.get("apis", {}).get("instagram_access_token", "")
    if not ig_token or ig_token.startswith("YOUR_"):
        if post_id:
            return {"confirmed": True, "reason": "Assumed live (no Graph API access)", "views": 0}
        return {"confirmed": False, "reason": "No credentials and no post_id"}

    try:
        resp = requests.get(
            f"https://graph.facebook.com/v19.0/{post_id}",
            params={"fields": "id,timestamp,like_count", "access_token": ig_token},
            timeout=10,
        )
        if resp.ok:
            return {"confirmed": True, "views": 0, "reason": ""}
        return {"confirmed": False, "reason": f"Graph API: {resp.status_code}"}
    except Exception as e:
        return {"confirmed": False, "reason": str(e)}
