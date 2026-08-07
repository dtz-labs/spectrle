# Adding a language edition

Eight editions are currently enabled: `pl en es ca lt sk cs pt`. A new
Latin-script edition needs a gettext catalog, an ASCII dictionary, and one Make
configuration.

## 1. Translate the interface

The English source messages live in `locales/messages.def`. If the game gains
or changes UI text, extract and merge the catalogs with:

```sh
make pot
make update-po
```

Create `locales/<code>.po` from the inherited `locales/hangman.pot` template
and translate every context. The filename is retained for compatibility; its
package metadata and messages belong to Wordle. Translations must use printable
ASCII and fit a 32-character Spectrum row. `ascii_notice` must explicitly say
that accents are absent and input is limited to `A-Z`.

Gettext is used only on the build host. `tools/build_locale.py` compiles the
selected `.po` into a generated C header, so no gettext library or multi-language
string table occupies Spectrum RAM.

## 2. Prepare the dictionary

Create `data/words-<code>-ascii.txt` with unique lowercase `a-z` words, 3-15
letters long. The 48K release automatically keeps only five-letter words; the
128K release can keep words of lengths 5 and 6 for its two playable boards.
OMW `.tab`, plain UTF-8, and GWA WordNet-LMF
`.xml` or `.xml.gz`
inputs can be imported with:

```sh
make import-wordnet \
  IMPORT_LANGUAGE=en \
  WORDNET_FILES="/path/to/wordnet.xml.gz /path/to/extra-lemmas.txt"
```

`tools/import_wordnet.py` removes accents, expands common Latin ligatures,
filters spaces, punctuation, and all-caps acronyms, then deduplicates after
folding. Use `--reject-uppercase` for sources whose capitalization reliably
marks proper names. With
`wordfreq==3.1.1` installed, `--frequency-language <code>` ranks retained
WordNet lemmas by common usage. `tools/import_wordfreq.py` is available when a
properly redistributable WordNet cannot be obtained. Always record source
licences and attribution in `data/README.md`.

## 3. Add the build configuration

Create `languages/<code>.mk`, for example:

```make
LANGUAGE_NAME := English
PROGRAM_NAME := wordle-en
LOCALE_PO := locales/en.po
DICTIONARY_WORDS := data/words-en-ascii.txt
DICTIONARY_WORDS_48 := 2249
DICTIONARY_WORDS_128 := 5176
DICTIONARY_MAX_48_BYTES := 20000
WORDLE_128_MAX_LENGTH := 6
```

Add the code to `BUILD_LANGUAGES` in `catalog.mk` when it is release-ready.
`make all-languages` discovers every configuration, while a chosen matrix can
be tested with `make BUILD_LANGUAGES="pl en"`.

Set the two counts to the number of eligible entries (length 5 for 48K and
length 5-6 for 128K), so the release does not silently discard common words.
Set `WORDLE_128_MAX_LENGTH := 6` only when the complete six-letter selection
fits the five dictionary banks; otherwise set it to `5` and make the 128K word
count match the five-letter selection.

The build fails if a translation is incomplete or invalid, a configured word
count is missing, a forbidden length enters a release, the 48K dictionary
exceeds its byte budget, or any 128K bank exceeds 16 KB. Use
`make RUN_LANGUAGE=<code> smoke` for both emulator variants of one edition, or
`make smoke-all` for the full release matrix.
