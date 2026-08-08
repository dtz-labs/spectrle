#!/usr/bin/env python3
"""Build the front-coded dictionaries embedded in the Spectrum releases."""

from __future__ import annotations

import argparse
import json
import math
import struct
import unicodedata
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from build_accented_wordlist import native_spelling
from normalize_words import unaccent_ascii

BLOCK_SIZE = 16
PHYSICAL_BANKS = (0, 1, 3, 4, 6)
ZX48_LENGTHS = (5,)

# Uppercase A-Z from the original 8x8 ZX Spectrum ROM font.  Accented glyphs
# are generated from these shapes, keeping the game visually native to the
# machine without shipping a second complete alphabet.
ZX_UPPERCASE = {
    "a": (0x00, 0x3C, 0x42, 0x42, 0x7E, 0x42, 0x42, 0x00),
    "b": (0x00, 0x7C, 0x42, 0x7C, 0x42, 0x42, 0x7C, 0x00),
    "c": (0x00, 0x3C, 0x42, 0x40, 0x40, 0x42, 0x3C, 0x00),
    "d": (0x00, 0x78, 0x44, 0x42, 0x42, 0x44, 0x78, 0x00),
    "e": (0x00, 0x7E, 0x40, 0x7C, 0x40, 0x40, 0x7E, 0x00),
    "f": (0x00, 0x7E, 0x40, 0x7C, 0x40, 0x40, 0x40, 0x00),
    "g": (0x00, 0x3C, 0x42, 0x40, 0x4E, 0x42, 0x3C, 0x00),
    "h": (0x00, 0x42, 0x42, 0x7E, 0x42, 0x42, 0x42, 0x00),
    "i": (0x00, 0x3E, 0x08, 0x08, 0x08, 0x08, 0x3E, 0x00),
    "j": (0x00, 0x02, 0x02, 0x02, 0x42, 0x42, 0x3C, 0x00),
    "k": (0x00, 0x44, 0x48, 0x70, 0x48, 0x44, 0x42, 0x00),
    "l": (0x00, 0x40, 0x40, 0x40, 0x40, 0x40, 0x7E, 0x00),
    "m": (0x00, 0x42, 0x66, 0x5A, 0x42, 0x42, 0x42, 0x00),
    "n": (0x00, 0x42, 0x62, 0x52, 0x4A, 0x46, 0x42, 0x00),
    "o": (0x00, 0x3C, 0x42, 0x42, 0x42, 0x42, 0x3C, 0x00),
    "p": (0x00, 0x7C, 0x42, 0x42, 0x7C, 0x40, 0x40, 0x00),
    "q": (0x00, 0x3C, 0x42, 0x42, 0x52, 0x4A, 0x3C, 0x00),
    "r": (0x00, 0x7C, 0x42, 0x42, 0x7C, 0x44, 0x42, 0x00),
    "s": (0x00, 0x3C, 0x40, 0x3C, 0x02, 0x42, 0x3C, 0x00),
    "t": (0x00, 0xFE, 0x10, 0x10, 0x10, 0x10, 0x10, 0x00),
    "u": (0x00, 0x42, 0x42, 0x42, 0x42, 0x42, 0x3C, 0x00),
    "v": (0x00, 0x42, 0x42, 0x42, 0x42, 0x24, 0x18, 0x00),
    "w": (0x00, 0x42, 0x42, 0x42, 0x42, 0x5A, 0x24, 0x00),
    "x": (0x00, 0x42, 0x24, 0x18, 0x18, 0x24, 0x42, 0x00),
    "y": (0x00, 0x82, 0x44, 0x28, 0x10, 0x10, 0x10, 0x00),
    "z": (0x00, 0x7E, 0x04, 0x08, 0x10, 0x20, 0x7E, 0x00),
}

