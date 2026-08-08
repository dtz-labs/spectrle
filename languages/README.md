# Adding a language edition

Eight editions are currently enabled: `pl en es ca lt sk cs pt`. A new
Latin-script edition needs a gettext catalog, a ranked UTF-8 dictionary, and
one Make configuration.

## 1. Translate the interface

The English source messages live in `locales/messages.def`. If the game gains
or changes UI text, extract and merge the catalogs with:

```sh
make pot
make update-po
```

Create `locales/<code>.po` from the inherited `locales/spectrle.pot` template
and translate every context. The filename is retained for compatibility; its
package metadata and messages belong to Spectrle. Translations may use national
letters available in that edition's UTF-8 dictionary and must fit a 32-character
Spectrum row. `ascii_notice` must explain that `A-Z` input also reveals the
edition's accented letters.

Gettext is used only on the build host. `tools/build_locale.py` maps national
letters to the dictionary's generated 8x8 glyphs and compiles the selected
`.po` into a C header, so no gettext library or multi-language string table
occupies Spectrum RAM.

## 2. Prepare the dictionary

Create `data/words-<code>-utf8.txt` with unique, NFC native spellings, ordered
from most to least common. Each spelling must fold to a lowercase `a-z` key of
five or six letters. The 48K release automatically keeps only five-letter
words; the 128K release keeps words of lengths 5 and 6 for its two boards.
OMW `.tab`, plain UTF-8, and GWA WordNet-LMF
`.xml` or `.xml.gz`
inputs can be imported with:

```sh
make import-wordnet \
  IMPORT_LANGUAGE=en \
  WORDNET_FILES="/path/to/wordnet.xml.gz /path/to/extra-lemmas.txt"
```

`tools/import_wordnet.py` creates the accentless selection used to filter a
source. `tools/build_accented_wordlist.py` then restores exact native spellings.
Use `--reject-uppercase` for sources whose capitalization reliably marks
proper names. With
`wordfreq==3.1.1` installed, `--frequency-language <code>` ranks retained
WordNet lemmas by common usage. `tools/import_wordfreq.py` is available when a
properly redistributable WordNet cannot be obtained. Always record source
licences and attribution in `data/README.md`.

## 3. Add the build configuration

Create `languages/<code>.mk`, for example:

```make
LANGUAGE_NAME := English
PROGRAM_NAME := spectrle-en
LOCALE_PO := locales/en.po
DICTIONARY_WORDS := data/words-en-utf8.txt
DICTIONARY_WORDS_48 := 0
DICTIONARY_WORDS_128 := 0
DICTIONARY_MAX_48_BYTES := 20000
SPECTRLE_128_MAX_LENGTH := 6
```

Add the code to `BUILD_LANGUAGES` in `catalog.mk` when it is release-ready.
`make all-languages` discovers every configuration, while a chosen matrix can
be tested with `make BUILD_LANGUAGES="pl en"`.

Zero counts enable automatic fitting: the builder keeps the ranked prefix and
drops only the least frequent words if the 48K budget or a 128K bank would
overflow. A positive count pins an exact prefix for reproducible experiments.
Set `SPECTRLE_128_MAX_LENGTH := 6` for the 5x5 and 6x6 release.

The build fails if a translation is incomplete or invalid, a configured word
count is impossible, a forbidden length enters a release, the 48K dictionary
exceeds its byte budget, or any 128K bank exceeds 16 KB. Use
`make RUN_LANGUAGE=<code> smoke` for both emulator variants of one edition, or
`make smoke-all` for the full release matrix.
