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


def test_classify_mixed_status_word_reports_ambiguous(dictionary):
    # "aid" has a noun entry (is_ste=True) and a verb entry (is_ste=False,
    # alternative "HELP"). Since some but not all entries are STE-approved,
    # the overall status must be "ambiguous" (not the unqualified "non_ste"
    # reserved for words where every sense is non-STE), and the non-STE
    # sense must still be present (with its own part_of_speech/is_ste) in
    # the flattened senses list.
    result = classify("aid", dictionary)
    assert result["status"] == "ambiguous"
    non_ste_senses = [s for s in result["senses"] if not s["is_ste"]]
    assert len(non_ste_senses) >= 1
    assert any(
        s["alternative"] is not None and s["alternative"]["word"] == "HELP"
        for s in non_ste_senses
    )
    assert any(s["part_of_speech"] == "v" for s in non_ste_senses)
    assert any(s["part_of_speech"] == "n" and s["is_ste"] for s in result["senses"])


def test_classify_unknown_word(dictionary):
    # "utilize" is itself a dictionary entry in this snapshot (non-STE, with
    # an alternative), so it doesn't exercise the unknown path. "frobnicate"
    # is not a real English word and is confirmed absent from single entries,
    # contractions, inflections, and the technical dictionary.
    result = classify("frobnicate", dictionary)
    assert result["status"] == "unknown"
    assert result["senses"] == []
    assert result["technical"] is None


from ste_mcp.matcher import check_text, check_word


def test_check_word_ste(dictionary):
    result = check_word("stop", dictionary)
    assert result["status"] == "ste"
    assert result["word"] == "stop"


def test_check_word_non_ste_reports_alternative(dictionary):
    result = check_word("abaft", dictionary)
    assert result["status"] == "non_ste"
    assert result["senses"][0]["alternative"]["word"] == "AFT OF"


def test_check_word_not_in_dictionary(dictionary):
    # "utilize" is itself a dictionary entry in this snapshot (non-STE), so it
    # doesn't exercise the not_in_dictionary path; use "frobnicate" (confirmed
    # absent from single/contractions/inflections/technical above) instead.
    result = check_word("frobnicate", dictionary)
    assert result["status"] == "not_in_dictionary"
    assert result["technical"] is None


def test_check_word_technical_term_reports_not_in_dictionary_with_technical(dictionary):
    result = check_word("2D", dictionary)
    assert result["status"] == "not_in_dictionary"
    assert result["technical"]["abbreviation_definition"] == "two-dimensional"


def test_check_word_mixed_senses_reports_ambiguous_with_note(dictionary):
    # "use" has a non-STE noun entry and an STE-approved verb entry in this
    # snapshot -- a genuine mix, not a single-entry non_ste word. check_word
    # must report "ambiguous" (not "non_ste"), keep every sense visible, and
    # include a note telling the caller to verify which sense applies.
    result = check_word("use", dictionary)
    assert result["status"] == "ambiguous"
    assert any(s["is_ste"] for s in result["senses"])
    assert any(not s["is_ste"] for s in result["senses"])
    assert result["note"] == (
        "This word has both STE-approved and non-STE senses; verify which applies in context."
    )


def test_check_word_mixed_senses_long_and_time(dictionary):
    # Confirm the mix isn't specific to "use": "long" (adj is_ste=True vs.
    # "as long as"/"no longer" non-STE) and "time" (noun is_ste=True vs.
    # verb is_ste=False) are also genuinely mixed in this snapshot.
    for word in ("long", "time"):
        result = check_word(word, dictionary)
        assert result["status"] == "ambiguous", word
        assert any(s["is_ste"] for s in result["senses"]), word
        assert any(not s["is_ste"] for s in result["senses"]), word


def test_check_word_all_non_ste_senses_still_reports_non_ste(dictionary):
    # "utilize" has only non-STE senses in this snapshot, so it must keep
    # reporting the unambiguous "non_ste" status, not "ambiguous".
    result = check_word("utilize", dictionary)
    assert result["status"] == "non_ste"
    assert all(not s["is_ste"] for s in result["senses"])
    assert "note" not in result


def test_check_word_fully_ste_word_unaffected(dictionary):
    # A word with only is_ste=True senses must remain unaffected by the
    # ambiguous-status change.
    result = check_word("stop", dictionary)
    assert result["status"] == "ste"
    assert "note" not in result


def test_check_text_flags_non_ste_word(dictionary):
    result = check_text("Install the unit abaft the panel.", dictionary)
    assert result["summary"]["non_ste"] == 1
    entry = result["non_ste"][0]
    assert entry["word"] == "abaft"
    assert entry["count"] == 1
    assert entry["positions"] == [{"line": 1, "start": 17, "end": 22}]


def test_check_text_mixed_sense_word_lands_in_ambiguous_bucket(dictionary):
    # "use" is a mixed-sense word (non-STE noun, STE verb) in this snapshot,
    # so it must land in the new "ambiguous" bucket, not "non_ste", and be
    # counted in summary["ambiguous"].
    result = check_text("Note the use of the tool.", dictionary)
    assert result["summary"]["ambiguous"] == 1
    ambiguous_words = {e["word"] for e in result["ambiguous"]}
    assert "use" in ambiguous_words
    non_ste_words = {e["word"] for e in result["non_ste"]}
    assert "use" not in non_ste_words
    entry = next(e for e in result["ambiguous"] if e["word"] == "use")
    assert any(s["is_ste"] for s in entry["senses"])
    assert any(not s["is_ste"] for s in entry["senses"])


