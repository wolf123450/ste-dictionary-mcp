"""Static map of English contractions to their STE expansion.

The dictionary snapshot contains zero contraction entries, but ASD-STE100
bans contractions outright, so contracted tokens are resolved here instead
of via dictionary lookup.
"""

CONTRACTIONS: dict[str, str] = {
    "don't": "DO NOT",
    "doesn't": "DOES NOT",
    "didn't": "DID NOT",
    "can't": "CANNOT",
    "couldn't": "COULD NOT",
    "won't": "WILL NOT",
    "wouldn't": "WOULD NOT",
    "shouldn't": "SHOULD NOT",
    "isn't": "IS NOT",
    "aren't": "ARE NOT",
    "wasn't": "WAS NOT",
    "weren't": "WERE NOT",
    "haven't": "HAVE NOT",
    "hasn't": "HAS NOT",
    "hadn't": "HAD NOT",
    "it's": "IT IS",
    "that's": "THAT IS",
    "there's": "THERE IS",
    "what's": "WHAT IS",
    "let's": "LET US",
    "you're": "YOU ARE",
    "they're": "THEY ARE",
    "we're": "WE ARE",
    "i'm": "I AM",
    "you'll": "YOU WILL",
    "we'll": "WE WILL",
    "they'll": "THEY WILL",
    "you've": "YOU HAVE",
    "we've": "WE HAVE",
    "they've": "THEY HAVE",
    "can't've": "CANNOT HAVE",
}
