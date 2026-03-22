#!/usr/bin/env python3
"""Bolt AI -- News Source Prober (HKEX-pattern inspired)

Applies the unique coding patterns discovered in the Operator 1 HKEX client
(oso4242424242/githubu-isu-meanu) to deeply probe RSS news sources:

1. **Session-based access** -- like hkex_scraper._get_session(), we create a
   requests.Session with persistent headers/cookies for polite crawling.

2. **Date-windowed queries** -- like HKEX's 14-day window limitation, we
   partition article analysis into time windows (6h/24h/48h/72h) and report
   freshness distribution per source.

3. **Field mapping (RSS -> canonical)** -- like the _BS_MAP/_IS_MAP/_CF_MAP
   dictionaries that map EastMoney STD_ITEM_CODE to canonical English names,
   we map heterogeneous RSS field names to a canonical article schema.

4. **Tiered fallback** -- like hk_hkex.py's akshare-first / scraper-fallback,
   we try http_utils.cached_get first, then fall back to a session-based GET.

5. **Client-side filtering** -- like HKEX's post-fetch stock code filtering,
   we apply AI-relevance keyword filtering after fetching.

6. **Double parsing** -- like HKEX's json.loads(response.json()["result"]),
   RSS feeds require feedparser.parse(response_text) after HTTP fetch.

Usage:
    from news_source_prober import deep_probe_source, deep_probe_all

    result = deep_probe_source("OpenAI Blog", "https://openai.com/blog/rss.xml")
    all_results = deep_probe_all()

CLI:
    python news_source_prober.py                          # Probe all sources
    python news_source_prober.py --source "OpenAI Blog"   # Probe one source
"""

from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Optional

import feedparser
import requests

from http_utils import cached_get, HTTPError

logger = logging.getLogger("bolt.prober")

# Cache directory for probe results
_PROBE_CACHE_DIR = Path("data/cache/probes")


# ---------------------------------------------------------------------------
# Canonical field mapping: RSS entry fields -> standardized schema
# (Inspired by HKEX _BS_MAP / _IS_MAP / _CF_MAP pattern)
# ---------------------------------------------------------------------------

# feedparser entry attribute -> canonical field name
_RSS_FIELD_MAP: dict[str, str] = {
    # Title variants
    "title":            "title",
    "title_detail":     "_title_detail",
    # Summary / description variants
    "summary":          "summary",
    "summary_detail":   "_summary_detail",
    "description":      "summary",
    "content":          "_content_blocks",
    # Link variants
    "link":             "link",
    "links":            "_links_list",
    "id":               "guid",
    "guidislink":       "_guid_is_link",
    # Date variants (RSS uses many different field names)
    "published":        "published_raw",
    "published_parsed": "published_parsed",
    "updated":          "updated_raw",
    "updated_parsed":   "updated_parsed",
    "created":          "created_raw",
    "created_parsed":   "created_parsed",
    # Author
    "author":           "author",
    "author_detail":    "_author_detail",
    "authors":          "_authors_list",
    # Categories / tags
    "tags":             "tags",
    "category":         "category",
    # Media
    "media_content":    "_media_content",
    "media_thumbnail":  "_media_thumbnail",
    "enclosures":       "_enclosures",
}

# AI-relevance keywords (same set used in news_aggregator.pre_filter)
_AI_KEYWORDS: set[str] = {
    "artificial intelligence", "machine learning", "deep learning",
    "neural network", "large language model", "llm", "gpt", "gemini",
    "claude", "chatgpt", "openai", "anthropic", "deepmind", "hugging face",
    "ai model", "ai tool", "ai startup", "ai regulation", "ai chip",
    "diffusion model", "transformer", "inference", "fine-tun", "rlhf",
    "generative ai", "gen ai", "multimodal", "robotics", "automation",
    "nvidia", "stable diffusion", "midjourney", "sora",
}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class CanonicalArticle:
    """Standardized article after field mapping (like HKEX's canonical rows)."""
    title: str = ""
    summary: str = ""
    link: str = ""
    guid: str = ""
    author: str = ""
    published_iso: str = ""
    age_hours: float = 999.0
    tags: list[str] = field(default_factory=list)
    ai_relevant: bool = False
    raw_fields_found: list[str] = field(default_factory=list)


