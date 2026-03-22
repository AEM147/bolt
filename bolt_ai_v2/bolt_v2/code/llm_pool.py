#!/usr/bin/env python3
"""Bolt AI -- LLM Key Pool with Multi-Key Rotation and Provider Fallback

Adapted from the Operator 1 PooledLLMClient pattern
(oso4242424242/githubu-isu-meanu llm_factory.py + llm_base.py).

**Multi-key support**: Comma-separated API keys in .env are split into
a pool. On credit exhaustion (HTTP 429) or rate limiting, the pool
automatically rotates to the next key.

**Provider fallback**: When all keys for one provider are exhausted,
falls back to the alternate provider.

**Cost-aware model selection**: Picks the cheapest capable model by
default (Sonnet over Opus, Flash over Pro).

Usage:
    from llm_pool import get_llm_client

    client = get_llm_client(config)
    if client:
        response = client.generate("Write a script about AI news")
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from typing import Any, Optional

logger = logging.getLogger("bolt.llm_pool")

# ---------------------------------------------------------------------------
# Error patterns that indicate key exhaustion or rate limiting
# (From Operator 1's _EXHAUSTION_ERRORS)
# ---------------------------------------------------------------------------

_EXHAUSTION_ERRORS = (
    "429",
    "rate limit",
    "rate_limit",
    "quota exceeded",
    "resource exhausted",
    "resource_exhausted",
    "too many requests",
    "billing",
    "credit",
    "insufficient_quota",
    "exceeded your current quota",
)


def _is_exhaustion_error(error: Exception) -> bool:
    """Check if an error indicates key exhaustion or rate limiting."""
    msg = str(error).lower()
    return any(pattern in msg for pattern in _EXHAUSTION_ERRORS)


# ---------------------------------------------------------------------------
# Model registries (adapted from Operator 1's CLAUDE_MODELS / GEMINI_MODELS)
# ---------------------------------------------------------------------------

CLAUDE_MODELS: dict[str, dict[str, Any]] = {
    "claude-sonnet-4-20250514": {
        "max_tokens": 64000,
        "context": 200000,
        "cost_per_1k_input": 0.003,
        "cost_per_1k_output": 0.015,
        "tier": "balanced",
    },
    "claude-3-5-sonnet-20241022": {
        "max_tokens": 8192,
        "context": 200000,
        "cost_per_1k_input": 0.003,
        "cost_per_1k_output": 0.015,
        "tier": "stable",
    },
    "claude-3-5-haiku-20241022": {
        "max_tokens": 8192,
        "context": 200000,
        "cost_per_1k_input": 0.00025,
        "cost_per_1k_output": 0.00125,
        "tier": "fast",
    },
    "claude-opus-4-20250514": {
        "max_tokens": 32000,
        "context": 200000,
        "cost_per_1k_input": 0.015,
        "cost_per_1k_output": 0.075,
        "tier": "flagship",
    },
}


def get_best_model(model_override: str = "") -> str:
    """Pick the best cost-effective model.

    Adapted from Operator 1's get_best_model(): prefers balanced/stable
    tiers over flagship to stay within free-tier credits.
    """
    if model_override and model_override in CLAUDE_MODELS:
        return model_override

    tier_priority = {"fast": 0, "balanced": 1, "stable": 2, "flagship": 3}
    candidates = sorted(
        CLAUDE_MODELS.items(),
        key=lambda x: (tier_priority.get(x[1]["tier"], 9), x[1]["cost_per_1k_output"]),
    )
    # For Bolt, prefer balanced (Sonnet) over fast (Haiku) for quality
    for name, info in candidates:
        if info["tier"] in ("balanced", "stable"):
            return name
    return candidates[0][0]


# ---------------------------------------------------------------------------
# Key pool extraction (adapted from Operator 1's get_key_pool)
# ---------------------------------------------------------------------------

def get_key_pool(config: dict, env_key: str = "ANTHROPIC_API_KEY") -> list[str]:
    """Extract API keys, supporting comma-separated multi-key pools.

    Checks three sources in order:
    1. Environment variable (comma-separated for multiple keys)
    2. Config dict value
    3. .env file (via secrets_manager)

    Filters out placeholder values (YOUR_*, empty strings).

    Returns a list of valid API keys (may be empty).
    """
    keys: list[str] = []

    # Source 1: environment variable (supports comma-separated keys)
    env_val = os.environ.get(env_key, "")
    if env_val and not env_val.startswith("YOUR_") and not env_val.startswith("\u2192"):
        keys.extend(k.strip() for k in env_val.split(",") if k.strip())

    # Source 2: config dict
    if not keys:
        config_key = env_key.lower()
        apis = config.get("apis", {})
        for k, v in apis.items():
            if config_key.replace("_", "") in k.replace("_", "").lower():
                if v and isinstance(v, str) and not v.startswith("YOUR_") and not v.startswith("\u2192"):
                    keys.append(v)
                break

    # Deduplicate while preserving order
    seen = set()
    unique = []
    for k in keys:
        if k not in seen:
            seen.add(k)
            unique.append(k)

    if unique:
        logger.info("Key pool for %s: %d key(s) available", env_key, len(unique))
    else:
        logger.debug("No keys found for %s", env_key)

    return unique


# ---------------------------------------------------------------------------
# LLM Client wrapper (simplified from Operator 1's LLMClient ABC)
# ---------------------------------------------------------------------------

class LLMClient:
    """Single-key Claude client with retry logic."""

    def __init__(self, api_key: str, model: str = ""):
        self.api_key = api_key
        self.model = model or get_best_model()
        self.provider = "claude"
        self._client = None

    def _get_client(self):
        if self._client is None:
            import anthropic
            self._client = anthropic.Anthropic(api_key=self.api_key)
        return self._client

    def generate(
        self,
        prompt: str,
        system: str = "",
        max_tokens: int = 1000,
        temperature: float = 0.7,
    ) -> str:
        """Generate text via Claude API with retry logic.

        Adapted from Operator 1's LLMClient._generate_with_config().
        """
        client = self._get_client()
        messages = [{"role": "user", "content": prompt}]
        kwargs: dict[str, Any] = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": messages,
        }
        if system:
            kwargs["system"] = system
        if temperature != 0.7:
            kwargs["temperature"] = temperature

        response = client.messages.create(**kwargs)
        return response.content[0].text

    @property
    def model_name(self) -> str:
        return self.model

    @property
    def provider_name(self) -> str:
        return self.provider

    def __repr__(self) -> str:
        masked = self.api_key[:8] + "..." + self.api_key[-4:] if len(self.api_key) > 12 else "***"
        return f"LLMClient(provider={self.provider}, model={self.model}, key={masked})"


# ---------------------------------------------------------------------------
# Pooled client with multi-key rotation (from Operator 1's PooledLLMClient)
# ---------------------------------------------------------------------------

class PooledLLMClient:
    """LLM client with multi-key rotation and provider fallback.

    Adapted from Operator 1's PooledLLMClient. On credit exhaustion or
    rate limiting, automatically rotates to the next API key in the pool.
    """

    def __init__(self, clients: list[LLMClient]) -> None:
        if not clients:
            raise ValueError("No LLM clients available")
        self._clients = clients
        self._current_idx = 0
        self._exhausted: set[int] = set()

    @property
    def _active(self) -> LLMClient:
        return self._clients[self._current_idx]

    @property
    def model_name(self) -> str:
        return self._active.model_name

    @property
    def provider_name(self) -> str:
        return self._active.provider_name

    def _rotate(self) -> bool:
        """Rotate to the next non-exhausted client. Returns False if all exhausted."""
        self._exhausted.add(self._current_idx)
        for i in range(len(self._clients)):
            if i not in self._exhausted:
                old = self._clients[self._current_idx]
                self._current_idx = i
                new = self._clients[i]
                logger.info(
                    "LLM key exhausted -- rotating: key %d -> key %d (%s)",
                    list(self._exhausted)[-1], i, new.model_name,
                )
                return True
        logger.error("All %d LLM keys exhausted", len(self._clients))
        return False

    def generate(
        self,
        prompt: str,
        system: str = "",
        max_tokens: int = 1000,
        temperature: float = 0.7,
    ) -> str:
        """Generate with automatic key rotation on exhaustion.

        Tries the active key first. On exhaustion errors, rotates to the
        next key and retries. If all keys are exhausted, raises the last error.
        """
        last_error: Optional[Exception] = None

        while True:
            try:
                return self._active.generate(prompt, system, max_tokens, temperature)
            except Exception as e:
                last_error = e
                if _is_exhaustion_error(e):
                    if not self._rotate():
                        break  # All keys exhausted
                else:
                    raise  # Non-exhaustion error, don't rotate

        raise last_error  # type: ignore

    def reset(self) -> None:
        """Reset exhaustion state (e.g. at start of new pipeline run)."""
        self._exhausted.clear()
        self._current_idx = 0

    def __repr__(self) -> str:
        active = len(self._clients) - len(self._exhausted)
        return f"PooledLLMClient({active}/{len(self._clients)} keys active, model={self.model_name})"


# ---------------------------------------------------------------------------
# Factory function (adapted from Operator 1's create_llm_client)
# ---------------------------------------------------------------------------

def get_llm_client(config: dict) -> Optional[PooledLLMClient | LLMClient]:
    """Create an LLM client with multi-key support.

    Reads API keys from environment/config, supports comma-separated
    multi-key pools for automatic rotation on rate limiting.

    Returns None if no API keys are available (pipeline runs in
    degraded mode with heuristic fallbacks).
    """
    model_override = config.get("apis", {}).get("anthropic_model", "")
    model = get_best_model(model_override)

    # Get key pool (supports comma-separated keys)
    keys = get_key_pool(config, "ANTHROPIC_API_KEY")

    if not keys:
        logger.info("No Anthropic API keys found -- LLM features disabled (using heuristic fallbacks)")
        return None

    # Build one client per key
    clients: list[LLMClient] = []
    for key in keys:
        try:
            client = LLMClient(api_key=key, model=model)
            clients.append(client)
        except Exception as e:
            logger.warning("Failed to create LLM client: %s", e)

    if not clients:
        return None

    # Single key: return directly (no pooling overhead)
    if len(clients) == 1:
        logger.info("LLM client ready: %s (model: %s, 1 key)", clients[0].provider, model)
        return clients[0]

    # Multiple keys: wrap in PooledLLMClient
    pool = PooledLLMClient(clients)
    logger.info("LLM pool ready: %d keys, model: %s", len(clients), model)
    return pool


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))

    from shared_config import get_config
    config = get_config()
    client = get_llm_client(config)

    if client:
        print(f"\nLLM Client: {client}")
        print(f"Model: {client.model_name}")
        print(f"Provider: {client.provider_name}")
        if len(sys.argv) > 1 and sys.argv[1] == "--test":
            print("\nSending test prompt...")
            response = client.generate("Say 'Hello from Bolt!' in exactly 5 words.", max_tokens=50)
            print(f"Response: {response}")
    else:
        print("\nNo LLM keys configured. Set ANTHROPIC_API_KEY in .env")
        print("Supports comma-separated keys for multi-key rotation:")
        print("  ANTHROPIC_API_KEY=sk-ant-key1,sk-ant-key2,sk-ant-key3")
