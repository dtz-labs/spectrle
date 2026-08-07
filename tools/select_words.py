#!/usr/bin/env python3
"""Select five-letter Polish Spectrle headwords from the official SJP.PL list."""

from __future__ import annotations

import argparse
import zipfile
from pathlib import Path

from normalize_words import unaccent_ascii

EXCLUDED_FRAGMENTS = (
    "kurw",
    "chuj",
    "pierd",
    "jeb",
    "cipa",
    "cipk",
    "kutas",
    "sperma",
    "dziwk",
    "skurw",
    "ruchacz",
)


def load_headwords(path: Path, length: int) -> set[str]:
    headwords: set[str] = set()
    with zipfile.ZipFile(path) as archive, archive.open("odm.txt") as stream:
        for raw in stream:
            line = raw.decode("utf-8").strip()
            if not line:
                continue
            word = line.split(",", 1)[0].strip()
            if (
                word
                and word[0].islower()
                and word.isalpha()
            ):
                folded = normalise(word)
                if (
                    len(folded) == length
                    and folded.isascii()
                    and folded.isalpha()
                    and any(vowel in folded for vowel in "aeiouy")
                    and not any(
                        fragment in folded for fragment in EXCLUDED_FRAGMENTS
                    )
                ):
                    headwords.add(folded)
    return headwords


def normalise(word: str) -> str:
    return unaccent_ascii(word)


def load_priority(path: Path | None, allowed: set[str]) -> list[str]:
    if path is None:
        return []

    priority: list[str] = []
    seen: set[str] = set()
    for raw in path.read_text(encoding="utf-8").splitlines():
        word = normalise(raw.strip())
        if word in allowed and word not in seen:
            priority.append(word)
            seen.add(word)
    return priority


def select(
    sjp_zip: Path,
    *,
    length: int = 5,
    limit: int = 0,
    priority_path: Path | None = None,
) -> list[str]:
    return select_lengths(
        sjp_zip,
        lengths=(length,),
        limit=limit,
        priority_path=priority_path,
    )


def select_lengths(
    sjp_zip: Path,
    *,
    lengths: tuple[int, ...],
    limit: int = 0,
    priority_path: Path | None = None,
) -> list[str]:
    headwords: set[str] = set()
    for length in lengths:
        headwords.update(load_headwords(sjp_zip, length))
    priority = load_priority(priority_path, headwords)
    priority_set = set(priority)
    ordered = priority + sorted(headwords - priority_set)

    if limit < 0:
        raise ValueError("limit cannot be negative")
    if limit and len(ordered) < limit:
        raise ValueError(f"only {len(ordered)} suitable words, need {limit}")
    return ordered[:limit] if limit else ordered


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sjp-zip", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--length", type=int, action="append", dest="lengths")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--priority-words", type=Path)
    args = parser.parse_args()

    lengths = tuple(args.lengths or (5,))
    words = select_lengths(
        args.sjp_zip,
        lengths=lengths,
        limit=args.limit,
        priority_path=args.priority_words,
    )
    length_label = "/".join(str(length) for length in lengths)
    header = (
        f"# Polish Spectrle {length_label}-letter headwords from SJP.PL.\n"
        "# Diacritics are intentionally folded to ASCII for the ZX Spectrum game.\n"
        "# Sources and licences: see data/README.md.\n"
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(header + "\n".join(words) + "\n", encoding="ascii")
    print(f"wrote {len(words)} words to {args.output}")


if __name__ == "__main__":
    main()
