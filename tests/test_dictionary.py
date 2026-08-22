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
    assert "IF  NOT" not in all_words
    assert "LET . STAY" not in all_words
    assert "AS ... AS" not in all_words
    assert "Be accurate. If it is possible, use the name of the product." not in all_words


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
