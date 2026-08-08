# Dictionary provenance

All release game lists (`words-*-utf8.txt`) contain frequency-ranked, NFC
native spellings with five- or six-letter accentless lookup keys. The 48K build
keeps five-letter entries and no other length. The 128K build keeps five- and
six-letter entries and divides the sorted result into five independently
compressed banks. If a memory limit is reached, only the least frequent tail
is omitted.

| code | committed | 48K | 128K | custom glyphs | lexical source |
| --- | ---: | ---: | ---: | ---: | --- |
| `pl` | 17,276 | 6,448 | 17,276 | 9 | SJP.PL `odmiany` + `growy` |
| `en` | 5,176 | 2,249 | 5,176 | 0 | Open English WordNet 2025 |
| `es` | 3,968 | 1,624 | 3,968 | 7 | MCR 3.0 via OMW 1.4 |
| `ca` | 4,920 | 2,117 | 4,920 | 12 | MCR 3.0 via OMW 1.4 |
| `lt` | 1,320 | 485 | 1,320 | 9 | Lithuanian WordNet via OMW 1.4 |
| `sk` | 3,638 | 1,602 | 3,638 | 17 | Slovak WordNet via OMW 1.4 |
| `cs` | 7,291 | 3,360 | 7,291 | 17 | wordfreq 3.1.1 fallback |
| `pt` | 5,048 | 2,225 | 5,048 | 21 | OpenWN-PT via OMW 1.4 |

## Native spelling and fonts

`words-<code>-utf8.txt` are the release lists. They restore the original NFC
Unicode spelling from the same lexical sources. Every spelling retains an
accentless five- or six-letter lookup key, so one Spectrum key matches both the
plain and accented variants.
For example, `canon` and `cañón` are separate Spanish answers but share the
input key `CANON`. Catalan `l·l` retains its middle dot and counts as two `l`
letters, not three characters.

The restoration keeps the existing frequency/WordNet selection, but it no
longer merges distinct source spellings that fold to one ASCII key. Polish is
intersected with SJP.PL's game list using exact Unicode spelling. This removes
31 false matches in the old folded intersection, such as the headword `gądek`
being admitted merely because the unrelated form `gadek` was playable.
When several native spellings share one folded key, their source-frequency
order is retained. Submitting the folded key resolves it to the highest-ranked
native spelling, so an accentless `BEZEN` is displayed as `BEZEŃ`.

The generated dictionary header contains a folding map and only the 8x8
bitmaps needed by that edition. Base `A-Z` comes from the Spectrum ROM; accented
letters are derived from those shapes with acute, caron, ogonek, stroke, and
the other required marks. This costs eight bytes per custom glyph rather than
a complete font per language.

The production `FC5E/16` footprints below include all selected dictionary
records. No current edition required frequency trimming (`dropped = 0` for
both machines):

| code | 48K words | 48K dictionary | 128K words | 128K dictionary | largest 128K bank | glyph bitmaps |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `pl` | 6,448 | 21,018 B | 17,276 | 57,115 B | 11,637 B | 72 B |
| `en` | 2,249 | 7,260 B | 5,176 | 16,853 B | 3,474 B | 0 B |
| `es` | 1,624 | 5,531 B | 3,968 | 14,015 B | 2,843 B | 56 B |
| `ca` | 2,117 | 7,233 B | 4,920 | 17,199 B | 3,495 B | 96 B |
| `lt` | 485 | 1,805 B | 1,320 | 5,045 B | 1,032 B | 72 B |
| `sk` | 1,602 | 5,825 B | 3,638 | 13,745 B | 2,822 B | 136 B |
| `cs` | 3,360 | 10,880 B | 7,291 | 23,288 B | 4,812 B | 136 B |
| `pt` | 2,225 | 7,665 B | 5,048 | 17,925 B | 3,614 B | 168 B |

The baseline five-letter size report in `accented-5letter-sizes.json` compares
two native-symbol versions of the front coding. Fixed width is
the simplest upper bound. The selected estimate leaves the 31 most frequent
symbols at five bits and uses an escape plus 2-4 extra bits for uncommon
symbols in alphabets larger than 32.

