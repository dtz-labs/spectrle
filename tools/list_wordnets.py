#!/usr/bin/env python3
"""Validate and print the actionable Latin-script WordNet catalog."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def load_catalog(path: Path) -> dict[str, object]:
    catalog = json.loads(path.read_text(encoding="utf-8"))
    languages = catalog.get("languages")
    if not isinstance(languages, list) or not languages:
        raise ValueError("catalog must contain a non-empty languages list")

    codes: set[str] = set()
    for language in languages:
        if not isinstance(language, dict):
            raise ValueError("each language must be an object")
        code = language.get("code")
        if not isinstance(code, str) or not re.fullmatch(r"[a-z]{2,3}", code):
            raise ValueError(f"invalid language code: {code!r}")
        if code in codes:
            raise ValueError(f"duplicate language code: {code}")
        codes.add(code)
        for key in ("name", "wordnet", "package", "region"):
            if not isinstance(language.get(key), str) or not language[key]:
                raise ValueError(f"{code}: missing {key}")

    review_languages = catalog.get("review_languages", [])
    if not isinstance(review_languages, list):
        raise ValueError("review_languages must be a list")
    for language in review_languages:
        if not isinstance(language, dict):
            raise ValueError("each review language must be an object")
        code = language.get("code")
        if not isinstance(code, str) or not re.fullmatch(r"[a-z]{2,3}", code):
            raise ValueError(f"invalid review language code: {code!r}")
        if code in codes:
            raise ValueError(f"duplicate language code across catalog: {code}")
        codes.add(code)
        for key in ("name", "wordnet"):
            if not isinstance(language.get(key), str) or not language[key]:
                raise ValueError(f"{code}: missing {key}")
    return catalog


def print_catalog(catalog: dict[str, object]) -> None:
    languages = catalog["languages"]
    assert isinstance(languages, list)
    for region in ("Europe", "Other"):
        selected = [item for item in languages if item["region"] == region]
        print(f"{region} ({len(selected)}):")
        for item in selected:
            status = f" [{item['build']}]" if item.get("build") else ""
            print(
                f"  {item['code']:>3}  {item['name']:<20} "
                f"{item['package']:<15} {item['wordnet']}{status}"
            )
    review = catalog.get("review_languages", [])
    assert isinstance(review, list)
    print(f"Source/licence review ({len(review)}; WordNet exists, not automated yet):")
    for item in review:
        print(f"  {item['code']:>3}  {item['name']:<20} {item['wordnet']}")
    print(
        f"Total: {len(languages)} automated candidates + "
        f"{len(review)} awaiting source review"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("catalog", type=Path)
    args = parser.parse_args()
    print_catalog(load_catalog(args.catalog))


if __name__ == "__main__":
    main()
