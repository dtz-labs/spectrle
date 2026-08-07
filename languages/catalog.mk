# Only these languages are built by default. Add a code after its locale,
# dictionary and languages/<code>.mk configuration are ready.
BUILD_LANGUAGES ?= pl en es ca lt sk cs pt

# Verified, downloadable WordNet inputs whose ordinary spelling uses the
# Latin alphabet. Details and exact package names live in wordnets.json.
WORDNET_LATIN_EUROPE := sq ca cs da de en eu fi fr gl hr is it lt nl nb nn \
	pl pt ro sk sl es sv
WORDNET_LATIN_OTHER := id zsm
WORDNET_LATIN_LANGUAGES := $(WORDNET_LATIN_EUROPE) $(WORDNET_LATIN_OTHER)
PLANNED_LANGUAGES := $(filter-out $(BUILD_LANGUAGES),$(WORDNET_LATIN_LANGUAGES))
