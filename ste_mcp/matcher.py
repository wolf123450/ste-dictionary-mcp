"""Word/text classification against the STE dictionary. No MCP imports —
pure logic, unit-testable standalone."""

from __future__ import annotations

import re

_SUFFIXES = ("ing", "es", "ed", "s")


def _stem_candidates(word: str):
    for suffix in _SUFFIXES:
        if word.endswith(suffix) and len(word) > len(suffix) + 1:
            yield word[: -len(suffix)]


def _from_entries(entries: list[dict], matched_as: str | None, dictionary) -> dict:
    is_ste = entries[0]["is_ste"]
    senses = [sense for entry in entries for sense in entry["senses"]]
    return {
        "status": "ste" if is_ste else "non_ste",
        "matched_as": matched_as,
        "part_of_speech": entries[0]["part_of_speech"],
        "senses": senses,
        "technical": dictionary.technical.get(entries[0]["word"].lower()),
    }


def classify(word_lower: str, dictionary) -> dict:
    """Classify one lowercased word/phrase against the dictionary.

    Resolution order (spec §3.1): exact match -> contraction -> inflection
    -> stem fallback -> technical dictionary -> unknown.
    """
    if word_lower in dictionary.single:
        return _from_entries(dictionary.single[word_lower], None, dictionary)

    if word_lower in dictionary.contractions:
        expansion = dictionary.contractions[word_lower]
        sense = {
            "definition": "",
            "ste_example": "",
            "non_ste_example": "",
            "alternative": {"word": expansion, "part_of_speech": ""},
            "note": None,
        }
        return {
            "status": "non_ste",
            "matched_as": f"{word_lower} (contraction)",
            "part_of_speech": "",
            "senses": [sense],
            "technical": None,
        }

    if word_lower in dictionary.inflections:
        canonical = dictionary.inflections[word_lower]
        canonical_lower = canonical.lower()
        if canonical_lower in dictionary.single:
            return _from_entries(
                dictionary.single[canonical_lower],
                f"{word_lower} (inflected form of {canonical})",
                dictionary,
            )

    for stem in _stem_candidates(word_lower):
        if stem in dictionary.single:
            canonical = dictionary.single[stem][0]["word"]
            return _from_entries(
                dictionary.single[stem],
                f"{word_lower} (stem of {canonical})",
                dictionary,
            )

    if word_lower in dictionary.technical:
        return {
            "status": "technical",
            "matched_as": None,
            "part_of_speech": "",
            "senses": [],
            "technical": dictionary.technical[word_lower],
        }

    return {
        "status": "unknown",
        "matched_as": None,
        "part_of_speech": "",
        "senses": [],
        "technical": None,
    }
