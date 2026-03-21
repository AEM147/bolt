#!/usr/bin/env python3
"""
Bolt AI — Secrets Manager
=========================
Loads all API keys and sensitive credentials from environment variables or a
.env file — NEVER from config.json. This means you can safely commit config.json
to git without leaking credentials.

Priority order:
  1. Real environment variables (os.environ) — best for production/Docker/VPS
  2. .env file in the project root — best for local development
  3. config.json fallback for non-sensitive settings only

Setup:
  cp .env.example .env
  nano .env          # Add your real keys
  # The .env file is gitignored automatically by setup.sh

Usage in code:
  from secrets_manager import get_secret, load_all_secrets

  api_key = get_secret("ANTHROPIC_API_KEY")
  config  = load_all_secrets(config)   # Injects secrets into config dict
"""

import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger("bolt.secrets")

# ── .env file location ────────────────────────────────────────────────────
# Searches for .env in: current dir, script dir, parent dir
_ENV_SEARCH_PATHS = [
    Path(".env"),
    Path(__file__).parent.parent / ".env",
    Path(__file__).parent / ".env",
]

_LOADED = False
_ENV_CACHE: dict = {}


def _load_dotenv() -> None:
    """Parse a .env file and inject into os.environ (if not already set)."""
    global _LOADED
    if _LOADED:
        return

    env_file = None
    for path in _ENV_SEARCH_PATHS:
        if path.exists():
            env_file = path
            break

    if not env_file:
        logger.debug(".env file not found — using environment variables only")
        _LOADED = True
        return

    logger.info(f"Loading secrets from {env_file}")
    try:
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            # Don't override real environment variables
            if key not in os.environ:
                os.environ[key] = value
                _ENV_CACHE[key] = value
    except Exception as e:
        logger.warning(f"Failed to parse .env: {e}")

    _LOADED = True


def get_secret(key: str, fallback: Optional[str] = None) -> Optional[str]:
    """
    Get a secret by its environment variable name.

    Args:
        key:      Environment variable name (e.g. "ANTHROPIC_API_KEY")
        fallback: Value to return if the key is not set

    Returns:
        The secret value, or fallback if not found.
    """
    _load_dotenv()
    value = os.environ.get(key, fallback)
    if value and value.startswith("YOUR_"):
        logger.debug(f"Secret {key} is still a placeholder — add real value to .env")
        return fallback
    return value


def get_secret_required(key: str) -> str:
    """Get a required secret. Raises ValueError if missing or placeholder."""
    value = get_secret(key)
    if not value:
        raise ValueError(
            f"Required secret '{key}' is not set.\n"
            f"Add it to your .env file:\n"
            f"  {key}=your_real_value_here"
        )
    return value


# ── Secret key mapping ─────────────────────────────────────────────────────
# Maps config.json paths to their corresponding environment variable names.
# This is the single source of truth for which env var maps to which config key.

SECRET_MAP: dict[str, str] = {
    # AI
    "apis.anthropic_api_key":        "ANTHROPIC_API_KEY",
    # Voice
    "apis.elevenlabs_api_key":       "ELEVENLABS_API_KEY",
    "apis.elevenlabs_voice_id":      "ELEVENLABS_VOICE_ID",
    "apis.google_cloud_tts_key":     "GOOGLE_CLOUD_TTS_KEY",
    # Avatar
    "apis.vidnoz_api_key":           "VIDNOZ_API_KEY",
    "apis.vidnoz_avatar_id":         "VIDNOZ_AVATAR_ID",
    "apis.did_api_key":              "DID_API_KEY",
    "apis.did_presenter_url":        "DID_PRESENTER_URL",
    # Publishing
    "apis.buffer_access_token":      "BUFFER_ACCESS_TOKEN",
    "apis.youtube_client_id":        "YOUTUBE_CLIENT_ID",
    "apis.youtube_client_secret":    "YOUTUBE_CLIENT_SECRET",
    "apis.youtube_refresh_token":    "YOUTUBE_REFRESH_TOKEN",
    "apis.tiktok_access_token":      "TIKTOK_ACCESS_TOKEN",
    "apis.instagram_access_token":   "INSTAGRAM_ACCESS_TOKEN",
    "apis.instagram_user_id":        "INSTAGRAM_USER_ID",
    # Notifications
    "apis.discord_webhook_url":      "DISCORD_WEBHOOK_URL",
    "notifications.email.username":  "EMAIL_USERNAME",
    "notifications.email.password":  "EMAIL_PASSWORD",
    "notifications.telegram.bot_token": "TELEGRAM_BOT_TOKEN",
    "notifications.telegram.chat_id":   "TELEGRAM_CHAT_ID",
}


def load_all_secrets(config: dict) -> dict:
    """
    Inject secrets from environment into the config dict.
    Call this once at startup — it returns a new config dict with
    all YOUR_* placeholders replaced by real values from .env.

    Args:
        config: The config dict loaded from config.json

    Returns:
        New config dict with secrets injected.
    """
    import copy
    _load_dotenv()
    cfg = copy.deepcopy(config)

    injected = 0
    missing = []

    for config_path, env_var in SECRET_MAP.items():
        value = get_secret(env_var)
        if not value:
            # Check if it's already set in config (non-placeholder)
            current = _get_nested(cfg, config_path)
            if current and not str(current).startswith("YOUR_"):
                continue  # Already set, not a placeholder
            missing.append(env_var)
            continue

        _set_nested(cfg, config_path, value)
        injected += 1

    if injected:
        logger.info(f"✅ Injected {injected} secrets from environment")
    if missing:
        logger.debug(f"Secrets not set (optional or will use free tier): {missing}")

    return cfg


