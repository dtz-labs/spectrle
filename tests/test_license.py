from __future__ import annotations

import ast
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LINE_RE = re.compile(r'LICENSE_LINE\(("(?:[^"\\]|\\.)*")\)')


class LicenseScreenTests(unittest.TestCase):
    def test_license_screen_is_not_linked_or_exposed_by_the_game(self) -> None:
        main = (ROOT / "src" / "main.c").read_text(encoding="utf-8")
        makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
        self.assertNotIn("license_show", main)
        self.assertNotIn("TXT_LICENSE_KEY", main)
        self.assertNotIn("src/license.c", makefile)

    def test_every_license_screen_line_fits(self) -> None:
        source = (ROOT / "src" / "license.c").read_text(encoding="utf-8")
        lines = [ast.literal_eval(value) for value in LINE_RE.findall(source)]
        self.assertEqual(len(lines), 96)
        self.assertTrue(all(len(line) <= 32 for line in lines))

    def test_screen_contains_original_and_zx_credits_and_full_terms(self) -> None:
        source = (ROOT / "src" / "license.c").read_text(encoding="utf-8")
        visible = " ".join(ast.literal_eval(value) for value in LINE_RE.findall(source))
        self.assertIn("SPECTRLE - BSD LICENSE", visible)
        for phrase in (
            "Copyright (c) 1983, 1993",
            "Written by Ken Arnold.",
            "Copyright (c) 2026 Michal Pasternak",
            "Redistribution and use in source and binary forms",
            "Neither the name of the University nor the names of its contributors",
            'REGENTS AND CONTRIBUTORS "AS IS"',
            "EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, visible)

        licence = (ROOT / "LICENSE").read_text(encoding="utf-8")
        self.assertIn("The Regents of the University of California", licence)
        self.assertIn("Michal Pasternak, ZX Spectrum version", licence)


if __name__ == "__main__":
    unittest.main()
