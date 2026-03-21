#!/usr/bin/env python3
"""
Bolt AI -- Centralized Configuration Loader
============================================
Single source of truth for loading config.json with secrets injected.

Every module should import config from here instead of loading config.json directly.
This ensures all API keys are properly resolved from environment variables / .env
via secrets_manager.load_all_secrets().

Usage:
    from shared_config import get_config

    config = get_config()
    api_key = config["apis"]["anthropic_api_key"]  # Real key, not placeholder
"""

import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger("bolt.config")

_CONFIG_CACHE: Optional[dict] = None
_DEFAULT_CONFIG_PATH = Path(__file__).parent / "config.json"


def get_config(path: Optional[str] = None, force_reload: bool = False) -> dict:
    """
    Load config.json with all secrets injected from environment variables.

    Uses a module-level cache so the file is only read once per process.
    Pass force_reload=True to re-read from disk (useful in tests).

    Args:
        path:         Override path to config.json. Defaults to code/config.json.
        force_reload: If True, bypass the cache and reload from disk.

    Returns:
        Config dict with all secrets resolved.
    """
    global _CONFIG_CACHE

    if _CONFIG_CACHE is not None and not force_reload and path is None:
        return _CONFIG_CACHE

    from secrets_manager import load_all_secrets

    config_path = Path(path) if path else _DEFAULT_CONFIG_PATH
    if not config_path.exists():
        # Fallback: try relative path from working directory
        config_path = Path("code/config.json")

    if not config_path.exists():
        raise FileNotFoundError(
            f"Config file not found at {config_path}. "
            "Run from the project root or pass the correct path."
        )

    logger.debug(f"Loading config from {config_path}")
    with open(config_path) as f:
        raw = json.load(f)

    config = load_all_secrets(raw)

    if path is None:
        _CONFIG_CACHE = config

    return config


def reset_cache() -> None:
    """Clear the config cache. Useful in tests."""
    global _CONFIG_CACHE
    _CONFIG_CACHE = None
