"""One-time setup script: download the NLTK data used by
`ste_mcp.structure.check_structure` and trim it to the English-only subset.

`check_structure` needs two small classic statistical models (not deep
learning): the `punkt_tab` sentence/word tokenizer and the
`averaged_perceptron_tagger_eng` POS tagger. NLTK's downloader fetches
`punkt_tab` with tokenizer data for ~19 languages (~58MB total across both
packages), which blows the project's <25MB footprint budget. This script
downloads only what's needed, then deletes every non-English `punkt_tab`
language directory and the leftover .zip archives, leaving ~6MB of data.

Run once after `pip install -r requirements.txt`:

    python scripts/download_nltk_data.py

Safe to re-run (idempotent): re-downloading is a no-op if the trimmed data
is already present, and the trim step just removes what re-downloading
would re-add.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import nltk

PACKAGES = ["punkt_tab", "averaged_perceptron_tagger_eng"]

# Non-English languages shipped in the punkt_tab package that we don't need.
_PUNKT_TAB_LANGS_TO_REMOVE = [
    "czech", "danish", "dutch", "estonian", "finnish", "french", "german",
    "greek", "italian", "malayalam", "norwegian", "polish", "portuguese",
    "russian", "slovene", "spanish", "swedish", "turkish",
]


def main() -> None:
    for package in PACKAGES:
        nltk.download(package)

    for data_path in nltk.data.path:
        base = Path(data_path)

        punkt_tab_dir = base / "tokenizers" / "punkt_tab"
        if punkt_tab_dir.is_dir():
            for lang in _PUNKT_TAB_LANGS_TO_REMOVE:
                shutil.rmtree(punkt_tab_dir / lang, ignore_errors=True)

        for zip_name in ("tokenizers/punkt_tab.zip", "taggers/averaged_perceptron_tagger_eng.zip"):
            zip_path = base / zip_name
            if zip_path.is_file():
                zip_path.unlink()

    print("NLTK data ready (punkt_tab: English only, averaged_perceptron_tagger_eng).")


if __name__ == "__main__":
    main()
