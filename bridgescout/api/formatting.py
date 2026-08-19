"""Pure presentation helpers shared by the API layer.

These turn raw pipeline output (full sentences, similarity scores) into the
short, clean labels and status text the frontend renders — tab titles,
headlines, and score status labels. No pipeline logic lives here.
"""

from __future__ import annotations

import re

# Cue phrases stripped from the front of a gap sentence so titles read as a
# clean heading instead of a mid-sentence fragment (e.g. "However, the
# model's performance drops..." -> "The model's performance drops...").
_GAP_TITLE_PREFIXES = [
    r"^however,?\s*",
    r"^a (?:key |significant |major |critical )?limitation (?:of (?:this|the) (?:work|study|approach|method|paper))?\s*is\s+that\s*",
    r"^this (?:limitation|challenge) (?:arises|remains)\s+because\s*",
    r"^this\s+(?:remains|is)\s+a\s+challenge\s+because\s*",
    r"^future\s+(?:work|research)\s+(?:is needed|should\s+(?:explore|investigate|address|focus on))\s*(?:on|for)?\s*",
]

DEFAULT_SCORE_THRESHOLD = 0.5


def clean_gap_title(text: str) -> str:
    """Strip filler cue phrases from a gap sentence so it reads as a clean title."""
    cleaned = text.strip()
    for pattern in _GAP_TITLE_PREFIXES:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
    cleaned = cleaned.strip().rstrip(".")
    if cleaned:
        cleaned = cleaned[0].upper() + cleaned[1:]
    return cleaned or text.strip()


def short_title(text: str, max_len: int = 28) -> str:
    return text if len(text) <= max_len else text[: max_len - 3] + "..."


def gap_headline(text: str, max_words: int = 8) -> str:
    words = clean_gap_title(text).split()
    if len(words) <= max_words:
        return " ".join(words)
    return " ".join(words[:max_words]) + "..."


def score_status_label(score: float, threshold: float = DEFAULT_SCORE_THRESHOLD) -> str:
    return "Strong match" if score >= threshold else "Needs review"
