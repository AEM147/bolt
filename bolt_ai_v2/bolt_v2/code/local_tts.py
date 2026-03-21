#!/usr/bin/env python3
"""
Bolt AI — Free Local Voice Generation (local_tts.py)
=====================================================
Replaces paid TTS services with Microsoft Edge TTS — completely free,
Azure neural quality, no API key, no account, no rate limits.

Edge-TTS speaks directly to the same backend as Microsoft Edge browser TTS,
which is powered by Azure Cognitive Services. Zero cost, studio quality.

Install: pip install edge-tts

Usage:
    from local_tts import generate_audio, list_voices, preview_voice

    # Generate audio for a Bolt script
    path = await generate_audio("Hey humans, Bolt here!", "bolt_20260321.mp3")

    # List available English voices
    list_voices()

    # Test a specific voice
    await preview_voice("en-US-ChristopherNeural")
"""

import asyncio
import json
import logging
from pathlib import Path

logger = logging.getLogger("bolt.local_tts")

# ── Recommended voices for Bolt's energetic robot persona ──────────────────
#
# Tier 1 — Best for Bolt (energetic, clear, broadcast quality):
#   en-US-GuyNeural         Deep, authoritative. Best for AI news delivery.
#   en-US-ChristopherNeural Rich baritone. Professional but warm.
#   en-US-EricNeural        Crisp and confident. Great for fast-paced content.
#   en-GB-RyanNeural        British accent — adds authority and distinctiveness.
#
# Tier 2 — Alternative character options:
#   en-US-DavisNeural       Slightly younger-sounding. Good for tools content.
#   en-AU-WilliamNeural     Australian accent — fun and distinctive.
#   en-US-AndrewNeural      Warm and relatable. Best for "daily life" pillar.
#
# How to switch: change BOLT_VOICE below and run: python local_tts.py --preview
#
BOLT_VOICE = "en-US-GuyNeural"

# Speaking rate: +0% = normal, +8% = slightly faster (energetic), +15% = fast
BOLT_RATE = "+8%"

# Pitch: +0Hz = normal, +5Hz = slightly higher (more enthusiasm)
BOLT_PITCH = "+5Hz"

# Volume: +0% = normal, +10% = slightly louder for clearer delivery
BOLT_VOLUME = "+10%"


async def generate_audio(
    text: str,
    output_filename: str = "bolt_audio.mp3",
    voice: str = BOLT_VOICE,
    rate: str = BOLT_RATE,
    pitch: str = BOLT_PITCH,
    volume: str = BOLT_VOLUME,
    output_dir: str = "content/audio",
) -> str | None:
    """
    Generate TTS audio using free Edge-TTS.

    Args:
        text:            The script text to synthesize.
        output_filename: Filename for the MP3 output.
        voice:           Edge-TTS voice name (see recommendations above).
        rate:            Speaking rate adjustment (e.g. "+8%", "-5%").
        pitch:           Pitch adjustment in Hz (e.g. "+5Hz", "-3Hz").
        volume:          Volume adjustment (e.g. "+10%", "-5%").
        output_dir:      Directory to save the audio file.

    Returns:
        Absolute path to the generated MP3, or None on failure.
    """
    try:
        import edge_tts
    except ImportError:
        logger.error("edge-tts not installed. Run: pip install edge-tts")
        return None

    output_path = Path(output_dir) / output_filename
    output_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info(f"🔊 Generating audio | Voice: {voice} | Rate: {rate} | {len(text)} chars")

    try:
        communicate = edge_tts.Communicate(
            text=text,
            voice=voice,
            rate=rate,
            pitch=pitch,
            volume=volume,
        )
        await communicate.save(str(output_path))

        size_kb = output_path.stat().st_size // 1024
        logger.info(f"✅ Audio generated: {output_path.name} ({size_kb} KB)")
        return str(output_path)

    except Exception as e:
        logger.error(f"❌ Edge-TTS failed: {e}")
        return None


async def generate_with_retries(
    text: str,
    output_filename: str,
    config: dict,
    max_retries: int = 3,
) -> str | None:
    """
    Generate audio with retry logic and voice fallback chain.
    Reads voice settings from config if available.
    """
    tts_config = config.get("local_tts", {})
    voices_to_try = tts_config.get("voice_fallback_chain", [
        BOLT_VOICE, "en-US-ChristopherNeural", "en-US-EricNeural", "en-GB-RyanNeural"
    ])
    rate   = tts_config.get("rate",   BOLT_RATE)
    pitch  = tts_config.get("pitch",  BOLT_PITCH)
    volume = tts_config.get("volume", BOLT_VOLUME)

    for voice in voices_to_try:
        for attempt in range(1, max_retries + 1):
            logger.info(f"Attempt {attempt}/{max_retries} with voice: {voice}")
            result = await generate_audio(
                text=text,
                output_filename=output_filename,
                voice=voice,
                rate=rate,
                pitch=pitch,
                volume=volume,
            )
            if result:
                return result
            if attempt < max_retries:
                await asyncio.sleep(2)
        logger.warning(f"Voice {voice} failed after {max_retries} attempts — trying next voice")

    logger.error("All voices in fallback chain failed")
    return None


