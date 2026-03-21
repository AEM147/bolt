"""Bolt AI -- Shared HTTP utilities with disk caching, retries, and rate limiting.

Inspired by the Operator 1 http_utils pattern (oso4242424242/githubu-isu-meanu).
Every outbound HTTP request in the pipeline should route through this module
to get consistent retry logic, disk caching, and per-host rate limiting.

Usage:
    from http_utils import cached_get, cached_post, HTTPError

    # GET with automatic retries + disk cache
    data = cached_get("https://api.example.com/data", cache_ttl_hours=6)

    # POST (no caching, but retries + rate limiting)
    resp = cached_post("https://api.example.com/submit", json={"key": "val"})
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse

import requests

logger = logging.getLogger("bolt.http")

CACHE_DIR = Path("data/cache/http")


class HTTPError(Exception):
    """Raised when an HTTP request fails after all retries."""

    def __init__(self, url: str, status_code: int, detail: str = "") -> None:
        self.url = url
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"HTTP {status_code} for {url}: {detail}")


# ---------------------------------------------------------------------------
# Disk cache
# ---------------------------------------------------------------------------

def _cache_key(url: str, params: Optional[dict] = None) -> str:
    """Deterministic SHA-256 hash for a request (URL + sorted params)."""
    raw = url + json.dumps(params or {}, sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()


def _cache_path(key: str, cache_dir: Path = CACHE_DIR) -> Path:
    return cache_dir / f"{key}.json"


def _read_cache(key: str, ttl_hours: float, cache_dir: Path = CACHE_DIR) -> Optional[Any]:
    """Return cached response if it exists and is fresh, else None."""
    path = _cache_path(key, cache_dir)
    if not path.exists():
        return None

    age_hours = (time.time() - path.stat().st_mtime) / 3600
    if age_hours > ttl_hours:
        logger.debug("Cache expired (%.1fh > %.1fh): %s", age_hours, ttl_hours, path.name)
        return None

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        logger.warning("Corrupt cache file, ignoring: %s", path.name)
        return None


def _write_cache(key: str, data: Any, cache_dir: Path = CACHE_DIR) -> None:
    """Persist JSON-serializable response to disk."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = _cache_path(key, cache_dir)
    try:
        path.write_text(json.dumps(data, default=str), encoding="utf-8")
    except (TypeError, OSError) as exc:
        logger.warning("Failed to write cache %s: %s", path.name, exc)


# ---------------------------------------------------------------------------
# Per-host rate limiting (adapted from Operator 1 pattern)
# ---------------------------------------------------------------------------

_last_request_time_by_host: dict[str, float] = {}

# Per-host rate limits (seconds between requests).
# Sources with known rate limits get specific values.
_HOST_RATE_LIMITS: dict[str, float] = {
    # RSS feeds -- be polite, 1 req/s per host
    "openai.com": 1.0,
    "www.anthropic.com": 1.0,
    "deepmind.google": 1.0,
    "techcrunch.com": 0.5,
    "www.theverge.com": 0.5,
    "www.technologyreview.com": 1.0,
    "www.wired.com": 0.5,
    "venturebeat.com": 0.5,
    "feeds.arstechnica.com": 0.5,
    "www.sciencedaily.com": 1.0,
    "ai.googleblog.com": 1.0,
    "huggingface.co": 1.0,
    "blogs.nvidia.com": 1.0,
    "www.microsoft.com": 1.0,
    "www.artificialintelligence-news.com": 1.0,
    "www.kdnuggets.com": 1.0,
    "towardsdatascience.com": 1.0,
    # APIs -- respect documented limits
    "api.anthropic.com": 0.1,       # 50 req/min -> ~1.2s
    "api.elevenlabs.io": 3.0,       # 20 req/min -> 3s
    "api.bufferapp.com": 3.0,
    "texttospeech.googleapis.com": 0.5,
    "www.googleapis.com": 0.2,
    "graph.facebook.com": 1.0,
}

