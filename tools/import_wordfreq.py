#!/usr/bin/env python3
"""Create a frequency-ranked ASCII Wordle list for a language."""

from __future__ import annotations

import argparse
from pathlib import Path

from normalize_words import unaccent_ascii


def import_words(language: str, minimum: int, maximum: int, limit: int) -> list[str]:
    try:
        from wordfreq import iter_wordlist
    except ImportError as error:
        raise RuntimeError("this generator requires wordfreq==3.1.1") from error

    words: list[str] = []
    seen: set[str] = set()
    for candidate in iter_wordlist(language):
        word = unaccent_ascii(candidate)
        if not word.isalpha() or not minimum <= len(word) <= maximum:
            continue
        if word in seen:
            continue
        seen.add(word)
        words.append(word)
        if len(words) == limit:
            break
    if len(words) < limit:
        raise ValueError(f"{language}: only {len(words)} words, need {limit}")
    return words


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--language", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=20_000)
    parser.add_argument("--min-length", type=int, default=3)
    parser.add_argument("--max-length", type=int, default=15)
    args = parser.parse_args()

    words = import_words(
        args.language,
        args.min_length,
        args.max_length,
        args.limit,
    )
    header = (
        f"# {args.language} Wordle words from wordfreq 3.1.1.\n"
        "# NO ACCENTS: folded to lowercase ASCII for ZX Spectrum.\n"
        "# wordfreq data: CC BY-SA 4.0; code: Apache-2.0.\n"
        "# Sources and attribution: see data/README.md.\n"
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(header + "\n".join(words) + "\n", encoding="ascii")
    print(f"{args.language}: wrote {len(words)} words to {args.output}")


if __name__ == "__main__":
    main()
