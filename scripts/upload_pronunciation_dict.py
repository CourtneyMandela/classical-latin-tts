#!/usr/bin/env python3
"""Upload a PLS pronunciation dictionary to ElevenLabs.

Prints the dictionary ID and version ID needed for .env.
"""

import os
import sys
import argparse

from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs


def upload_dictionary(pls_file: str, dict_name: str) -> None:
    load_dotenv()
    api_key = os.environ.get("ELEVENLABS_API_KEY")
    if not api_key:
        print("Error: ELEVENLABS_API_KEY not set in environment or .env", file=sys.stderr)
        sys.exit(1)

    client = ElevenLabs(api_key=api_key)

    with open(pls_file, "rb") as f:
        result = client.pronunciation_dictionaries.create_from_file(
            file=f,
            name=dict_name,
        )

    print(f"Dictionary uploaded: '{dict_name}'")
    print(f"  ID:         {result.id}")
    print(f"  Version ID: {result.version_id}")
    print(f"\nAdd to your .env:")
    print(f"  PRONUNCIATION_DICT_ID={result.id}")
    print(f"  PRONUNCIATION_DICT_VERSION_ID={result.version_id}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Upload a PLS pronunciation dictionary to ElevenLabs"
    )
    parser.add_argument(
        "pls_file",
        nargs="?",
        default="data/latin_pronunciation.pls",
        help="Path to PLS file (default: data/latin_pronunciation.pls)",
    )
    parser.add_argument(
        "--name",
        default="Classical Latin",
        help="Dictionary name in ElevenLabs (default: Classical Latin)",
    )
    args = parser.parse_args()
    upload_dictionary(args.pls_file, args.name)


if __name__ == "__main__":
    main()
