#!/usr/bin/env python3
"""Measure experimental front-coded dictionaries with native letter glyphs."""

from __future__ import annotations

import argparse
import json
import math
import struct
from collections import Counter
from pathlib import Path

import build_dictionary
from build_accented_wordlist import native_spelling
from normalize_words import unaccent_ascii

BLOCK_SIZE = 16


def load_native_words(path: Path, lengths: tuple[int, ...] = (5,)) -> list[str]:
    words: list[str] = []
    seen: set[str] = set()
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw or raw.startswith("#"):
            continue
        word = native_spelling(raw)
        key = unaccent_ascii(word)
        if len(key) not in lengths:
            continue
        if not key.isascii() or not key.isalpha():
            raise ValueError(f"not a native word: {word!r} -> {key!r}")
        if word in seen:
            raise ValueError(f"duplicate native spelling: {word!r}")
        seen.add(word)
        words.append(word)
    return words


def pack_symbols(symbols: str, alphabet: dict[str, int], bits_per_symbol: int) -> bytes:
    result = bytearray()
    accumulator = 0
    bits = 0
    for symbol in symbols:
        accumulator = (accumulator << bits_per_symbol) | alphabet[symbol]
        bits += bits_per_symbol
        while bits >= 8:
            bits -= 8
            result.append((accumulator >> bits) & 0xFF)
            accumulator &= (1 << bits) - 1
    if bits:
        result.append((accumulator << (8 - bits)) & 0xFF)
    return bytes(result)


def encode(words: list[str]) -> tuple[bytes, str, int]:
    alphabet_text = "".join(sorted(set("".join(words))))
    bits_per_symbol = max(1, math.ceil(math.log2(len(alphabet_text))))
    alphabet = {symbol: index for index, symbol in enumerate(alphabet_text)}
    ordered = sorted(words, key=lambda word: (unaccent_ascii(word), word))
    block_count = (len(ordered) + BLOCK_SIZE - 1) // BLOCK_SIZE
    header_size = 4 + 2 * block_count
    records = bytearray()
    offsets: list[int] = []
    previous = ""

    for index, word in enumerate(ordered):
        if index % BLOCK_SIZE == 0:
            previous = ""
            offsets.append(header_size + len(records))
        prefix = 0
        while (
            prefix < len(previous)
            and prefix < len(word)
            and previous[prefix] == word[prefix]
        ):
            prefix += 1
        suffix = word[prefix:]
        if prefix > 15 or not 1 <= len(suffix) <= 15:
            raise AssertionError((previous, word, prefix, suffix))
        records.append((prefix << 4) | len(suffix))
        records.extend(pack_symbols(suffix, alphabet, bits_per_symbol))
        previous = word

    result = bytearray(struct.pack("<HH", len(ordered), block_count))
    result.extend(struct.pack(f"<{block_count}H", *offsets))
    result.extend(records)
    blob = bytes(result)
    decoded = [
        decode(blob, index, alphabet_text, bits_per_symbol)
        for index in range(len(ordered))
    ]
    if decoded != ordered:
        raise AssertionError("experimental dictionary round trip failed")
    return blob, alphabet_text, bits_per_symbol


def unpack_symbols(
    data: bytes,
    position: int,
    length: int,
    alphabet: str,
    bits_per_symbol: int,
) -> tuple[str, int]:
    symbols: list[str] = []
    accumulator = 0
    bits = 0
    mask = (1 << bits_per_symbol) - 1
    for _ in range(length):
        while bits < bits_per_symbol:
            accumulator = (accumulator << 8) | data[position]
            position += 1
            bits += 8
        bits -= bits_per_symbol
        value = (accumulator >> bits) & mask
        accumulator &= (1 << bits) - 1 if bits else 0
        symbols.append(alphabet[value])
    return "".join(symbols), position


def decode(
    blob: bytes,
    index: int,
    alphabet: str,
    bits_per_symbol: int,
) -> str:
    count, block_count = struct.unpack_from("<HH", blob)
    if not 0 <= index < count:
        raise IndexError(index)
    block, within = divmod(index, BLOCK_SIZE)
    if block >= block_count:
        raise AssertionError(block)
    position = struct.unpack_from("<H", blob, 4 + 2 * block)[0]
    word = ""
    for _ in range(within + 1):
        header = blob[position]
        position += 1
        prefix, suffix_length = header >> 4, header & 15
        suffix, position = unpack_symbols(
            blob,
            position,
            suffix_length,
            alphabet,
            bits_per_symbol,
        )
        word = word[:prefix] + suffix
    return word


