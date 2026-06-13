"""Document processor for Classical Latin TTS pipeline.

Extracts text from PDF or TXT files and splits into labelled sections.
"""

import re
from dataclasses import dataclass
from typing import List


@dataclass
class Section:
    title: str
    text: str


def extract_text(file_path: str) -> str:
    """Extract plain text from a PDF or TXT file.

    Args:
        file_path: Path to the source file.

    Returns:
        The extracted text as a single string.

    Raises:
        ValueError: If the file type is not supported.
    """
    if file_path.endswith(".pdf"):
        import pdfplumber
        pages = []
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    pages.append(text)
        return "\n\n".join(pages)
    elif file_path.endswith(".txt"):
        with open(file_path, encoding="utf-8") as f:
            return f.read()
    else:
        raise ValueError(
            f"Unsupported file type: {file_path!r}. Only .pdf and .txt are supported."
        )


def split_document(text: str) -> List[Section]:
    """Split document text into labelled sections.

    Tries chapter detection first; falls back to fixed-size chunks.

    Args:
        text: Full document text.

    Returns:
        List of Section objects.
    """
    chapters = _detect_chapters(text)
    if len(chapters) >= 2:
        return chapters
    return _split_into_chunks(text)


# ── Roman numeral heading pattern ────────────────────────────────────────────
_ROMAN_HEADING = re.compile(r"^[IVXLC]+\.\s+\S")


def _is_heading(line: str) -> bool:
    """Return True if *line* looks like a chapter/section heading."""
    stripped = line.strip()
    if not stripped:
        return False
    # Must be short
    if len(stripped) >= 80:
        return False
    # Roman numeral + period: "I. Title", "XIV. Something"
    if _ROMAN_HEADING.match(stripped):
        return True
    # "Chapter N" or "CHAPTER N"
    if re.match(r"^(Chapter|CHAPTER)\s+\S", stripped):
        return True
    # All-caps word(s), 3–60 chars
    if 3 <= len(stripped) <= 60 and stripped == stripped.upper() and stripped.replace(" ", "").isalpha():
        return True
    return False


def _detect_chapters(text: str) -> List[Section]:
    """Scan *text* for chapter/section headings and split on them.

    Args:
        text: Full document text.

    Returns:
        List of Sections, or empty list if fewer than 2 headings found.
    """
    lines = text.splitlines()
    sections = []
    current_title = None
    current_lines = []

    for line in lines:
        if _is_heading(line):
            if current_title is not None:
                body = "\n".join(current_lines).strip()
                if body:
                    sections.append(Section(title=current_title, text=body))
            current_title = line.strip()
            current_lines = []
        else:
            current_lines.append(line)

    # Flush last section
    if current_title is not None:
        body = "\n".join(current_lines).strip()
        if body:
            sections.append(Section(title=current_title, text=body))

    if len(sections) < 2:
        return []
    return sections


def _split_into_chunks(text: str, target_words: int = 350) -> List[Section]:
    """Split *text* into roughly equal chunks, breaking on blank lines.

    Args:
        text: Full document text.
        target_words: Approximate word count per chunk before starting a new one.

    Returns:
        List of Sections titled "Part 1", "Part 2", etc.
    """
    # Split on one or more blank lines to get paragraphs
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]

    sections = []
    chunk_parts = []
    word_count = 0
    part_num = 1

    for para in paragraphs:
        words_in_para = len(para.split())
        chunk_parts.append(para)
        word_count += words_in_para

        if word_count >= target_words:
            sections.append(Section(title=f"Part {part_num}", text="\n\n".join(chunk_parts)))
            part_num += 1
            chunk_parts = []
            word_count = 0

    # Flush remaining text
    if chunk_parts:
        sections.append(Section(title=f"Part {part_num}", text="\n\n".join(chunk_parts)))

    return sections
