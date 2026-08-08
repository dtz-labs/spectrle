from __future__ import annotations

import json
import sys
import tempfile
import unittest
import unicodedata
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import build_accented_wordlist  # noqa: E402
import build_dictionary  # noqa: E402
import measure_accented_dictionaries  # noqa: E402


class AccentedWordlistTests(unittest.TestCase):
    def test_committed_lists_match_the_memory_report(self) -> None:
        report = json.loads(
            (ROOT / "data" / "accented-5letter-sizes.json").read_text(encoding="utf-8")
        )
        for expected in report["languages"]:
            language = expected["language"]
            native_path = ROOT / "data" / f"words-{language}-utf8.txt"
            ascii_path = ROOT / "data" / f"words-{language}-ascii.txt"
            with self.subTest(language=language):
                words = measure_accented_dictionaries.load_native_words(native_path)
                self.assertTrue(
                    all(word == unicodedata.normalize("NFC", word) for word in words)
                )
                self.assertEqual(
                    measure_accented_dictionaries.measure(
                        language, native_path, ascii_path
                    ),
                    expected,
                )

    def test_native_words_use_accentless_five_letter_keys(self) -> None:
        examples = {
            "żądać": "zadac",
            "niños": "ninos",
            "škoda": "skoda",
            "al\N{MIDDLE DOT}lot": "allot",
        }
        for word, key in examples.items():
            with self.subTest(word=word):
                self.assertTrue(
                    build_accented_wordlist.is_native_word(
                        word, "ca" if "\N{MIDDLE DOT}" in word else "pl", key
                    )
                )

    def test_polish_selection_requires_exact_playable_spelling(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            temp_path = Path(temp)
            sjp_zip = temp_path / "sjp.zip"
            games_zip = temp_path / "games.zip"
            with zipfile.ZipFile(sjp_zip, "w") as archive:
                archive.writestr(
                    "odm.txt", "banka, banki\nbańka, bańki\ngądek, gądka\n"
                )
            with zipfile.ZipFile(games_zip, "w") as archive:
                archive.writestr("slowa.txt", "banka\nbańka\ngadek\n")

            words, missing = build_accented_wordlist.polish_words(
                sjp_zip, games_zip, {"banka", "gadek"}
            )
            self.assertEqual(words, ["banka", "bańka"])
            self.assertEqual(missing, {"gadek"})

    def test_unicode_front_coding_uses_language_alphabet_width(self) -> None:
        words = ["banka", "bańka", "canon", "cañón", "škoda"]
        blob, alphabet, bits = measure_accented_dictionaries.encode(words)
        self.assertTrue(blob)
        self.assertIn("ń", alphabet)
        self.assertIn("ñ", alphabet)
        self.assertIn("š", alphabet)
        self.assertEqual(bits, (len(alphabet) - 1).bit_length())
        ordered = sorted(
            words,
            key=lambda word: (
                measure_accented_dictionaries.unaccent_ascii(word),
                word,
            ),
        )
        self.assertEqual(
            [
                measure_accented_dictionaries.decode(blob, index, alphabet, bits)
                for index in range(len(words))
            ],
            ordered,
        )

    def test_escape_encoding_round_trip_for_large_alphabet(self) -> None:
        symbols = "abcdefghijklmnopqrstuvwxyzáéíóúñčďěňřšťž"
        words = [symbol + "aaaa" for symbol in symbols]
        blob, direct, escaped, escape_bits = (
            measure_accented_dictionaries.encode_escape(words)
        )
        self.assertEqual(len(direct), 31)
        self.assertGreater(len(escaped), 1)
        ordered = sorted(
            words,
            key=lambda word: (
                measure_accented_dictionaries.unaccent_ascii(word),
                word,
            ),
        )
        self.assertEqual(
            [
                measure_accented_dictionaries.decode_escape(
                    blob, index, direct, escaped, escape_bits
                )
                for index in range(len(words))
            ],
            ordered,
        )

    def test_each_language_embeds_only_its_national_glyphs(self) -> None:
        expected = {
            "pl": "óąćęłńśźż",
            "en": "",
            "es": "áéíñóúü",
            "ca": "àáçèéíïòóúüŀ",
            "lt": "ąčėęįšūųž",
            "sk": "áäéíóôúýčďĺľňŕšťž",
            "cs": "áéíóöúüýčďěňřšťůž",
            "pt": "àáâãçèéêíóôõöúüāăńōūṇ",
        }
        for language, characters in expected.items():
            with self.subTest(language=language):
                source = build_dictionary.load_native_source(
                    ROOT / "data" / f"words-{language}-utf8.txt"
                )
                encoding = build_dictionary.build_native_encoding(source)
                self.assertEqual("".join(encoding.characters[26:]), characters)
                for character in characters:
                    glyph = build_dictionary.custom_glyph(character)
                    base = build_dictionary.base_letter(character)
                    self.assertEqual(len(glyph), 8)
                    self.assertNotEqual(glyph, build_dictionary.ZX_UPPERCASE[base])
                    symbol = encoding.symbol_ids[character]
                    self.assertEqual(
                        encoding.folds[symbol], ord(base) - ord("a") + 1
                    )


if __name__ == "__main__":
    unittest.main()
