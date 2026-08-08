#!/usr/bin/env python3
"""Restore native spelling to Spectrle release word lists.

The legacy lists provide ranked ASCII lookup keys.  This tool goes back to the
same lexical sources and keeps every native spelling represented by a selected
five- or six-letter key.  The resulting frequency-ranked UTF-8 files are the
inputs for the accent-aware release dictionaries.
"""

from __future__ import annotations

import argparse
import unicodedata
import zipfile
from collections.abc import Iterable
from pathlib import Path

from import_wordnet import xml_lemmas
from normalize_words import unaccent_ascii

DEFAULT_LENGTHS = (5,)


def native_spelling(text: str) -> str:
    """Return one stable, lowercase Unicode representation."""
    return unicodedata.normalize("NFC", text.strip().casefold())


def is_latin_letter(character: str) -> bool:
    return character.isalpha() and "LATIN" in unicodedata.name(character, "")


def is_native_word(
    word: str,
    language: str,
    key: str,
    lengths: tuple[int, ...] = DEFAULT_LENGTHS,
) -> bool:
    """Validate a native spelling whose lookup key has an enabled length.

    Catalan's middle dot is not a letter of its own: ``al\N{MIDDLE DOT}lel``
    therefore remains a five-letter word.  It is retained in the source form
    and is collapsed to one display-aware glyph by the dictionary builder.
    """
    if len(key) not in lengths or not key.isascii() or not key.isalpha():
        return False

    for character in word:
        if is_latin_letter(character):
            continue
        if language == "ca" and character == "\N{MIDDLE DOT}":
            continue
        return False

    if language == "ca" and "\N{MIDDLE DOT}" in word:
        if word.count("\N{MIDDLE DOT}") != 1 or "l\N{MIDDLE DOT}l" not in word:
            return False
    return sum(character.isalpha() for character in word) == len(key)


def load_ascii_keys(
    path: Path, lengths: tuple[int, ...] = DEFAULT_LENGTHS
) -> list[str]:
    keys: list[str] = []
    seen: set[str] = set()
    for raw in path.read_text(encoding="ascii").splitlines():
        word = raw.strip()
        if not word or word.startswith("#") or len(word) not in lengths:
            continue
        if not word.isalpha() or not word.islower():
            raise ValueError(f"invalid ASCII lookup key: {word!r}")
        if word not in seen:
            keys.append(word)
            seen.add(word)
    return keys


def rank_words(
    words: Iterable[str],
    key_order: list[str],
    frequency_language: str | None = None,
) -> list[str]:
    """Put common spellings first so memory trimming removes the rare tail."""
    unique = set(words)
    key_rank = {key: index for index, key in enumerate(key_order)}
    scores: dict[str, float] = {}
    if frequency_language is not None:
        try:
            from wordfreq import word_frequency
        except ImportError as error:
            raise RuntimeError("frequency ranking requires wordfreq==3.1.1") from error
        scores = {word: word_frequency(word, frequency_language) for word in unique}
    return sorted(
        unique,
        key=lambda word: (
            -scores.get(word, 0.0),
            key_rank[unaccent_ascii(word)],
            word,
        ),
    )


def wordnet_words(
    paths: list[Path],
    language: str,
    allowed_keys: list[str],
    *,
    reject_uppercase: bool = False,
    lengths: tuple[int, ...] = DEFAULT_LENGTHS,
    frequency_language: str | None = None,
) -> tuple[list[str], set[str]]:
    words: set[str] = set()
    covered: set[str] = set()
    allowed = set(allowed_keys)

    for path in paths:
        for candidate in xml_lemmas(path):
            if candidate.isupper() or (
                reject_uppercase and any(char.isupper() for char in candidate)
            ):
                continue
            word = native_spelling(candidate)
            key = unaccent_ascii(word)
            if key not in allowed or not is_native_word(word, language, key, lengths):
                continue
            words.add(word)
            covered.add(key)

    missing = allowed - covered
    if missing:
        sample = ", ".join(sorted(missing)[:10])
        raise ValueError(
            f"{language}: source did not restore {len(missing)} keys: {sample}"
        )
    return rank_words(words, allowed_keys, frequency_language), missing


def wordfreq_words(
    language: str,
    allowed_keys: list[str],
    *,
    selection_limit: int,
    lengths: tuple[int, ...] = DEFAULT_LENGTHS,
) -> tuple[list[str], set[str]]:
    try:
        from wordfreq import iter_wordlist
    except ImportError as error:
        raise RuntimeError("wordfreq generation requires wordfreq==3.1.1") from error

    words: list[str] = []
    seen_words: set[str] = set()
    selected_keys: set[str] = set()
    allowed = set(allowed_keys)

    # Reproduce import_wordfreq.py's original cutoff.  Native variants seen
    # before the Nth distinct ASCII key are retained instead of being merged.
    for candidate in iter_wordlist(language):
        word = native_spelling(candidate)
        key = unaccent_ascii(word)
        if not key.isalpha() or not 3 <= len(key) <= 15:
            continue
        if (
            key in allowed
            and word not in seen_words
            and is_native_word(word, language, key, lengths)
        ):
            words.append(word)
            seen_words.add(word)
        selected_keys.add(key)
        if len(selected_keys) == selection_limit:
            break

    missing = allowed - {unaccent_ascii(word) for word in words}
    if missing:
        sample = ", ".join(sorted(missing)[:10])
        raise ValueError(
            f"{language}: wordfreq did not restore {len(missing)} keys: {sample}"
        )
    return words, missing


