#include <assert.h>
#include <stdint.h>

#include "game.h"

static const char *const words[] = {
    "array", "bezen", "civic", "planet", "rarer", "screen"
};

#define LETTER_A_OGONEK 27u
#define LETTER_S_ACUTE 28u
#define LETTER_N_ACUTE 29u

static void encode_word(uint8_t *target, const char *source)
{
    while (*source)
        *target++ = (uint8_t)(*source++ - 'a' + 1);
    *target = 0u;
}

static uint8_t encoded_length(const uint8_t *word)
{
    uint8_t length = 0u;
    while (*word++)
        ++length;
    return length;
}

uint16_t dictionary_count(void)
{
    return (uint16_t)(sizeof(words) / sizeof(words[0]));
}

void dictionary_get(uint16_t index, uint8_t *word)
{
    encode_word(word, words[index]);
    if (index == 1u)
        word[4] = LETTER_N_ACUTE;
}

uint8_t dictionary_fold_letter(uint8_t letter)
{
    if (letter == LETTER_A_OGONEK)
        return 1u;
    if (letter == LETTER_S_ACUTE)
        return 19u;
    if (letter == LETTER_N_ACUTE)
        return 14u;
    return letter;
}

uint8_t dictionary_contains(const uint8_t *word)
{
    uint8_t i;
    uint8_t candidate[SPECTRLE_MAX_LENGTH + 1u];

    for (i = 0u; i < dictionary_count(); ++i) {
        uint8_t column = 0u;
        dictionary_get(i, candidate);
        while (candidate[column] &&
               dictionary_fold_letter(candidate[column]) ==
                   dictionary_fold_letter(word[column]))
            ++column;
        if (dictionary_fold_letter(candidate[column]) ==
            dictionary_fold_letter(word[column]))
            return 1u;
    }
    return 0u;
}

uint8_t dictionary_resolve(uint8_t *word)
{
    uint8_t i;
    uint8_t candidate[SPECTRLE_MAX_LENGTH + 1u];

    for (i = 0u; i < dictionary_count(); ++i) {
        uint8_t column = 0u;
        dictionary_get(i, candidate);
        while (candidate[column] &&
               dictionary_fold_letter(candidate[column]) ==
                   dictionary_fold_letter(word[column]))
            ++column;
        if (dictionary_fold_letter(candidate[column]) ==
            dictionary_fold_letter(word[column])) {
            column = 0u;
            do {
                word[column] = candidate[column];
            } while (candidate[column++] != 0u);
            return 1u;
        }
    }
    return 0u;
}

static void enter_word(GameState *game, const char *word)
{
    while (*word)
        assert(game_add_letter(game, *word++));
}

static void test_duplicate_scoring(void)
{
    uint8_t tiles[SPECTRLE_MAX_LENGTH];
    uint8_t answer[SPECTRLE_MAX_LENGTH + 1u];
    uint8_t guess[SPECTRLE_MAX_LENGTH + 1u];

    encode_word(answer, "array");
    encode_word(guess, "rarer");
    game_score_word(answer, guess, 5u, tiles);
    assert(tiles[0] == TILE_PRESENT);
    assert(tiles[1] == TILE_PRESENT);
    assert(tiles[2] == TILE_CORRECT);
    assert(tiles[3] == TILE_ABSENT);
    assert(tiles[4] == TILE_ABSENT);

    encode_word(answer, "civic");
    encode_word(guess, "cacao");
    game_score_word(answer, guess, 5u, tiles);
    assert(tiles[0] == TILE_CORRECT);
    assert(tiles[1] == TILE_ABSENT);
    assert(tiles[2] == TILE_PRESENT);
    assert(tiles[3] == TILE_ABSENT);
    assert(tiles[4] == TILE_ABSENT);

    encode_word(answer, "asasa");
    answer[0] = LETTER_A_OGONEK;
    answer[1] = LETTER_S_ACUTE;
    encode_word(guess, "asasa");
    game_score_word(answer, guess, 5u, tiles);
    assert(tiles[0] == TILE_CORRECT);
    assert(tiles[1] == TILE_CORRECT);
}

static void test_submit_and_keyboard(void)
{
    GameState game;

    game_init(&game);
    encode_word(game.word, "array");
    game.length = 5u;

    enter_word(&game, "rarer");
    assert(game_submit(&game) == SUBMIT_ACCEPTED);
    assert(game.attempt == 1u);
    assert(game.keyboard['r' - 'a'] == TILE_CORRECT);
    assert(game.keyboard['a' - 'a'] == TILE_PRESENT);
    assert(game.keyboard['e' - 'a'] == TILE_ABSENT);

    enter_word(&game, "array");
    assert(game_submit(&game) == SUBMIT_WON);
    assert(game_won(&game));
    assert(!game_lost(&game));
    assert(game.keyboard['a' - 'a'] == TILE_CORRECT);
}

