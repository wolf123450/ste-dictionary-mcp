"""Hand-authored additions for modal verbs that ASD-STE100 restricts but that
are missing from the scraped `data/ste_dictionary.json` snapshot.

ASD-STE100 approves only MUST/MAY/CAN/WILL as modal verbs. The scraped
snapshot already flags "should" and "would" as non-STE (with alternatives
IF/MUST and CAN respectively), but "could" and "might" are entirely absent
from the snapshot -- a data gap, since they are exactly the kind of modal
verb STE prohibits. These entries are authored here, separate from the
scraped data, to keep provenance clear (mirrors ste_mcp/contractions.py).

Each entry matches the shape `dictionary._load_ste_entries` produces after
sanitizing a scraped record, so it can be merged directly into
`Dictionary.single` and flow through `matcher.classify()`/`_from_entries`
with no special-casing.
"""

MODAL_ENTRIES: list[dict] = [
    {
        "id": "modal-could",
        "word": "could",
        "part_of_speech": "v",
        "part_of_speech_display": "verb",
        "other_forms": "",
        "is_ste": False,
        "senses": [
            {
                "definition": "",
                "ste_example": "THE TECHNICIAN CAN REMOVE THE PANEL WITHOUT TOOLS.",
                "non_ste_example": "The technician could remove the panel without tools.",
                "alternative": {"word": "CAN", "part_of_speech": "v"},
                "note": None,
                "part_of_speech": "v",
                "is_ste": False,
            }
        ],
    },
    {
        "id": "modal-might",
        "word": "might",
        "part_of_speech": "v",
        "part_of_speech_display": "verb",
        "other_forms": "",
        "is_ste": False,
        "senses": [
            {
                "definition": "",
                "ste_example": "THE INDICATOR MAY SHOW AN INCORRECT READING.",
                "non_ste_example": "The indicator might show an incorrect reading.",
                "alternative": {"word": "MAY", "part_of_speech": "v"},
                "note": None,
                "part_of_speech": "v",
                "is_ste": False,
            }
        ],
    },
]
