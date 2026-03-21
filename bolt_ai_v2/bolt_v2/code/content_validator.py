#!/usr/bin/env python3
"""
Bolt AI — Content Quality Validator (content_validator.py)
===========================================================
Enforces quality controls BEFORE a script goes into the pipeline.
This runs after Claude generates the script and BEFORE it's approved —
catching issues the AI quality gate misses.

Checks:
  1. Banned words / phrases (config-driven, zero code changes)
  2. Script length (word count within min/max bounds)
  3. Duplicate detection (same story already published recently)
  4. Required structure (hook, catchphrase, CTA present)
  5. Misinformation flags (phrases like "confirmed that", "100% certain")
  6. Repetitive content (too similar to last 5 scripts)

Usage:
  from content_validator import ContentValidator
  validator = ContentValidator(config)
  result = validator.validate(script_text, article)
  if not result.passed:
      logger.warning(f"Script failed validation: {result.failures}")
"""

import hashlib
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

logger = logging.getLogger("bolt.validator")


@dataclass
class ValidationResult:
    passed:   bool
    score:    float             # 0.0 – 10.0 combined penalty score
    failures: list[str]        # Human-readable failure descriptions
    warnings: list[str]        # Non-blocking issues
    checks:   dict             # Per-check pass/fail detail


# ── Default banned words (config.json overrides these) ────────────────────

DEFAULT_BANNED_WORDS = [
    # Epistemic weasel words
    "allegedly", "reportedly", "may have", "we think", "supposedly",
    "claimed", "some say", "might be", "could be",
    # Misinformation risk
    "100% confirmed", "breaking: official", "just confirmed",
    "guaranteed", "certain that", "proven fact",
    # Off-brand for Bolt
    "in conclusion", "to summarize", "as I mentioned",
    "firstly", "secondly", "thirdly", "in summary",
    # Copyright risk
    "according to [publication]", "as reported by",
]

# Phrases that suggest the script is hallucinating specific details
HALLUCINATION_RISK_PHRASES = [
    r"\$\d{1,3}[,.]?\d{3}",      # Specific dollar amounts (easily wrong)
    r"\b\d{1,3}%\b",              # Specific percentages (easily wrong)
    r"on (january|february|march|april|may|june|july|august|september|october|november|december) \d{1,2}",
    r"\b(ceo|cto|cfo|president) [A-Z][a-z]+ [A-Z][a-z]+",  # Named executives
]

# Bolt's required structural elements
REQUIRED_PATTERNS = {
    "hook":        r"^(hey|bolt here|what's up|beep boop|\w+ here[,!])",
    "catchphrase": r"(stay curious|let's get wired|bolt out|stay plugged|ai download)",
}

SIMILARITY_THRESHOLD = 0.65   # Jaccard similarity — flag if > 65% overlap with recent script