def pack_escape_symbols(
    symbols: str,
    direct: dict[str, int],
    escaped: dict[str, int],
    escape_bits: int,
) -> bytes:
    result = bytearray()
    accumulator = 0
    bits = 0

    def append(value: int, width: int) -> None:
        nonlocal accumulator, bits
        accumulator = (accumulator << width) | value
        bits += width
        while bits >= 8:
            bits -= 8
            result.append((accumulator >> bits) & 0xFF)
            accumulator &= (1 << bits) - 1

    for symbol in symbols:
        if symbol in direct:
            append(direct[symbol], 5)
        else:
            append(31, 5)
            append(escaped[symbol], escape_bits)
    if bits:
        result.append((accumulator << (8 - bits)) & 0xFF)
    return bytes(result)


def encode_escape(words: list[str]) -> tuple[bytes, str, str, int]:
    """Use 31 frequent five-bit symbols and escape the uncommon remainder."""
    frequencies = Counter("".join(words))
    alphabet = sorted(frequencies)
    if len(alphabet) <= 32:
        blob, alphabet_text, _ = encode(words)
        return blob, alphabet_text, "", 0

    ranked = sorted(alphabet, key=lambda symbol: (-frequencies[symbol], symbol))
    direct_text = "".join(ranked[:31])
    escaped_text = "".join(ranked[31:])
    direct = {symbol: index for index, symbol in enumerate(direct_text)}
    escaped = {symbol: index for index, symbol in enumerate(escaped_text)}
    escape_bits = max(1, math.ceil(math.log2(len(escaped_text))))
    ordered = sorted(words, key=lambda word: (unaccent_ascii(word), word))
    block_count = (len(ordered) + BLOCK_SIZE - 1) // BLOCK_SIZE
    header_size = 4 + 2 * block_count
    records = bytearray()
    offsets: list[int] = []
    previous = ""

    for index, word in enumerate(ordered):
        if index % BLOCK_SIZE == 0:
            previous = ""
            offsets.append(header_size + len(records))
        prefix = 0
        while (
            prefix < len(previous)
            and prefix < len(word)
            and previous[prefix] == word[prefix]
        ):
            prefix += 1
        suffix = word[prefix:]
        records.append((prefix << 4) | len(suffix))
        records.extend(pack_escape_symbols(suffix, direct, escaped, escape_bits))
        previous = word

    result = bytearray(struct.pack("<HH", len(ordered), block_count))
    result.extend(struct.pack(f"<{block_count}H", *offsets))
    result.extend(records)
    blob = bytes(result)
    decoded = [
        decode_escape(
            blob,
            index,
            direct_text,
            escaped_text,
            escape_bits,
        )
        for index in range(len(ordered))
    ]
    if decoded != ordered:
        raise AssertionError("escape dictionary round trip failed")
    return blob, direct_text, escaped_text, escape_bits


def unpack_escape_symbols(
    data: bytes,
    position: int,
    length: int,
    direct: str,
    escaped: str,
    escape_bits: int,
) -> tuple[str, int]:
    symbols: list[str] = []
    accumulator = 0
    bits = 0

    def read(width: int) -> int:
        nonlocal accumulator, bits, position
        while bits < width:
            accumulator = (accumulator << 8) | data[position]
            position += 1
            bits += 8
        bits -= width
        value = (accumulator >> bits) & ((1 << width) - 1)
        accumulator &= (1 << bits) - 1 if bits else 0
        return value

    for _ in range(length):
        value = read(5)
        if value < 31:
            symbols.append(direct[value])
        else:
            symbols.append(escaped[read(escape_bits)])
    return "".join(symbols), position


