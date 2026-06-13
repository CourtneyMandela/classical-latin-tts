"""ElevenLabs TTS pipeline for classical Latin.

Requires .env with:
  ELEVENLABS_API_KEY
  VOICE_ID              — from upload_voice.py
  PRONUNCIATION_DICT_ID — optional, from upload_pronunciation_dict.py
  PRONUNCIATION_DICT_VERSION_ID — optional
  ELEVENLABS_MODEL      — optional, default: eleven_multilingual_v2
"""

import os
import re
import unicodedata
from pathlib import Path

from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs
from elevenlabs.types import PronunciationDictionaryVersionLocator, VoiceSettings


def _load_config() -> dict:
    load_dotenv()
    config = {
        "api_key": os.environ.get("ELEVENLABS_API_KEY", ""),
        "voice_id": os.environ.get("VOICE_ID", ""),
        "dict_id": os.environ.get("PRONUNCIATION_DICT_ID", ""),
        "dict_version_id": os.environ.get("PRONUNCIATION_DICT_VERSION_ID", ""),
        "model_id": os.environ.get("ELEVENLABS_MODEL", "eleven_multilingual_v2"),
    }
    required = ["api_key", "voice_id"]
    missing = [k.upper() for k in required if not config[k]]
    if missing:
        raise EnvironmentError(
            f"Missing required environment variables: {', '.join(missing)}\n"
            "Copy .env.example to .env and fill in your values."
        )
    return config


def _strip_macrons(text: str) -> str:
    """Remove macrons/diacritics (ā→a, ē→e …) so ElevenLabs doesn't skip words."""
    return "".join(
        c for c in unicodedata.normalize("NFD", text)
        if unicodedata.category(c) != "Mn"
    )


def _split_sentences(text: str) -> list[str]:
    """Split on sentence-ending punctuation, keeping the punctuation."""
    parts = re.split(r"(?<=[.?!])\s+", text.strip())
    return [p.strip() for p in parts if p.strip()]


def _synthesize_sentence(client: ElevenLabs, sentence: str, config: dict, speed: float) -> bytes:
    kwargs = {
        "voice_id": config["voice_id"],
        "text": sentence,
        "model_id": config["model_id"],
        "voice_settings": VoiceSettings(
            stability=0.5,
            similarity_boost=0.8,
            speed=speed,
        ),
    }
    if config["dict_id"]:
        locator = PronunciationDictionaryVersionLocator(
            pronunciation_dictionary_id=config["dict_id"],
            version_id=config["dict_version_id"] or None,
        )
        kwargs["pronunciation_dictionary_locators"] = [locator]

    audio = client.text_to_speech.convert(**kwargs)
    return b"".join(audio)


def latin_to_speech(text: str, output_path: str, speed: float = 0.85) -> None:
    """Synthesize Latin text to an MP3 file using the cloned voice."""
    config = _load_config()
    client = ElevenLabs(api_key=config["api_key"])

    # Strip macrons — ElevenLabs skips/garbles macronized Unicode
    clean_text = _strip_macrons(text)

    # Synthesize sentence by sentence to prevent word-skipping
    sentences = _split_sentences(clean_text)
    audio_parts = []
    for i, sentence in enumerate(sentences, 1):
        print(f"  Synthesizing sentence {i}/{len(sentences)}: {sentence[:60]}...")
        audio_parts.append(_synthesize_sentence(client, sentence, config, speed))

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "wb") as f:
        for part in audio_parts:
            f.write(part)

    label = "with pronunciation dictionary" if config["dict_id"] else "no pronunciation dictionary"
    print(f"Saved: {output_path} ({label})")
