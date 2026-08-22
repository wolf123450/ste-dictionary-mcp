"""Unit tests for ste_mcp.structure -- one positive/negative example per rule.

Fixtures are written one-sentence-per-line (see structure.py's module
docstring for why: sentences are tokenized per line, so a sentence wrapped
across lines without its own terminal punctuation would be mis-split).
"""

from ste_mcp.structure import check_structure


def test_sentence_length_flags_long_sentence():
    text = (
        "Remove the access panel cover assembly before you start the daily "
        "maintenance inspection procedure for this specific unit "
        "configuration today right now."
    )
    result = check_structure(text)
    assert result["summary"]["sentence_length"] == 1
    assert result["sentence_length"][0]["line"] == 1


def test_sentence_length_ignores_short_sentence():
    result = check_structure("Remove the panel.")
    assert result["summary"]["sentence_length"] == 0


def test_passive_voice_flags_be_plus_participle():
    result = check_structure("The valve was removed by the technician.")
    assert result["summary"]["passive_voice"] == 1
    finding = result["passive_voice"][0]
    assert "was" in [w.lower() for w in finding["trigger_words"]]
    assert "removed" in [w.lower() for w in finding["trigger_words"]]


def test_passive_voice_ignores_active_sentence():
    result = check_structure("The technician removed the panel.")
    assert result["summary"]["passive_voice"] == 0


def test_non_imperative_flags_subject_plus_finite_verb():
    result = check_structure("You must remove the panel before the procedure starts.")
    assert result["summary"]["non_imperative"] == 1


def test_non_imperative_ignores_imperative_sentence():
    result = check_structure("Remove the panel before you start the procedure.")
    assert result["summary"]["non_imperative"] == 0


def test_non_imperative_ignores_imperative_negation():
    result = check_structure("Do not touch the hot exhaust pipe.")
    assert result["summary"]["non_imperative"] == 0


def test_noun_clusters_flags_four_or_more_consecutive_nouns():
    result = check_structure("Check the engine oil pressure sensor wire connector.")
    assert result["summary"]["noun_clusters"] == 1
    words = result["noun_clusters"][0]["words"]
    assert len(words) >= 4


def test_noun_clusters_ignores_short_runs():
    result = check_structure("Check the oil pressure gauge reading value carefully.")
    assert result["summary"]["noun_clusters"] == 0


def test_paragraph_length_flags_long_paragraph():
    lines = [f"Remove item {i}." for i in range(7)]
    text = "\n".join(lines)
    result = check_structure(text)
    assert result["summary"]["paragraph_length"] == 1
    assert result["paragraph_length"][0]["sentence_count"] == 7


def test_paragraph_length_ignores_short_paragraph():
    lines = [f"Remove item {i}." for i in range(6)]
    text = "\n".join(lines)
    result = check_structure(text)
    assert result["summary"]["paragraph_length"] == 0


def test_gerund_as_noun_flags_sentence_initial_gerund_subject():
    result = check_structure("Monitoring the pressure is important.")
    assert result["summary"]["gerund_as_noun"] == 1
    assert result["gerund_as_noun"][0]["word"].lower() == "monitoring"


def test_gerund_as_noun_ignores_progressive_verb_phrase():
    result = check_structure("You are monitoring the pressure now.")
    assert result["summary"]["gerund_as_noun"] == 0


def test_check_structure_rejects_non_string():
    import pytest

    with pytest.raises(ValueError):
        check_structure(123)  # type: ignore[arg-type]


def test_check_structure_rejects_empty_text():
    import pytest

    with pytest.raises(ValueError):
        check_structure("   ")


def test_check_structure_summary_has_all_six_rule_counts():
    result = check_structure("Remove the panel.")
    assert set(result["summary"].keys()) == {
        "sentence_length",
        "passive_voice",
        "non_imperative",
        "noun_clusters",
        "paragraph_length",
        "gerund_as_noun",
    }
