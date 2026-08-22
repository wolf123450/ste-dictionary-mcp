"""Load and sanitize the STE dictionary snapshot into in-memory lookup
structures. No MCP imports — pure data logic, unit-testable standalone."""

from __future__ import annotations

import json
import re
from pathlib import Path

from ste_mcp.contractions import CONTRACTIONS

_REPLACEMENT_CHAR = "�"
_ELLIPSIS = "..."
_ELLIPSIS_CHAR = "…"
_STE_FILE = "ste_dictionary.json"
_TECH_FILE = "raw_tech_dict.json"
_SOURCE = "ste.valaratomics.com"


def _is_corrupted_word(word: str) -> bool:
    """Sanitization rules from spec §4.1, rules 1-3 (and reused for rule 4
    on alternative words)."""
    if not word:
        return True
    if _REPLACEMENT_CHAR in word:
        return True
    if _ELLIPSIS in word:
        return True
    if _ELLIPSIS_CHAR in word:
        return True
    tokens = word.split()
    if len(tokens) >= 3 and not word.isupper():
        return True
    return False


def _sanitize_alternative(alt: dict | None) -> tuple[dict | None, str | None]:
    if not alt:
        return None, None
    word = alt.get("word", "")
    if _is_corrupted_word(word):
        return None, word
    return {"word": word, "part_of_speech": alt.get("part_of_speech", "")}, None


def _load_ste_entries(path: Path) -> tuple[list[dict], int]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    entries = []
    dropped = 0
    for rec in raw:
        word = rec.get("word", "")
        if _is_corrupted_word(word):
            dropped += 1
            continue
        senses = []
        for row in rec.get("rows", []):
            alternative, note_word = _sanitize_alternative(row.get("alternative"))
            note = f"reword; see definition: {note_word}" if note_word else None
            senses.append(
                {
                    "definition": row.get("definition", ""),
                    "ste_example": row.get("ste_example", ""),
                    "non_ste_example": row.get("non_ste_example", ""),
                    "alternative": alternative,
                    "note": note,
                }
            )
        entries.append(
            {
                "id": rec["id"],
                "word": word,
                "part_of_speech": rec.get("part_of_speech", ""),
                "part_of_speech_display": rec.get("part_of_speech_display", ""),
                "other_forms": rec.get("other_forms", ""),
                "is_ste": bool(rec.get("is_ste", False)),
                "senses": senses,
            }
        )
    return entries, dropped


def _load_technical_entries(path: Path) -> dict[str, dict]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    technical = {}
    for rec in raw:
        word = rec.get("word", "")
        if _is_corrupted_word(word):
            continue
        technical[word.lower()] = {
            "word": word,
            "part_of_speech": rec.get("part_of_speech", ""),
            "definition": rec.get("definition", ""),
            "abbreviation_definition": rec.get("abbreviation_definition", ""),
            "source": rec.get("source", ""),
        }
    return technical


def _build_inflections(entries: list[dict]) -> dict[str, str]:
    inflections = {}
    for entry in entries:
        forms = entry.get("other_forms", "")
        if not forms:
            continue
        for form in re.split(r"[,;/]", forms):
            form = form.strip().lower()
            if form:
                inflections[form] = entry["word"]
    return inflections


class Dictionary:
    """In-memory index over the STE and technical dictionary snapshots."""

    def __init__(self, data_dir: str | Path):
        self.data_dir = Path(data_dir)
        ste_path = self.data_dir / _STE_FILE
        tech_path = self.data_dir / _TECH_FILE
        if not ste_path.exists():
            raise FileNotFoundError(f"Missing required data file: {ste_path}")
        if not tech_path.exists():
            raise FileNotFoundError(f"Missing required data file: {tech_path}")

        entries, dropped = _load_ste_entries(ste_path)

        self.single: dict[str, list[dict]] = {}
        for entry in entries:
            self.single.setdefault(entry["word"].lower(), []).append(entry)

        self.phrases = sorted(
            (e for e in entries if not e["is_ste"] and " " in e["word"]),
            key=lambda e: len(e["word"].split()),
            reverse=True,
        )
        self.inflections = _build_inflections(entries)
        self.technical = _load_technical_entries(tech_path)
        self.contractions = CONTRACTIONS

        self.sanitized_dropped = dropped
        self.multi_word_phrases = len(self.phrases)
        self.terms_total = len(entries) + dropped
        self.terms_ste = sum(1 for e in entries if e["is_ste"])
        self.terms_non_ste = sum(1 for e in entries if not e["is_ste"])
        self.technical_terms = len(self.technical)
        self.source = _SOURCE
        self.data_files = {
            _STE_FILE: ste_path.stat().st_mtime,
            _TECH_FILE: tech_path.stat().st_mtime,
        }

    def info(self) -> dict:
        return {
            "source": self.source,
            "data_files": {name: str(mtime) for name, mtime in self.data_files.items()},
            "terms_total": self.terms_total,
            "terms_ste": self.terms_ste,
            "terms_non_ste": self.terms_non_ste,
            "sanitized_dropped": self.sanitized_dropped,
            "multi_word_phrases": self.multi_word_phrases,
            "technical_terms": self.technical_terms,
        }
