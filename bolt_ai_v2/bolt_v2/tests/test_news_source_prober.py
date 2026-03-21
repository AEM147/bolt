"""
Tests for news_source_prober.py -- HKEX-pattern inspired RSS probing.
Covers field mapping, time windowing, tiered fetch, and client-side filtering.
"""

from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

from news_source_prober import (
    _map_entry_to_canonical,
    _analyze_time_windows,
    _clean,
    deep_probe_source,
    CanonicalArticle,
    TimeWindow,
    _AI_KEYWORDS,
    _RSS_FIELD_MAP,
)


# ── Sample RSS XML for mocking ────────────────────────────────────────────

SAMPLE_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
<title>Test AI Blog</title>
<item>
  <title>OpenAI launches GPT-5 with amazing capabilities</title>
  <description>A new large language model that changes everything.</description>
  <link>https://example.com/gpt5</link>
  <pubDate>Thu, 20 Mar 2026 12:00:00 +0000</pubDate>
  <category>AI</category>
</item>
<item>
  <title>Best recipes for spring 2026</title>
  <description>Cooking tips for the season.</description>
  <link>https://example.com/recipes</link>
  <pubDate>Wed, 19 Mar 2026 08:00:00 +0000</pubDate>
</item>
<item>
  <title>Anthropic Claude update improves reasoning</title>
  <description>Claude gets smarter with new fine-tuning approach.</description>
  <link>https://example.com/claude</link>
  <pubDate>Mon, 17 Mar 2026 10:00:00 +0000</pubDate>