TOP_MARKS = {
    "ACUTE ACCENT": (0x0C, 0x18),
    "GRAVE ACCENT": (0x30, 0x18),
    "CIRCUMFLEX ACCENT": (0x18, 0x24),
    "CARON": (0x24, 0x18),
    "BREVE": (0x24, 0x18),
    "DIAERESIS": (0x24, 0x00),
    "TILDE": (0x32, 0x4C),
    "MACRON": (0x3C, 0x00),
    "DOT ABOVE": (0x18, 0x00),
    "RING ABOVE": (0x18, 0x24),
}


@dataclass(frozen=True)
class NativeWord:
    text: str
    key: str
    symbols: bytes
    rank: int


@dataclass(frozen=True)
class NativeEncoding:
    characters: tuple[str, ...]
    symbol_ids: dict[str, int]
    folds: tuple[int, ...]
    direct: tuple[int, ...]
    escaped: tuple[int, ...]
    packed_codes: dict[int, tuple[int, int | None]]
    escape_bits: int


def load_words(path: Path, required: int = 20_000) -> list[str]:
    words: list[str] = []
    seen: set[str] = set()

    for raw in path.read_text(encoding="ascii").splitlines():
        word = raw.strip()
        if not word or word.startswith("#"):
            continue
        if not (3 <= len(word) <= 15):
            raise ValueError(f"word outside 3..15 characters: {word!r}")
        if not word.isascii() or not word.isalpha() or not word.islower():
            raise ValueError(f"word is not lowercase ASCII: {word!r}")
        if word in seen:
            raise ValueError(f"duplicate word: {word!r}")
        seen.add(word)
        words.append(word)

    if len(words) < required:
        raise ValueError(f"need at least {required} words, got {len(words)}")
    return words


def pack_letters(letters: str) -> bytes:
    result = bytearray()
    accumulator = 0
    bits = 0

    for letter in letters:
        accumulator = (accumulator << 5) | (ord(letter) - ord("a") + 1)
        bits += 5
        while bits >= 8:
            bits -= 8
            result.append((accumulator >> bits) & 0xFF)
            accumulator &= (1 << bits) - 1
    if bits:
        result.append((accumulator << (8 - bits)) & 0xFF)
    return bytes(result)


def encode(words: list[str]) -> bytes:
    ordered = sorted(words)
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
        records.extend(pack_letters(suffix))
        previous = word

    result = bytearray(struct.pack("<HH", len(ordered), block_count))
    result.extend(struct.pack(f"<{block_count}H", *offsets))
    result.extend(records)
    return bytes(result)


def unpack_letters(data: bytes, position: int, length: int) -> tuple[str, int]:
    letters: list[str] = []
    accumulator = 0
    bits = 0

    for _ in range(length):
        while bits < 5:
            accumulator = (accumulator << 8) | data[position]
            position += 1
            bits += 8
        bits -= 5
        value = (accumulator >> bits) & 31
        accumulator = accumulator & ((1 << bits) - 1) if bits else 0
        letters.append(chr(ord("a") + value - 1))
    return "".join(letters), position


def decode(blob: bytes, index: int) -> str:
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
        suffix, position = unpack_letters(blob, position, suffix_length)
        word = word[:prefix] + suffix
    return word


def verify(blob: bytes, expected: list[str]) -> None:
    ordered = sorted(expected)
    decoded = [decode(blob, index) for index in range(len(ordered))]
    if decoded != ordered:
        for index, (actual, wanted) in enumerate(zip(decoded, ordered)):
            if actual != wanted:
                raise AssertionError(
                    f"dictionary mismatch at {index}: {actual!r} != {wanted!r}"
                )
        raise AssertionError("dictionary has a mismatched length")


def storage_spelling(word: str) -> str:
    """Collapse Catalan L middle-dot L to five/six drawable letter cells."""
    return word.replace("l\N{MIDDLE DOT}l", "\N{LATIN SMALL LETTER L WITH MIDDLE DOT}l")


