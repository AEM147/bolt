"""
Tests for persistent article deduplication across pipeline runs.

The pre-plan requires that the same story is never processed twice
across runs. This test suite verifies the article_hashes table and
the DB-backed dedup methods.
"""

import hashlib

import pytest
from database import BoltDB


class TestArticleHashStorage:
    """Verify that article hashes are persisted and queried correctly."""

    def test_store_and_check_hash(self, temp_db: BoltDB):
        articles = [{"title": "GPT-5 Launches Today", "source": "TechCrunch"}]
        stored = temp_db.store_article_hashes(articles)
        assert stored == 1

        h = hashlib.md5("gpt-5 launches today".encode()).hexdigest()
        assert temp_db.has_article_hash(h)

    def test_unknown_hash_returns_false(self, temp_db: BoltDB):
        assert not temp_db.has_article_hash("deadbeef" * 4)

    def test_get_seen_hashes_returns_set(self, temp_db: BoltDB):
        articles = [
            {"title": "Article One", "source": "A"},
            {"title": "Article Two", "source": "B"},
        ]
        temp_db.store_article_hashes(articles)
        seen = temp_db.get_seen_hashes()
        assert len(seen) == 2
        assert isinstance(seen, set)

    def test_duplicate_store_is_idempotent(self, temp_db: BoltDB):
        articles = [{"title": "Same Title", "source": "X"}]
        temp_db.store_article_hashes(articles)
        temp_db.store_article_hashes(articles)  # second call
        seen = temp_db.get_seen_hashes()
        assert len(seen) == 1

    def test_prune_old_hashes(self, temp_db: BoltDB):
        # Store some articles
        articles = [{"title": "Old News", "source": "Y"}]
        temp_db.store_article_hashes(articles)

        # Pruning with max_age_days=0 should remove everything
        deleted = temp_db.prune_old_hashes(max_age_days=0)
        assert deleted >= 1
        assert len(temp_db.get_seen_hashes()) == 0

    def test_prune_keeps_recent_hashes(self, temp_db: BoltDB):
        articles = [{"title": "Fresh News", "source": "Z"}]
        temp_db.store_article_hashes(articles)

        # Pruning with a large max_age should keep everything
        deleted = temp_db.prune_old_hashes(max_age_days=365)
        assert deleted == 0
        assert len(temp_db.get_seen_hashes()) == 1


class TestDeduplicateWithPersistentHashes:
    """Verify that the deduplicate() function works with DB-loaded hashes."""

    def test_dedup_skips_previously_seen(self, temp_db: BoltDB):
        from news_aggregator import deduplicate

        # Store a hash in the DB
        old_articles = [{"title": "AI Breakthrough", "source": "Test"}]
        temp_db.store_article_hashes(old_articles)
        seen = temp_db.get_seen_hashes()

        # New run has the same article plus a new one
        new_articles = [
            {"title": "AI Breakthrough"},
            {"title": "Completely New Story"},
        ]
        result = deduplicate(new_articles, seen)

        # Only the new story should survive
        assert len(result) == 1
        assert result[0]["title"] == "Completely New Story"