class ContentValidator:
    """Validates Bolt scripts against multiple quality dimensions."""

    def __init__(self, config: dict):
        self.config = config
        qg = config.get("quality_gate", {})
        self.min_words   = qg.get("min_script_words", 80)
        self.max_words   = qg.get("max_script_words", 135)
        self.banned      = [w.lower() for w in qg.get("banned_words", DEFAULT_BANNED_WORDS)]
        self.min_score   = qg.get("min_overall_score", 8.5)

    # ── Main validate entry point ──────────────────────────────────────────

    def validate(self, script: str, article: dict,
                  recent_scripts: list[str] = None) -> ValidationResult:
        """
        Run all checks against a script.

        Args:
            script:         The generated script text.
            article:        The source article dict (title, summary, source, link).
            recent_scripts: List of recently published script texts for dedup check.

        Returns:
            ValidationResult with passed flag, failures, warnings.
        """
        failures = []
        warnings = []
        checks   = {}

        # 1. Length check
        check_length, length_msg = self._check_length(script)
        checks["length"] = check_length
        if not check_length:
            failures.append(length_msg)
        elif "warning" in length_msg.lower():
            warnings.append(length_msg)

        # 2. Banned words
        check_banned, banned_found = self._check_banned_words(script)
        checks["banned_words"] = check_banned
        if not check_banned:
            failures.append(f"Banned words found: {', '.join(banned_found)}")

        # 3. Required structure
        check_struct, struct_missing = self._check_structure(script)
        checks["structure"] = check_struct
        if not check_struct:
            failures.append(f"Missing required elements: {', '.join(struct_missing)}")

        # 4. Hallucination risk phrases
        check_halluc, halluc_matches = self._check_hallucination_risk(script)
        checks["hallucination_risk"] = check_halluc
        if not check_halluc:
            warnings.append(f"Potential hallucination risk phrases: {'; '.join(halluc_matches[:2])}")
            # Don't fail — warn only

        # 5. Duplicate detection
        if recent_scripts:
            check_dup, sim_score = self._check_duplicate(script, recent_scripts)
            checks["duplicate"] = check_dup
            if not check_dup:
                failures.append(f"Script too similar to recent content (similarity: {sim_score:.0%})")
        else:
            checks["duplicate"] = True

        # 6. DB-based duplicate (check if same article title published recently)
        check_article_dup = self._check_article_not_recent(article)
        checks["article_not_recent"] = check_article_dup
        if not check_article_dup:
            failures.append(f"Article '{article.get('title','')[:40]}...' was published within the last 72h")

        # 7. Source URL sanity
        check_source, source_msg = self._check_source(article)
        checks["source"] = check_source
        if not check_source:
            warnings.append(source_msg)

        passed = len(failures) == 0
        penalty = len(failures) * 1.5 + len(warnings) * 0.3
        score   = max(0.0, 10.0 - penalty)

        if not passed:
            logger.warning(
                "Script failed validation",
                extra={"failures": failures, "warnings": warnings, "score": score}
            )
        else:
            logger.info(
                "Script passed validation",
                extra={"warnings": warnings, "score": score, "checks_passed": sum(checks.values())}
            )

        return ValidationResult(
            passed=passed, score=round(score, 1),
            failures=failures, warnings=warnings, checks=checks
        )

    # ── Individual checks ──────────────────────────────────────────────────

    def _check_length(self, script: str) -> tuple[bool, str]:
        """Word count must be within [min_words, max_words]."""
        words = len(script.split())
        if words < self.min_words:
            return False, f"Script too short: {words} words (min: {self.min_words})"
        if words > self.max_words:
            return False, f"Script too long: {words} words (max: {self.max_words})"
        # Warn if close to limits
        if words < self.min_words + 5:
            return True, f"warning: Script is short ({words} words) — aim for {self.min_words + 15}+"
        return True, f"OK: {words} words"

    def _check_banned_words(self, script: str) -> tuple[bool, list[str]]:
        """No banned words or phrases."""
        script_lower = script.lower()
        found = [phrase for phrase in self.banned if phrase in script_lower]
        return len(found) == 0, found

    def _check_structure(self, script: str) -> tuple[bool, list[str]]:
        """Script must have a hook opening and Bolt's catchphrase."""
        script_lower = script.lower()
        missing = []
        for element, pattern in REQUIRED_PATTERNS.items():
            if not re.search(pattern, script_lower, re.IGNORECASE):
                missing.append(element)
        return len(missing) == 0, missing

    def _check_hallucination_risk(self, script: str) -> tuple[bool, list[str]]:
        """Flag specific numbers/names that could be hallucinated."""
        matches = []
        for pattern in HALLUCINATION_RISK_PHRASES:
            found = re.findall(pattern, script, re.IGNORECASE)
            matches.extend(found)
        # Warn if more than 2 specific claims (harder to verify)
        return len(matches) <= 2, matches

    def _check_duplicate(self, script: str,
                           recent_scripts: list[str]) -> tuple[bool, float]:
        """
        Jaccard similarity against recent scripts.
        Returns (passed, max_similarity_score).
        """
        def tokenize(text): return set(re.findall(r'\b\w+\b', text.lower()))
        tokens_new = tokenize(script)
        max_sim = 0.0
        for recent in recent_scripts[-10:]:  # Check last 10
            tokens_old = tokenize(recent)
            union = tokens_new | tokens_old
            if union:
                sim = len(tokens_new & tokens_old) / len(union)
                max_sim = max(max_sim, sim)
        passed = max_sim < SIMILARITY_THRESHOLD
        return passed, max_sim

    def _check_article_not_recent(self, article: dict) -> bool:
        """Check DB to see if the same article title was used in the last 72h."""
        try:
            from database import get_db
            db = get_db()
            cutoff = (datetime.now(timezone.utc) - timedelta(hours=72)).isoformat()
            with db._get_conn_ctx() as conn:
                count = conn.execute("""
                    SELECT COUNT(*) FROM articles
                    WHERE title = ? AND status = 'used' AND fetched_at > ?
                """, (article.get("title", ""), cutoff)).fetchone()[0]
            return count == 0
        except Exception:
            return True  # If DB unavailable, don't block

    def _check_source(self, article: dict) -> tuple[bool, str]:
        """Warn if the article has no source URL (harder to verify)."""
        if not article.get("link") and article.get("source") == "Bolt Backup":
            return True, "Backup/evergreen content — no source URL to verify"
        if not article.get("link"):
            return True, "Warning: article has no source URL"
        return True, "OK"

    # ── Batch check for pipeline integration ──────────────────────────────

    def validate_and_log(self, script: str, article: dict,
                          content_id: str = "") -> ValidationResult:
        """
        Validate and write the result to the DB if available.
        Use this in script_generator.py after Claude generates a script.
        """
        try:
            from database import get_db
            db = get_db()
            recent = [s["script"] for s in db.get_scripts(status="published", limit=10)]
        except Exception:
            recent = []

        result = self.validate(script, article, recent_scripts=recent)

        logger.info(
            "Validation complete",
            extra={
                "content_id":  content_id,
                "passed":      result.passed,
                "score":       result.score,
                "failures":    len(result.failures),
                "warnings":    len(result.warnings),
            }
        )
        return result
