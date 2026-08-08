#!/usr/bin/env python3
"""Fail the build if either release crosses its Spectrum memory window."""

from __future__ import annotations

import argparse
import glob
import re
from pathlib import Path


def map_symbol(path: Path, name: str) -> int | None:
    pattern = re.compile(rf"^{re.escape(name)}\s*=\s*\$([0-9A-Fa-f]+)\b")
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = pattern.match(line)
        if match:
            return int(match.group(1), 16)
    return None


def tape_blocks(path: Path) -> list[int]:
    """Length of every block in a .tap file.

    z88dk-appmake writes the 128K dictionary banks as extra tape blocks. It
    derives their names from the binary and drops them without a word when it
    cannot match them, so the tape has to be counted rather than trusted.
    """
    data = path.read_bytes()
    lengths: list[int] = []
    offset = 0
    while offset + 2 <= len(data):
        length = data[offset] | (data[offset + 1] << 8)
        offset += 2 + length
        if offset > len(data):
            raise SystemExit(f"{path.name} ends inside a tape block")
        lengths.append(length)
    if offset != len(data):
        raise SystemExit(f"{path.name} has {len(data) - offset} trailing bytes")
    return lengths


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--map48", type=Path, required=True)
    parser.add_argument("--bin48", type=Path, required=True)
    parser.add_argument("--map128", type=Path, required=True)
    parser.add_argument("--bin128", type=Path, required=True)
    parser.add_argument("--bank-glob", required=True)
    parser.add_argument("--tap128", type=Path, required=True)
    args = parser.parse_args()

    size48 = args.bin48.stat().st_size
    size128 = args.bin128.stat().st_size
    if size48 > 0x8000:
        raise SystemExit(f"48K image crosses 0xffff: {size48} bytes from 0x8000")
    if size128 > 0x4000:
        raise SystemExit(f"128K fixed image crosses 0xbfff: {size128} bytes from 0x8000")

    banks = sorted(Path(path) for path in glob.glob(args.bank_glob))
    expected = {0, 1, 3, 4, 6}
    found: set[int] = set()
    for bank in banks:
        match = re.search(r"_BANK_(\d+)\.bin$", bank.name)
        if not match:
            continue
        number = int(match.group(1))
        if number in expected:
            found.add(number)
            size = bank.stat().st_size
            if size > 0x4000:
                raise SystemExit(f"bank {number} exceeds 16K: {size} bytes")
    if found != expected:
        raise SystemExit(f"missing dictionary banks: {sorted(expected - found)}")

    tap_blocks = tape_blocks(args.tap128)
    # loader header+data, code header+data, then one block per dictionary bank.
    wanted = 4 + len(expected)
    if len(tap_blocks) != wanted:
        raise SystemExit(
            f"{args.tap128.name} holds {len(tap_blocks)} tape blocks, expected "
            f"{wanted}; the dictionary banks are missing from the tape"
        )

    end48 = map_symbol(args.map48, "__BSS_END_tail")
    end128 = map_symbol(args.map128, "__BSS_END_tail")
    if end48 is not None and 0x10000 - end48 < 2048:
        raise SystemExit(
            f"48K leaves only {0x10000 - end48} bytes above BSS for the stack"
        )
    print(
        f"48K main image: {size48} bytes"
        + (
            f", BSS ends ${end48:04x}, stack headroom {0x10000 - end48} bytes"
            if end48 is not None
            else ""
        )
    )
    print(f"128K fixed image: {size128} bytes" + (f", BSS ends ${end128:04x}" if end128 else ""))
    print("128K dictionary banks: " + ", ".join(str(number) for number in sorted(found)))
    print(f"128K tape: {len(tap_blocks)} blocks, {args.tap128.stat().st_size} bytes")


if __name__ == "__main__":
    main()
