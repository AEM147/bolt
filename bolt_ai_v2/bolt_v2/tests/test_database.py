"""
Tests for the database module.
Covers article and script CRUD operations.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import patch
from pathlib import Path


class TestDatabaseArticles:
    """Test article storage and retrieval."""

    def test_save_and_retrieve_article(self, temp_db, sample_article):
        temp_db.save_article(sample_article)
        articles = temp_db.get_recent_articles(limit=10)
        assert len(articles) >= 1
        found = [a for a in articles if a["title"] == sample_article["title"]]
        assert len(found) == 1

    def test_save_articles_batch(self, temp_db, sample_article):
        articles = [
            {**sample_article, "title": f"Article {i}"}
            for i in range(5)
        ]
        temp_db.save_articles(articles)
        result = temp_db.get_recent_articles(limit=10)
        assert len(result) >= 5


class TestDatabaseScripts:
    """Test script storage and retrieval."""

    def test_save_and_retrieve_script(self, temp_db, sample_script):
        temp_db.save_script(sample_script)
        scripts = temp_db.get_scripts(limit=10)
        assert len(scripts) >= 1
        found = [s for s in scripts if s["content_id"] == sample_script["content_id"]]
        assert len(found) == 1

    def test_get_pending_scripts(self, temp_db, sample_script):
        # Save an approved script
        temp_db.save_script(sample_script)
        # Save a pending one
        pending = {**sample_script, "content_id": "bolt_pending_001", "status": "pending_review"}
        temp_db.save_script(pending)
        result = temp_db.get_scripts(status="pending_review")
        assert any(s["content_id"] == "bolt_pending_001" for s in result)


class TestDatabaseJobs:
    """Test job queue operations."""

    def test_enqueue_and_fetch_job(self, temp_db):
        temp_db.enqueue_job("video", content_id="test_001", max_attempts=3)
        jobs = temp_db.get_pending_jobs(limit=5)
        assert len(jobs) >= 1
        assert jobs[0]["job_type"] == "video"
        assert jobs[0]["content_id"] == "test_001"