| code | native spellings | lookup keys | current ASCII | fixed width | selected | font/map estimate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `pl` | 6,448 | 6,355 | 19,904 B | 22,819 B | 21,007 B | 140 B |
| `en` | 2,249 | 2,249 | 7,260 B | 7,260 B | 7,260 B | 0 B |
| `es` | 1,624 | 1,612 | 5,333 B | 5,526 B | 5,526 B | 112 B |
| `ca` | 2,117 | 2,076 | 6,689 B | 7,827 B | 7,228 B | 162 B |
| `lt` | 485 | 484 | 1,709 B | 1,805 B | 1,805 B | 136 B |
| `sk` | 1,602 | 1,578 | 5,211 B | 6,299 B | 5,835 B | 222 B |
| `cs` | 3,360 | 3,139 | 9,443 B | 11,626 B | 10,869 B | 212 B |
| `pt` | 2,225 | 2,102 | 6,786 B | 8,299 B | 7,648 B | 232 B |

The final column is a conservative data-only estimate of one decode byte and
one folding byte per alphabet symbol plus one 8-byte bitmap per non-ASCII
glyph. The UTF-8 text file sizes are disk/source sizes, not Spectrum RAM.

`tools/build_accented_wordlist.py` regenerates one native list from its original
WordNet, wordfreq, or SJP.PL input. `tools/measure_accented_dictionaries.py`
round-trips both candidate encodings and writes the JSON report.

## Polish

`words-pl-utf8.txt` was generated on 2026-08-08 from the native forms selected
by the ranked `words-pl-ascii.txt` keys and these sources:

- SJP.PL `odmiany`, release `sjp-odm-20260803.zip`, as the authority for
  accepted Polish headwords. This project selects its Apache License 2.0
  option: <https://sjp.pl/sl/odmiany/>.
- SJP.PL `słownik do gier`, release `sjp-20260803.zip`, as the authority for
  which of those headwords may be played. That list is offered under GPL 2 or
  Creative Commons Attribution 4.0 International only, so this project selects
  CC BY 4.0 for it: <https://sjp.pl/sl/growy/>.

The selection contains every normalized five- and six-letter lowercase
headword that passes the documented character filter; no external frequency
list decides whether a Polish word exists. Headwords that SJP.PL marks
`niedopuszczalne w grach` are dropped, which removes abbreviations, brand
names, and similar entries no player would guess. The generator requires at
least one vowel and removes a small explicit set of vulgar stems.

## WordNet editions

The English list comes from Open English WordNet 2025 (CC BY 4.0). Spanish and
Catalan use the Multilingual Central Repository 3.0 data (CC BY 3.0). The
Lithuanian and Slovak OMW packages offer their WordNet data under AGPL-3.0,
CC BY-SA 3.0, and ODbL 1.0. Portuguese uses OpenWN-PT (CC BY-SA 3.0), together
with the upstream Princeton WordNet and Wiktionary notices included by that
project.

The six source WordNets were normalized from their original UTF-8 lemmas and
ranked with `wordfreq==3.1.1` before truncation. All-caps acronyms are rejected
before case folding; Open English WordNet capitalization is also used to remove
proper-name lemmas. Relevant upstream attribution:

- John P. McCrae et al., Open English WordNet;
- Aitor Gonzalez-Agirre, Egoitz Laparra, and German Rigau, MCR 3.0 (2012);
- Radovan Garabik and Indre Pileckyte, Lithuanian WordNet (2013);
- Valeria de Paiva and Alexandre Rademaker, OpenWN-PT (2012);
- Francis Bond and Ryan Foster, Open Multilingual WordNet (2013).

Sources: <https://en-word.net/downloads>,
<https://github.com/omwn/omw-data/releases/tag/v1.4>, and the per-package
`LICENSE`/`citation.bib` files distributed by OMW.

## Frequency ranking and Czech fallback

`wordfreq` code is Apache-2.0 and its aggregated frequency data is CC BY-SA
4.0: <https://github.com/rspeer/wordfreq>. It ranks the common lemmas retained
for all six WordNet-derived lists.

The current Czech WordNet is not openly downloadable for redistribution, and
the older Czech WordNet has non-commercial/licensing constraints. Therefore
the Czech edition transparently uses the Czech `wordfreq` list directly rather
than claiming WordNet provenance. This choice is recorded in
`languages/wordnets.json`.

## Reproduction rules

`tools/normalize_words.py` applies Unicode decomposition plus explicit rules
for Latin letters and ligatures to construct the lowercase `a-z` input key.
`tools/build_accented_wordlist.py` retains distinct native spellings that share
that key and ranks them for deterministic memory trimming. The release build
needs only the committed UTF-8 lists; large upstream archives are not copied
into the project.

`tools/import_wordnet.py` imports OMW tabs, plain lists, and WordNet-LMF XML.
`tools/import_wordfreq.py` generates the documented fallback. Each resulting
file embeds a short provenance header; every upstream licence and attribution
continues to apply to derived dictionary data and tapes containing it.
