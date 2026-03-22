"""
Tests for llm_pool.py -- multi-key rotation and provider fallback.
Adapted from Operator 1's PooledLLMClient pattern.
"""

import os
from unittest.mock import patch, MagicMock

import pytest

from llm_pool import (
    get_key_pool,
    get_best_model,
    get_llm_client,
    LLMClient,
    PooledLLMClient,
    _is_exhaustion_error,
    CLAUDE_MODELS,
)


class TestKeyPool:
    """Test multi-key pool extraction."""

    def test_single_key_from_env(self):
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-test-key"}):
            keys = get_key_pool({}, "ANTHROPIC_API_KEY")
            assert keys == ["sk-ant-test-key"]

    def test_comma_separated_keys(self):
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-key1,sk-key2,sk-key3"}):
            keys = get_key_pool({}, "ANTHROPIC_API_KEY")
            assert len(keys) == 3
            assert keys == ["sk-key1", "sk-key2", "sk-key3"]

    def test_filters_placeholder_keys(self):
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "YOUR_API_KEY"}):
            keys = get_key_pool({}, "ANTHROPIC_API_KEY")
            assert keys == []

    def test_filters_arrow_placeholders(self):
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "\u2192 set ANTHROPIC_API_KEY in .env"}):
            keys = get_key_pool({}, "ANTHROPIC_API_KEY")
            assert keys == []

    def test_falls_back_to_config(self):
        with patch.dict(os.environ, {}, clear=True):
            # Remove env var if it exists
            os.environ.pop("ANTHROPIC_API_KEY", None)
            config = {"apis": {"anthropic_api_key": "sk-from-config"}}
            keys = get_key_pool(config, "ANTHROPIC_API_KEY")
            assert keys == ["sk-from-config"]

    def test_deduplicates_keys(self):
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-dup,sk-dup,sk-other"}):
            keys = get_key_pool({}, "ANTHROPIC_API_KEY")
            assert len(keys) == 2
            assert keys == ["sk-dup", "sk-other"]

    def test_empty_env_and_config(self):
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("ANTHROPIC_API_KEY", None)
            keys = get_key_pool({"apis": {}}, "ANTHROPIC_API_KEY")
            assert keys == []


class TestModelSelection:
    """Test cost-aware model selection."""

    def test_default_picks_balanced(self):
        model = get_best_model()
        info = CLAUDE_MODELS[model]
        assert info["tier"] in ("balanced", "stable")

    def test_override_respected(self):
        model = get_best_model("claude-opus-4-20250514")
        assert model == "claude-opus-4-20250514"

    def test_invalid_override_falls_back(self):
        model = get_best_model("nonexistent-model")
        assert model in CLAUDE_MODELS


class TestExhaustionDetection:
    """Test error pattern matching for key rotation."""

    def test_detects_429(self):
        assert _is_exhaustion_error(Exception("HTTP 429 Too Many Requests"))

    def test_detects_rate_limit(self):
        assert _is_exhaustion_error(Exception("rate limit exceeded"))

    def test_detects_quota(self):
        assert _is_exhaustion_error(Exception("quota exceeded for this billing period"))

    def test_non_exhaustion_error(self):
        assert not _is_exhaustion_error(Exception("invalid API key format"))

    def test_generic_error(self):
        assert not _is_exhaustion_error(Exception("connection refused"))


class TestPooledLLMClient:
    """Test multi-key rotation behavior."""

    def test_single_client_works(self):
        mock_client = MagicMock(spec=LLMClient)
        mock_client.generate.return_value = "Hello from Bolt!"
        mock_client.model_name = "claude-sonnet-4-20250514"
        mock_client.provider_name = "claude"

        pool = PooledLLMClient([mock_client])
        result = pool.generate("Say hello")
        assert result == "Hello from Bolt!"

    def test_rotates_on_exhaustion(self):
        client1 = MagicMock(spec=LLMClient)
        client1.generate.side_effect = Exception("429 rate limit exceeded")
        client1.model_name = "model1"

        client2 = MagicMock(spec=LLMClient)
        client2.generate.return_value = "Response from key 2"
        client2.model_name = "model2"

        pool = PooledLLMClient([client1, client2])
        result = pool.generate("Test prompt")
        assert result == "Response from key 2"

    def test_raises_when_all_exhausted(self):
        client1 = MagicMock(spec=LLMClient)
        client1.generate.side_effect = Exception("429 rate limit")
        client1.model_name = "m1"

        client2 = MagicMock(spec=LLMClient)
        client2.generate.side_effect = Exception("quota exceeded")
        client2.model_name = "m2"

        pool = PooledLLMClient([client1, client2])
        with pytest.raises(Exception, match="quota exceeded"):
            pool.generate("Test")

    def test_non_exhaustion_error_not_rotated(self):
        client1 = MagicMock(spec=LLMClient)
        client1.generate.side_effect = ValueError("bad input")
        client1.model_name = "m1"

        client2 = MagicMock(spec=LLMClient)
        client2.model_name = "m2"

        pool = PooledLLMClient([client1, client2])
        with pytest.raises(ValueError, match="bad input"):
            pool.generate("Test")
        # client2 should NOT have been called
        client2.generate.assert_not_called()

    def test_reset_clears_exhaustion(self):
        client1 = MagicMock(spec=LLMClient)
        client1.model_name = "m1"
        client1.provider_name = "claude"

        pool = PooledLLMClient([client1])
        pool._exhausted.add(0)
        pool.reset()
        assert len(pool._exhausted) == 0
        assert pool._current_idx == 0

    def test_repr(self):
        client = MagicMock(spec=LLMClient)
        client.model_name = "claude-sonnet-4-20250514"
        pool = PooledLLMClient([client])
        assert "1/1 keys active" in repr(pool)


class TestGetLLMClient:
    """Test the factory function."""

    def test_returns_none_without_keys(self):
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("ANTHROPIC_API_KEY", None)
            client = get_llm_client({"apis": {}})
            assert client is None

    def test_returns_single_client_for_one_key(self):
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test-single"}):
            with patch.dict("sys.modules", {"anthropic": MagicMock()}):
                client = get_llm_client({"apis": {"anthropic_model": "claude-sonnet-4-20250514"}})
                assert client is not None
                assert isinstance(client, LLMClient)

    def test_returns_pooled_client_for_multiple_keys(self):
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-key1,sk-key2"}):
            with patch.dict("sys.modules", {"anthropic": MagicMock()}):
                client = get_llm_client({"apis": {}})
                assert client is not None
                assert isinstance(client, PooledLLMClient)