def audit() -> dict:
    """
    Audit which secrets are set and which are missing.
    Safe to call — only checks for existence, never prints values.
    """
    _load_dotenv()
    results = {"set": [], "missing": [], "placeholder": []}

    for config_path, env_var in SECRET_MAP.items():
        raw = os.environ.get(env_var, "")
        if not raw:
            results["missing"].append(env_var)
        elif raw.startswith("YOUR_"):
            results["placeholder"].append(env_var)
        else:
            results["set"].append(env_var)

    return results


def print_audit() -> None:
    """Print a human-readable secrets audit."""
    results = audit()
    print(f"\n{'─'*55}")
    print(f"  🔐 BOLT — SECRETS AUDIT")
    print(f"{'─'*55}")
    print(f"  ✅ Set ({len(results['set'])}):         {', '.join(results['set'][:3])}{'...' if len(results['set'])>3 else ''}")
    print(f"  ⚠️  Placeholder ({len(results['placeholder'])}): {', '.join(results['placeholder'][:3])}")
    print(f"  ❌ Missing ({len(results['missing'])}):    {', '.join(results['missing'][:3])}{'...' if len(results['missing'])>3 else ''}")
    print(f"\n  Minimum required for basic pipeline:")
    required = ["ANTHROPIC_API_KEY"]
    for r in required:
        status = "✅" if r in results["set"] else "❌"
        print(f"    {status} {r}")
    print(f"\n  Edit your .env file:  nano .env")
    print(f"  Then re-run:          python secrets_manager.py\n")


# ── Nested dict helpers ────────────────────────────────────────────────────

def _get_nested(d: dict, path: str):
    keys = path.split(".")
    for k in keys:
        if not isinstance(d, dict):
            return None
        d = d.get(k)
    return d


def _set_nested(d: dict, path: str, value: str) -> None:
    keys = path.split(".")
    for k in keys[:-1]:
        d = d.setdefault(k, {})
    d[keys[-1]] = value


# ── CLI ────────────────────────────────────────────────────────────────────

def main():
    import argparse
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    parser = argparse.ArgumentParser(description="Bolt AI — Secrets Manager")
    parser.add_argument("--audit", action="store_true", help="Audit which secrets are set")
    parser.add_argument("--get", metavar="KEY", help="Get a specific secret (value masked)")
    parser.add_argument("--generate-env", action="store_true", help="Generate a .env.example file")
    args = parser.parse_args()

    if args.audit:
        print_audit()
    elif args.get:
        val = get_secret(args.get)
        if val:
            masked = val[:4] + "****" + val[-4:] if len(val) > 8 else "****"
            print(f"✅ {args.get} = {masked}")
        else:
            print(f"❌ {args.get} is not set")
    elif args.generate_env:
        _generate_example()
    else:
        print_audit()


def _generate_example() -> None:
    """Generate a .env.example file with all required keys."""
    lines = [
        "# Bolt AI — Environment Variables",
        "# Copy this file to .env and fill in your real values",
        "# NEVER commit .env to git — it contains your API keys",
        "",
        "# ── AI (Required) ─────────────────────────────────────",
        "ANTHROPIC_API_KEY=sk-ant-your-key-here",
        "",
        "# ── Voice (Free options — use edge-tts for $0 cost) ────",
        "ELEVENLABS_API_KEY=your-elevenlabs-key   # 10K chars/month free",
        "ELEVENLABS_VOICE_ID=your-voice-id        # Get from elevenlabs.io",
        "GOOGLE_CLOUD_TTS_KEY=your-gcp-key        # 1M chars/month free",
        "",
        "# ── Avatar Video (Free options available) ───────────────",
        "VIDNOZ_API_KEY=your-vidnoz-key           # Free plan available",
        "VIDNOZ_AVATAR_ID=your-avatar-id",
        "DID_API_KEY=your-did-key                 # 20 free videos/month",
        "DID_PRESENTER_URL=https://your-avatar-image.jpg",
        "",
        "# ── Publishing ──────────────────────────────────────────",
        "BUFFER_ACCESS_TOKEN=your-buffer-token    # Free: 3 channels",
        "YOUTUBE_CLIENT_ID=your-yt-client-id",
        "YOUTUBE_CLIENT_SECRET=your-yt-secret",
        "YOUTUBE_REFRESH_TOKEN=your-yt-refresh",
        "TIKTOK_ACCESS_TOKEN=your-tiktok-token",
        "INSTAGRAM_ACCESS_TOKEN=your-ig-token",
        "INSTAGRAM_USER_ID=your-ig-user-id",
        "",
        "# ── Notifications (Free) ────────────────────────────────",
        "DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...",
        "TELEGRAM_BOT_TOKEN=your-bot-token        # Optional",
        "TELEGRAM_CHAT_ID=your-chat-id            # Optional",
        "EMAIL_USERNAME=your@gmail.com            # Optional",
        "EMAIL_PASSWORD=your-app-password         # Optional",
    ]
    example = Path(".env.example")
    example.write_text("\n".join(lines))
    print(f"✅ Generated: {example}")
    print(f"   Run: cp .env.example .env && nano .env")


if __name__ == "__main__":
    main()
