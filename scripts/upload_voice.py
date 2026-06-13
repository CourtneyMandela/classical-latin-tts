#!/usr/bin/env python3
"""Upload audio samples to ElevenLabs as an Instant Voice Clone (IVC).

IVC does not require consent recording from the speaker — it learns purely
from the uploaded audio. Prints the resulting voice_id for use in .env.
"""

import os
import sys
import argparse
from pathlib import Path

from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs


def upload_voice(audio_dir: str, voice_name: str, description: str) -> None:
    load_dotenv()
    api_key = os.environ.get("ELEVENLABS_API_KEY")
    if not api_key:
        print("Error: ELEVENLABS_API_KEY not set in environment or .env", file=sys.stderr)
        sys.exit(1)

    audio_path = Path(audio_dir)
    audio_files = sorted(
        list(audio_path.glob("*.wav")) + list(audio_path.glob("*.mp3"))
    )
    if not audio_files:
        print(f"No audio files found in {audio_dir}", file=sys.stderr)
        sys.exit(1)

    # ElevenLabs IVC accepts a maximum of 25 files
    max_files = 25
    if len(audio_files) > max_files:
        total = len(audio_files)
        step = total / max_files
        audio_files = [audio_files[int(i * step)] for i in range(max_files)]
        print(f"Selecting {max_files} evenly-spaced files from {total} total...")

    print(f"Uploading {len(audio_files)} file(s) as IVC voice '{voice_name}'...")

    client = ElevenLabs(api_key=api_key)
    file_handles = [open(f, "rb") for f in audio_files]
    try:
        voice = client.voices.ivc.create(
            name=voice_name,
            files=file_handles,
            description=description,
        )
    finally:
        for fh in file_handles:
            fh.close()

    print(f"\nVoice created successfully.")
    print(f"Voice ID: {voice.voice_id}")
    print(f"\nAdd to your .env:\n  VOICE_ID={voice.voice_id}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Upload voice samples to ElevenLabs as an Instant Voice Clone"
    )
    parser.add_argument("audio_dir", help="Directory of normalized WAV files to upload")
    parser.add_argument(
        "--name", default="Lingua Latina Classica", help="Voice name in ElevenLabs"
    )
    parser.add_argument(
        "--description",
        default="Classical Latin narrator, reconstructed pronunciation (Allen/Vox Latina)",
        help="Voice description",
    )
    args = parser.parse_args()
    upload_voice(args.audio_dir, args.name, args.description)


if __name__ == "__main__":
    main()