# Default delay between requests to unknown hosts
_DEFAULT_DELAY_S = 0.5


def _extract_host(url: str) -> str:
    """Extract hostname from URL for per-host rate limiting."""
    try:
        return urlparse(url).hostname or "unknown"
    except Exception:
        return "unknown"


def _rate_limit_wait(url: str) -> None:
    """Sleep if needed to respect per-host rate limits."""
    host = _extract_host(url)
    min_interval = _HOST_RATE_LIMITS.get(host, _DEFAULT_DELAY_S)
    if min_interval <= 0:
        return

    now = time.time()
    last_time = _last_request_time_by_host.get(host, 0.0)
    elapsed = now - last_time
    if elapsed < min_interval:
        sleep_time = min_interval - elapsed
        logger.debug("Rate limiting [%s]: sleeping %.2fs", host, sleep_time)
        time.sleep(sleep_time)
    _last_request_time_by_host[host] = time.time()


# ---------------------------------------------------------------------------
# Core GET with retries + caching
# ---------------------------------------------------------------------------

def cached_get(
    url: str,
    params: Optional[dict] = None,
    headers: Optional[dict] = None,
    cache_ttl_hours: float = 1.0,
    max_retries: int = 3,
    backoff_factor: float = 2.0,
    timeout: int = 15,
    cache_dir: Optional[Path] = None,
) -> Any:
    """HTTP GET with disk caching and exponential-backoff retries.

    Parameters
    ----------
    url:
        Full request URL.
    params:
        Optional query parameters.
    headers:
        Optional request headers.
    cache_ttl_hours:
        Cache freshness threshold in hours. Set to 0 to skip cache.
    max_retries:
        Number of retry attempts on failure.
    backoff_factor:
        Exponential backoff multiplier.
    timeout:
        Request timeout in seconds.
    cache_dir:
        Override cache directory. Defaults to data/cache/http.

    Returns
    -------
    Parsed JSON response, or raw text if not JSON.

    Raises
    ------
    HTTPError
        After all retries are exhausted.
    """
    effective_cache_dir = cache_dir or CACHE_DIR

    # Check cache first
    if cache_ttl_hours > 0:
        key = _cache_key(url, params)
        cached = _read_cache(key, cache_ttl_hours, effective_cache_dir)
        if cached is not None:
            logger.debug("Cache hit: %s", url[:80])
            return cached

    retryable_codes = {429, 500, 502, 503, 504}
    last_error = None

    for attempt in range(max_retries):
        _rate_limit_wait(url)

        try:
            resp = requests.get(url, params=params, headers=headers, timeout=timeout)

            if resp.status_code == 429:
                # Rate limited -- honor Retry-After header if present
                retry_after = int(resp.headers.get("Retry-After", backoff_factor ** attempt))
                logger.warning("Rate limited (429) on %s, waiting %ds", _extract_host(url), retry_after)
                time.sleep(retry_after)
                continue

            if resp.status_code in retryable_codes:
                logger.warning(
                    "Retryable HTTP %d from %s (attempt %d/%d)",
                    resp.status_code, _extract_host(url), attempt + 1, max_retries,
                )
                time.sleep(backoff_factor ** attempt)
                continue

            resp.raise_for_status()

            # Parse response
            try:
                data = resp.json()
            except (json.JSONDecodeError, ValueError):
                data = resp.text

            # Write to cache
            if cache_ttl_hours > 0:
                _write_cache(key, data, effective_cache_dir)

            return data

        except requests.exceptions.Timeout:
            logger.warning("Timeout on %s (attempt %d/%d)", _extract_host(url), attempt + 1, max_retries)
            last_error = f"Timeout after {timeout}s"
            time.sleep(backoff_factor ** attempt)

        except requests.exceptions.ConnectionError as e:
            logger.warning("Connection error on %s: %s", _extract_host(url), str(e)[:100])
            last_error = str(e)[:200]
            time.sleep(backoff_factor ** attempt)

        except requests.exceptions.HTTPError as e:
            raise HTTPError(url, e.response.status_code if e.response else 0, str(e))

    raise HTTPError(url, 0, f"All {max_retries} retries exhausted. Last error: {last_error}")