@dataclass
class TimeWindow:
    """Article count within a time window (like HKEX's 14-day windows)."""
    label: str = ""
    from_hours: float = 0
    to_hours: float = 0
    count: int = 0
    articles: list[str] = field(default_factory=list)  # titles


@dataclass
class ProbeResult:
    """Full probe result for one source."""
    name: str = ""
    url: str = ""
    status: str = "error"  # ok | empty | error | unreachable
    fetch_method: str = ""  # cached_get | session_fallback
    total_articles: int = 0
    ai_relevant_count: int = 0
    time_windows: list[TimeWindow] = field(default_factory=list)
    canonical_fields_found: list[str] = field(default_factory=list)
    feed_title: str = ""
    feed_format: str = ""  # rss20 | atom10 | rdf | unknown
    error: Optional[str] = None
    probe_duration_ms: int = 0
    articles: list[CanonicalArticle] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Session management (HKEX pattern: _get_session)
# ---------------------------------------------------------------------------

def _get_session() -> requests.Session:
    """Create a polite requests session with persistent headers.

    Mirrors hkex_scraper._get_session() -- establishes a session
    with a real User-Agent and connection pooling.
    """
    session = requests.Session()
    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "application/rss+xml, application/xml, text/xml, */*",
    })
    return session


# ---------------------------------------------------------------------------
# Field mapping (HKEX pattern: _BS_MAP / _IS_MAP code-to-canonical)
# ---------------------------------------------------------------------------

def _map_entry_to_canonical(entry: Any) -> CanonicalArticle:
    """Map a feedparser entry to canonical schema using _RSS_FIELD_MAP.

    Like HKEX's STD_ITEM_CODE -> canonical_name translation, this maps
    the heterogeneous RSS field names to a standardized structure.
    """
    article = CanonicalArticle()
    found_fields: list[str] = []

    for rss_field, canonical_name in _RSS_FIELD_MAP.items():
        val = getattr(entry, rss_field, None)
        if val is not None:
            found_fields.append(rss_field)

    article.raw_fields_found = found_fields

    # Map core fields
    article.title = _clean(getattr(entry, "title", ""))
    raw_summary = getattr(entry, "summary", getattr(entry, "description", ""))
    article.summary = _clean(raw_summary)[:500]
    article.link = getattr(entry, "link", "")
    article.guid = getattr(entry, "id", article.link)
    article.author = getattr(entry, "author", "")

    # Tags
    tags_raw = getattr(entry, "tags", [])
    if tags_raw:
        article.tags = [t.get("term", "") for t in tags_raw if isinstance(t, dict)]

    # Date parsing (try multiple fields, like HKEX tries multiple date patterns)
    published_parsed = getattr(entry, "published_parsed", None)
    if not published_parsed:
        published_parsed = getattr(entry, "updated_parsed", None)
    if not published_parsed:
        published_parsed = getattr(entry, "created_parsed", None)

    if published_parsed:
        try:
            pub_dt = datetime(*published_parsed[:6], tzinfo=timezone.utc)
            article.published_iso = pub_dt.isoformat()
            article.age_hours = max(
                0, (datetime.now(timezone.utc) - pub_dt).total_seconds() / 3600
            )
        except Exception:
            pass

    # AI relevance check (like HKEX's client-side stock code filtering)
    combined = (article.title + " " + article.summary).lower()
    article.ai_relevant = any(kw in combined for kw in _AI_KEYWORDS)

    return article


def _clean(raw: str) -> str:
    """Strip HTML and normalize whitespace."""
    clean = re.sub(r"<[^>]+>", " ", raw or "")
    return re.sub(r"\s+", " ", clean).strip()