def load_native_source(path: Path) -> list[tuple[str, str]]:
    words: list[tuple[str, str]] = []
    seen: set[str] = set()
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw or raw.startswith("#"):
            continue
        word = native_spelling(raw)
        key = unaccent_ascii(word)
        if len(key) not in (5, 6) or not key.isascii() or not key.isalpha():
            raise ValueError(f"invalid native word: {word!r} -> {key!r}")
        stored = storage_spelling(word)
        if len(stored) != len(key):
            raise ValueError(f"native word does not fit letter cells: {word!r}")
        if word in seen:
            raise ValueError(f"duplicate native spelling: {word!r}")
        seen.add(word)
        words.append((word, stored))
    return words


def base_letter(character: str) -> str:
    folded = unaccent_ascii(character)
    if len(folded) != 1 or folded < "a" or folded > "z":
        raise ValueError(f"cannot fold dictionary symbol {character!r}: {folded!r}")
    return folded


def build_native_encoding(source: list[tuple[str, str]]) -> NativeEncoding:
    extras = sorted(
        {
            character
            for _, stored in source
            for character in stored
            if ord(character) > 127
        }
    )
    characters = tuple(chr(ord("a") + index) for index in range(26)) + tuple(extras)
    if len(characters) > 63:
        raise ValueError(
            f"native alphabet has {len(characters)} symbols; maximum is 63"
        )
    symbol_ids = {character: index + 1 for index, character in enumerate(characters)}
    folds = (0,) + tuple(
        ord(base_letter(character)) - ord("a") + 1 for character in characters
    )

    frequencies = Counter(character for _, stored in source for character in stored)
    used = sorted(
        frequencies, key=lambda character: (-frequencies[character], character)
    )
    if len(used) <= 32:
        direct_characters = used
        escaped_characters: list[str] = []
        escape_bits = 0
    else:
        direct_characters = used[:31]
        escaped_characters = used[31:]
        escape_bits = max(1, math.ceil(math.log2(len(escaped_characters))))

    direct = tuple(symbol_ids[character] for character in direct_characters)
    escaped = tuple(symbol_ids[character] for character in escaped_characters)
    packed_codes: dict[int, tuple[int, int | None]] = {
        symbol_ids[character]: (index, None)
        for index, character in enumerate(direct_characters)
    }
    for index, character in enumerate(escaped_characters):
        packed_codes[symbol_ids[character]] = (31, index)
    return NativeEncoding(
        characters=characters,
        symbol_ids=symbol_ids,
        folds=folds,
        direct=direct,
        escaped=escaped,
        packed_codes=packed_codes,
        escape_bits=escape_bits,
    )


def native_words(
    source: list[tuple[str, str]], encoding: NativeEncoding
) -> list[NativeWord]:
    return [
        NativeWord(
            text=word,
            key=unaccent_ascii(word),
            symbols=bytes(encoding.symbol_ids[character] for character in stored),
            rank=rank,
        )
        for rank, (word, stored) in enumerate(source)
    ]


def native_sort_key(word: NativeWord, encoding: NativeEncoding) -> tuple[bytes, int]:
    folded = bytes(encoding.folds[symbol] for symbol in word.symbols)
    # Variants sharing one accentless keyboard key remain adjacent.  Their
    # source-frequency rank makes the first entry the canonical UI spelling.
    return folded, word.rank


def pack_native_symbols(symbols: bytes, encoding: NativeEncoding) -> bytes:
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
        code, escaped = encoding.packed_codes[symbol]
        append(code, 5)
        if escaped is not None:
            append(escaped, encoding.escape_bits)
    if bits:
        result.append((accumulator << (8 - bits)) & 0xFF)
    return bytes(result)


