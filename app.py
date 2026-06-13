#!/usr/bin/env python3
"""Gradio web app for the Classical Latin TTS pipeline.

Run:
    python app.py

Then open http://localhost:7860 in your browser.
"""

import re
import sys
import zipfile
import tempfile
from pathlib import Path

# Ensure src/ is importable when running from project root
sys.path.insert(0, str(Path(__file__).parent / "src"))

import gradio as gr
from tts_pipeline import latin_to_speech
from document_processor import split_document, extract_text

# Project root for output directory
_PROJECT_ROOT = Path(__file__).parent


# ── Helpers ──────────────────────────────────────────────────────────────────

def _word_count(text):
    return len(text.split())


def _estimate_minutes(text):
    """Rough estimate: Latin read aloud ~120 words/min at speed 1.0."""
    wpm = 120.0
    return _word_count(text) / wpm


def _build_preview(sections):
    lines = []
    for i, sec in enumerate(sections, 1):
        wc = _word_count(sec.text)
        mins = _estimate_minutes(sec.text)
        # Fixed-width columns
        title_col = sec.title[:36].ljust(38)
        lines.append(f"  {i:>2}. {title_col} {wc:>5} words  (~{mins:.1f} min)")
    return "\n".join(lines)


def _sanitize_filename(title, max_len=40):
    """Keep only alphanumeric chars and underscores; truncate."""
    name = re.sub(r"[^A-Za-z0-9]+", "_", title).strip("_")
    return name[:max_len]


# ── Callbacks ─────────────────────────────────────────────────────────────────

def load_and_preview(text_input, file_upload):
    """Extract text, split into sections, return state + preview string."""
    try:
        if file_upload is not None:
            # file_upload is a filepath string in Gradio 4+
            raw_text = extract_text(file_upload)
        elif text_input and text_input.strip():
            raw_text = text_input.strip()
        else:
            return (
                [],
                "No input provided. Paste text or upload a file.",
                gr.update(interactive=False),
                gr.update(interactive=False),
            )

        sections = split_document(raw_text)
        if not sections:
            return (
                [],
                "Could not detect any sections in the document.",
                gr.update(interactive=False),
                gr.update(interactive=False),
            )

        preview = _build_preview(sections)
        return (
            sections,
            preview,
            gr.update(interactive=True),
            gr.update(interactive=True),
        )
    except Exception as exc:
        return (
            [],
            f"Error loading document: {exc}",
            gr.update(interactive=False),
            gr.update(interactive=False),
        )


def generate_sample(sections, speed):
    """Synthesize the first 3 sentences of the first section."""
    if not sections:
        return None

    first_text = sections[0].text
    # Split on sentence-ending punctuation followed by whitespace
    sentences = re.split(r"(?<=[.?!])\s+", first_text.strip())
    sample_text = " ".join(sentences[:3]).strip()
    if not sample_text:
        sample_text = first_text[:500]

    tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
    tmp.close()
    latin_to_speech(sample_text, tmp.name, speed=speed)
    return tmp.name


def generate_all(sections, speed):
    """Synthesize all sections and package them into a ZIP."""
    if not sections:
        return [], None

    out_dir = _PROJECT_ROOT / "output"
    out_dir.mkdir(parents=True, exist_ok=True)

    file_paths = []
    total = len(sections)
    for i, section in enumerate(sections, 1):
        print(f"[{i}/{total}] {section.title}")
        safe_title = _sanitize_filename(section.title)
        filename = f"{i:02d}_{safe_title}.mp3"
        out_path = out_dir / filename
        latin_to_speech(section.text, str(out_path), speed=speed)
        file_paths.append(str(out_path))

    # Create ZIP
    zip_path = str(out_dir / "latin_audio.zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for fp in file_paths:
            zf.write(fp, Path(fp).name)

    return file_paths, zip_path


# ── UI ────────────────────────────────────────────────────────────────────────

with gr.Blocks(title="Classical Latin TTS") as demo:
    gr.Markdown("# Classical Latin TTS")

    sections_state = gr.State([])

    # ── Load Text ──────────────────────────────────────────────────────────────
    gr.Markdown("## Load Text")
    with gr.Tabs():
        with gr.Tab("Paste Text"):
            text_input = gr.Textbox(
                lines=10,
                placeholder="Paste Latin text here...",
                label="Latin Text",
            )
        with gr.Tab("Upload File"):
            file_upload = gr.File(
                file_types=[".pdf", ".txt"],
                label="Upload .pdf or .txt",
            )

    load_btn = gr.Button("Load & Preview", variant="primary")

    # ── Sections Detected ──────────────────────────────────────────────────────
    gr.Markdown("## Sections Detected")
    sections_preview = gr.Textbox(
        lines=12,
        interactive=False,
        label="Detected sections",
    )

    # ── Settings ───────────────────────────────────────────────────────────────
    gr.Markdown("## Settings")
    speed_slider = gr.Slider(
        minimum=0.6,
        maximum=1.2,
        step=0.05,
        value=0.85,
        label="Speed (1.0 = normal)",
    )

    # ── Actions ────────────────────────────────────────────────────────────────
    gr.Markdown("## Actions")
    with gr.Row():
        sample_btn = gr.Button("Preview Sample", interactive=False)
        generate_btn = gr.Button("Generate All", variant="primary", interactive=False)

    # ── Sample ─────────────────────────────────────────────────────────────────
    gr.Markdown("## Sample")
    sample_audio = gr.Audio(label="Sample preview")

    # ── Generated Files ────────────────────────────────────────────────────────
    gr.Markdown("## Generated Files")
    generated_files = gr.File(file_count="multiple", label="Generated MP3s (click to download)")
    zip_download = gr.File(label="Download all as ZIP")

    # ── Wiring ─────────────────────────────────────────────────────────────────
    load_btn.click(
        fn=load_and_preview,
        inputs=[text_input, file_upload],
        outputs=[sections_state, sections_preview, sample_btn, generate_btn],
    )

    sample_btn.click(
        fn=generate_sample,
        inputs=[sections_state, speed_slider],
        outputs=[sample_audio],
    )

    generate_btn.click(
        fn=generate_all,
        inputs=[sections_state, speed_slider],
        outputs=[generated_files, zip_download],
    )


if __name__ == "__main__":
    demo.launch()
