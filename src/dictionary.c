#include "dictionary.h"
#include "dictionary_meta.h"

#ifdef ZX128
#include <arch/z80.h>
#include <intrinsic.h>
#endif

#define BLOCK_SHIFT 4u
#define BLOCK_MASK 15u

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

static void decode_word(const uint8_t *blob, uint16_t index, char *word)
{
    uint16_t block = index >> BLOCK_SHIFT;
    uint8_t within = (uint8_t)(index & BLOCK_MASK);
    uint16_t offset = read_u16(blob + 4u + (block << 1));
    const uint8_t *record = blob + offset;
    uint8_t entry;

    word[0] = '\0';

    for (entry = 0u; entry <= within; ++entry) {
        uint8_t header = *record++;
        uint8_t prefix = header >> 4;
        uint8_t suffix = header & 15u;
        uint16_t accumulator = 0u;
        uint8_t bits = 0u;
        uint8_t i;

        for (i = 0u; i < suffix; ++i) {
            uint8_t value;

            while (bits < 5u) {
                accumulator = (uint16_t)((accumulator << 8) | *record++);
                bits = (uint8_t)(bits + 8u);
            }
            bits = (uint8_t)(bits - 5u);
            value = (uint8_t)((accumulator >> bits) & 31u);
            if (bits == 0u)
                accumulator = 0u;
            else
                accumulator &= (uint16_t)((1u << bits) - 1u);
            word[prefix + i] = (char)('a' + value - 1u);
        }
        word[prefix + suffix] = '\0';
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

void dictionary_get(uint16_t index, char *word)
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

static int8_t compare_words(const char *left, const char *right)
{
    while (*left && *left == *right) {
        ++left;
        ++right;
    }
    if (*left == *right)
        return 0;
    return (uint8_t)*left < (uint8_t)*right ? -1 : 1;
}

uint8_t dictionary_contains(const char *word)
{
    uint16_t low = 0u;
    uint16_t high = dictionary_count();
    char candidate[MAX_WORD_LENGTH + 1u];

    while (low < high) {
        uint16_t middle = (uint16_t)(low + ((high - low) >> 1));
        int8_t order;

        dictionary_get(middle, candidate);
        order = compare_words(candidate, word);
        if (order == 0)
            return 1u;
        if (order < 0)
            low = (uint16_t)(middle + 1u);
        else
            high = middle;
    }
    return 0u;
}
