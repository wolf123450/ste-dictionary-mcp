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
    # A word can have multiple entries (one per part of speech), and they can
    # disagree on is_ste (e.g. "aid" as a noun is STE, but as a verb is not).
    # The overall status must be "non_ste" if ANY entry is non-STE -- only
    # report "ste" when every matched entry is STE-approved. Each flattened
    # sense also carries its own part_of_speech/is_ste so a caller can tell
    # exactly which sense is non-STE, since that information is lost once
    # senses from multiple entries are merged into one list.
    all_ste = all(entry["is_ste"] for entry in entries)
    senses = [
        {**sense, "part_of_speech": entry["part_of_speech"], "is_ste": entry["is_ste"]}
        for entry in entries
        for sense in entry["senses"]
    ]
    return {
        "status": "ste" if all_ste else "non_ste",
        "matched_as": matched_as,
        # Top-level part_of_speech is kept for backward compatibility with
        # the common single-POS case; it reflects only the first matched
        # entry. When entries disagree on POS or is_ste, the per-sense
        # "part_of_speech"/"is_ste" fields above are the authoritative source.
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
            # Fix 4: contractions have no part of speech, and are always
            # non-STE, but the field must still be present so callers that
            # filter senses by is_ste don't silently miss them.
            "part_of_speech": "",
            "is_ste": False,
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


MAX_TEXT_CHARS = 200_000
MAX_BUCKET_ENTRIES = 200
_TOKEN_RE = re.compile(r"[a-z0-9]+(?:['-][a-z0-9]+)*")


def check_word(word: str, dictionary) -> dict:
    """Tool-facing wrapper over classify() matching spec §3.1's output shape."""
    word_lower = word.strip().lower()
    result = classify(word_lower, dictionary)
    status = result["status"]
    out_status = "not_in_dictionary" if status in ("technical", "unknown") else status
    return {
        "word": word,
        "status": out_status,
        "matched_as": result["matched_as"] or word_lower,
        "part_of_speech": result["part_of_speech"],
        "senses": result["senses"],
        "technical": result["technical"],
    }


def _record(bucket: dict, word: str, line_no: int, start: int, end: int, **extra) -> None:
    key = word.lower()
    if key not in bucket:
        if len(bucket) >= MAX_BUCKET_ENTRIES:
            bucket["__truncated__"] = True
            return
        bucket[key] = {"word": word, "count": 0, "positions": [], **extra}
    entry = bucket[key]
    entry["count"] += 1
    entry["positions"].append({"line": line_no, "start": start, "end": end})


def _classify_and_record(word: str, original_word: str, line_no: int, start: int, end: int, dictionary, buckets) -> None:
    result = classify(word.lower(), dictionary)
    status = result["status"]
    if status == "ste":
        return
    if status == "non_ste":
        _record(buckets["non_ste"], original_word, line_no, start, end, senses=result["senses"])
    elif status == "technical":
        _record(
            buckets["technical"],
            original_word,
            line_no,
            start,
            end,
            definition=result["technical"]["definition"],
            abbreviation_definition=result["technical"]["abbreviation_definition"],
        )
    else:
        _record(buckets["unknown"], original_word, line_no, start, end)


def _classify_token(token: str, line: str, line_no: int, start: int, end: int, dictionary, buckets) -> None:
    result = classify(token, dictionary)
    if result["status"] != "unknown" or "-" not in token:
        _classify_and_record(token, line[start:end], line_no, start, end, dictionary, buckets)
        return
    # Hyphen fallback (spec §5.4): the whole token is unknown, so check each
    # hyphen-separated part on its own instead of flagging the compound.
    cursor = start
    for part in token.split("-"):
        part_start = cursor
        part_end = part_start + len(part)
        cursor = part_end + 1  # skip the hyphen
        if part and not part.isdigit():
            _classify_and_record(part, line[part_start:part_end], line_no, part_start, part_end, dictionary, buckets)


def _finalize(bucket: dict) -> tuple[list[dict], bool]:
    truncated = bucket.pop("__truncated__", False)
    return list(bucket.values()), truncated


def check_text(text: str, dictionary, include_unknown: bool = True) -> dict:
    """Scan text for non-STE, unknown, and technical words (spec §3.2, §5)."""
    if not isinstance(text, str):
        raise ValueError("text must be a string")
    if not text.strip():
        raise ValueError("text must not be empty")
    if len(text) > MAX_TEXT_CHARS:
        raise ValueError(f"text exceeds the {MAX_TEXT_CHARS}-character limit; split the document")

    buckets = {"non_ste": {}, "unknown": {}, "technical": {}}
    tokens_scanned = 0

    for line_no, line in enumerate(text.split("\n"), start=1):
        lowered = line.lower()
        consumed = [False] * len(lowered)

        for phrase_entry in dictionary.phrases:
            phrase = phrase_entry["word"].lower()
            pattern = re.compile(r"\b" + re.escape(phrase).replace(r"\ ", r"\s+") + r"\b")
            for match in pattern.finditer(lowered):
                mstart, mend = match.span()
                if any(consumed[mstart:mend]):
                    continue
                for i in range(mstart, mend):
                    consumed[i] = True
                tokens_scanned += 1
                _record(
                    buckets["non_ste"],
                    line[mstart:mend],
                    line_no,
                    mstart,
                    mend,
                    senses=phrase_entry["senses"],
                )

        for match in _TOKEN_RE.finditer(lowered):
            mstart, mend = match.span()
            if any(consumed[mstart:mend]):
                continue
            token = match.group()
            if token.isdigit():
                continue
            tokens_scanned += 1
            _classify_token(token, line, line_no, mstart, mend, dictionary, buckets)

    non_ste_items, non_ste_truncated = _finalize(buckets["non_ste"])
    technical_items, technical_truncated = _finalize(buckets["technical"])
    unknown_items, unknown_truncated = _finalize(buckets["unknown"])

    summary = {
        "tokens_scanned": tokens_scanned,
        "non_ste": len(non_ste_items),
        "unknown": len(unknown_items),
        "technical": len(technical_items),
    }
    if non_ste_truncated:
        summary["non_ste_truncated"] = True
    if technical_truncated:
        summary["technical_truncated"] = True
    if unknown_truncated and include_unknown:
        summary["unknown_truncated"] = True

    result = {"summary": summary, "non_ste": non_ste_items, "technical": technical_items}
    if include_unknown:
        result["unknown"] = unknown_items
    return result
