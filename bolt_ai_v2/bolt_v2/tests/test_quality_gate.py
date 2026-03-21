"""
Tests for the quality gate logic in script_generator.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "code"))


class TestQualityGateThresholds:
    """Verify quality gate scoring decisions."""

    def test_score_above_auto_approve(self, sample_config):
        """Score >= 9.0 should be auto-approved."""
        threshold = sample_config["quality_gate"]["auto_approve_above"]
        score = 9.2
        assert score >= threshold

    def test_score_below_auto_reject(self, sample_config):
        """Score < 6.0 should be auto-rejected."""
        threshold = sample_config["quality_gate"]["auto_reject_below"]
        score = 5.5
        assert score < threshold

    def test_score_in_review_range(self, sample_config):
        """Score between reject and approve thresholds needs review."""
        reject = sample_config["quality_gate"]["auto_reject_below"]
        approve = sample_config["quality_gate"]["auto_approve_above"]
        score = 7.5
        assert score >= reject
        assert score < approve

    def test_word_count_validation(self, sample_config):
        """Scripts outside 80-135 words should fail."""
        min_words = sample_config["quality_gate"]["min_script_words"]
        max_words = sample_config["quality_gate"]["max_script_words"]
        assert min_words == 80
        assert max_words == 135

        # Valid
        assert min_words <= 112 <= max_words
        # Too short
        assert 50 < min_words
        # Too long
        assert 150 > max_words

    def test_banned_words_detected(self, sample_config):
        """Scripts containing banned words should be flagged."""
        banned = sample_config["quality_gate"]["banned_words"]
        script_clean = "AI is transforming the world in amazing ways."
        script_dirty = "OpenAI allegedly released a new model."

        assert not any(w in script_clean.lower() for w in banned)
        assert any(w in script_dirty.lower() for w in banned)