def cached_post(
    url: str,
    json_data: Optional[dict] = None,
    data: Optional[Any] = None,
    headers: Optional[dict] = None,
    max_retries: int = 3,
    backoff_factor: float = 2.0,
    timeout: int = 30,
) -> Any:
    """HTTP POST with retries (no caching -- POST is not idempotent).

    Parameters
    ----------
    url:
        Full request URL.
    json_data:
        JSON body to send.
    data:
        Form/raw body to send.
    headers:
        Optional request headers.

    Returns
    -------
    Parsed JSON response.

    Raises
    ------
    HTTPError
        After all retries are exhausted.
    """
    retryable_codes = {429, 500, 502, 503, 504}
    last_error = None

    for attempt in range(max_retries):
        _rate_limit_wait(url)

        try:
            resp = requests.post(
                url, json=json_data, data=data, headers=headers, timeout=timeout,
            )

            if resp.status_code == 429:
                retry_after = int(resp.headers.get("Retry-After", backoff_factor ** attempt))
                logger.warning("Rate limited (429) on POST %s, waiting %ds", _extract_host(url), retry_after)
                time.sleep(retry_after)
                continue

            if resp.status_code in retryable_codes:
                time.sleep(backoff_factor ** attempt)
                continue

            resp.raise_for_status()

            try:
                return resp.json()
            except (json.JSONDecodeError, ValueError):
                return resp.text

        except requests.exceptions.Timeout:
            last_error = f"Timeout after {timeout}s"
            time.sleep(backoff_factor ** attempt)

        except requests.exceptions.ConnectionError as e:
            last_error = str(e)[:200]
            time.sleep(backoff_factor ** attempt)

        except requests.exceptions.HTTPError as e:
            raise HTTPError(url, e.response.status_code if e.response else 0, str(e))

    raise HTTPError(url, 0, f"POST retries exhausted. Last error: {last_error}")


# ---------------------------------------------------------------------------
# Async variant for aiohttp (used by news_aggregator)
# ---------------------------------------------------------------------------

async def async_cached_get(
    session,
    url: str,
    cache_ttl_hours: float = 1.0,
    timeout_s: int = 10,
    cache_dir: Optional[Path] = None,
) -> Optional[str]:
    """Async HTTP GET with disk caching. Returns response text or None.

    Uses aiohttp session for concurrent fetching but still writes/reads
    the same disk cache as cached_get().

    Parameters
    ----------
    session:
        aiohttp.ClientSession instance.
    url:
        Full URL to fetch.
    cache_ttl_hours:
        Cache freshness threshold.
    timeout_s:
        Request timeout.

    Returns
    -------
    Response text (RSS XML), or None on failure.
    """
    import aiohttp

    effective_cache_dir = cache_dir or CACHE_DIR

    # Check cache
    if cache_ttl_hours > 0:
        key = _cache_key(url, None)
        cached = _read_cache(key, cache_ttl_hours, effective_cache_dir)
        if cached is not None:
            logger.debug("Async cache hit: %s", url[:80])
            return cached

    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout_s)) as resp:
            text = await resp.text()

            # Cache the raw text
            if cache_ttl_hours > 0:
                _write_cache(key, text, effective_cache_dir)

            return text
    except Exception as e:
        logger.warning("Async GET failed [%s]: %s", _extract_host(url), str(e)[:100])
        return None


# ---------------------------------------------------------------------------
# Request audit log (for debugging/monitoring)
# ---------------------------------------------------------------------------

_request_log: list[dict[str, Any]] = []


def get_request_log() -> list[dict[str, Any]]:
    """Return the audit log of all HTTP requests made during this process."""
    return list(_request_log)


def clear_request_log() -> None:
    """Clear the request audit log."""
    _request_log.clear()
