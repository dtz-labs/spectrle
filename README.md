# Spectrle for ZX Spectrum

An unofficial, ASCII-only word-guessing game for the ZX Spectrum, released as
independent 48K and 128K tapes in eight languages. The 48K tape is strictly a
5x5 game. The 128K tape offers two board sizes when the language data fits:

- `5x5`: five-letter word, five guesses;
- `6x6`: six-letter word, six guesses.

Play the current release in
[JSSpeccy](https://dtz-labs.github.io/spectrle/) or download an individual TAP
from [GitHub Releases](https://github.com/dtz-labs/spectrle/releases).

| code | edition | 48K: 5 letters | 128K: 5-6 letters |
| --- | --- | ---: | ---: |
| `pl` | Polish | 6,718 | 18,023 |
| `en` | English | 2,249 | 5,176 |
| `es` | Spanish | 1,612 | 3,939 |
| `ca` | Catalan | 2,076 | 4,844 |
| `lt` | Lithuanian | 484 | 1,316 |
| `sk` | Slovak | 1,578 | 3,604 |
| `cs` | Czech | 3,139 | 6,893 |
| `pt` | Portuguese | 2,102 | 4,751 |

The Polish edition is generated from the complete five- and six-letter
headword selection in SJP.PL: 6,718 five-letter and 11,305 six-letter entries.
The common entries `banal`, `larwa`, and `sitwa` are covered by regression
tests and are present in the 48K dictionary.

Every edition explicitly says that it has no accents and accepts only `A-Z`.
Diacritics and Latin ligatures are folded while dictionaries are imported, so
every accepted word can be entered on an unmodified Spectrum keyboard.

## Playing

On 48K, press `1` for the only 5x5 board. On 128K, choose `1` or `2` for the
5x5 or 6x6 board. Type a word with `A-Z`, erase with `CAPS SHIFT+0`, and press
`ENTER` to submit it. A guess must
have the selected length and exist in the edition's dictionary; rejected
guesses do not consume an attempt.

The score follows the classic duplicate-letter rules: exact matches are assigned
first, then remaining copies are marked as present only while unmatched copies
remain in the answer.

- `[A]` on green: correct letter and position;
- `(A)` on yellow: present in another position;
- ` A ` on blue: absent from the word.

The bracket shapes repeat every colour signal, so the board remains readable
without relying on colour alone. The on-screen alphabet keeps the strongest
known state for each letter. Accepted guesses, rejected guesses, wins, and
losses have distinct 1-bit beeper cues; every cue restores a black border.

After a round, `ENTER` keeps the selected board, `M` returns to the board menu,
and `Q` exits. The game has no licence screen or licence-menu shortcut.

## Build, run, and test

A sibling z88dk checkout is used by default. `make` builds all eight enabled
languages and both memory variants:

```sh
make
make list-languages
make test
make smoke-all
```

Override the compiler location with `Z88DK=/path/to/z88dk`. Select a language
when starting ZEsarUX; the default is Polish:

```sh
make RUN_LANGUAGE=en run-zx48
make RUN_LANGUAGE=en run-zx128
make RUN_LANGUAGE=es smoke
```

Local builds write tapes under the ignored `build/<code>/` directory. For example, English produces
`build/en/spectrle-en-48.tap` and `build/en/spectrle-en-128.tap`; Polish produces
`build/pl/spectrle-pl-48.tap` and `build/pl/spectrle-pl-128.tap`.

## GitHub releases and web player

CI compiles and validates all 16 language/machine combinations in the official
z88dk container. Pushing a `v*` tag runs `.github/workflows/release.yml`, which
creates a GitHub Release and attaches every `.tap` file directly, together with
`SHA256SUMS`. Generated files are not committed under `build/` or `dist/`.

After a successful release, `.github/workflows/pages.yml` downloads those TAP
assets and the pinned JSSpeccy 3 distribution, then deploys the player from
`site/` to GitHub Pages. The player’s language and machine selectors map to
release files named `spectrle-<language>-<48|128>.tap`.

The host tests cover duplicate-letter scoring, per-release mode restrictions,
dictionary validation, gettext catalogs, word-list normalization, and build
provenance. The ZEsarUX smoke test boots the real 48K and 128K tapes, selects
5x5 on 48K and 6x6 on 128K, rejects an incomplete guess without consuming an
attempt, solves the round, checks every green tile, proves that no tile is
drawn after the selected grid, and verifies sound state, partial redraws, the
border, and a 256x192 screenshot.

## Gettext translations

UI localization uses GNU gettext as a build-time format, without linking a
gettext runtime into the Spectrum program. Canonical English messages and
stable contexts are in [locales/messages.def](locales/messages.def). The
translator template is [locales/spectrle.pot](locales/spectrle.pot). Each
edition has a `locales/<code>.po` catalog.

```sh
make pot                 # extract a fresh .pot
make update-po           # merge it into every .po
make check-translations  # validate the catalogs
```

During each language build, Python compiles its `.po` into a small `locale.h`
containing only that edition's strings. The generator rejects missing entries,
non-ASCII output, lines wider than 32 characters, and stat labels that leave no
room for numbers. See
[languages/README.md](languages/README.md) for the complete language recipe.

## Dictionaries and memory layout

OMW tabs, plain UTF-8 word lists, and GWA WordNet-LMF XML can be normalized
with `tools/import_wordnet.py`. `tools/normalize_words.py` follows the same
rule-based idea as PostgreSQL `unaccent`, applies Unicode decomposition and
explicit Latin-letter expansions, and emits unique lowercase ASCII words.
`tools/build_dictionary.py` compiles them to the byte-packed `FC5/16` format.

```sh
make import-wordnet \
  IMPORT_LANGUAGE=en \
  WORDNET_FILES="/path/to/wordnet.xml.gz"
```

`FC5/16` sorts words into blocks of 16. The first word in each block is stored
in full; following words store four-bit common-prefix and suffix lengths.
Suffix letters use five bits each (`a=1` through `z=26`). The 128K dictionary
is split over physical banks 0, 1, 3, 4, and 6; game code and the decompressor
stay in fixed RAM. The builder selects all five-letter entries for 48K and all
enabled five- and six-letter entries for 128K. Every build proves that the 48K
image and all five 16K banks fit. See [data/README.md](data/README.md) for
provenance and separate word-data licences.

## Source licence and provenance

This project was converted from the BSD Hangman ZX Spectrum codebase. The
original BSD Hangman was written by Ken Arnold and carries the 1983/1993
Regents of the University of California BSD licence. The ZX Spectrum source is
copyright 2026 Michal Pasternak under the same BSD 3-Clause terms; see
[LICENSE](LICENSE). These terms are not displayed inside the game. Word data
has separate terms documented under `data/`;
distributed TAP files containing that data should be accompanied by the
applicable notices.