# ---------------------------------------------------------------------------
# Date-windowed analysis (HKEX pattern: 14-day window iteration)
# ---------------------------------------------------------------------------

# Time windows for article freshness analysis
_TIME_WINDOWS = [
    ("0-6h",   0,  6),
    ("6-24h",  6,  24),
    ("24-48h", 24, 48),
    ("48-72h", 48, 72),
    ("72h+",   72, 9999),
]


def _analyze_time_windows(articles: list[CanonicalArticle]) -> list[TimeWindow]:
    """Partition articles into time windows like HKEX's date-windowed queries.

    Instead of querying an API with from/to dates, we classify fetched
    articles into freshness buckets to understand source publishing cadence.
    """
    windows = []
    for label, from_h, to_h in _TIME_WINDOWS:
        in_window = [a for a in articles if from_h <= a.age_hours < to_h]
        windows.append(TimeWindow(
            label=label,
            from_hours=from_h,
            to_hours=to_h,
            count=len(in_window),
            articles=[a.title[:60] for a in in_window[:3]],
        ))
    return windows


# ---------------------------------------------------------------------------
# Tiered fetch (HKEX pattern: akshare fast path -> scraper fallback)
# ---------------------------------------------------------------------------

def _fetch_feed_tiered(url: str) -> tuple[str, str]:
    """Fetch RSS feed using tiered fallback (like HKEX's akshare -> scraper).

    Tier 1: http_utils.cached_get (disk cache + retries + rate limiting)
    Tier 2: Session-based requests.get (fresh fetch with browser headers)

    Returns (feed_text, method_used).
    """
    # Tier 1: cached_get (fast path, like akshare)
    try:
        text = cached_get(url, cache_ttl_hours=0.5, max_retries=2, timeout=15)
        if text and isinstance(text, str) and len(text) > 100:
            return text, "cached_get"
    except HTTPError as e:
        logger.debug("Tier 1 (cached_get) failed for %s: HTTP %d", url, e.status_code)
    except Exception as e:
        logger.debug("Tier 1 (cached_get) failed for %s: %s", url, str(e)[:100])

    # Tier 2: session-based fallback (like HKEX scraper)
    try:
        session = _get_session()
        resp = session.get(url, timeout=15)
        resp.raise_for_status()
        text = resp.text
        if text and len(text) > 100:
            return text, "session_fallback"
    except Exception as e:
        logger.debug("Tier 2 (session) failed for %s: %s", url, str(e)[:100])

    return "", "none"


# ---------------------------------------------------------------------------
# Main probe function
# ---------------------------------------------------------------------------

def deep_probe_source(name: str, url: str, reliability: float = 0.0) -> ProbeResult:
    """Deeply probe a single RSS source using HKEX-inspired patterns.

    Combines:
    1. Tiered fetch (cached_get -> session fallback)
    2. Double parsing (HTTP response -> feedparser)
    3. Field mapping (RSS fields -> canonical schema)
    4. Date-windowed analysis (article freshness distribution)
    5. Client-side AI-relevance filtering

    Parameters
    ----------
    name : str
        Human-readable source name.
    url : str
        RSS feed URL.
    reliability : float
        Configured reliability score (0.0-1.0).

    Returns
    -------
    ProbeResult with full diagnostic information.
    """
    start = time.time()
    result = ProbeResult(name=name, url=url)

    # Step 1: Tiered fetch
    text, method = _fetch_feed_tiered(url)
    result.fetch_method = method

    if not text:
        result.status = "unreachable"
        result.error = "Both fetch tiers failed"
        result.probe_duration_ms = int((time.time() - start) * 1000)
        return result

    # Step 2: Double parsing (like HKEX's json.loads(response.json()["result"]))
    # RSS requires feedparser.parse() after HTTP fetch
    feed = feedparser.parse(text)

    result.feed_title = getattr(feed.feed, "title", "")
    result.feed_format = feed.version or "unknown"

    if not feed.entries:
        result.status = "empty"
        result.error = f"Feed parsed ({result.feed_format}) but 0 entries"
        result.probe_duration_ms = int((time.time() - start) * 1000)
        return result

    # Step 3: Field mapping (RSS -> canonical, like _BS_MAP pattern)
    articles: list[CanonicalArticle] = []
    all_fields: set[str] = set()

    for entry in feed.entries:
        canonical = _map_entry_to_canonical(entry)
        articles.append(canonical)
        all_fields.update(canonical.raw_fields_found)

    result.articles = articles
    result.total_articles = len(articles)
    result.canonical_fields_found = sorted(all_fields)

    # Step 4: Client-side AI filtering (like HKEX's stock code filtering)
    result.ai_relevant_count = sum(1 for a in articles if a.ai_relevant)

    # Step 5: Date-windowed analysis (like HKEX's 14-day windows)
    result.time_windows = _analyze_time_windows(articles)

    result.status = "ok"
    result.probe_duration_ms = int((time.time() - start) * 1000)

    logger.info(
        "Probe [%s]: %s | %d articles (%d AI-relevant) | format=%s | %dms | via %s",
        name, result.status, result.total_articles, result.ai_relevant_count,
        result.feed_format, result.probe_duration_ms, result.fetch_method,
    )
    return result