def encode_native(words: list[NativeWord], encoding: NativeEncoding) -> bytes:
    ordered = sorted(words, key=lambda word: native_sort_key(word, encoding))
    block_count = (len(ordered) + BLOCK_SIZE - 1) // BLOCK_SIZE
    header_size = 4 + 2 * block_count
    records = bytearray()
    offsets: list[int] = []
    previous = b""

    for index, word in enumerate(ordered):
        if index % BLOCK_SIZE == 0:
            previous = b""
            offsets.append(header_size + len(records))
        prefix = 0
        while (
            prefix < len(previous)
            and prefix < len(word.symbols)
            and previous[prefix] == word.symbols[prefix]
        ):
            prefix += 1
        suffix = word.symbols[prefix:]
        if prefix > 15 or not 1 <= len(suffix) <= 15:
            raise AssertionError((previous, word.text, prefix, suffix))
        records.append((prefix << 4) | len(suffix))
        records.extend(pack_native_symbols(suffix, encoding))
        previous = word.symbols

    result = bytearray(struct.pack("<HH", len(ordered), block_count))
    result.extend(struct.pack(f"<{block_count}H", *offsets))
    result.extend(records)
    return bytes(result)


def read_native_symbol(
    data: bytes,
    position: int,
    accumulator: int,
    bits: int,
    encoding: NativeEncoding,
) -> tuple[int, int, int, int]:
    def read(width: int) -> int:
        nonlocal position, accumulator, bits
        while bits < width:
            accumulator = (accumulator << 8) | data[position]
            position += 1
            bits += 8
        bits -= width
        value = (accumulator >> bits) & ((1 << width) - 1)
        accumulator &= (1 << bits) - 1 if bits else 0
        return value

    code = read(5)
    if encoding.escape_bits and code == 31:
        symbol = encoding.escaped[read(encoding.escape_bits)]
    else:
        symbol = encoding.direct[code]
    return symbol, position, accumulator, bits


def decode_native(blob: bytes, index: int, encoding: NativeEncoding) -> bytes:
    count, block_count = struct.unpack_from("<HH", blob)
    if not 0 <= index < count:
        raise IndexError(index)
    block, within = divmod(index, BLOCK_SIZE)
    if block >= block_count:
        raise AssertionError(block)
    position = struct.unpack_from("<H", blob, 4 + 2 * block)[0]
    word = b""
    for _ in range(within + 1):
        header = blob[position]
        position += 1
        prefix, suffix_length = header >> 4, header & 15
        suffix = bytearray()
        accumulator = 0
        bits = 0
        for _ in range(suffix_length):
            symbol, position, accumulator, bits = read_native_symbol(
                blob, position, accumulator, bits, encoding
            )
            suffix.append(symbol)
        word = word[:prefix] + bytes(suffix)
    return word


def verify_native(
    blob: bytes, expected: list[NativeWord], encoding: NativeEncoding
) -> None:
    ordered = sorted(expected, key=lambda word: native_sort_key(word, encoding))
    decoded = [decode_native(blob, index, encoding) for index in range(len(ordered))]
    wanted = [word.symbols for word in ordered]
    if decoded != wanted:
        raise AssertionError("native dictionary round trip failed")


def length_counts(words: list[str]) -> dict[str, int]:
    counts = Counter(map(len, words))
    return {str(length): counts[length] for length in range(3, 16)}


def native_length_counts(words: list[NativeWord]) -> dict[str, int]:
    counts = Counter(len(word.key) for word in words)
    return {str(length): counts[length] for length in range(3, 16)}


