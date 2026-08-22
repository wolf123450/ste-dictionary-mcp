"""FastMCP server exposing the STE dictionary tools over stdio."""

import os
from typing import Any

from mcp.server.fastmcp import FastMCP

from ste_mcp.dictionary import Dictionary
from ste_mcp.matcher import check_text as _check_text
from ste_mcp.matcher import check_word as _check_word

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