def decode_escape(
    blob: bytes,
    index: int,
    direct: str,
    escaped: str,
    escape_bits: int,
) -> str:
    count, block_count = struct.unpack_from("<HH", blob)
    if not 0 <= index < count:
        raise IndexError(index)
    block, within = divmod(index, BLOCK_SIZE)
    if block >= block_count:
        raise AssertionError(block)
    position = struct.unpack_from("<H", blob, 4 + 2 * block)[0]
    word = ""
    for _ in range(within + 1):
        header = blob[position]
        position += 1
        prefix, suffix_length = header >> 4, header & 15
        suffix, position = unpack_escape_symbols(
            blob,
            position,
            suffix_length,
            direct,
            escaped,
            escape_bits,
        )
        word = word[:prefix] + suffix
    return word


def measure(language: str, native_path: Path, ascii_path: Path) -> dict[str, object]:
    words = load_native_words(native_path)
    fixed_blob, alphabet, bits_per_symbol = encode(words)
    blob, direct_symbols, escaped_symbols, escape_bits = encode_escape(words)
    ascii_words = [
        word
        for word in build_dictionary.load_words(ascii_path, required=1)
        if len(word) == 5
    ]
    ascii_blob = build_dictionary.encode(ascii_words)
    keys = {unaccent_ascii(word) for word in words}
    ascii_keys = set(ascii_words)
    accented_characters = [character for character in alphabet if ord(character) > 127]
    decode_map_bytes = 0 if not accented_characters else len(alphabet)
    fold_map_bytes = 0 if not accented_characters else len(alphabet)
    glyph_bytes = 8 * len(accented_characters)
    support_bytes = decode_map_bytes + fold_map_bytes + glyph_bytes

    return {
        "language": language,
        "words": len(words),
        "accentless_keys": len(keys),
        "additional_spellings": len(words) - len(keys),
        "omitted_ascii_keys": sorted(ascii_keys - keys),
        "words_with_non_ascii": sum(
            any(ord(character) > 127 for character in word) for word in words
        ),
        "alphabet": alphabet,
        "alphabet_symbols": len(alphabet),
        "bits_per_symbol": bits_per_symbol,
        "selected_encoding": (
            "fixed-width"
            if not escaped_symbols
            else "5-bit frequent symbols plus escape"
        ),
        "escape_encoding": {
            "direct_symbols": direct_symbols,
            "escaped_symbols": escaped_symbols,
            "extra_bits_after_escape": escape_bits,
        },
        "utf8_file_bytes": native_path.stat().st_size,
        "fixed_width_dictionary_bytes": len(fixed_blob),
        "dictionary_bytes": len(blob),
        "bytes_per_word": round(len(blob) / len(words), 3),
        "ascii_words": len(ascii_words),
        "ascii_dictionary_bytes": len(ascii_blob),
        "dictionary_delta_bytes": len(blob) - len(ascii_blob),
        "dictionary_delta_percent": round(
            100 * (len(blob) - len(ascii_blob)) / len(ascii_blob), 1
        ),
        "fixed_width_delta_bytes": len(fixed_blob) - len(ascii_blob),
        "fixed_width_delta_percent": round(
            100 * (len(fixed_blob) - len(ascii_blob)) / len(ascii_blob), 1
        ),
        "support_estimate": {
            "decode_map_bytes": decode_map_bytes,
            "fold_map_bytes": fold_map_bytes,
            "new_glyphs": len(accented_characters),
            "font_bytes_at_8_per_glyph": glyph_bytes,
            "total_bytes": support_bytes,
        },
        "dictionary_plus_support_bytes": len(blob) + support_bytes,
        "total_delta_vs_ascii_bytes": len(blob) + support_bytes - len(ascii_blob),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dictionary",
        action="append",
        nargs=3,
        metavar=("LANGUAGE", "NATIVE_WORDS", "ASCII_WORDS"),
        required=True,
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    report = {
        "format": "experimental Unicode FC5/16",
        "notes": [
            "Words are ordered by accentless key, then native spelling.",
            "The fixed-width measurement uses the minimum width for each language alphabet.",
            "The selected measurement keeps the 31 most frequent symbols at five bits and escapes uncommon symbols when the alphabet exceeds 32.",
            "Support estimate includes decode and folding bytes per symbol plus one 8-byte bitmap per non-ASCII glyph.",
            "Decoder/rendering code changes are not included.",
        ],
        "languages": [
            measure(language, Path(native), Path(ascii_words))
            for language, native, ascii_words in args.dictionary
        ],
    }
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
