"""ElevenLabs TTS pipeline for classical Latin.

Requires .env with:
  ELEVENLABS_API_KEY
  VOICE_ID              — from upload_voice.py
  PRONUNCIATION_DICT_ID — from upload_pronunciation_dict.py
  PRONUNCIATION_DICT_VERSION_ID — from upload_pronunciation_dict.py
  ELEVENLABS_MODEL      — optional, default: eleven_multilingual_v2
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs


def _load_config() -> dict:
    load_dotenv()
    config = {
        "api_key": os.environ.get("ELEVENLABS_API_KEY", ""),
        "voice_id": os.environ.get("VOICE_ID", ""),
        "dict_id": os.environ.get("PRONUNCIATION_DICT_ID", ""),
        "dict_version_id": os.environ.get("PRONUNCIATION_DICT_VERSION_ID", ""),
        "model_id": os.environ.get("ELEVENLABS_MODEL", "eleven_multilingual_v2"),
    }
    required = ["api_key", "voice_id", "dict_id"]
    missing = [k.upper() for k in required if not config[k]]
    if missing:
        raise EnvironmentError(
            f"Missing required environment variables: {', '.join(missing)}\n"
            "Copy .env.example to .env and fill in your values."
        )
    return config


def latin_to_speech(text: str, output_path: str) -> None:
    """Synthesize Latin text to an MP3 file using the cloned voice + pronunciation dictionary."""
    config = _load_config()
    client = ElevenLabs(api_key=config["api_key"])

    locator: dict = {"pronunciation_dictionary_id": config["dict_id"]}
    if config["dict_version_id"]:
        locator["version_id"] = config["dict_version_id"]

    audio = client.text_to_speech.convert(
        voice_id=config["voice_id"],
        text=text,
        model_id=config["model_id"],
        pronunciation_dictionary_locators=[locator],
    )

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "wb") as f:
        for chunk in audio:
            f.write(chunk)

    print(f"Saved: {output_path}")
