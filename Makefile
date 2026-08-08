.DEFAULT_GOAL := all

# Single source of truth for the release version. `release.yml` refuses to
# publish a tag that does not match it, so tapes cannot claim the wrong build.
VERSION := $(strip $(shell cat VERSION))
VERSION_TAG := v$(VERSION)

include languages/catalog.mk

# With no LANGUAGE selected this Makefile orchestrates every enabled edition.
# Each language is then built in a recursive invocation with isolated outputs.
ifeq ($(strip $(LANGUAGE)),)

RUN_LANGUAGE ?= pl
WORDNET_MIN_COUNT ?= 1
GETTEXT_MESSAGES := locales/messages.def
GETTEXT_POT := locales/spectrle.pot
GETTEXT_PO_FILES := $(wildcard locales/*.po)
AVAILABLE_LANGUAGES := $(filter-out catalog,$(basename $(notdir $(wildcard languages/*.mk))))
MATRIX_LANGUAGES := $(sort $(BUILD_LANGUAGES) $(AVAILABLE_LANGUAGES))
ENABLED_TARGETS := $(addprefix build-,$(BUILD_LANGUAGES))
MATRIX_TARGETS := $(addprefix build-,$(MATRIX_LANGUAGES))
SMOKE_MATRIX_TARGETS := $(addprefix smoke-language-,$(BUILD_LANGUAGES))
PREPARE_TARGETS := $(addprefix prepare-,$(BUILD_LANGUAGES))
TAPE_TARGETS := $(addprefix tapes-,$(BUILD_LANGUAGES))

.PHONY: all all-languages host-test test prepare tapes dictionaries layout list-languages \
	list-wordnets import-wordnet pot update-po check-translations clean \
	run-48 run-128 run-zx48 run-zx128 smoke smoke-48 smoke-128 smoke-all \
	$(SMOKE_MATRIX_TARGETS) \
	$(MATRIX_TARGETS) $(addprefix test-,$(BUILD_LANGUAGES)) \
	$(PREPARE_TARGETS) $(TAPE_TARGETS) \
	$(addprefix dictionaries-,$(BUILD_LANGUAGES)) \
	$(addprefix layout-,$(BUILD_LANGUAGES))

all: host-test $(ENABLED_TARGETS)

all-languages: host-test $(addprefix build-,$(AVAILABLE_LANGUAGES))

# Generate Python-built inputs on the Ubuntu runner before compiling inside
# the official z88dk image, which only needs the prepared assembly and headers.
prepare: $(PREPARE_TARGETS)

$(PREPARE_TARGETS): prepare-%:
	$(MAKE) --no-print-directory LANGUAGE=$* language-prepare

tapes: $(TAPE_TARGETS)

$(TAPE_TARGETS): tapes-%:
	$(MAKE) --no-print-directory LANGUAGE=$* language-tapes

host-test:
	python3 -m unittest discover -s tests -v

pot: $(GETTEXT_MESSAGES)
	@command -v xgettext >/dev/null 2>&1 || { echo "GNU xgettext not found" >&2; exit 127; }
	xgettext --language=C --from-code=UTF-8 \
		--keyword=LOCALE_TEXT:1c,2 --add-comments=TRANSLATORS --sort-by-file \
		--package-name='ZX Spectrum Spectrle' --package-version=1.0 \
		--msgid-bugs-address=mpasternak --output=$(GETTEXT_POT) $(GETTEXT_MESSAGES)

update-po: pot
	@command -v msgmerge >/dev/null 2>&1 || { echo "GNU msgmerge not found" >&2; exit 127; }
	@for po in $(GETTEXT_PO_FILES); do \
		msgmerge --update --backup=none "$$po" $(GETTEXT_POT); \
	done

check-translations:
	@command -v msgfmt >/dev/null 2>&1 || { echo "GNU msgfmt not found" >&2; exit 127; }
	@for po in $(GETTEXT_PO_FILES); do \
		msgfmt --check --check-format -o /dev/null "$$po"; \
	done

$(MATRIX_TARGETS): build-%:
	$(MAKE) --no-print-directory LANGUAGE=$* language-all

test: host-test $(addprefix test-,$(BUILD_LANGUAGES))

$(addprefix test-,$(BUILD_LANGUAGES)): test-%:
	$(MAKE) --no-print-directory LANGUAGE=$* language-test

dictionaries: $(addprefix dictionaries-,$(BUILD_LANGUAGES))

$(addprefix dictionaries-,$(BUILD_LANGUAGES)): dictionaries-%:
	$(MAKE) --no-print-directory LANGUAGE=$* language-dictionaries

layout: $(addprefix layout-,$(BUILD_LANGUAGES))

$(addprefix layout-,$(BUILD_LANGUAGES)): layout-%:
	$(MAKE) --no-print-directory LANGUAGE=$* language-layout

list-languages:
	@echo "Build now: $(BUILD_LANGUAGES)"
	@echo "Ready configurations: $(AVAILABLE_LANGUAGES)"
	@echo "Planned from verified WordNets: $(PLANNED_LANGUAGES)"
	@echo "Build every ready edition: make all-languages"
	@echo 'Custom matrix: make BUILD_LANGUAGES="pl en ..."'
	@echo "Full source catalog: make list-wordnets"

list-wordnets:
	python3 tools/list_wordnets.py languages/wordnets.json

import-wordnet:
	@test -n "$(IMPORT_LANGUAGE)" || { echo "set IMPORT_LANGUAGE=xx" >&2; exit 2; }
	@test -n "$(WORDNET_FILES)" || { echo 'set WORDNET_FILES="file1.tab file2.tab"' >&2; exit 2; }
	python3 tools/import_wordnet.py \
		$(foreach file,$(WORDNET_FILES),--input $(file)) \
		--output data/words-$(IMPORT_LANGUAGE)-ascii.txt \
		--language $(IMPORT_LANGUAGE) --min-count $(WORDNET_MIN_COUNT)

run-zx48:
	$(MAKE) --no-print-directory LANGUAGE=$(RUN_LANGUAGE) language-run-zx48

run-zx128:
	$(MAKE) --no-print-directory LANGUAGE=$(RUN_LANGUAGE) language-run-zx128

run-48: run-zx48

run-128: run-zx128

smoke: smoke-48 smoke-128

smoke-all: $(SMOKE_MATRIX_TARGETS)

$(SMOKE_MATRIX_TARGETS): smoke-language-%:
	$(MAKE) --no-print-directory LANGUAGE=$* language-smoke-48
	$(MAKE) --no-print-directory LANGUAGE=$* language-smoke-128

smoke-48:
	$(MAKE) --no-print-directory LANGUAGE=$(RUN_LANGUAGE) language-smoke-48

smoke-128:
	$(MAKE) --no-print-directory LANGUAGE=$(RUN_LANGUAGE) language-smoke-128

clean:
	rm -rf build

else

LANGUAGE_CONFIG := languages/$(LANGUAGE).mk
ifeq ($(wildcard $(LANGUAGE_CONFIG)),)
$(error Missing $(LANGUAGE_CONFIG); add locale, dictionary and language configuration first)
endif
include $(LANGUAGE_CONFIG)

Z88DK ?= ../z88dk
LOCAL_ZCC := $(abspath $(Z88DK))/bin/zcc
ifneq ($(wildcard $(LOCAL_ZCC)),)
ZCC ?= $(LOCAL_ZCC)
ZCC_ENV := PATH=$(abspath $(Z88DK))/bin:/usr/bin:/bin ZCCCFG=$(abspath $(Z88DK))/lib/config
else
# The official z88dk Docker image already exports zcc and ZCCCFG.
ZCC ?= zcc
ZCC_ENV :=
endif

BUILD := build/$(LANGUAGE)
GEN := $(BUILD)/generated
COMMON_SOURCES := src/main.c src/game.c src/screen.c src/sound.c src/dictionary.c
COMMON_HEADERS := src/game.h src/screen.h src/game_sound.h src/dictionary.h
OPT ?= -SO2 --max-allocs-per-node10000
WARNFLAGS ?= --less-pedantic
COMMON_FLAGS := +zx -compiler=sdcc --reserve-regs-iy $(OPT) $(WARNFLAGS) -vn \
	-Isrc -I$(GEN) -DSPECTRLE_128_MAX_LENGTH=$(SPECTRLE_128_MAX_LENGTH)

DICT_TOOL := tools/build_dictionary.py
LOCALE_TOOL := tools/build_locale.py
LOCALE_MESSAGES := locales/messages.def
DICT_STAMP := $(GEN)/dictionary.stamp
LOCALE_STAMP := $(GEN)/locale.stamp
DICT_ASM48 := $(GEN)/dictionary_blob.asm
DICT_ASM128 := $(GEN)/dictionary_banks.asm

OBJS48 := $(patsubst src/%.c,$(BUILD)/48/%.o,$(COMMON_SOURCES)) \
	$(BUILD)/48/dictionary_blob.o
OBJS128 := $(patsubst src/%.c,$(BUILD)/128/%.o,$(COMMON_SOURCES)) \
	$(BUILD)/128/dictionary_banks.o

# z88dk-appmake derives the 128K bank block names from the binary name and
# mishandles dots in it, silently dropping the dictionary banks from the tape.
# So compile to a dot-free stem and only the finished tape carries the version.
STEM48 := $(BUILD)/$(PROGRAM_NAME)-48
STEM128 := $(BUILD)/$(PROGRAM_NAME)-128
BIN48 := $(STEM48).bin
BIN128 := $(STEM128).bin
MAP48 := $(STEM48).map
MAP128 := $(STEM128).map
BUILT_TAP48 := $(STEM48).tap
BUILT_TAP128 := $(STEM128).tap
TAP48 := $(STEM48)-$(VERSION_TAG).tap
TAP128 := $(STEM128)-$(VERSION_TAG).tap

.PHONY: language-all language-prepare language-tapes language-test language-layout \
	language-dictionaries language-locale check-zesarux \
	language-run-zx48 language-run-zx128 language-smoke-48 language-smoke-128

language-all: language-tapes language-test language-layout

language-prepare: $(DICT_STAMP) $(LOCALE_STAMP)

language-tapes: $(TAP48) $(TAP128)

language-dictionaries: $(DICT_STAMP)

language-locale: $(LOCALE_STAMP)

$(DICT_STAMP): $(DICTIONARY_WORDS) $(DICT_TOOL) $(LANGUAGE_CONFIG)
	@mkdir -p $(BUILD) $(GEN)
	python3 $(DICT_TOOL) --words $(DICTIONARY_WORDS) --build-dir $(BUILD) \
		--header $(GEN)/dictionary_meta.h --language $(LANGUAGE) \
		--words-48 $(DICTIONARY_WORDS_48) --words-128 $(DICTIONARY_WORDS_128) \
		--max-length-128 $(SPECTRLE_128_MAX_LENGTH) \
		--max-48-bytes $(DICTIONARY_MAX_48_BYTES) \
		--asm48 $(DICT_ASM48) --asm128 $(DICT_ASM128)
	@touch $@

$(LOCALE_STAMP): $(LOCALE_PO) $(LOCALE_MESSAGES) $(LOCALE_TOOL) $(LANGUAGE_CONFIG)
	@mkdir -p $(BUILD) $(GEN)
	python3 $(LOCALE_TOOL) --messages $(LOCALE_MESSAGES) --po $(LOCALE_PO) \
		--code $(LANGUAGE) --name $(LANGUAGE_NAME) \
		--header $(GEN)/locale.h --manifest $(BUILD)/locale-manifest.json
	@touch $@

$(BUILD)/48/%.o: src/%.c $(COMMON_HEADERS) $(DICT_STAMP) \
		$(LOCALE_STAMP) Makefile $(LANGUAGE_CONFIG)
	@mkdir -p $(@D)
	$(ZCC_ENV) $(ZCC) $(COMMON_FLAGS) -DZX48 -c $< -o $@

$(BUILD)/128/%.o: src/%.c $(COMMON_HEADERS) $(DICT_STAMP) \
		$(LOCALE_STAMP) Makefile $(LANGUAGE_CONFIG)
	@mkdir -p $(@D)
	$(ZCC_ENV) $(ZCC) $(COMMON_FLAGS) -DZX128 -c $< -o $@

$(BUILD)/48/dictionary_blob.o: $(DICT_STAMP)
	@mkdir -p $(@D)
	$(ZCC_ENV) $(ZCC) +zx -vn -c $(DICT_ASM48) -o $@

$(BUILD)/128/dictionary_banks.o: $(DICT_STAMP)
	@mkdir -p $(@D)
	$(ZCC_ENV) $(ZCC) +zx -vn -c $(DICT_ASM128) -o $@

$(TAP48): $(OBJS48)
	$(ZCC_ENV) $(ZCC) $(COMMON_FLAGS) -DZX48 \
		-pragma-define:CRT_ORG_CODE=0x8000 \
		-pragma-define:REGISTER_SP=0xffff \
		-m -create-app -o $(BIN48) $(OBJS48)
	@test -f $(BUILT_TAP48) || { echo "z88dk did not create $(BUILT_TAP48)" >&2; exit 1; }
	mv $(BUILT_TAP48) $@

$(TAP128): $(OBJS128)
	$(ZCC_ENV) $(ZCC) $(COMMON_FLAGS) -DZX128 \
		-pragma-define:CRT_ORG_CODE=0x8000 \
		-pragma-define:REGISTER_SP=0xbfff \
		-pragma-define:CRT_STACK_SIZE=1024 \
		-lndos -m -create-app -o $(BIN128) $(OBJS128)
	@test -f $(BUILT_TAP128) || { echo "z88dk did not create $(BUILT_TAP128)" >&2; exit 1; }
	mv $(BUILT_TAP128) $@

language-test: $(DICT_STAMP) $(LOCALE_STAMP)
	python3 tools/check_dictionary_fit.py \
		--manifest $(BUILD)/dictionary-manifest.json --words $(DICTIONARY_WORDS) \
		--expected-48 $(DICTIONARY_WORDS_48) \
		--expected-128 $(DICTIONARY_WORDS_128) \
		--max-length-128 $(SPECTRLE_128_MAX_LENGTH) \
		--max-48-bytes $(DICTIONARY_MAX_48_BYTES)

language-layout: $(TAP48) $(TAP128)
	python3 tools/check_layout.py \
		--map48 $(MAP48) --bin48 $(BIN48) \
		--map128 $(MAP128) --bin128 $(BIN128) \
		--bank-glob '$(STEM128)_BANK_*.bin' \
		--tap128 $(TAP128)

check-zesarux:
	@test -x /Applications/ZEsarUX.app/Contents/MacOS/zesarux || \
		command -v zesarux >/dev/null 2>&1 || { echo "ZEsarUX not found" >&2; exit 127; }

language-run-zx48: $(TAP48) check-zesarux
	$${ZESARUX:-/Applications/ZEsarUX.app/Contents/MacOS/zesarux} \
		--noconfigfile --machine 48k --tape $(abspath $(TAP48)) --fastautoload

language-run-zx128: $(TAP128) check-zesarux
	$${ZESARUX:-/Applications/ZEsarUX.app/Contents/MacOS/zesarux} \
		--noconfigfile --machine 128k --tape $(abspath $(TAP128)) --fastautoload

language-smoke-48: $(TAP48) check-zesarux
	python3 tools/zesarux_smoke.py --machine 48k --tap $(TAP48) \
		--max-length 5 \
		--map $(MAP48) --locale-manifest $(BUILD)/locale-manifest.json \
		--screenshot $(BUILD)/$(PROGRAM_NAME)-48-smoke.pbm

language-smoke-128: $(TAP128) check-zesarux
	python3 tools/zesarux_smoke.py --machine 128k --tap $(TAP128) \
		--max-length $(SPECTRLE_128_MAX_LENGTH) \
		--map $(MAP128) --locale-manifest $(BUILD)/locale-manifest.json \
		--screenshot $(BUILD)/$(PROGRAM_NAME)-128-smoke.pbm

endif