async def list_voices(filter_language: str = "en-") -> None:
    """
    Print all available Edge-TTS voices filtered by language prefix.
    Run this to discover new voices: python local_tts.py --list
    """
    try:
        import edge_tts
        voices = await edge_tts.list_voices()
        en_voices = [v for v in voices if v["ShortName"].startswith(filter_language)]
        print(f"\n{'─'*60}")
        print(f"  Available voices ({filter_language}*) — {len(en_voices)} total")
        print(f"{'─'*60}")
        for v in sorted(en_voices, key=lambda x: x["ShortName"]):
            gender = "♂" if v["Gender"] == "Male" else "♀"
            print(f"  {gender} {v['ShortName']:35s}  {v.get('Locale','')}")
        print(f"{'─'*60}\n")
    except ImportError:
        print("Install edge-tts first: pip install edge-tts")


async def preview_voice(voice: str, text: str = None) -> None:
    """
    Generate a preview MP3 for a specific voice so you can audition it.
    Output saved to content/audio/preview_{voice}.mp3
    """
    if text is None:
        text = (
            "Hey humans, Bolt here! I'm your AI-powered news robot, bringing you "
            "the latest in artificial intelligence every single day. "
            "Stay curious, humans! Let's get wired!"
        )
    filename = f"preview_{voice.replace('-','_')}.mp3"
    print(f"Generating preview: {voice}")
    result = await generate_audio(text, filename, voice=voice)
    if result:
        print(f"✅ Preview saved: {result}")
        print(f"   Play with: mpg123 {result}  OR  vlc {result}")
    else:
        print(f"❌ Preview failed for {voice}")


async def benchmark_voices(
    text: str = "Hey humans, Bolt here! Today in AI: a major breakthrough.",
) -> None:
    """
    Generate a short sample for every recommended Bolt voice.
    Useful for picking the best character voice.
    """
    candidates = [
        "en-US-GuyNeural",
        "en-US-ChristopherNeural",
        "en-US-EricNeural",
        "en-GB-RyanNeural",
        "en-US-DavisNeural",
        "en-AU-WilliamNeural",
    ]
    print(f"\nBenchmarking {len(candidates)} voices...\n")
    for voice in candidates:
        fname = f"bench_{voice.replace('-','_')}.mp3"
        result = await generate_audio(text, fname, voice=voice, rate="+5%")
        status = f"✅ {result}" if result else "❌ failed"
        print(f"  {voice:35s} {status}")
    print(f"\nListen to the bench_*.mp3 files in content/audio/ and pick your favourite.\n")


# ── CLI entry point ────────────────────────────────────────────────────────

def main():
    import argparse
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    parser = argparse.ArgumentParser(description="Bolt AI — Free Local TTS")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--list",       action="store_true",  help="List all available English voices")
    group.add_argument("--preview",    metavar="VOICE",      help="Generate a preview for a specific voice")
    group.add_argument("--benchmark",  action="store_true",  help="Generate samples for all recommended voices")
    group.add_argument("--test",       action="store_true",  help="Generate a quick test with the default Bolt voice")
    group.add_argument("--generate",   metavar="TEXT",       help="Generate audio for custom text")
    parser.add_argument("--voice",     default=BOLT_VOICE,   help="Voice to use (with --generate)")
    parser.add_argument("--output",    default="bolt_custom.mp3", help="Output filename (with --generate)")
    args = parser.parse_args()

    if args.list:
        asyncio.run(list_voices())
    elif args.preview:
        asyncio.run(preview_voice(args.preview))
    elif args.benchmark:
        asyncio.run(benchmark_voices())
    elif args.test:
        text = "Hey humans, Bolt here! Computing the latest AI news for you right now. Stay curious, humans! Let's get wired!"
        asyncio.run(generate_audio(text, "test_bolt_voice.mp3", voice=BOLT_VOICE))
        print(f"\nDefault Bolt voice: {BOLT_VOICE}")
        print(f"Audio saved to: content/audio/test_bolt_voice.mp3")
        print(f"To change voice, edit BOLT_VOICE in local_tts.py or set it in config.json")
    elif args.generate:
        asyncio.run(generate_audio(args.generate, args.output, voice=args.voice))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