def deep_probe_all(config_path: str = "code/config.json") -> list[ProbeResult]:
    """Probe all configured news sources."""
    from shared_config import get_config
    config = get_config(config_path)
    sources = config.get("news_sources", {})

    results = []
    for name, info in sources.items():
        result = deep_probe_source(
            name=name,
            url=info["url"],
            reliability=info.get("reliability", 0.0),
        )
        results.append(result)
        # Polite delay between sources
        time.sleep(0.3)

    ok = sum(1 for r in results if r.status == "ok")
    logger.info("Deep probe complete: %d/%d sources OK", ok, len(results))
    return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _print_probe_result(r: ProbeResult) -> None:
    """Pretty-print a single probe result."""
    status_icon = {"ok": "OK", "empty": "EMPTY", "error": "ERR", "unreachable": "DOWN"}.get(r.status, "???")
    print(f"\n  [{status_icon:5s}] {r.name}")
    print(f"         URL:      {r.url}")
    print(f"         Format:   {r.feed_format} | Title: {r.feed_title[:50]}")
    print(f"         Method:   {r.fetch_method} | Duration: {r.probe_duration_ms}ms")
    print(f"         Articles: {r.total_articles} total, {r.ai_relevant_count} AI-relevant")
    print(f"         Fields:   {', '.join(r.canonical_fields_found[:10])}")

    if r.time_windows:
        print("         Freshness:")
        for w in r.time_windows:
            bar = "#" * min(w.count, 20)
            print(f"           {w.label:8s} {w.count:3d} {bar}")
            for title in w.articles[:2]:
                print(f"                    - {title}")

    if r.error:
        print(f"         Error:    {r.error}")


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    # Add code dir to path
    sys.path.insert(0, str(Path(__file__).parent))

    if "--source" in sys.argv:
        idx = sys.argv.index("--source")
        source_name = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else ""
        from shared_config import get_config
        config = get_config()
        sources = config.get("news_sources", {})
        if source_name in sources:
            result = deep_probe_source(source_name, sources[source_name]["url"],
                                        sources[source_name].get("reliability", 0))
            print(f"\n{'='*65}")
            print(f"  Deep Probe: {source_name}")
            print(f"{'='*65}")
            _print_probe_result(result)
            print(f"{'='*65}\n")
        else:
            print(f"Source '{source_name}' not found. Available: {', '.join(sources.keys())}")
    else:
        results = deep_probe_all()
        print(f"\n{'='*65}")
        print(f"  Deep Probe Results ({sum(1 for r in results if r.status=='ok')}/{len(results)} OK)")
        print(f"{'='*65}")
        for r in results:
            _print_probe_result(r)
        print(f"{'='*65}\n")
