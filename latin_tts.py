#!/usr/bin/env python3
"""Latin TTS CLI — convert classical Latin text to speech.

Requires a populated .env (see .env.example).

Usage:
  python latin_tts.py "Gallia est omnis divisa in partes tres"
  python latin_tts.py "veni vidi vici" --output veni.mp3
  python latin_tts.py --input-file passage.txt --output passage.mp3
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))
from tts_pipeline import latin_to_speech


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert classical Latin text to speech (ElevenLabs + CLTK pronunciation)"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("text", nargs="?", help="Latin text to synthesize")
    group.add_argument("--input-file", "-i", metavar="FILE", help="Text file to synthesize")
    parser.add_argument(
        "--output", "-o", default="output.mp3", metavar="FILE", help="Output MP3 path (default: output.mp3)"
    )
    parser.add_argument(
        "--speed", "-s", type=float, default=0.85, metavar="SPEED",
        help="Speech speed: 1.0=normal, 0.85=slightly slower (default: 0.85)"
    )
    args = parser.parse_args()

    if args.input_file:
        text = Path(args.input_file).read_text(encoding="utf-8").strip()
    else:
        text = args.text

    if not text:
        parser.error("No text provided.")

    try:
        latin_to_speech(text, args.output, speed=args.speed)
    except EnvironmentError as e:
        print(f"Configuration error:\n{e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
