# Spectrle for ZX Spectrum

An unofficial word-guessing game for the ZX Spectrum, released as independent
48K and 128K tapes in eight languages. Answers retain their native accents,
while the unmodified Spectrum keyboard still uses `A-Z`. The 48K tape is
strictly a 5x5 game. The 128K tape offers two board sizes:

- `5x5`: five-letter word, five guesses;
- `6x6`: six-letter word, six guesses.

Play the current release in
[JSSpeccy](https://dtz-labs.github.io/spectrle/) or download an individual TAP
from [GitHub Releases](https://github.com/dtz-labs/spectrle/releases).

| code | edition | 48K: 5 letters | 128K: 5-6 letters |
| --- | --- | ---: | ---: |
| `pl` | Polish | 6,448 | 17,276 |
| `en` | English | 2,249 | 5,176 |
| `es` | Spanish | 1,624 | 3,968 |
| `ca` | Catalan | 2,117 | 4,920 |
| `lt` | Lithuanian | 485 | 1,320 |
| `sk` | Slovak | 1,602 | 3,638 |
| `cs` | Czech | 3,360 | 7,291 |
| `pt` | Portuguese | 2,225 | 5,048 |

The Polish edition is generated from every five- and six-letter SJP.PL headword
that SJP.PL also admits in word games: 6,448 five-letter and 10,828 six-letter
entries. Headwords flagged `niedopuszczalne w grach` — abbreviations, brand
names and the like — are excluded. The common entries `banał`, `larwa`, and
`sitwa` are covered by regression tests and are present in the 48K dictionary.

Each edition embeds only the accented glyphs used by its own dictionary. They
are generated in the original ZX Spectrum 8x8 style; plain `A-Z` continue to
come directly from the ROM. Input is accent-insensitive: pressing `A` matches
both `A` and `Ą` in Polish, `S` matches `S`, `Ś`, or Czech `Š`, and the same
rule applies to each language. A correct tile reveals the answer's native
glyph. See [data/README.md](data/README.md#native-spelling-and-fonts).

## Playing

On 48K, press `1` for the only 5x5 board. On 128K, choose `1` or `2` for the
5x5 or 6x6 board. Type a word with `A-Z` (without entering accents), erase with
`CAPS SHIFT+0`, and press `ENTER` to submit it. An accepted guess is then
rewritten in its most frequent native spelling, for example `BEZEN` becomes
`BEZEŃ`. A guess must
have the selected length and exist in the edition's dictionary; rejected
guesses do not consume an attempt.

The score follows the classic duplicate-letter rules: exact matches are assigned
first, then remaining copies are marked as present only while unmatched copies
remain in the answer.

- `[A]` on green: correct letter and position;
- `(A)` on yellow: present in another position;
- ` A ` on blue: absent from the word.

The bracket shapes repeat every colour signal, so the board remains readable
without relying on colour alone. The on-screen alphabet includes every national
glyph beside its base family (`A Ą`, `N Ń`, `S Ś/Š`). Once a family is tried,
each glyph separately reports whether that exact form occurs in the answer.
Thus `ORKAN` against `GĄSKA` marks both `A` and `Ą` as present; against the
fictional `GĄSKĄ`, it marks `Ą` as present and `A` as absent. If an accentless
key matches an accented answer glyph in the correct position, the accented
glyph receives the correct-position state.
Accepted guesses, rejected guesses, wins, and
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

Local builds write tapes under the ignored `build/<code>/` directory. Every tape
name carries the version from [VERSION](VERSION), so a downloaded file names its
own build. With `VERSION` at `1.3.0`, English produces
`build/en/spectrle-en-48-v1.3.0.tap` and `build/en/spectrle-en-128-v1.3.0.tap`.

## GitHub releases and web player

CI compiles and validates all 16 language/machine combinations in the official
z88dk container. Pushing a `v*` tag runs `.github/workflows/release.yml`, which
creates a GitHub Release and attaches every `.tap` file directly, together with
`SHA256SUMS`. Generated files are not committed under `build/` or `dist/`.

After a successful release, `.github/workflows/pages.yml` downloads those TAP
assets and the pinned JSSpeccy 3 distribution, then deploys the player from
`site/` to GitHub Pages. The player’s language and machine selectors map to
release files named `spectrle-<language>-<48|128>-v<version>.tap`, and the
player reads the tag from `release.json` to build that name. The release
workflow refuses to publish a tag that does not match `VERSION`, so bump that
file in the same commit you tag.

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
containing only that edition's strings. National characters are encoded with
the same generated 8x8 glyphs as dictionary answers. The generator rejects
missing glyphs, lines wider than 32 characters, and stat labels that leave no
room for numbers. See
[languages/README.md](languages/README.md) for the complete language recipe.

## Dictionaries and memory layout

OMW tabs, plain UTF-8 word lists, and GWA WordNet-LMF XML can be normalized
with `tools/import_wordnet.py`. `tools/build_accented_wordlist.py` restores and
ranks the native spellings used by the release. `tools/normalize_words.py`
provides the accentless input keys. `tools/build_dictionary.py` compiles the
result to the byte-packed `FC5E/16` format.

```sh
make import-wordnet \
  IMPORT_LANGUAGE=en \
  WORDNET_FILES="/path/to/wordnet.xml.gz"
```

`FC5E/16` sorts words into blocks of 16. The first word in each block is stored
in full; following words store four-bit common-prefix and suffix lengths.
The 31 most frequent symbols use five bits; rarer national letters use an
escape code. The 128K dictionary is split over physical banks 0, 1, 3, 4, and
6; game code and the decompressor stay in fixed RAM. The builder selects all
five-letter entries for 48K and all enabled five- and six-letter entries for
128K. If a future list exceeds a memory limit, its frequency-ranked tail is
trimmed automatically. Every build proves that the 48K image and all five 16K
banks fit. See [data/README.md](data/README.md) for provenance and separate
word-data licences.
