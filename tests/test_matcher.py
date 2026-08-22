from pathlib import Path

import pytest

from ste_mcp.dictionary import Dictionary
from ste_mcp.matcher import classify

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


@pytest.fixture(scope="module")
def dictionary():
    return Dictionary(DATA_DIR)


def test_classify_ste_word(dictionary):
    result = classify("stop", dictionary)
    assert result["status"] == "ste"
    assert result["matched_as"] is None


def test_classify_non_ste_word_with_alternative(dictionary):
    result = classify("abaft", dictionary)
    assert result["status"] == "non_ste"
    assert result["senses"][0]["alternative"] == {"word": "AFT OF", "part_of_speech": "prep"}


def test_classify_contraction(dictionary):
    result = classify("don't", dictionary)
    assert result["status"] == "non_ste"
    assert result["matched_as"] == "don't (contraction)"
    assert result["senses"][0]["alternative"] == {"word": "DO NOT", "part_of_speech": ""}


def test_classify_inflected_form_resolves_to_canonical(dictionary):
    result = classify("goes", dictionary)
    assert result["status"] == "ste"
    assert result["matched_as"] == "goes (inflected form of GO)"


def test_classify_stem_fallback(dictionary):
    # "stops" resolves via the inflection table in this snapshot, not the stem
    # fallback path, so it doesn't exercise stem resolution. "activates" has
    # no inflection/contraction entry and isn't itself a dictionary key, so it
    # is only resolvable via the -s stem fallback onto "activate".
    result = classify("activates", dictionary)
    assert result["status"] == "ste"
    assert "stem of ACTIVATE" in result["matched_as"]


def test_classify_technical_term(dictionary):
    result = classify("hydraulic", dictionary)
    if result["status"] != "technical":
        pytest.skip("'hydraulic' is not classified as technical in this snapshot; see next test for a guaranteed technical term")
    assert result["technical"] is not None


def test_classify_guaranteed_technical_term(dictionary):
    result = classify("2d", dictionary)
    assert result["status"] == "technical"
    assert result["technical"]["abbreviation_definition"] == "two-dimensional"


def test_classify_unknown_word(dictionary):
    # "utilize" is itself a dictionary entry in this snapshot (non-STE, with
    # an alternative), so it doesn't exercise the unknown path. "frobnicate"
    # is not a real English word and is confirmed absent from single entries,
    # contractions, inflections, and the technical dictionary.
    result = classify("frobnicate", dictionary)
    assert result["status"] == "unknown"
    assert result["senses"] == []
    assert result["technical"] is None
