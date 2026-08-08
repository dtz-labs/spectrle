#!/usr/bin/env python3
"""Compile a localized UI catalog into a Spectrum C header."""

from __future__ import annotations

import argparse
import ast
import gettext
import json
import re
import shutil
import subprocess
import tempfile
import unicodedata
from pathlib import Path

from build_dictionary import build_native_encoding, load_native_source

MESSAGE_RE = re.compile(
    r'^LOCALE_TEXT\("(?P<context>[a-z][a-z0-9_]*)",\s*'
    r'(?P<message>"(?:[^"\\]|\\.)*")\)\s*$'
)

REQUIRED = {
    "title_48",
    "title_128",
    "ascii_notice",
    "dictionary_prefix",
    "dictionary_suffix",
    "mode_5_line",
    "mode_6_line",
    "choose_5",
    "choose_5_6",
    "keyboard",
    "try_label",
    "wins_label",
    "type_word",
    "not_enough",
    "not_in_dictionary",
    "next_guess",
    "correct",
    "present",
    "absent",
    "won",
    "word_prefix",
    "next_prompt",
    "thanks",
    "any_key",
}


def load_messages(path: Path) -> dict[str, str]:
    messages: dict[str, str] = {}
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("/*") or line.startswith("*") or line.startswith("*/"):
            continue
        match = MESSAGE_RE.fullmatch(line)
        if match is None:
            raise ValueError(f"invalid message definition at {path}:{line_number}: {line}")
        context = match.group("context")
        if context in messages:
            raise ValueError(f"duplicate gettext context {context!r} in {path}")
        messages[context] = ast.literal_eval(match.group("message"))

    missing = REQUIRED - messages.keys()
    extra = messages.keys() - REQUIRED
    if missing or extra:
        raise ValueError(f"message keys: missing={sorted(missing)}, extra={sorted(extra)}")
    return messages


def load_catalog(po_path: Path) -> gettext.GNUTranslations:
    msgfmt = shutil.which("msgfmt")
    if msgfmt is None:
        raise RuntimeError("GNU msgfmt is required to compile gettext catalogs")
    with tempfile.TemporaryDirectory() as temp:
        mo_path = Path(temp) / "messages.mo"
        subprocess.run(
            [msgfmt, "--check", "--check-format", "-o", str(mo_path), str(po_path)],
            check=True,
        )
        with mo_path.open("rb") as stream:
            return gettext.GNUTranslations(stream)


def encode_string(text: str, custom_symbols: dict[str, int]) -> bytes:
    encoded = bytearray()
    for character in text:
        if 32 <= ord(character) <= 126:
            encoded.append(ord(character))
            continue
        folded = unicodedata.normalize("NFC", character.casefold())
        if len(folded) != 1 or folded not in custom_symbols:
            raise ValueError(f"no dictionary glyph for UI character {character!r}")
        encoded.append(0x80 + custom_symbols[folded])
    return bytes(encoded)


def validate_strings(
    strings: dict[str, str], custom_symbols: dict[str, int]
) -> dict[str, bytes]:
    encoded: dict[str, bytes] = {}
    for key, text in strings.items():
        if any(ord(char) < 32 or ord(char) == 127 for char in text):
            raise ValueError(f"{key} contains a control character: {text!r}")
        if len(text) > 32:
            raise ValueError(f"{key} exceeds the Spectrum row: {len(text)} characters")
        encoded[key] = encode_string(text, custom_symbols)
    if "A-Z" not in strings["ascii_notice"]:
        raise ValueError("ascii_notice must explain the A-Z input")
    for key in ("try_label", "wins_label"):
        if len(strings[key]) > 10:
            raise ValueError(f"{key} leaves no room for its five-digit value")
    return encoded


def c_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=True)


def c_byte_string(value: bytes) -> str:
    result = ['"']
    for byte in value:
        if byte == ord('"'):
            result.append(r'\"')
        elif byte == ord("\\"):
            result.append(r"\\")
        elif 32 <= byte <= 126:
            result.append(chr(byte))
        else:
            result.append(f"\\{byte:03o}")
    result.append('"')
    return "".join(result)


def build(
    messages_path: Path,
    po_path: Path,
    code: str,
    name: str,
    words_path: Path,
    header: Path,
    manifest: Path,
) -> None:
    if re.fullmatch(r"[a-z]{2,3}", code) is None:
        raise ValueError(f"invalid locale code: {code!r}")
    messages = load_messages(messages_path)
    catalog = load_catalog(po_path)
    raw_catalog = catalog._catalog  # GNUTranslations exposes compiled msgctxt keys here.

    strings: dict[str, str] = {}
    for context, message in messages.items():
        catalog_key = f"{context}\x04{message}"
        if catalog_key not in raw_catalog:
            raise ValueError(f"{po_path} has no translation for context {context!r}")
        translated = catalog.pgettext(context, message)
        if not isinstance(translated, str) or not translated:
            raise ValueError(f"{po_path} has an empty translation for context {context!r}")
        strings[context] = translated

    active_contexts = {
        key.split("\x04", 1)[0]
        for key in raw_catalog
        if isinstance(key, str) and "\x04" in key
    }
    extra = active_contexts - messages.keys()
    if extra:
        raise ValueError(f"{po_path} has obsolete active contexts: {sorted(extra)}")
    dictionary_encoding = build_native_encoding(load_native_source(words_path))
    custom_symbols = {
        character: index
        for index, character in enumerate(dictionary_encoding.characters[26:])
    }
    encoded_strings = validate_strings(strings, custom_symbols)

    locale = {"code": code, "name": name, "strings": strings}
    lines = [
        "/* Generated by tools/build_locale.py from a gettext PO catalog. */",
        "#ifndef SPECTRLE_LOCALE_H",
        "#define SPECTRLE_LOCALE_H",
        "",
        f"#define LOCALE_CODE {c_string(code)}",
        f"#define LOCALE_NAME {c_string(name)}",
    ]
    for key in sorted(strings):
        lines.append(
            f"#define TXT_{key.upper()} {c_byte_string(encoded_strings[key])}"
        )
    lines.extend(("", "#endif", ""))

    header.parent.mkdir(parents=True, exist_ok=True)
    manifest.parent.mkdir(parents=True, exist_ok=True)
    header.write_text("\n".join(lines), encoding="ascii")
    manifest.write_text(
        json.dumps(locale, ensure_ascii=True, indent=2) + "\n", encoding="ascii"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--messages", type=Path, required=True)
    parser.add_argument("--po", type=Path, required=True)
    parser.add_argument("--code", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--words", type=Path, required=True)
    parser.add_argument("--header", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    build(
        args.messages,
        args.po,
        args.code,
        args.name,
        args.words,
        args.header,
        args.manifest,
    )
    print(f"locale {args.po} -> {args.header}")


if __name__ == "__main__":
    main()
