#!/usr/bin/env python3
"""One-way importer from the project's old JSON locales to gettext PO."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from build_locale import load_messages


def po_quote(text: str) -> str:
    return json.dumps(text, ensure_ascii=False)


def convert(messages_path: Path, json_path: Path, po_path: Path) -> None:
    messages = load_messages(messages_path)
    locale = json.loads(json_path.read_text(encoding="utf-8"))
    code = locale["code"]
    strings = locale["strings"]
    if strings.keys() != messages.keys():
        raise ValueError(f"{json_path} and {messages_path} have different message keys")

    lines = [
        "# Translation catalog for ZX Spectrum Wordle.",
        "msgid \"\"",
        "msgstr \"\"",
        '"Project-Id-Version: zx-spectrum-wordle 1.0\\n"',
        '"Report-Msgid-Bugs-To: \\n"',
        '"POT-Creation-Date: 2026-08-07 00:00+0200\\n"',
        '"PO-Revision-Date: 2026-08-07 00:00+0200\\n"',
        '"Last-Translator: Michal Pasternak\\n"',
        f'"Language-Team: {code}\\n"',
        f'"Language: {code}\\n"',
        '"MIME-Version: 1.0\\n"',
        '"Content-Type: text/plain; charset=UTF-8\\n"',
        '"Content-Transfer-Encoding: 8bit\\n"',
        "",
    ]
    for context, message in messages.items():
        lines.extend(
            (
                f"msgctxt {po_quote(context)}",
                f"msgid {po_quote(message)}",
                f"msgstr {po_quote(strings[context])}",
                "",
            )
        )
    po_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--messages", type=Path, required=True)
    parser.add_argument("--json", type=Path, required=True)
    parser.add_argument("--po", type=Path, required=True)
    args = parser.parse_args()
    convert(args.messages, args.json, args.po)


if __name__ == "__main__":
    main()
