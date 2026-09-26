"""Mirrors backend/eval/metrics.py's _normalize_thai -- duplicated, not
imported, so this package doesn't reach into eval/'s private functions.
See MEMORY.md's 2026-09-21 entry: plain unicodedata.normalize("NFC", ...)
alone is NOT enough for Thai SARA AM."""
import re
import unicodedata

_THAI_TONE_MARKS = "่้๊๋"


def normalize_thai(s: str) -> str:
    s = unicodedata.normalize("NFC", s)
    s = s.replace("ำ", "ํา")
    s = re.sub(f"ํ([{_THAI_TONE_MARKS}])", r"\1ํ", s)
    return s


def normalize_alias(s: str) -> str:
    return normalize_thai(s.strip()).lower()
