"""
Shared pytest fixtures for Bolt AI tests.
"""

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

# Add code directory to path so modules can be imported
sys.path.insert(0, str(Path(__file__).parent.parent / "code"))


@pytest.fixture
def sample_config():
    """A minimal config dict with test values (no real API keys)."""
    return {
        "version": "2.2-test",
        "character": {
            "name": "Bolt",
            "tagline": "Your AI news robot",
            "catchphrases": ["Stay curious, humans!"],
            "personality": "enthusiastic",
            "target_duration_seconds": 45,
            "max_words_per_script": 130,
        },
        "apis": {
            "anthropic_api_key": "sk-ant-test-key",
            "anthropic_model": "claude-sonnet-4-20250514",
            "elevenlabs_api_key": "",
            "elevenlabs_voice_id": "",
            "google_cloud_tts_key": "",
            "discord_webhook_url": "",
            "youtube_client_id": "",
            "youtube_client_secret": "",
            "youtube_refresh_token": "",
            "buffer_access_token": "",
            "tiktok_access_token": "",
            "instagram_access_token": "",
            "instagram_user_id": "",
            "vidnoz_api_key": "",
            "vidnoz_avatar_id": "",
            "did_api_key": "",
            "did_presenter_url": "",
        },
        "platforms": {
            "youtube": {"enabled": False, "post_time": "14:00", "timezone": "UTC"},
            "tiktok": {"enabled": False, "post_time": "19:00", "timezone": "UTC"},
            "instagram": {"enabled": False, "post_time": "12:00", "timezone": "UTC"},
        },
        "content_pillars": {
            "monday": "ai_news",
            "tuesday": "ai_tools",
            "wednesday": "ai_concepts",
            "thursday": "ai_news",
            "friday": "ai_tools",
            "saturday": "ai_concepts",
            "sunday": "ai_daily_life",
        },
        "automation": {
            "news_fetch_interval_hours": 6,
            "auto_publish_threshold": 8.5,
            "auto_publish_enabled": False,
            "review_queue_enabled": True,
            "max_retries": 3,
            "notify_discord": False,
        },
        "quality_gate": {
            "min_script_words": 80,
            "max_script_words": 135,
            "min_overall_score": 8.5,
            "auto_approve_above": 9.0,
            "auto_reject_below": 6.0,
            "banned_words": ["allegedly", "reportedly"],
        },
        "cost_tracking": {
            "monthly_budget_alert": 10.0,
            "monthly_budget_hard_stop": 20.0,
            "daily_budget_alert": 3.0,
            "daily_budget_hard_stop": 5.0,
            "per_video_budget_alert": 0.50,
            "per_video_budget_hard_stop": 1.00,
        },
        "hashtags": {
            "ai_news": ["#AINews", "#AI"],
            "ai_tools": ["#AITools"],
            "ai_concepts": ["#LearnAI"],
            "ai_daily_life": ["#AILife"],
        },
        "news_sources": {
            "Test Source": {"url": "https://example.com/rss", "reliability": 0.9}
        },
        "paths": {
            "audio": "/tmp/bolt_test/audio",
            "video": "/tmp/bolt_test/video",
            "thumbnails": "/tmp/bolt_test/thumbnails",
            "queue": "/tmp/bolt_test/queue",
            "published": "/tmp/bolt_test/published",
            "analytics": "/tmp/bolt_test/analytics",
        },
    }


@pytest.fixture
def sample_config_file(sample_config, tmp_path):
    """Write sample config to a temp file and return the path."""
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(sample_config, indent=2))
    return str(config_path)


@pytest.fixture
def temp_db(tmp_path):
    """Create a temporary SQLite database and return the DB instance."""
    db_path = tmp_path / "test_bolt.db"
    # Patch the default path before importing
    with patch("database.DEFAULT_DB_PATH", db_path):
        from database import BoltDB
        db = BoltDB(str(db_path))
        yield db


@pytest.fixture
def sample_article():
    """A sample article dict as returned by news_aggregator."""
    return {
        "title": "OpenAI Releases GPT-5 with Revolutionary Capabilities",
        "summary": "OpenAI has announced GPT-5, featuring major improvements in reasoning.",
        "link": "https://example.com/gpt5",
        "source": "Test Source",
        "reliability": 0.95,
        "age_hours": 4.0,
        "timeliness": 1.0,
        "published_iso": "2026-03-21T10:00:00+00:00",
        "claude_score": 8.7,
        "heuristic_score": 7.5,
        "pillar": "ai_news",
    }


@pytest.fixture
def sample_script():
    """A sample script dict as returned by script_generator."""
    return {
        "content_id": "bolt_20260321_063000",
        "article": {
            "title": "OpenAI Releases GPT-5",
            "source": "Test Source",
        },
        "pillar": "ai_news",
        "script": (
            "Hold on to your circuits, humans! OpenAI just dropped GPT-5 and it is "
            "absolutely wild. This new model can reason through complex problems like "
            "a human scientist. It can write code, analyze data, and even create art "
            "that would make Picasso jealous. The biggest deal? It uses 90 percent less "
            "energy than GPT-4 while being ten times smarter. This means AI is about to "
            "get a lot more accessible for everyone. If you are not paying attention to AI "
            "right now, you are missing the biggest tech revolution in history. "
            "Stay curious, humans!"
        ),
        "quality": {
            "hook_strength": 9.0,
            "simplicity": 9.2,
            "bolt_voice": 8.8,
            "pacing": 9.0,
            "word_count": 112,
            "overall_score": 9.0,
            "pass": True,
            "feedback": "",
        },
        "captions": {
            "youtube": {"title": "GPT-5 Is HERE", "description": "The future is now."},
            "tiktok": {"caption": "GPT-5 just dropped"},
            "instagram": {"caption": "OpenAI changed everything"},
        },
        "status": "approved",
        "auto_approved": True,
        "generated_at": "2026-03-21T06:30:00+00:00",
    }
