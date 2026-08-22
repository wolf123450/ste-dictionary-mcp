"""Structural ASD-STE100 rule checks (sentence length, passive voice,
imperative mood, noun clusters, paragraph length, gerund-as-noun) using
NLTK's classic statistical POS tagger. No MCP imports -- pure logic,
unit-testable standalone, mirroring the module boundary of
ste_mcp/dictionary.py and ste_mcp/matcher.py.

This is NOT a grammar checker and NOT a machine-learning model beyond a
small classic statistical tagger: it uses NLTK's averaged perceptron
tagger (English) plus the punkt_tab sentence/word tokenizer -- lightweight
statistical models (a few MB), not a dependency parser, not spaCy, not a
LanguageTool-style rule engine. See README.md's Setup section for the
one-time NLTK data download step; if that data is missing, the functions
below raise a RuntimeError naming the exact command to run.

Design notes and known limitations (read before trusting a finding):

* Sentences are tokenized per LINE, not across the whole document. This
  keeps position reporting simple and consistent with matcher.py's
  check_text (1-based line numbers), but it means: a long sentence that a
  human hard-wrapped across two lines is scored as two shorter sentences
  (sentence_length may under-count), and a paragraph whose sentences are
  each wrapped across multiple lines will over-count its sentence total
  (paragraph_length may over-count). This tool assumes one
  instruction/sentence per line, which matches ASD-STE100 procedural
  writing style; free-flowing prose wrapped at a fixed column width should
  be reflowed to one sentence per line before calling this tool.
* The imperative-mood and gerund-as-noun heuristics rely only on POS tags
  (no dependency parse), so they will sometimes misclassify unusual
  sentence structures -- e.g. a sentence-initial word the tagger mistags
  as NNP/JJ instead of VB/NN can slip past either heuristic. Both
  heuristics default to NOT flagging when the pattern is ambiguous, to
  keep false positives low at the cost of some misses. Treat every finding
  here as a candidate for human review, not a certainty.
"""

from __future__ import annotations

MAX_TEXT_CHARS = 200_000
MAX_SENTENCE_WORDS = 20
MAX_NOUN_CLUSTER_RUN = 3  # runs of 4+ are flagged
MAX_PARAGRAPH_SENTENCES = 6

NOUN_TAGS = {"NN", "NNS", "NNP", "NNPS"}
BE_FORMS = {"am", "is", "are", "was", "were", "be", "been", "being"}
FINITE_VERB_TAGS = {"VBZ", "VBD", "VBP", "MD"}
SUBJECT_TAGS = {"PRP", "NN", "NNS", "NNP", "NNPS", "WP", "EX", "DT"}
_ADVERB_TAGS = {"RB", "RBR", "RBS"}

_NLTK_SETUP_HINT = (
    "NLTK data not found. Run this one-time setup step: "
    "python scripts/download_nltk_data.py"
)


def _nltk():
    try:
        import nltk
    except ImportError as exc:
        raise RuntimeError(
            "nltk is required for check_structure; install it via "
            "`pip install -r requirements.txt`."
        ) from exc
    return nltk


def _pos_tag_sentence(sentence: str) -> list[tuple[str, str]]:
    nltk = _nltk()
    try:
        tokens = nltk.word_tokenize(sentence)
        return nltk.pos_tag(tokens)
    except LookupError as exc:
        raise RuntimeError(_NLTK_SETUP_HINT) from exc


def _sentences_in_line(line: str) -> list[tuple[str, int, int]]:
    """Split one line into (sentence_text, start_offset, end_offset)
    triples, offsets 0-based within the line."""
    if not line.strip():
        return []
    nltk = _nltk()
    try:
        sentences = nltk.sent_tokenize(line)
    except LookupError as exc:
        raise RuntimeError(_NLTK_SETUP_HINT) from exc
    results = []
    cursor = 0
    for sent in sentences:
        idx = line.find(sent, cursor)
        if idx == -1:
            idx = line.find(sent)
        if idx == -1:
            continue
        results.append((sent, idx, idx + len(sent)))
        cursor = idx + len(sent)
    return results


def _word_count(tagged: list[tuple[str, str]]) -> int:
    return sum(1 for word, _tag in tagged if any(ch.isalnum() for ch in word))


def _find_passive(tagged: list[tuple[str, str]]) -> list[list[str]]:
    findings = []
    n = len(tagged)
    i = 0
    while i < n:
        word, _tag = tagged[i]
        if word.lower() in BE_FORMS:
            j = i + 1
            while j < n and (tagged[j][1] in _ADVERB_TAGS or tagged[j][0].lower() == "not"):
                j += 1
            if j < n and tagged[j][1] == "VBN":
                findings.append([tagged[k][0] for k in range(i, j + 1)])
        i += 1
    return findings


def _first_content_index(tagged: list[tuple[str, str]]) -> int | None:
    for idx, (word, _tag) in enumerate(tagged):
        if any(ch.isalnum() for ch in word):
            return idx
    return None


def _is_imperative(tagged: list[tuple[str, str]]) -> bool:
    """Heuristic imperative-mood detector (see module docstring for
    limitations). Defaults to True (don't flag) when the pattern is
    ambiguous, to keep false positives low."""
    idx = _first_content_index(tagged)
    if idx is None:
        return True

    word, tag = tagged[idx]
    if tag == "VB":
        return True

    # "Do not <verb>" / "Does not <verb>" imperative negation -- checked by
    # surface word, not tag, since "Do" is frequently mistagged NNP at the
    # start of a sentence.
    if (
        word.lower() in ("do", "does")
        and idx + 2 < len(tagged)
        and tagged[idx + 1][0].lower() == "not"
        and tagged[idx + 2][1] == "VB"
    ):
        return True

    if tag in SUBJECT_TAGS:
        for k in range(idx + 1, min(idx + 5, len(tagged))):
            t2 = tagged[k][1]
            if t2 in FINITE_VERB_TAGS:
                return False
            if t2 == "VB":
                break
        return True

    return True


