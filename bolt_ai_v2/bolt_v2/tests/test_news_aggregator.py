"""
Tests for the news_aggregator module.
Covers scoring, deduplication, HTML cleaning, and feed probing via http_utils.
"""

import hashlib
import json
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

from news_aggregator import (
    clean_html,
    article_age_hours,
    timeliness_score,
    deduplicate,
    probe_feeds,
    score_article_heuristic,
    pre_filter,
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


# ── Tests for probe_feeds using http_utils.cached_get ──────────────────────


SAMPLE_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><title>Test</title>
<item><title>AI breakthrough announced</title>
<description>A major AI company has announced a new model.</description>
<link>https://example.com/1</link></item>
<item><title>New robot deployed</title>
<description>Robots are being deployed in warehouses.</description>
<link>https://example.com/2</link></item>
</channel></rss>"""


class TestProbeFeeds:
    """Tests for probe_feeds() which uses http_utils.cached_get to
    health-check RSS feed URLs."""

    @patch("news_aggregator.cached_get")
    @patch("news_aggregator.load_config")
    def test_probe_ok_feeds(self, mock_config, mock_get):
        """Feeds that return valid RSS are reported as 'ok'."""
        mock_config.return_value = {
            "news_sources": {
                "TechCrunch": {"url": "https://techcrunch.com/feed", "reliability": 0.9},
            },
            "paths": {"queue": "/tmp/bolt_test/queue"},
        }
        mock_get.return_value = SAMPLE_RSS

        results = probe_feeds()
        assert len(results) == 1
        assert results[0]["status"] == "ok"
        assert results[0]["article_count"] == 2
        assert results[0]["error"] is None

    @patch("news_aggregator.cached_get")
    @patch("news_aggregator.load_config")
    def test_probe_empty_response(self, mock_config, mock_get):
        """Feeds that return empty content are reported as 'empty'."""
        mock_config.return_value = {
            "news_sources": {
                "Dead Feed": {"url": "https://dead.example.com/rss", "reliability": 0.5},
            },
            "paths": {"queue": "/tmp/bolt_test/queue"},
        }
        mock_get.return_value = ""

        results = probe_feeds()
        assert len(results) == 1
        assert results[0]["status"] == "empty"

    @patch("news_aggregator.cached_get")
    @patch("news_aggregator.load_config")
    def test_probe_http_error(self, mock_config, mock_get):
        """Feeds that raise HTTPError are reported as 'error'."""
        from http_utils import HTTPError
        mock_config.return_value = {
            "news_sources": {
                "Broken": {"url": "https://broken.example.com/rss", "reliability": 0.3},
            },
            "paths": {"queue": "/tmp/bolt_test/queue"},
        }
        mock_get.side_effect = HTTPError("https://broken.example.com/rss", 503, "Service Unavailable")

        results = probe_feeds()
        assert len(results) == 1
        assert results[0]["status"] == "error"
        assert "503" in results[0]["error"]

    @patch("news_aggregator.cached_get")
    @patch("news_aggregator.load_config")
    def test_probe_multiple_feeds(self, mock_config, mock_get):
        """Probe correctly reports mixed results across multiple feeds."""
        mock_config.return_value = {
            "news_sources": {
                "Good": {"url": "https://good.example.com/rss", "reliability": 0.9},
                "Bad": {"url": "https://bad.example.com/rss", "reliability": 0.5},
            },
            "paths": {"queue": "/tmp/bolt_test/queue"},
        }

        def side_effect(url, **kwargs):
            if "good" in url:
                return SAMPLE_RSS
            raise Exception("Connection refused")

        mock_get.side_effect = side_effect

        results = probe_feeds()
        assert len(results) == 2
        ok_count = sum(1 for r in results if r["status"] == "ok")
        err_count = sum(1 for r in results if r["status"] == "error")
        assert ok_count == 1
        assert err_count == 1

    @patch("news_aggregator.cached_get")
    @patch("news_aggregator.load_config")
    def test_probe_empty_rss_feed(self, mock_config, mock_get):
        """Feed that parses but has zero entries is reported as 'empty'."""
        mock_config.return_value = {
            "news_sources": {
                "Empty RSS": {"url": "https://empty.example.com/rss", "reliability": 0.7},
            },
            "paths": {"queue": "/tmp/bolt_test/queue"},
        }
        empty_rss = '<?xml version="1.0"?><rss version="2.0"><channel><title>Empty</title></channel></rss>'
        mock_get.return_value = empty_rss

        results = probe_feeds()
        assert len(results) == 1
        assert results[0]["status"] == "empty"
        assert results[0]["article_count"] == 0


class TestScoreArticleHeuristic:
    """Tests for the heuristic scoring function."""

    def test_high_reliability_recent(self):
        article = {"reliability": 1.0, "timeliness": 1.0, "title": "AI breakthrough announced"}
        score = score_article_heuristic(article)
        assert score >= 7.0

    def test_low_reliability_old(self):
        article = {"reliability": 0.3, "timeliness": 0.0, "title": "Some article"}
        score = score_article_heuristic(article)
        assert score < 3.0

    def test_impact_words_boost(self):
        base_article = {"reliability": 0.7, "timeliness": 0.8, "title": "AI update"}
        boosted_article = {"reliability": 0.7, "timeliness": 0.8, "title": "OpenAI launches breakthrough new model"}
        base_score = score_article_heuristic(base_article)
        boosted_score = score_article_heuristic(boosted_article)
        assert boosted_score > base_score

    def test_max_score_capped(self):
        article = {"reliability": 1.0, "timeliness": 1.0,
                   "title": "breakthrough launches first record billion open-source"}
        score = score_article_heuristic(article)
        assert score <= 9.0


class TestPreFilter:
    """Tests for the AI-relevance pre-filter."""

    def test_keeps_ai_articles(self):
        articles = [
            {"title": "OpenAI releases new GPT model", "summary": "A new LLM.", "age_hours": 5},
            {"title": "Best pizza in NYC", "summary": "Food review.", "age_hours": 5},
        ]
        result = pre_filter(articles)
        assert len(result) == 1
        assert "OpenAI" in result[0]["title"]

    def test_filters_old_articles(self):
        articles = [
            {"title": "Old AI news about machine learning", "summary": "Deep learning.", "age_hours": 100},
        ]
        result = pre_filter(articles)
        assert len(result) == 0

    def test_keeps_recent_ai_articles(self):
        articles = [
            {"title": "Anthropic Claude update", "summary": "New features.", "age_hours": 2},
        ]
        result = pre_filter(articles)
        assert len(result) == 1
