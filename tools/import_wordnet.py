#!/usr/bin/env python3
"""Convert OMW/WordNet tab files or plain word lists to Spectrle ASCII words."""

from __future__ import annotations

import argparse
import gzip
import xml.etree.ElementTree as ET
from pathlib import Path

from normalize_words import unaccent_ascii


def candidate_from_line(line: str) -> str | None:
    fields = line.rstrip("\r\n").split("\t")
    if len(fields) == 1:
        return fields[0].strip()
    if any("lemma" in field.casefold() for field in fields[:-1]):
        return fields[-1].strip()
    if len(fields) == 2:
        return fields[-1].strip()
    return None


def xml_lemmas(path: Path):
    opener = gzip.open if path.name.endswith(".gz") else open
    with opener(path, "rb") as stream:
        for _, element in ET.iterparse(stream, events=("end",)):
            if element.tag.rsplit("}", 1)[-1] == "Lemma":
                written_form = element.attrib.get("writtenForm")
                if written_form:
                    yield written_form
            element.clear()


def text_lemmas(path: Path):
    with path.open(encoding="utf-8-sig", errors="strict") as stream:
        for line in stream:
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            candidate = candidate_from_line(line)
            if candidate is not None:
                yield candidate


def import_words(
    paths: list[Path],
    minimum: int,
    maximum: int,
    frequency_language: str | None = None,
    reject_uppercase: bool = False,
) -> list[str]:
    words: list[str] = []
    seen: set[str] = set()
    scores: dict[str, float] = {}
    score_word = None
    if frequency_language is not None:
        try:
            from wordfreq import word_frequency
        except ImportError as error:
            raise RuntimeError(
                "frequency ranking requires wordfreq==3.1.1"
            ) from error
        score_word = word_frequency

    for path in paths:
        candidates = (
            xml_lemmas(path)
            if path.name.endswith((".xml", ".xml.gz"))
            else text_lemmas(path)
        )
        for candidate in candidates:
            # WordNets contain acronyms such as "CIO" alongside ordinary
            # lemmas. Folding those to lowercase creates bogus Spectrle words.
            # Some sources also use capitalization reliably for proper names;
            # those can be rejected with the stricter flag.
            if candidate.isupper() or (
                reject_uppercase and any(char.isupper() for char in candidate)
            ):
                continue
            word = unaccent_ascii(candidate)
            if not word.isalpha() or not minimum <= len(word) <= maximum:
                continue
            if word not in seen:
                seen.add(word)
                words.append(word)
            if score_word is not None:
                score = score_word(candidate.casefold(), frequency_language)
                if score > scores.get(word, -1.0):
                    scores[word] = score
    if score_word is not None:
        words.sort(key=lambda word: (-scores.get(word, 0.0), word))
    return words


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--language", required=True)
    parser.add_argument("--min-length", type=int, default=3)
    parser.add_argument("--max-length", type=int, default=15)
    parser.add_argument("--min-count", type=int, default=1)
    parser.add_argument("--limit", type=int)
    parser.add_argument(
        "--frequency-language",
        help="rank retained lemmas using this wordfreq language code",
    )
    parser.add_argument(
        "--reject-uppercase",
        action="store_true",
        help="also reject title/mixed-case lemmas (proper names in reliable sources)",
    )
    args = parser.parse_args()

    words = import_words(
        args.input,
        args.min_length,
        args.max_length,
        args.frequency_language,
        args.reject_uppercase,
    )
    if len(words) < args.min_count:
        raise SystemExit(
            f"{args.language}: imported {len(words)} words, need {args.min_count}"
        )
    if args.limit is not None:
        words = words[: args.limit]
    header = (
        f"# {args.language} Spectrle words imported from OMW/WordNet.\n"
        "# NO ACCENTS: diacritics and Latin ligatures become lowercase ASCII.\n"
        + (
            f"# Ranked with wordfreq 3.1.1 for {args.frequency_language}.\n"
            if args.frequency_language
            else ""
        )
        + "# ALL-CAPS acronyms were rejected before ASCII folding.\n"
        + (
            "# Capitalized proper-name lemmas were also rejected.\n"
            if args.reject_uppercase
            else ""
        )
        + "# Preserve the licences and attribution of every input dataset.\n"
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(header + "\n".join(words) + "\n", encoding="ascii")
    print(f"{args.language}: wrote {len(words)} words to {args.output}")


if __name__ == "__main__":
    main()
