#!/usr/bin/env python3
"""Check that a language dictionary is complete and fits both releases."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def source_count(path: Path) -> int:
    return sum(
        1
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    )


def check_modes(
    lengths: dict[str, int], allowed_lengths: tuple[int, ...], release: str
) -> None:
    for length in range(3, 16):
        count = int(lengths.get(str(length), 0))
        if length in allowed_lengths and count == 0:
            raise SystemExit(f"{release}: no words for {length}x{length} mode")
        if length not in allowed_lengths and count != 0:
            raise SystemExit(
                f"{release}: contains {count} unusable {length}-letter words"
            )


def check(
    manifest_path: Path,
    words_path: Path,
    expected_48: int,
    expected_128: int,
    max_48_bytes: int,
    max_length_128: int,
) -> None:
    manifest = json.loads(manifest_path.read_text(encoding="ascii"))
    zx48 = manifest["zx48"]
    zx128 = manifest["zx128"]

    available = source_count(words_path)
    if manifest.get("source_count") != available:
        raise SystemExit(
            f"manifest source count {manifest.get('source_count')} != {available}"
        )
    if expected_48 and zx48["words"] != expected_48:
        raise SystemExit(f"48K contains {zx48['words']} words, expected {expected_48}")
    if expected_128 and zx128["words"] != expected_128:
        raise SystemExit(
            f"128K contains {zx128['words']} words, expected {expected_128}"
        )
    eligible = manifest.get("eligible_words", {})
    for release, data in (("zx48", zx48), ("zx128", zx128)):
        available_release = int(eligible.get(release, -1))
        if available_release < int(data["words"]):
            raise SystemExit(f"{release}: selected more words than are eligible")
        if int(data.get("dropped_words", -1)) != available_release - int(
            data["words"]
        ):
            raise SystemExit(f"{release}: incorrect dropped-word count")
    if zx48["bytes"] > max_48_bytes or not zx48.get("fits"):
        raise SystemExit(
            f"48K dictionary uses {zx48['bytes']} / {max_48_bytes} bytes"
        )

    banks = zx128.get("banks", [])
    if len(banks) != 5:
        raise SystemExit(f"128K contains {len(banks)} dictionary banks, expected 5")
    for bank in banks:
        if bank["bytes"] > 16_384:
            raise SystemExit(
                f"128K bank {bank['physical_bank']} uses {bank['bytes']} / 16384 bytes"
            )
    if sum(int(bank["words"]) for bank in banks) != int(zx128["words"]):
        raise SystemExit("128K bank word counts do not add up")
    if not zx128.get("fits"):
        raise SystemExit("128K dictionary manifest reports an overflow")

    if zx48.get("allowed_lengths") != [5]:
        raise SystemExit("48K must allow only five-letter words")
    expected_lengths_128 = list(range(5, max_length_128 + 1))
    if zx128.get("allowed_lengths") != expected_lengths_128:
        raise SystemExit(
            f"128K must allow only lengths {expected_lengths_128}"
        )
    check_modes(zx48["lengths"], (5,), "48K")
    check_modes(zx128["lengths"], tuple(expected_lengths_128), "128K")
    print(
        f"PASS {manifest.get('language', '?')}: "
        f"48K {zx48['words']} words/{zx48['bytes']} bytes; "
        f"128K {zx128['words']} words/{zx128['bytes']} bytes in 5 banks"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--words", type=Path, required=True)
    parser.add_argument("--expected-48", type=int, required=True)
    parser.add_argument("--expected-128", type=int, required=True)
    parser.add_argument("--max-48-bytes", type=int, required=True)
    parser.add_argument("--max-length-128", type=int, choices=(5, 6), required=True)
    args = parser.parse_args()
    check(
        args.manifest,
        args.words,
        args.expected_48,
        args.expected_128,
        args.max_48_bytes,
        args.max_length_128,
    )


if __name__ == "__main__":
    main()