def custom_glyph(character: str) -> tuple[int, ...]:
    base = base_letter(character)
    glyph = list(ZX_UPPERCASE[base])
    decomposition = unicodedata.normalize("NFD", character)
    marks = [
        unicodedata.name(mark, "")
        for mark in decomposition[1:]
        if unicodedata.category(mark).startswith("M")
    ]
    top_rows = [0, 0]
    has_top = False
    has_bottom = False
    for mark in marks:
        matched = False
        for name, rows in TOP_MARKS.items():
            if name in mark:
                top_rows[0] |= rows[0]
                top_rows[1] |= rows[1]
                has_top = True
                matched = True
                break
        if matched:
            continue
        if any(name in mark for name in ("OGONEK", "CEDILLA", "BELOW")):
            has_bottom = True
            continue
        raise ValueError(f"no ZX glyph recipe for {character!r}: {mark}")

    if has_top:
        glyph = top_rows + glyph[1:7]
    if has_bottom:
        if any("OGONEK" in mark for mark in marks):
            glyph[7] |= 0x0C
        elif any("DOT BELOW" in mark for mark in marks):
            glyph[7] |= 0x18
        else:
            glyph[7] |= 0x18

    if character == "\N{LATIN SMALL LETTER L WITH STROKE}":
        glyph[3] |= 0x08
        glyph[4] |= 0x10
        glyph[5] |= 0x20
    elif character == "\N{LATIN SMALL LETTER L WITH MIDDLE DOT}":
        glyph[3] |= 0x04
        glyph[4] |= 0x04
    return tuple(glyph)


def c_initializer(values: tuple[int, ...] | list[int]) -> str:
    if not values:
        return "{0u}"
    return "{" + ", ".join(f"{value}u" for value in values) + "}"


