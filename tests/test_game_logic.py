from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class GameLogicTests(unittest.TestCase):
    def test_c_game_state_and_wordle_scoring(self) -> None:
        for release_define in (None, "ZX48"):
            with self.subTest(release=release_define or "128K"), tempfile.TemporaryDirectory() as temp:
                executable = Path(temp) / "game-harness"
                command = [
                    "cc",
                    "-std=c99",
                    "-Wall",
                    "-Wextra",
                    "-Werror",
                    f"-I{ROOT / 'src'}",
                ]
                if release_define is not None:
                    command.append(f"-D{release_define}")
                command.extend(
                    [
                        str(ROOT / "src" / "game.c"),
                        str(ROOT / "tests" / "game_harness.c"),
                        "-o",
                        str(executable),
                    ]
                )
                subprocess.run(command, check=True)
                subprocess.run([str(executable)], check=True)


if __name__ == "__main__":
    unittest.main()