def _find_noun_clusters(tagged: list[tuple[str, str]]) -> list[list[str]]:
    findings = []
    n = len(tagged)
    i = 0
    while i < n:
        if tagged[i][1] in NOUN_TAGS:
            j = i
            while j < n and tagged[j][1] in NOUN_TAGS:
                j += 1
            if j - i > MAX_NOUN_CLUSTER_RUN:
                findings.append([tagged[k][0] for k in range(i, j)])
            i = j
        else:
            i += 1
    return findings


def _find_gerund_as_noun(tagged: list[tuple[str, str]]) -> list[str]:
    findings = []
    n = len(tagged)
    for i, (word, tag) in enumerate(tagged):
        if tag != "VBG":
            continue
        prev_word = tagged[i - 1][0] if i > 0 else None
        prev_tag = tagged[i - 1][1] if i > 0 else None
        next_word = tagged[i + 1][0] if i + 1 < n else None

        preceded_by_be = prev_word is not None and prev_word.lower() in BE_FORMS
        if preceded_by_be:
            continue  # part of a progressive verb phrase, not nominal

        is_sentence_start = i == 0
        preceded_by_det_or_prep = prev_tag in ("DT", "PRP$", "IN")
        followed_by_copula = next_word is not None and next_word.lower() in BE_FORMS

        if is_sentence_start or preceded_by_det_or_prep or followed_by_copula:
            findings.append(word)
    return findings


def _paragraphs(text: str) -> list[tuple[int, int, list[tuple[int, str]]]]:
    """Split text into paragraphs (blocks of consecutive non-blank lines
    separated by blank lines). Returns (start_line, end_line, lines) where
    lines is a list of (1-based line_no, line_text)."""
    lines = text.split("\n")
    paragraphs: list[tuple[int, int, list[tuple[int, str]]]] = []
    current: list[tuple[int, str]] = []
    for line_no, line in enumerate(lines, start=1):
        if line.strip() == "":
            if current:
                paragraphs.append((current[0][0], current[-1][0], current))
                current = []
        else:
            current.append((line_no, line))
    if current:
        paragraphs.append((current[0][0], current[-1][0], current))
    return paragraphs


def check_structure(text: str) -> dict:
    """Scan text for structural ASD-STE100 violations that a word-list
    dictionary can't catch: overlong sentences, passive voice, non-imperative
    mood, noun clusters of 4+, overlong paragraphs, and gerunds used as
    nouns/adjectives rather than progressive verbs. Diagnostic only -- no
    rewrite suggestions. See module docstring for the per-line sentence
    tokenization assumption and heuristic limitations. Positions are 1-based
    line numbers with 0-based character offsets, consistent with
    matcher.check_text."""
    if not isinstance(text, str):
        raise ValueError("text must be a string")
    if not text.strip():
        raise ValueError("text must not be empty")
    if len(text) > MAX_TEXT_CHARS:
        raise ValueError(f"text exceeds the {MAX_TEXT_CHARS}-character limit; split the document")

    findings: dict[str, list[dict]] = {
        "sentence_length": [],
        "passive_voice": [],
        "non_imperative": [],
        "noun_clusters": [],
        "paragraph_length": [],
        "gerund_as_noun": [],
    }

    for _start_line, _end_line, lines in _paragraphs(text):
        sentence_count = 0
        for line_no, line in lines:
            for sent, s_start, s_end in _sentences_in_line(line):
                sentence_count += 1
                tagged = _pos_tag_sentence(sent)

                word_count = _word_count(tagged)
                if word_count > MAX_SENTENCE_WORDS:
                    findings["sentence_length"].append(
                        {
                            "line": line_no,
                            "start": s_start,
                            "end": s_end,
                            "sentence": sent,
                            "word_count": word_count,
                        }
                    )

                for trigger_words in _find_passive(tagged):
                    findings["passive_voice"].append(
                        {
                            "line": line_no,
                            "start": s_start,
                            "end": s_end,
                            "sentence": sent,
                            "trigger_words": trigger_words,
                        }
                    )

                if not _is_imperative(tagged):
                    findings["non_imperative"].append(
                        {
                            "line": line_no,
                            "start": s_start,
                            "end": s_end,
                            "sentence": sent,
                        }
                    )

                for words in _find_noun_clusters(tagged):
                    findings["noun_clusters"].append(
                        {
                            "line": line_no,
                            "start": s_start,
                            "end": s_end,
                            "sentence": sent,
                            "words": words,
                        }
                    )

                for word in _find_gerund_as_noun(tagged):
                    findings["gerund_as_noun"].append(
                        {
                            "line": line_no,
                            "start": s_start,
                            "end": s_end,
                            "sentence": sent,
                            "word": word,
                        }
                    )

        if sentence_count > MAX_PARAGRAPH_SENTENCES:
            findings["paragraph_length"].append(
                {
                    "start_line": _start_line,
                    "end_line": _end_line,
                    "sentence_count": sentence_count,
                }
            )

    summary = {rule: len(items) for rule, items in findings.items()}
    return {"summary": summary, **findings}
