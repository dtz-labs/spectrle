from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import build_dictionary  # noqa: E402
import list_wordnets  # noqa: E402


class DictionaryTests(unittest.TestCase):
    def test_latin_wordnet_catalog(self) -> None:
        catalog = list_wordnets.load_catalog(ROOT / "languages" / "wordnets.json")
        languages = catalog["languages"]
        self.assertEqual(len(languages), 26)
        self.assertEqual(len(catalog["review_languages"]), 8)
        self.assertEqual(
            [item["code"] for item in languages if item.get("build")],
            ["ca", "cs", "en", "lt", "pl", "pt", "sk", "es"],
        )

    def test_small_round_trip_and_prefix_reset(self) -> None:
        words = [
            "dom",
            "domek",
            "domowy",
            "drabina",
            "ekran",
            "gra",
            "komputer",
            "monitor",
            "program",
            "slowo",
            "spektrum",
            "spectrle",
            "zabawa",
            "zagadka",
            "zamek",
            "zegar",
            "zeszyt",
        ]
        blob = build_dictionary.encode(words)
        build_dictionary.verify(blob, words)
        self.assertLess(len(blob), sum(map(len, words)))

    def test_generated_assembly_keeps_relative_binary_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            temp_path = Path(temp)
            previous = Path.cwd()
            try:
                os.chdir(temp_path)
                build_dictionary.write_assembly(
                    Path("build/pl/generated/dictionary_blob.asm"),
                    Path("build/pl/generated/dictionary_banks.asm"),
                    Path("build/pl"),
                )
            finally:
                os.chdir(previous)

            generated = temp_path / "build" / "pl" / "generated"
            assembly48 = (generated / "dictionary_blob.asm").read_text()
            assembly128 = (generated / "dictionary_banks.asm").read_text()
            self.assertIn('BINARY "build/pl/dict48.bin"', assembly48)
            self.assertIn('BINARY "build/pl/dict128-bank0.bin"', assembly128)
            self.assertNotIn(temp_path.as_posix(), assembly48 + assembly128)

    def test_release_dictionary_build(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            temp_path = Path(temp)
            words_path = ROOT / "data" / "words-pl-utf8.txt"
            manifest = build_dictionary.build(
                words_path,
                temp_path,
                temp_path / "dictionary_meta.h",
                language="pl",
                max_48_bytes=22_000,
                asm48=temp_path / "generated" / "dictionary_blob.asm",
                asm128=temp_path / "generated" / "dictionary_banks.asm",
            )
            self.assertEqual(manifest["zx48"]["words"], 6_448)
            self.assertEqual(manifest["zx128"]["words"], 17_276)
            self.assertLess(manifest["zx48"]["bytes"], 22_000)
            self.assertEqual(len(manifest["zx128"]["banks"]), 5)
            self.assertEqual(manifest["zx48"]["allowed_lengths"], [5])
            self.assertEqual(manifest["zx128"]["allowed_lengths"], [5, 6])
            self.assertEqual(manifest["zx48"]["lengths"]["5"], 6_448)
            self.assertEqual(manifest["zx128"]["lengths"]["5"], 6_448)
            self.assertEqual(manifest["zx128"]["lengths"]["6"], 10_828)
            self.assertEqual(manifest["zx128"]["lengths"]["7"], 0)
            self.assertEqual(
                sum(bank["words"] for bank in manifest["zx128"]["banks"]),
                17_276,
            )
            self.assertTrue(
                all(bank["bytes"] <= 16_384 for bank in manifest["zx128"]["banks"])
            )

            blob48 = (temp_path / "dict48.bin").read_bytes()
            source = build_dictionary.load_native_source(words_path)
            encoding = build_dictionary.build_native_encoding(source)
            native_words = build_dictionary.native_words(source, encoding)
            selected48 = [word for word in native_words if len(word.key) == 5]
            ordered48 = sorted(
                selected48,
                key=lambda word: build_dictionary.native_sort_key(word, encoding),
            )
            decoded48 = [
                build_dictionary.decode_native(blob48, index, encoding)
                for index in range(manifest["zx48"]["words"])
            ]
            self.assertEqual(decoded48, [word.symbols for word in ordered48])
            words48 = {word.text for word in selected48}
            for ordinary_word in ("banał", "larwa", "sitwa"):
                self.assertIn(ordinary_word, words48)
            # SJP.PL lists these as headwords but bars them from word games.
            for barred_word in ("codak", "afaik", "ampex"):
                self.assertNotIn(barred_word, words48)
            self.assertEqual({len(word.key) for word in selected48}, {5})

            loaded = json.loads((temp_path / "dictionary-manifest.json").read_text())
            self.assertEqual(loaded["format"], "FC5E/16")
            self.assertEqual(loaded["language"], "pl")
            self.assertEqual(loaded["source_count"], 17_276)
            self.assertEqual(loaded["alphabet"]["custom_glyphs"], 9)
            self.assertEqual(loaded["zx48"]["dropped_words"], 0)
            self.assertEqual(loaded["zx128"]["dropped_words"], 0)
            self.assertTrue(loaded["zx48"]["fits"])
            self.assertTrue(loaded["zx128"]["fits"])
            self.assertIn(
                "_dictionary_blob",
                (temp_path / "generated" / "dictionary_blob.asm").read_text(),
            )

            five_only = build_dictionary.build(
                words_path,
                temp_path / "five-only",
                temp_path / "five-only" / "dictionary_meta.h",
                language="pl",
                max_length_128=5,
                max_48_bytes=22_000,
            )
            self.assertEqual(five_only["zx128"]["words"], 6_448)
            self.assertEqual(five_only["zx128"]["allowed_lengths"], [5])

            trimmed = build_dictionary.build(
                words_path,
                temp_path / "trimmed",
                temp_path / "trimmed" / "dictionary_meta.h",
                language="pl",
                max_length_128=5,
                max_48_bytes=10_000,
            )
            kept = trimmed["zx48"]["words"]
            self.assertGreater(kept, 0)
            self.assertLess(kept, len(selected48))
            self.assertLessEqual(trimmed["zx48"]["bytes"], 10_000)
            self.assertEqual(
                trimmed["zx48"]["dropped_words"], len(selected48) - kept
            )
            trimmed_blob = (temp_path / "trimmed" / "dict48.bin").read_bytes()
            ranked_prefix = selected48[:kept]
            ordered_prefix = sorted(
                ranked_prefix,
                key=lambda word: build_dictionary.native_sort_key(word, encoding),
            )
            self.assertEqual(
                [
                    build_dictionary.decode_native(trimmed_blob, index, encoding)
                    for index in range(kept)
                ],
                [word.symbols for word in ordered_prefix],
            )

    def test_rejects_impossible_language_configuration(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            temp_path = Path(temp)
            with self.assertRaisesRegex(ValueError, "five-letter 48K words"):
                build_dictionary.build(
                    ROOT / "data" / "words-pl-utf8.txt",
                    temp_path,
                    temp_path / "dictionary_meta.h",
                    words_48_count=6_449,
                    max_48_bytes=22_000,
                )


if __name__ == "__main__":
    unittest.main()
