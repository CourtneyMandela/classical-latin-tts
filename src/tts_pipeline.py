"""ElevenLabs TTS pipeline for classical Latin.

Requires .env with:
  ELEVENLABS_API_KEY
  VOICE_ID         — from upload_voice.py
  ELEVENLABS_MODEL — optional, default: eleven_multilingual_v2
"""

import os
import re
import unicodedata
from pathlib import Path

from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs
from elevenlabs.types import VoiceSettings


def _load_config() -> dict:
    load_dotenv()
    config = {
        "api_key": os.environ.get("ELEVENLABS_API_KEY", ""),
        "voice_id": os.environ.get("VOICE_ID", ""),
        "model_id": os.environ.get("ELEVENLABS_MODEL", "eleven_multilingual_v2"),
    }
    missing = [k.upper() for k in ("api_key", "voice_id") if not config[k]]
    if missing:
        raise EnvironmentError(
            f"Missing required environment variables: {', '.join(missing)}\n"
            "Copy .env.example to .env and fill in your values."
        )
    return config


# ── Classical Latin text pre-processor ───────────────────────────────────────
# Rewrites Latin text so ElevenLabs pronounces it correctly without needing
# a pronunciation dictionary (which breaks IVC voices).

_MACRON_MAP = str.maketrans("āēīōūĀĒĪŌŪ", "aeiouAEIOU")

# Diphthong rewrites must run before single-vowel rules.
_DIPHTHONG_MAP = [
    ("ae", "ai"),
    ("Ae", "Ai"),
    ("AE", "AI"),
    ("oe", "oi"),
    ("Oe", "Oi"),
]

def _rewrite_latin(text: str) -> str:
    """Rewrite Latin text for correct Classical pronunciation by ElevenLabs."""
    # 1. Strip macrons
    t = text.translate(_MACRON_MAP)

    # 2. Diphthongs (ae→ai, oe→oi)
    for src, dst in _DIPHTHONG_MAP:
        t = t.replace(src, dst)

    # 3. qu → kw (must come before c→k rule)
    t = re.sub(r'[Qq]u', lambda m: 'Kw' if m.group()[0].isupper() else 'kw', t)

    # 4. c/C → k/K always (Classical Latin c is always /k/)
    t = re.sub(r'[Cc]', lambda m: 'K' if m.group().isupper() else 'k', t)

    # 5. v/V → w/W (consonantal; Classical Latin v is /w/)
    t = re.sub(r'[Vv]', lambda m: 'W' if m.group().isupper() else 'w', t)

    # 6. j/J → y/Y
    t = re.sub(r'[Jj]', lambda m: 'Y' if m.group().isupper() else 'y', t)

    # 7. Fix swallowed final consonant clusters — model elides -st/-xt endings.
    #    Doubling the preceding vowel forces the cluster to be articulated.
    _CLUSTER_FIXES = [
        # word  → rewrite   (whole-word matches only)
        (r'\best\b',  'esst'),
        (r'\bEst\b',  'Esst'),
        (r'\bEST\b',  'ESST'),
        (r'\bpost\b', 'posst'),
        (r'\bPost\b', 'Posst'),
        (r'\bPOST\b', 'POSST'),
    ]
    for pattern, replacement in _CLUSTER_FIXES:
        t = re.sub(pattern, replacement, t)

    return t


def _to_ssml(text: str, speed: float) -> str:
    """Wrap text in an SSML prosody envelope to lock the speech rate."""
    escaped = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    rate = int(round(speed * 100))
    return f'<speak><prosody rate="{rate}%">{escaped}</prosody></speak>'


_MAX_CHARS = 4500  # ElevenLabs hard limit is ~5000; stay under it


def _split_chunks(text: str) -> list[str]:
    """Split at paragraph then sentence boundaries to stay under the char limit."""
    if len(text) <= _MAX_CHARS:
        return [text]

    # Try paragraph breaks first
    paragraphs = re.split(r"\n\s*\n", text.strip())
    chunks: list[str] = []
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        if len(para) <= _MAX_CHARS:
            chunks.append(para)
        else:
            # Fall back to sentence splitting for very long paragraphs
            sentences = re.split(r"(?<=[.?!])\s+", para)
            current = ""
            for sent in sentences:
                if current and len(current) + 1 + len(sent) > _MAX_CHARS:
                    chunks.append(current.strip())
                    current = sent
                else:
                    current = (current + " " + sent).strip() if current else sent
            if current:
                chunks.append(current.strip())
    return [c for c in chunks if c]


def _synthesize_chunk(client: ElevenLabs, chunk: str, config: dict, speed: float) -> bytes:
    audio = client.text_to_speech.convert(
        voice_id=config["voice_id"],
        text=_to_ssml(chunk, speed),  # SSML prosody locks rate more reliably than speed param alone
        model_id=config["model_id"],
        voice_settings=VoiceSettings(
            stability=0.85,
            similarity_boost=0.75,
            style=0.0,
            use_speaker_boost=True,
            speed=speed,
        ),
    )
    return b"".join(audio)


def latin_to_speech(text: str, output_path: str, speed: float = 0.85) -> None:
    """Synthesize Latin text to an MP3 file using the cloned voice."""
    config = _load_config()
    client = ElevenLabs(api_key=config["api_key"])

    rewritten = _rewrite_latin(text)
    chunks = _split_chunks(rewritten)

    audio_parts = []
    for i, chunk in enumerate(chunks, 1):
        print(f"  [{i}/{len(chunks)}] synthesizing {len(chunk)} chars...")
        audio_parts.append(_synthesize_chunk(client, chunk, config, speed))

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "wb") as f:
        for part in audio_parts:
            f.write(part)

    print(f"Saved: {output_path}")
