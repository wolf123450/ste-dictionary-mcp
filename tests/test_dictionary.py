from ste_mcp.contractions import CONTRACTIONS


def test_contractions_cover_common_cases():
    assert CONTRACTIONS["don't"] == "DO NOT"
    assert CONTRACTIONS["can't"] == "CANNOT"
    assert CONTRACTIONS["won't"] == "WILL NOT"
    assert CONTRACTIONS["isn't"] == "IS NOT"


def test_contractions_are_lowercase_keys():
    assert all(key == key.lower() for key in CONTRACTIONS)


import json
from pathlib import Path

import pytest

from ste_mcp.dictionary import Dictionary

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


@pytest.fixture(scope="module")
def dictionary():
    return Dictionary(DATA_DIR)


def test_raises_on_missing_data_dir(tmp_path):
    with pytest.raises(FileNotFoundError):
        Dictionary(tmp_path / "does-not-exist")


def test_blank_word_entry_is_dropped(dictionary):
    assert "" not in dictionary.single
    for entries in dictionary.single.values():
        assert all(e["word"] for e in entries)


def test_corrupted_entries_are_dropped(dictionary):
    all_words = {e["word"] for entries in dictionary.single.values() for e in entries}
    assert "AS ... AS" not in all_words
    assert "Be accurate. If it is possible, use the name of the product." not in all_words
    # Real ellipsis-corrupted word entries present in the live snapshot
    # (U+2026 "…", not literal ASCII "..."); confirmed by direct inspection
    # of data/ste_dictionary.json.
    assert "IF … NOT" not in all_words
    assert "LET …. STAY" not in all_words
    assert "MAKE…SOFT" not in all_words
    assert "TIGHTEN … WITH YOUR HAND" not in all_words


def test_ellipsis_corrupted_alternative_is_dropped_with_note(dictionary):
    # Several rows in the live snapshot (e.g. id 3442's alternative
    # "IF … NOT", U+2026 ellipsis) must be sanitized to alternative=None
    # with a note, never passed through with the ellipsis character intact.
    found_sanitized = False
    for entries_list in dictionary.single.values():
        for entry in entries_list:
            for sense in entry["senses"]:
                if sense["alternative"] is not None:
                    assert "…" not in sense["alternative"]["word"]
                    found_sanitized = True
    assert found_sanitized


def test_all_caps_multiword_phrase_is_kept(dictionary):
    all_words = {e["word"] for entries in dictionary.single.values() for e in entries}
    assert "IF IT IS POSSIBLE" in all_words or "FOR EXAMPLE" in all_words


def test_known_non_ste_entry_shape(dictionary):
    entries = dictionary.single["abaft"]
    assert len(entries) == 1
    entry = entries[0]
    assert entry["is_ste"] is False
    assert entry["part_of_speech"] == "prep"
    sense = entry["senses"][0]
    assert sense["alternative"] == {"word": "AFT OF", "part_of_speech": "prep"}
    assert sense["note"] is None


def test_note_like_alternative_becomes_none_with_note(dictionary):
    note_found = False
    for entries in dictionary.single.values():
        for entry in entries:
            for sense in entry["senses"]:
                if sense["note"] is not None:
                    assert sense["alternative"] is None
                    note_found = True
    assert note_found, "expected at least one note-like alternative in the snapshot"


def test_phrases_are_non_ste_multiword_and_longest_first(dictionary):
    assert all(" " in p["word"] and not p["is_ste"] for p in dictionary.phrases)
    lengths = [len(p["word"].split()) for p in dictionary.phrases]
    assert lengths == sorted(lengths, reverse=True)


def test_inflections_map_to_canonical_word(dictionary):
    assert dictionary.inflections.get("goes") == "GO" or any(
        v == "GO" for v in dictionary.inflections.values()
    )


def test_technical_dictionary_loaded(dictionary):
    assert "2d" in dictionary.technical
    assert dictionary.technical["2d"]["abbreviation_definition"] == "two-dimensional"


