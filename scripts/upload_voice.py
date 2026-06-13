#!/usr/bin/env python3
"""Upload audio samples to ElevenLabs as an Instant Voice Clone (IVC).

IVC does not require consent recording from the speaker — it learns purely
from the uploaded audio. Prints the resulting voice_id for use in .env.
"""

import os
import sys
import argparse
import subprocess
import tempfile
from pathlib import Path

from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs

# ElevenLabs IVC limits
_MAX_FILES = 25
_CLIP_DURATION = 120  # seconds — 2 min per clip, well within 11 MB limit
_CLIP_START = 30      # skip first 30s (often intro/silence)


def _extract_clip(src: Path, dest: Path) -> bool:
    """Extract a 2-minute MP3 clip from src, starting at 30s."""
    result = subprocess.run(
        [
            "ffmpeg", "-y", "-i", str(src),
            "-ss", str(_CLIP_START),
            "-t", str(_CLIP_DURATION),
            "-ac", "1", "-ar", "44100",
            "-codec:a", "libmp3lame", "-b:a", "128k",
            str(dest),
        ],
        capture_output=True,
    )
    # Reject clips under 100 KB — file was too short or extraction failed
    if result.returncode != 0 or not dest.exists() or dest.stat().st_size < 100_000:
        return False
    return True


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

    # Select up to 25 evenly-spaced files
    if len(audio_files) > _MAX_FILES:
        total = len(audio_files)
        step = total / _MAX_FILES
        audio_files = [audio_files[int(i * step)] for i in range(_MAX_FILES)]
        print(f"Selected {_MAX_FILES} evenly-spaced files from {total} total.")

    print(f"Extracting {_CLIP_DURATION}s clips and uploading as IVC voice '{voice_name}'...")

    client = ElevenLabs(api_key=api_key)

    with tempfile.TemporaryDirectory() as tmpdir:
        clips = []
        for i, src in enumerate(audio_files):
            clip = Path(tmpdir) / f"clip_{i:03d}.mp3"
            if _extract_clip(src, clip):
                clips.append(clip)
            else:
                print(f"  Warning: could not extract clip from {src.name}, skipping.")

        if not clips:
            print("Error: no clips could be extracted.", file=sys.stderr)
            sys.exit(1)

        print(f"Uploading {len(clips)} clip(s)...")
        file_handles = [open(c, "rb") for c in clips]
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
