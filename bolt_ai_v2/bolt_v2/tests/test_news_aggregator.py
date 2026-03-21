"""
Tests for the news_aggregator module.
Covers scoring, deduplication, and HTML cleaning.
"""

import hashlib
from datetime import datetime, timezone, timedelta

from news_aggregator import (
    clean_html,
    article_age_hours,
    timeliness_score,
    deduplicate,
)


class TestCleanHtml:
    def test_strips_tags(self):
        assert clean_html("<p>Hello <b>world</b></p>") == "Hello world"

    def test_normalises_whitespace(self):
        assert clean_html("  too   many   spaces  ") == "too many spaces"

    def test_handles_none(self):
        assert clean_html(None) == ""

    def test_handles_empty(self):
        assert clean_html("") == ""


class TestArticleAgeHours:
    def test_returns_999_for_none(self):
        assert article_age_hours(None) == 999

    def test_recent_article(self):
        now = datetime.now(timezone.utc)
        one_hour_ago = now - timedelta(hours=1)
        parsed = one_hour_ago.timetuple()[:6]
        age = article_age_hours(parsed)
        assert 0.5 < age < 1.5  # roughly 1 hour

    def test_old_article(self):
        old = datetime(2020, 1, 1, tzinfo=timezone.utc)
        age = article_age_hours(old.timetuple()[:6])
        assert age > 1000


class TestTimelinessScore:
    def test_brand_new(self):
        assert timeliness_score(1) == 1.0

    def test_six_hours(self):
        assert timeliness_score(6) == 1.0

    def test_twelve_hours(self):
        assert timeliness_score(12) == 0.8

    def test_thirty_hours(self):
        assert timeliness_score(30) == 0.5

    def test_sixty_hours(self):
        assert timeliness_score(60) == 0.2

    def test_very_old(self):
        assert timeliness_score(100) == 0.0


class TestDeduplicate:
    def test_removes_exact_duplicates(self):
        articles = [
            {"title": "AI breakthrough"},
            {"title": "AI breakthrough"},
            {"title": "New robot announced"},
        ]
        result = deduplicate(articles, set())
        assert len(result) == 2

    def test_case_insensitive(self):
        articles = [
            {"title": "AI Breakthrough"},
            {"title": "ai breakthrough"},
        ]
        result = deduplicate(articles, set())
        assert len(result) == 1

    def test_respects_seen_hashes(self):
        h = hashlib.md5("ai breakthrough".encode()).hexdigest()
        articles = [{"title": "AI Breakthrough"}]
        result = deduplicate(articles, {h})
        assert len(result) == 0

    def test_preserves_order(self):
        articles = [
            {"title": "First"},
            {"title": "Second"},
            {"title": "Third"},
        ]
        result = deduplicate(articles, set())
        assert [a["title"] for a in result] == ["First", "Second", "Third"]
