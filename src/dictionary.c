#include "dictionary.h"
#include "dictionary_meta.h"

#ifdef ZX128
#include <arch/z80.h>
#include <intrinsic.h>
#endif

#define BLOCK_SHIFT 4u
#define BLOCK_MASK 15u

static const uint8_t dictionary_folds[DICTIONARY_ALPHABET_SIZE + 1u] =
    DICTIONARY_FOLD_SYMBOLS;
static const uint8_t dictionary_direct[DICTIONARY_DIRECT_COUNT] =
    DICTIONARY_DIRECT_SYMBOLS;
#if DICTIONARY_ESCAPED_COUNT > 0
static const uint8_t dictionary_escaped[DICTIONARY_ESCAPED_COUNT] =
    DICTIONARY_ESCAPED_SYMBOLS;
#endif

#ifdef ZX48
extern const uint8_t dictionary_blob[];
#else
extern const uint8_t dictionary_bank0[];
extern const uint8_t dictionary_bank1[];
extern const uint8_t dictionary_bank3[];
extern const uint8_t dictionary_bank4[];
extern const uint8_t dictionary_bank6[];

#define ZX_BANKM (*(volatile uint8_t *)23388)

static const uint8_t *const dictionary_banks[DICTIONARY_128_BANKS] = {
    dictionary_bank0,
    dictionary_bank1,
    dictionary_bank3,
    dictionary_bank4,
    dictionary_bank6
};

static const uint8_t physical_banks[DICTIONARY_128_BANKS] = {0u, 1u, 3u, 4u, 6u};
static const uint16_t dictionary_bank_words[DICTIONARY_128_BANKS] = {
    DICTIONARY_128_BANK0_WORDS,
    DICTIONARY_128_BANK1_WORDS,
    DICTIONARY_128_BANK3_WORDS,
    DICTIONARY_128_BANK4_WORDS,
    DICTIONARY_128_BANK6_WORDS
};

static void write_page_state(uint8_t state)
{
    ZX_BANKM = state;
    z80_outp(0x7ffdu, state);
}

static uint8_t page_dictionary_bank(uint8_t logical_bank)
{
    uint8_t old_state = ZX_BANKM;
    uint8_t state = (uint8_t)((old_state & 0xf8u) | physical_banks[logical_bank]);

    intrinsic_di();
    write_page_state(state);
    return old_state;
}

static void restore_page(uint8_t old_state)
{
    write_page_state(old_state);
    intrinsic_ei();
}
#endif

static uint16_t read_u16(const uint8_t *p)
{
    return (uint16_t)p[0] | ((uint16_t)p[1] << 8);
}

static uint8_t read_bits(const uint8_t **record, uint16_t *accumulator,
                         uint8_t *bits, uint8_t width)
{
    uint8_t value;

    while (*bits < width) {
        *accumulator = (uint16_t)((*accumulator << 8) | *(*record)++);
        *bits = (uint8_t)(*bits + 8u);
    }
    *bits = (uint8_t)(*bits - width);
    value = (uint8_t)((*accumulator >> *bits) & ((1u << width) - 1u));
    if (*bits == 0u)
        *accumulator = 0u;
    else
        *accumulator &= (uint16_t)((1u << *bits) - 1u);
    return value;
}

static void decode_word(const uint8_t *blob, uint16_t index, uint8_t *word)
{
    uint16_t block = index >> BLOCK_SHIFT;
    uint8_t within = (uint8_t)(index & BLOCK_MASK);
    uint16_t offset = read_u16(blob + 4u + (block << 1));
    const uint8_t *record = blob + offset;
    uint8_t entry;

    word[0] = 0u;

    for (entry = 0u; entry <= within; ++entry) {
        uint8_t header = *record++;
        uint8_t prefix = header >> 4;
        uint8_t suffix = header & 15u;
        uint16_t accumulator = 0u;
        uint8_t bits = 0u;
        uint8_t i;

        for (i = 0u; i < suffix; ++i) {
            uint8_t code = read_bits(&record, &accumulator, &bits, 5u);
            uint8_t value;

#if DICTIONARY_ESCAPE_BITS > 0
            if (code == 31u) {
                uint8_t escaped = read_bits(&record, &accumulator, &bits,
                                            DICTIONARY_ESCAPE_BITS);
                value = dictionary_escaped[escaped];
            } else
#endif
            {
                value = dictionary_direct[code];
            }
            word[prefix + i] = value;
        }
        word[prefix + suffix] = 0u;
    }
}

uint16_t dictionary_count(void)
{
#ifdef ZX48
    return DICTIONARY_48_WORDS;
#else
    return DICTIONARY_128_WORDS;
#endif
}

void dictionary_get(uint16_t index, uint8_t *word)
{
#ifdef ZX48
    decode_word(dictionary_blob, index, word);
#else
    uint8_t bank = 0u;
    uint8_t old_state;

    while (index >= dictionary_bank_words[bank]) {
        index = (uint16_t)(index - dictionary_bank_words[bank]);
        ++bank;
    }

    old_state = page_dictionary_bank(bank);
    decode_word(dictionary_banks[bank], index, word);
    restore_page(old_state);
#endif
}

uint8_t dictionary_fold_letter(uint8_t letter)
{
    if (letter > DICTIONARY_ALPHABET_SIZE)
        return 0u;
    return dictionary_folds[letter];
}

static int8_t compare_words(const uint8_t *left, const uint8_t *right)
{
    uint8_t left_letter = dictionary_fold_letter(*left);
    uint8_t right_letter = dictionary_fold_letter(*right);

    while (*left && left_letter == right_letter) {
        ++left;
        ++right;
        left_letter = dictionary_fold_letter(*left);
        right_letter = dictionary_fold_letter(*right);
    }
    if (left_letter == right_letter)
        return 0;
    return left_letter < right_letter ? -1 : 1;
}

static uint8_t dictionary_lookup(const uint8_t *word, uint8_t *resolved)
{
    uint16_t low = 0u;
    uint16_t high = dictionary_count();
    uint8_t candidate[MAX_WORD_LENGTH + 1u];

    /* Lower bound selects the most frequent native spelling in a folded-key
       group because the builder orders equal keys by source-frequency rank. */
    while (low < high) {
        uint16_t middle = (uint16_t)(low + ((high - low) >> 1));
        int8_t order;

        dictionary_get(middle, candidate);
        order = compare_words(candidate, word);
        if (order < 0)
            low = (uint16_t)(middle + 1u);
        else
            high = middle;
    }
    if (low >= dictionary_count())
        return 0u;
    dictionary_get(low, candidate);
    if (compare_words(candidate, word) != 0)
        return 0u;
    if (resolved != 0) {
        uint8_t index = 0u;

        do {
            resolved[index] = candidate[index];
        } while (candidate[index++] != 0u);
    }
    return 1u;
}

uint8_t dictionary_contains(const uint8_t *word)
{
    return dictionary_lookup(word, 0);
}

uint8_t dictionary_resolve(uint8_t *word)
{
    return dictionary_lookup(word, word);
}
