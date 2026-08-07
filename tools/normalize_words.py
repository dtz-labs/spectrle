#!/usr/bin/env python3
"""PostgreSQL-unaccent-style transliteration for Latin-script word lists."""

from __future__ import annotations

import unicodedata

# NFKD removes combining accents. These letters and ligatures need explicit
# rules, just as PostgreSQL's unaccent.rules expands AE, OE, sharp s, etc.
EXPANSIONS = str.maketrans(
    {
        "æ": "ae",
        "ǽ": "ae",
        "œ": "oe",
        "ø": "o",
        "ł": "l",
        "đ": "d",
        "ð": "d",
        "þ": "th",
        "ħ": "h",
        "ı": "i",
        "ŋ": "n",
        "ŧ": "t",
    }
)


def unaccent_ascii(text: str) -> str:
    expanded = text.casefold().translate(EXPANSIONS)
    decomposed = unicodedata.normalize("NFKD", expanded)
    without_marks = "".join(
        character
        for character in decomposed
        if not unicodedata.category(character).startswith("M")
    )
    return without_marks.encode("ascii", "ignore").decode("ascii")