def test_info_reports_counts_and_provenance(dictionary):
    info = dictionary.info()
    assert info["source"] == "ste.valaratomics.com"
    assert info["terms_total"] == info["terms_ste"] + info["terms_non_ste"] + info["sanitized_dropped"]
    assert info["technical_terms"] == len(dictionary.technical)
    assert info["multi_word_phrases"] == len(dictionary.phrases)
    assert set(info["data_files"]) == {"ste_dictionary.json", "raw_tech_dict.json"}


def test_dictionary_info_pinned_counts(dictionary):
    # Fix 6: pin the actual current values (post Fix 1/Fix 2) so a future
    # regression that silently drops data during sanitization fails a
    # concrete assertion, not just the terms_total identity check above
    # (which holds true regardless of how much data is dropped).
    info = dictionary.info()
    # +2 vs. the scraped-only snapshot for the hand-authored "could"/"might"
    # modal-verb additions (see ste_mcp/modals.py), both non-STE.
    assert info["terms_total"] == 2429
    assert info["terms_ste"] == 1068
    assert info["terms_non_ste"] == 1319
    assert info["sanitized_dropped"] == 42
    assert info["multi_word_phrases"] == 42
    assert info["technical_terms"] == 3042


def test_technical_multiword_term_confirmed_in_raw_data():
    # Confirm the term is actually present in the raw source data before
    # asserting on the sanitized dictionary, per the task instructions.
    raw = json.loads((DATA_DIR / "raw_tech_dict.json").read_text(encoding="utf-8"))
    assert any(
        rec.get("word", "").strip() == "American National Standards Institute"
        for rec in raw
    )


def test_technical_multiword_term_is_kept(dictionary):
    # Fix 1: the technical dictionary must not apply the STE dictionary's
    # sentence-fragment/ALL-CAPS rule 3 -- legitimate multi-word technical
    # terms like "American National Standards Institute" are not ALL-CAPS
    # and were previously (wrongly) dropped by _is_corrupted_word.
    entry = dictionary.technical.get("american national standards institute")
    assert entry is not None
    assert entry["word"] == "American National Standards Institute"
    assert entry["abbreviation_definition"] == "ANSI"


def test_phrases_with_valid_alternative_confirmed_in_raw_data():
    raw = json.loads((DATA_DIR / "ste_dictionary.json").read_text(encoding="utf-8"))
    by_word = {rec.get("word", "").strip().lower(): rec for rec in raw}
    assert by_word["by means of"]["rows"][0]["alternative"]["word"] == "WITH"
    assert by_word["back and forth"]["rows"][0]["alternative"]["word"] == "DIRECTION"


def test_non_ste_phrase_with_valid_alternative_is_kept(dictionary):
    # Fix 2: a genuine 3+-token non-STE phrase with a clean alternative and
    # no internal sentence punctuation must survive sanitization, unlike a
    # sentence-fragment note (e.g. the "Be accurate..." case below).
    for word in ("by means of", "back and forth"):
        assert word in dictionary.single
        entry = dictionary.single[word][0]
        assert entry["is_ste"] is False
        assert entry["senses"][0]["alternative"] is not None

    all_words = {e["word"] for entries in dictionary.single.values() for e in entries}
    assert "by means of" in all_words
    assert "back and forth" in all_words

    phrase_words = {p["word"] for p in dictionary.phrases}
    assert "by means of" in phrase_words
    assert "back and forth" in phrase_words


def test_sentence_fragment_note_still_dropped(dictionary):
    # Existing sentence-fragment-shaped "words" (no valid alternative, and/or
    # containing sentence punctuation) must still be dropped under the
    # refined rule 3.
    all_words = {e["word"] for entries in dictionary.single.values() for e in entries}
    assert "Be accurate. If it is possible, use the name of the product." not in all_words