</item>
</channel>
</rss>"""


# ── Field mapping tests (HKEX _BS_MAP pattern) ────────────────────────────


class TestRSSFieldMap:
    """Verify the RSS field mapping dictionary covers essential fields."""

    def test_title_mapped(self):
        assert "title" in _RSS_FIELD_MAP
        assert _RSS_FIELD_MAP["title"] == "title"

    def test_summary_mapped(self):
        assert "summary" in _RSS_FIELD_MAP
        assert _RSS_FIELD_MAP["summary"] == "summary"

    def test_link_mapped(self):
        assert "link" in _RSS_FIELD_MAP
        assert _RSS_FIELD_MAP["link"] == "link"

    def test_date_fields_mapped(self):
        assert "published" in _RSS_FIELD_MAP
        assert "published_parsed" in _RSS_FIELD_MAP
        assert "updated" in _RSS_FIELD_MAP
        assert "updated_parsed" in _RSS_FIELD_MAP

    def test_map_has_minimum_coverage(self):
        """Mapping should cover at least 15 RSS field variants."""
        assert len(_RSS_FIELD_MAP) >= 15


class TestMapEntryToCanonical:
    """Test the feedparser entry -> canonical article mapping."""

    def test_maps_basic_fields(self):
        entry = MagicMock()
        entry.title = "Test AI Article"
        entry.summary = "<p>Some <b>bold</b> content</p>"
        entry.link = "https://example.com/test"
        entry.id = "https://example.com/test"
        entry.author = "Test Author"
        entry.published_parsed = (2026, 3, 20, 12, 0, 0, 3, 79, 0)
        entry.tags = [{"term": "AI"}, {"term": "Tech"}]
        entry.description = None
        entry.updated_parsed = None
        entry.created_parsed = None

        article = _map_entry_to_canonical(entry)

        assert article.title == "Test AI Article"
        assert "<b>" not in article.summary  # HTML tags stripped
        assert article.link == "https://example.com/test"
        assert article.author == "Test Author"
        assert "AI" in article.tags
        assert article.published_iso != ""

    def test_ai_relevance_detection(self):
        entry = MagicMock()
        entry.title = "OpenAI launches new GPT model"
        entry.summary = "A new large language model."
        entry.link = ""
        entry.id = ""
        entry.author = ""
        entry.published_parsed = None
        entry.updated_parsed = None
        entry.created_parsed = None
        entry.tags = []

        article = _map_entry_to_canonical(entry)
        assert article.ai_relevant is True

    def test_non_ai_article_not_relevant(self):
        entry = MagicMock()
        entry.title = "Best pizza in NYC"
        entry.summary = "Food review and restaurant guide."
        entry.link = ""
        entry.id = ""
        entry.author = ""
        entry.published_parsed = None
        entry.updated_parsed = None
        entry.created_parsed = None
        entry.tags = []

        article = _map_entry_to_canonical(entry)
        assert article.ai_relevant is False

    def test_tracks_raw_fields_found(self):
        entry = MagicMock()
        entry.title = "Test"
        entry.summary = "Summary"
        entry.link = "http://test.com"
        entry.id = "123"
        entry.author = ""
        entry.published_parsed = None
        entry.updated_parsed = None
        entry.created_parsed = None
        entry.tags = []

        article = _map_entry_to_canonical(entry)
        assert len(article.raw_fields_found) > 0


# ── Date-windowed analysis tests (HKEX 14-day window pattern) ─────────────


class TestTimeWindows:
    """Test date-windowed article analysis."""

    def test_articles_sorted_into_windows(self):
        articles = [
            CanonicalArticle(title="Fresh", age_hours=2),
            CanonicalArticle(title="Today", age_hours=10),
            CanonicalArticle(title="Yesterday", age_hours=30),
            CanonicalArticle(title="Old", age_hours=60),
            CanonicalArticle(title="Ancient", age_hours=200),
        ]
        windows = _analyze_time_windows(articles)
        assert len(windows) == 5

        # 0-6h window should have 1 article
        assert windows[0].label == "0-6h"
        assert windows[0].count == 1

        # 6-24h should have 1
        assert windows[1].count == 1

        # 24-48h should have 1
        assert windows[2].count == 1

        # 48-72h should have 1
        assert windows[3].count == 1

        # 72h+ should have 1
        assert windows[4].count == 1

    def test_empty_articles_produce_zero_counts(self):
        windows = _analyze_time_windows([])
        assert all(w.count == 0 for w in windows)

    def test_window_titles_limited(self):
        """Window articles list should be capped at 3 titles."""
        articles = [CanonicalArticle(title=f"Article {i}", age_hours=2) for i in range(10)]
        windows = _analyze_time_windows(articles)
        assert len(windows[0].articles) <= 3


# ── Clean HTML helper ─────────────────────────────────────────────────────


class TestClean:
    def test_strips_html(self):
        assert _clean("<p>Hello <b>world</b></p>") == "Hello world"

    def test_normalizes_whitespace(self):
        assert _clean("  too   many   spaces  ") == "too many spaces"

    def test_handles_none(self):
        assert _clean(None) == ""


# ── Tiered fetch + full probe tests ───────────────────────────────────────


class TestDeepProbeSource:
    """Test the full probe pipeline with mocked HTTP."""

    @patch("news_source_prober.cached_get")
    def test_probe_ok_via_cached_get(self, mock_get):
        """Tier 1 (cached_get) succeeds -- should report 'ok' and 'cached_get'."""
        mock_get.return_value = SAMPLE_RSS

        result = deep_probe_source("Test Blog", "https://test.com/rss")

        assert result.status == "ok"
        assert result.fetch_method == "cached_get"
        assert result.total_articles == 3
        assert result.ai_relevant_count == 2  # GPT-5 and Claude articles
        assert result.feed_format == "rss20"
        assert len(result.time_windows) == 5

    @patch("news_source_prober._get_session")
    @patch("news_source_prober.cached_get")
    def test_probe_falls_back_to_session(self, mock_get, mock_session):
        """Tier 1 fails, Tier 2 (session) succeeds."""
        mock_get.side_effect = Exception("cache miss")

        mock_resp = MagicMock()
        mock_resp.text = SAMPLE_RSS
        mock_resp.raise_for_status = MagicMock()
        mock_session.return_value.get.return_value = mock_resp

        result = deep_probe_source("Test Blog", "https://test.com/rss")

        assert result.status == "ok"
        assert result.fetch_method == "session_fallback"
        assert result.total_articles == 3

    @patch("news_source_prober._get_session")
    @patch("news_source_prober.cached_get")
    def test_probe_unreachable(self, mock_get, mock_session):
        """Both tiers fail -- should report 'unreachable'."""
        mock_get.side_effect = Exception("fail")
        mock_session.return_value.get.side_effect = Exception("also fail")

        result = deep_probe_source("Dead Blog", "https://dead.com/rss")

        assert result.status == "unreachable"
        assert result.error is not None

    @patch("news_source_prober.cached_get")
    def test_probe_empty_feed(self, mock_get):
        """Feed parses but has no entries."""
        empty_rss = '<?xml version="1.0"?><rss version="2.0"><channel><title>Empty</title></channel></rss>'
        mock_get.return_value = empty_rss

        result = deep_probe_source("Empty Blog", "https://empty.com/rss")

        assert result.status == "empty"
        assert result.total_articles == 0

    @patch("news_source_prober.cached_get")
    def test_probe_captures_canonical_fields(self, mock_get):
        """Probe should report which RSS fields were found in the feed."""
        mock_get.return_value = SAMPLE_RSS

        result = deep_probe_source("Test Blog", "https://test.com/rss")

        assert len(result.canonical_fields_found) > 0
        assert "link" in result.canonical_fields_found
        assert "title" in result.canonical_fields_found

    @patch("news_source_prober.cached_get")
    def test_probe_duration_measured(self, mock_get):
        """Probe should measure execution time."""
        mock_get.return_value = SAMPLE_RSS

        result = deep_probe_source("Test Blog", "https://test.com/rss")

        assert result.probe_duration_ms >= 0