def read_zip_lines(path: Path, member: str) -> Iterable[str]:
    with zipfile.ZipFile(path) as archive, archive.open(member) as stream:
        for raw in stream:
            yield raw.decode("utf-8").strip()


def polish_words(
    sjp_zip: Path,
    games_zip: Path,
    allowed_keys: list[str],
    *,
    lengths: tuple[int, ...] = DEFAULT_LENGTHS,
    frequency_language: str | None = None,
) -> tuple[list[str], set[str]]:
    # Exact native spelling matters here.  Comparing only unaccented forms
    # incorrectly admitted e.g. the headword "g\N{LATIN SMALL LETTER A WITH OGONEK}dek"
    # merely because the unrelated playable form "gadek" was present.
    playable = {
        native_spelling(word) for word in read_zip_lines(games_zip, "slowa.txt") if word
    }
    words: set[str] = set()
    allowed = set(allowed_keys)

    for line in read_zip_lines(sjp_zip, "odm.txt"):
        if not line:
            continue
        candidate = line.split(",", 1)[0].strip()
        if not candidate or not candidate[0].islower():
            continue
        word = native_spelling(candidate)
        key = unaccent_ascii(word)
        if (
            word in playable
            and key in allowed
            and is_native_word(word, "pl", key, lengths)
        ):
            words.add(word)

    covered = {unaccent_ascii(word) for word in words}
    return (
        rank_words(words, allowed_keys, frequency_language),
        allowed - covered,
    )


def write_words(
    output: Path,
    language: str,
    words: list[str],
    source_label: str,
) -> None:
    lengths = sorted({len(unaccent_ascii(word)) for word in words})
    length_label = "/".join(str(length) for length in lengths)
    header = (
        f"# {language} Spectrle {length_label}-letter words with native spelling.\n"
        "# UTF-8 NFC; diacritics are preserved. Input uses the accentless key.\n"
        "# Most frequent spellings come first for deterministic memory trimming.\n"
        f"# Restored from {source_label} using the current ASCII selection.\n"
        "# Sources, licences, and attribution: see data/README.md.\n"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(header + "\n".join(words) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--language", required=True)
    parser.add_argument("--ascii-words", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--length", type=int, action="append", dest="lengths")
    parser.add_argument("--frequency-language")
    subparsers = parser.add_subparsers(dest="source_type", required=True)

    wordnet_parser = subparsers.add_parser("wordnet")
    wordnet_parser.add_argument("--input", type=Path, action="append", required=True)
    wordnet_parser.add_argument("--reject-uppercase", action="store_true")

    wordfreq_parser = subparsers.add_parser("wordfreq")
    wordfreq_parser.add_argument("--selection-limit", type=int, default=20_000)

    polish_parser = subparsers.add_parser("polish")
    polish_parser.add_argument("--sjp-zip", type=Path, required=True)
    polish_parser.add_argument("--games-zip", type=Path, required=True)

    args = parser.parse_args()
    lengths = tuple(args.lengths or DEFAULT_LENGTHS)
    allowed_keys = load_ascii_keys(args.ascii_words, lengths)

    if args.source_type == "wordnet":
        words, missing = wordnet_words(
            args.input,
            args.language,
            allowed_keys,
            reject_uppercase=args.reject_uppercase,
            lengths=lengths,
            frequency_language=args.frequency_language,
        )
        source_label = "the original WordNet lemmas"
    elif args.source_type == "wordfreq":
        words, missing = wordfreq_words(
            args.language,
            allowed_keys,
            selection_limit=args.selection_limit,
            lengths=lengths,
        )
        source_label = f"wordfreq 3.1.1 (first {args.selection_limit:,} keys)"
    else:
        words, missing = polish_words(
            args.sjp_zip,
            args.games_zip,
            allowed_keys,
            lengths=lengths,
            frequency_language=args.frequency_language,
        )
        source_label = "SJP.PL odmiany and slownik do gier"

    write_words(args.output, args.language, words, source_label)
    covered = len({unaccent_ascii(word) for word in words})
    print(
        f"{args.language}: wrote {len(words)} native spellings for {covered} keys "
        f"to {args.output}"
    )
    if missing:
        print(
            f"{args.language}: omitted {len(missing)} old ASCII keys without an "
            "exact native playable headword: " + ", ".join(sorted(missing))
        )


if __name__ == "__main__":
    main()