static void test_invalid_guesses_do_not_cost_attempts(void)
{
    GameState game;

    game_init(&game);
    encode_word(game.word, "civic");
    game.length = 5u;

    enter_word(&game, "civi");
    assert(game_submit(&game) == SUBMIT_INCOMPLETE);
    assert(game.attempt == 0u);
    assert(game_add_letter(&game, 'z'));
    assert(game_submit(&game) == SUBMIT_UNKNOWN);
    assert(game.attempt == 0u);
    assert(game.input_length == 5u);
    assert(game_delete_letter(&game));
    assert(game.input_length == 4u);
}

static void test_guess_resolves_to_native_spelling(void)
{
    GameState game;

    game_init(&game);
    encode_word(game.word, "array");
    game.length = 5u;
    enter_word(&game, "bezen");
    assert(game_submit(&game) == SUBMIT_ACCEPTED);
    assert(game.guesses[0][4] == LETTER_N_ACUTE);
}

static void set_scored_attempt(GameState *game, const char *answer,
                               const char *guess)
{
    game_init(game);
    encode_word(game->word, answer);
    encode_word(game->guesses[0], guess);
    game->length = 5u;
    game->attempt = 1u;
}

static void score_first_attempt(GameState *game)
{
    game_score_word(game->word, game->guesses[0], game->length,
                    game->tiles[0]);
}

static void test_national_keyboard_symbols(void)
{
    GameState game;

    set_scored_attempt(&game, "gaska", "orkan");
    game.word[1] = LETTER_A_OGONEK;
    score_first_attempt(&game);
    assert(game_keyboard_symbol_state(&game, 1u) == TILE_PRESENT);
    assert(game_keyboard_symbol_state(&game, LETTER_A_OGONEK) == TILE_PRESENT);

    game.word[4] = LETTER_A_OGONEK;
    score_first_attempt(&game);
    assert(game_keyboard_symbol_state(&game, 1u) == TILE_ABSENT);
    assert(game_keyboard_symbol_state(&game, LETTER_A_OGONEK) == TILE_PRESENT);

    encode_word(game.guesses[0], "barka");
    score_first_attempt(&game);
    assert(game_keyboard_symbol_state(&game, 1u) == TILE_ABSENT);
    assert(game_keyboard_symbol_state(&game, LETTER_A_OGONEK) == TILE_CORRECT);

    game_init(&game);
    encode_word(game.word, "bezen");
    game.word[4] = LETTER_N_ACUTE;
    game.length = 5u;
    enter_word(&game, "bezen");
    assert(game_submit(&game) == SUBMIT_WON);
    assert(game.guesses[0][4] == LETTER_N_ACUTE);
    assert(game_keyboard_symbol_state(&game, 14u) == TILE_ABSENT);
    assert(game_keyboard_symbol_state(&game, LETTER_N_ACUTE) == TILE_CORRECT);
}

static void test_all_grid_sizes_select_matching_words(void)
{
    GameState game;

    game_init(&game);
#ifdef ZX48
    game_new_round(&game, 6u);
    assert(game.length == 5u);
    assert(encoded_length(game.word) == 5u);
#else
    game_new_round(&game, 6u);
    assert(game.length == 6u);
    assert(encoded_length(game.word) == 6u);
    game_new_round(&game, 7u);
    assert(game.length == 5u);
    assert(encoded_length(game.word) == 5u);
#endif
    assert(game.attempt == 0u);
}

static void assert_attempt_budget(
    const char *answer, const char *guess, uint8_t length)
{
    GameState game;
    uint8_t attempt;

    game_init(&game);
    encode_word(game.word, answer);
    game.length = length;
    for (attempt = 0u; attempt < length; ++attempt) {
        enter_word(&game, guess);
        assert(game_submit(&game) ==
               (attempt + 1u == length ? SUBMIT_LOST : SUBMIT_ACCEPTED));
    }
    assert(game.attempt == length);
    assert(game_lost(&game));
    assert(!game_add_letter(&game, 'a'));
}

static void test_attempt_budget_matches_grid_size(void)
{
    assert_attempt_budget("array", "rarer", 5u);
#ifndef ZX48
    assert_attempt_budget("planet", "screen", 6u);
#endif
}

int main(void)
{
    test_duplicate_scoring();
    test_submit_and_keyboard();
    test_invalid_guesses_do_not_cost_attempts();
    test_guess_resolves_to_native_spelling();
    test_national_keyboard_symbols();
    test_all_grid_sizes_select_matching_words();
    test_attempt_budget_matches_grid_size();
    return 0;
}