def test_check_text_flags_contraction(dictionary):
    result = check_text("Don't open the door.", dictionary)
    words = {e["word"] for e in result["non_ste"]}
    assert "Don't" in words


def test_check_text_preserves_original_casing(dictionary):
    # The spec (§5) requires output to show the token as it appeared in the
    # original text, not the lowercased form used internally for matching.
    result = check_text("ABAFT the panel is broken.", dictionary)
    non_ste_words = {e["word"] for e in result["non_ste"]}
    assert "ABAFT" in non_ste_words
    assert "abaft" not in non_ste_words

    result2 = check_text("Please Frobnicate the tool.", dictionary)
    unknown_words = {e["word"] for e in result2["unknown"]}
    assert "Frobnicate" in unknown_words
    assert "frobnicate" not in unknown_words


def test_check_text_phrase_matched_once_not_twice(dictionary):
    result = check_text("Refer according to the manual.", dictionary)
    non_ste_words = [e["word"] for e in result["non_ste"]]
    assert non_ste_words.count("according to") <= 1
    assert "according" not in non_ste_words
    assert "to" not in non_ste_words


def test_check_text_hyphenated_known_parts_not_flagged_unknown(dictionary):
    result = check_text("Check the high-speed motor.", dictionary)
    unknown_words = {e["word"] for e in result["unknown"]}
    assert "high-speed" not in unknown_words
    assert "high" not in unknown_words
    assert "speed" not in unknown_words


def test_check_text_technical_bucket(dictionary):
    result = check_text("The unit uses a 2D display.", dictionary)
    technical_words = {e["word"] for e in result["technical"]}
    assert "2D" in technical_words


def test_check_text_unknown_word(dictionary):
    # "utilize" is itself a dictionary entry in this snapshot (non-STE), so it
    # would land in the non_ste bucket, not unknown; use "frobnicate" instead.
    result = check_text("Please frobnicate the correct tool.", dictionary)
    unknown_words = {e["word"] for e in result["unknown"]}
    assert "frobnicate" in unknown_words


def test_check_text_include_unknown_false_omits_bucket(dictionary):
    result = check_text("Please frobnicate the correct tool.", dictionary, include_unknown=False)
    assert "unknown" not in result


def test_check_text_rejects_empty_string(dictionary):
    with pytest.raises(ValueError):
        check_text("", dictionary)


def test_check_text_rejects_over_length_input(dictionary):
    with pytest.raises(ValueError):
        check_text("a" * 200_001, dictionary)


def test_check_text_approved_ste_word_produces_no_output(dictionary):
    result = check_text("Open the door and stop the test.", dictionary)
    all_words = (
        {e["word"] for e in result["non_ste"]}
        | {e["word"] for e in result["ambiguous"]}
        | {e["word"] for e in result["unknown"]}
        | {e["word"] for e in result["technical"]}
    )
    assert "open" not in all_words
    assert "stop" not in all_words


def test_lookup_technical_term_found_shape(dictionary):
    entry = dictionary.technical.get("2d")
    assert entry is not None
    payload = {"found": True, **entry}
    assert payload["found"] is True
    assert payload["abbreviation_definition"] == "two-dimensional"


def test_lookup_technical_term_not_found_shape(dictionary):
    entry = dictionary.technical.get("not-a-real-term-xyz")
    assert entry is None


def test_check_text_technical_bucket_includes_abbreviation_definition(dictionary):
    # Fix 3: check_text's technical bucket must also carry
    # abbreviation_definition, since most technical entries put their
    # content there instead of in `definition`.
    result = check_text("The unit uses a 2D display.", dictionary)
    entry = next(e for e in result["technical"] if e["word"] == "2D")
    assert entry["abbreviation_definition"] == "two-dimensional"


def test_contraction_sense_has_part_of_speech_and_is_ste(dictionary):
    # Fix 4: every sense dict, regardless of match path, must carry
    # part_of_speech and is_ste so a caller can filter senses by is_ste
    # without missing contraction/phrase matches.
    result = classify("don't", dictionary)
    sense = result["senses"][0]
    assert sense["part_of_speech"] == ""
    assert sense["is_ste"] is False


def test_phrase_match_sense_has_part_of_speech_and_is_ste(dictionary):
    result = check_text("Refer according to the manual.", dictionary)
    phrase_entry = next(e for e in result["non_ste"] if e["word"].lower() == "according to")
    sense = phrase_entry["senses"][0]
    assert "part_of_speech" in sense
    assert sense["is_ste"] is False


def test_phrase_match_reports_original_casing_not_canonical(dictionary):
    # Fix 4b: the phrase pass must report the original-case substring from
    # the input text, matching the token pass's behavior, not the
    # dictionary's canonical (lowercase) spelling.
    result = check_text("ACCORDING TO the manual, refer to it.", dictionary)
    words = {e["word"] for e in result["non_ste"]}
    assert "ACCORDING TO" in words
    assert "according to" not in words
