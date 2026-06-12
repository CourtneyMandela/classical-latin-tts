#!/usr/bin/env python3
"""Preprocess audio files for ElevenLabs IVC upload.

Converts to mono WAV 44.1 kHz and loudness-normalizes to -18 LUFS integrated,
which is ElevenLabs' recommended target for voice cloning samples.
"""

import argparse
import subprocess
import sys
from pathlib import Path


def prepare_audio(input_dir: str, output_dir: str, target_lufs: float = -18.0) -> None:
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    audio_files = sorted(
        list(input_path.glob("*.mp3")) + list(input_path.glob("*.wav"))
    )
    if not audio_files:
        print(f"No MP3/WAV files found in {input_dir}", file=sys.stderr)
        sys.exit(1)

    print(f"Found {len(audio_files)} audio files. Normalizing to {target_lufs} LUFS...")

    ok = 0
    for f in audio_files:
        out_file = output_path / (f.stem + ".wav")
        result = subprocess.run(
            [
                "ffmpeg-normalize", str(f),
                "-o", str(out_file),
                "-ext", "wav",
                "-ar", "44100",
                "-ac", "1",
                "-t", str(target_lufs),
                "--force",
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            ok += 1
            print(f"  OK  {f.name}")
        else:
            print(f"  ERR {f.name}: {result.stderr[-200:]}", file=sys.stderr)

    print(f"\n{ok}/{len(audio_files)} files written to {output_dir}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Normalize audio files for ElevenLabs IVC upload"
    )
    parser.add_argument("input_dir", help="Directory containing source MP3/WAV files")
    parser.add_argument("output_dir", help="Directory for normalized WAV output")
    parser.add_argument(
        "--lufs", type=float, default=-18.0, help="Target LUFS integrated (default: -18)"
    )
    args = parser.parse_args()
    prepare_audio(args.input_dir, args.output_dir, args.lufs)


if __name__ == "__main__":
    main()