def write_header(
    path: Path,
    sizes: dict[str, int],
    words_48_count: int,
    words_128_count: int,
    bank_word_counts: list[int],
    max_length_128: int,
    encoding: NativeEncoding,
) -> None:
    bank_macros = "\n".join(
        f"#define DICTIONARY_128_BANK{physical}_WORDS {count}u"
        for physical, count in zip(PHYSICAL_BANKS, bank_word_counts, strict=True)
    )
    custom_characters = encoding.characters[26:]
    custom_glyphs = tuple(
        byte for character in custom_characters for byte in custom_glyph(character)
    )
    text = f"""/* Generated by tools/build_dictionary.py. */
#ifndef SPECTRLE_DICTIONARY_META_H
#define SPECTRLE_DICTIONARY_META_H

#define DICTIONARY_BLOCK_SIZE {BLOCK_SIZE}u
#define DICTIONARY_48_WORDS {words_48_count}u
#define DICTIONARY_48_BYTES {sizes['48']}u
#define DICTIONARY_128_WORDS {words_128_count}u
#define DICTIONARY_128_BANKS {len(PHYSICAL_BANKS)}u
#define DICTIONARY_128_MAX_LENGTH {max_length_128}u
#define DICTIONARY_ALPHABET_SIZE {len(encoding.characters)}u
#define DICTIONARY_DIRECT_COUNT {len(encoding.direct)}u
#define DICTIONARY_ESCAPED_COUNT {len(encoding.escaped)}u
#define DICTIONARY_ESCAPE_BITS {encoding.escape_bits}u
#define DICTIONARY_CUSTOM_GLYPHS_COUNT {len(custom_characters)}u
#define DICTIONARY_FOLD_SYMBOLS {c_initializer(encoding.folds)}
#define DICTIONARY_DIRECT_SYMBOLS {c_initializer(encoding.direct)}
#define DICTIONARY_ESCAPED_SYMBOLS {c_initializer(encoding.escaped)}
#define DICTIONARY_CUSTOM_GLYPHS {c_initializer(custom_glyphs)}
{bank_macros}

#endif
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="ascii")


def write_assembly(asm48: Path, asm128: Path, build_dir: Path) -> None:
    # Actions prepares these files on the host and compiles them in a Docker
    # checkout mounted at /src. Preserve relative paths so the generated
    # assembly remains valid on both sides of that mount boundary.
    dictionary48 = (build_dir / "dict48.bin").as_posix()
    asm48.parent.mkdir(parents=True, exist_ok=True)
    asm48.write_text(
        "SECTION RODATA\n\n"
        "PUBLIC _dictionary_blob\n\n"
        "_dictionary_blob:\n"
        f'    BINARY "{dictionary48}"\n',
        encoding="ascii",
    )

    bank_lines: list[str] = []
    for physical in PHYSICAL_BANKS:
        dictionary = (build_dir / f"dict128-bank{physical}.bin").as_posix()
        bank_lines.extend(
            (
                f"SECTION RODATA_{physical}",
                f"PUBLIC _dictionary_bank{physical}",
                f"_dictionary_bank{physical}:",
                f'    BINARY "{dictionary}"',
                "",
            )
        )
    asm128.parent.mkdir(parents=True, exist_ok=True)
    asm128.write_text("\n".join(bank_lines), encoding="ascii")


def split_banks(
    words: list[NativeWord], encoding: NativeEncoding
) -> list[tuple[list[NativeWord], bytes]]:
    ordered = sorted(words, key=lambda word: native_sort_key(word, encoding))
    bank_base, bank_extra = divmod(len(ordered), len(PHYSICAL_BANKS))
    result: list[tuple[list[NativeWord], bytes]] = []
    start = 0
    for logical in range(len(PHYSICAL_BANKS)):
        count = bank_base + (1 if logical < bank_extra else 0)
        bank_words = ordered[start : start + count]
        start += count
        result.append((bank_words, encode_native(bank_words, encoding)))
    return result


def maximum_prefix(limit: int, fits) -> int:
    low = 1
    high = limit
    best = 0
    while low <= high:
        middle = (low + high) // 2
        if fits(middle):
            best = middle
            low = middle + 1
        else:
            high = middle - 1
    return best


def build(
    words_path: Path,
    build_dir: Path,
    header_path: Path,
    *,
    language: str = "pl",
    words_48_count: int | None = None,
    words_128_count: int | None = None,
    max_length_128: int = 6,
    max_48_bytes: int = 20_000,
    asm48: Path | None = None,
    asm128: Path | None = None,
) -> dict[str, object]:
    if max_length_128 not in (5, 6):
        raise ValueError("128K maximum word length must be 5 or 6")
    zx128_lengths = tuple(range(5, max_length_128 + 1))
    source = load_native_source(words_path)
    encoding = build_native_encoding(source)
    all_words = native_words(source, encoding)
    eligible48 = [word for word in all_words if len(word.key) in ZX48_LENGTHS]
    eligible128 = [word for word in all_words if len(word.key) in zx128_lengths]

    if words_48_count is None:
        words_48_count = maximum_prefix(
            len(eligible48),
            lambda count: len(encode_native(eligible48[:count], encoding))
            <= max_48_bytes,
        )
    if words_128_count is None:
        words_128_count = maximum_prefix(
            len(eligible128),
            lambda count: all(
                len(blob) <= 16_384
                for _, blob in split_banks(eligible128[:count], encoding)
            ),
        )
    if not 0 < words_48_count <= len(eligible48):
        raise ValueError(
            f"need {words_48_count} five-letter 48K words, got {len(eligible48)}"
        )
    if not 0 < words_128_count <= len(eligible128):
        raise ValueError(
            f"need {words_128_count} eligible 128K words through "
            f"length {max_length_128}, got {len(eligible128)}"
        )

    words48 = eligible48[:words_48_count]
    words128 = eligible128[:words_128_count]
    if not all(
        any(len(word.key) == length for word in words128) for length in zx128_lengths
    ):
        raise ValueError("frequency trimming removed an enabled 128K word length")
    build_dir.mkdir(parents=True, exist_ok=True)

    blob48 = encode_native(words48, encoding)
    verify_native(blob48, words48, encoding)
    (build_dir / "dict48.bin").write_bytes(blob48)

    bank_manifest: list[dict[str, object]] = []
    bank_word_counts: list[int] = []
    sizes = {"48": len(blob48)}
    bank_data = split_banks(words128, encoding)
    for logical, (physical, (bank_words, blob)) in enumerate(
        zip(PHYSICAL_BANKS, bank_data, strict=True)
    ):
        verify_native(blob, bank_words, encoding)
        if len(blob) > 16_384:
            raise ValueError(f"dictionary bank {physical} is too large: {len(blob)}")
        output = build_dir / f"dict128-bank{physical}.bin"
        output.write_bytes(blob)
        sizes[f"bank{physical}"] = len(blob)
        bank_word_counts.append(len(bank_words))
        bank_manifest.append(
            {
                "logical_bank": logical,
                "physical_bank": physical,
                "words": len(bank_words),
                "bytes": len(blob),
                "first": bank_words[0].text,
                "last": bank_words[-1].text,
            }
        )

    if len(blob48) > max_48_bytes:
        raise ValueError(
            f"48K dictionary exceeds its {max_48_bytes}-byte budget: {len(blob48)}"
        )

    write_header(
        header_path,
        sizes,
        words_48_count,
        words_128_count,
        bank_word_counts,
        max_length_128,
        encoding,
    )
    if (asm48 is None) != (asm128 is None):
        raise ValueError("both asm48 and asm128 must be provided together")
    if asm48 is not None and asm128 is not None:
        write_assembly(asm48, asm128, build_dir)

    manifest: dict[str, object] = {
        "format": "FC5E/16",
        "description": "native-symbol front coding; 5-bit frequent symbols plus escape",
        "language": language,
        "source_words": str(words_path),
        "source_count": len(all_words),
        "alphabet": {
            "symbols": len(encoding.characters),
            "custom_glyphs": len(encoding.characters) - 26,
            "direct_symbols": len(encoding.direct),
            "escaped_symbols": len(encoding.escaped),
            "escape_bits": encoding.escape_bits,
        },
        "eligible_words": {
            "zx48": len(eligible48),
            "zx128": len(eligible128),
        },
        "limits": {
            "zx48_max_bytes": max_48_bytes,
            "zx128_bank_max_bytes": 16_384,
        },
        "zx48": {
            "allowed_lengths": list(ZX48_LENGTHS),
            "words": words_48_count,
            "dropped_words": len(eligible48) - words_48_count,
            "bytes": len(blob48),
            "fits": len(blob48) <= max_48_bytes,
            "bytes_per_word": round(len(blob48) / words_48_count, 3),
            "lengths": native_length_counts(words48),
        },
        "zx128": {
            "allowed_lengths": list(zx128_lengths),
            "words": words_128_count,
            "dropped_words": len(eligible128) - words_128_count,
            "bytes": sum(int(bank["bytes"]) for bank in bank_manifest),
            "bytes_per_word": round(
                sum(int(bank["bytes"]) for bank in bank_manifest) / words_128_count,
                3,
            ),
            "fits": all(int(bank["bytes"]) <= 16_384 for bank in bank_manifest),
            "lengths": native_length_counts(words128),
            "banks": bank_manifest,
        },
    }
    (build_dir / "dictionary-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=True, indent=2) + "\n", encoding="ascii"
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--words", type=Path, required=True)
    parser.add_argument("--build-dir", type=Path, required=True)
    parser.add_argument("--header", type=Path, required=True)
    parser.add_argument("--language", default="pl")
    parser.add_argument("--words-48", type=int, default=0)
    parser.add_argument("--words-128", type=int, default=0)
    parser.add_argument("--max-length-128", type=int, choices=(5, 6), default=6)
    parser.add_argument("--max-48-bytes", type=int, default=20_000)
    parser.add_argument("--asm48", type=Path)
    parser.add_argument("--asm128", type=Path)
    args = parser.parse_args()

    manifest = build(
        args.words,
        args.build_dir,
        args.header,
        language=args.language,
        words_48_count=args.words_48 or None,
        words_128_count=args.words_128 or None,
        max_length_128=args.max_length_128,
        max_48_bytes=args.max_48_bytes,
        asm48=args.asm48,
        asm128=args.asm128,
    )
    print(f"48K: {manifest['zx48']['words']} words / {manifest['zx48']['bytes']} bytes")
    print(
        f"128K: {manifest['zx128']['words']} words / "
        f"{manifest['zx128']['bytes']} bytes in {len(PHYSICAL_BANKS)} banks"
    )


if __name__ == "__main__":
    main()
