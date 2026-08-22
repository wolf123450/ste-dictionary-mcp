"""FastMCP server exposing the STE dictionary tools over stdio."""

import os
from typing import Any

from mcp.server.fastmcp import FastMCP

from ste_mcp.dictionary import Dictionary
from ste_mcp.matcher import check_text as _check_text
from ste_mcp.matcher import check_word as _check_word
from ste_mcp.structure import check_structure as _check_structure

DATA_DIR = os.environ.get("STE_DATA_DIR", "./data")
dictionary = Dictionary(DATA_DIR)

mcp = FastMCP("ste-dictionary")


@mcp.tool()
def check_word(word: str) -> dict[str, Any]:
    """Check whether a single word or phrase is ASD-STE100 Simple Technical
    English (STE). Returns status (ste/non_ste/ambiguous/not_in_dictionary),
    the STE alternative(s) with example sentences when non-STE, and
    technical-dictionary info when the word is an approved technical term.
    "ambiguous" means the word has both an STE-approved sense and a non-STE
    sense (all matched senses are still included, plus a note asking the
    caller to verify which sense applies in context) -- "non_ste" is reserved
    for words where every matched sense is non-STE."""
    return _check_word(word, dictionary)


@mcp.tool()
def check_text(text: str, include_unknown: bool = True) -> dict[str, Any]:
    """Scan a block of text for STE violations. Returns non_ste words (with
    STE alternatives and examples), ambiguous words (words with both an
    STE-approved sense and a non-STE sense, so the caller must check which
    sense applies in context), technical terms (informational), and
    optionally unknown words not found in either dictionary. Positions are
    1-based line numbers and 0-based character offsets. Input is capped at
    200,000 characters."""
    return _check_text(text, dictionary, include_unknown)


@mcp.tool()
def check_structure(text: str) -> dict[str, Any]:
    """Scan a block of text for structural ASD-STE100 violations that a
    word-list dictionary can't catch: sentences over ~20 words, passive
    voice (BE-verb + past-participle), non-imperative mood in instructional
    text, noun clusters of 4+ consecutive nouns, paragraphs over ~6
    sentences, and gerunds used as nouns/adjectives rather than progressive
    verbs. Uses a small classic statistical POS tagger (NLTK), not a full
    grammar checker -- diagnostic only, no rewrite suggestions. The
    imperative-mood and gerund-as-noun rules are inherently heuristic (see
    ste_mcp/structure.py's docstring); treat findings as candidates for
    human review. Sentences are tokenized per line (1-based line numbers,
    0-based character offsets within the line, consistent with
    check_text), so this assumes one sentence per line. Requires the NLTK
    punkt_tab and averaged_perceptron_tagger_eng data packages -- see
    README.md's Setup section."""
    return _check_structure(text)


@mcp.tool()
def lookup_technical_term(term: str) -> dict[str, Any]:
    """Look up an approved technical term or abbreviation and its
    definition/expansion."""
    entry = dictionary.technical.get(term.strip().lower())
    if entry is None:
        return {"found": False, "term": term}
    return {"found": True, **entry}


@mcp.tool()
def dictionary_info() -> dict[str, Any]:
    """Return provenance and coverage stats for the loaded STE dictionary
    snapshot (source, term counts, sanitization counts, data file mtimes)."""
    return dictionary.info()


if __name__ == "__main__":
    mcp.run()
