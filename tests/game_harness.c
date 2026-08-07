#include <assert.h>
#include <stdint.h>
#include <string.h>

#include "game.h"

static const char *const words[] = {
    "array", "civic", "planet", "rarer", "screen"
};

uint16_t dictionary_count(void)
{
    return (uint16_t)(sizeof(words) / sizeof(words[0]));
}

void dictionary_get(uint16_t index, char *word)
{
    strcpy(word, words[index]);
}

uint8_t dictionary_contains(const char *word)
{
    uint8_t i;

    for (i = 0u; i < dictionary_count(); ++i) {
        if (strcmp(words[i], word) == 0)
            return 1u;
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
    uint8_t tiles[WORDLE_MAX_LENGTH];

    game_score_word("array", "rarer", 5u, tiles);
    assert(tiles[0] == TILE_PRESENT);
    assert(tiles[1] == TILE_PRESENT);
    assert(tiles[2] == TILE_CORRECT);
    assert(tiles[3] == TILE_ABSENT);
    assert(tiles[4] == TILE_ABSENT);

    game_score_word("civic", "cacao", 5u, tiles);
    assert(tiles[0] == TILE_CORRECT);
    assert(tiles[1] == TILE_ABSENT);
    assert(tiles[2] == TILE_PRESENT);
    assert(tiles[3] == TILE_ABSENT);
    assert(tiles[4] == TILE_ABSENT);
}

static void test_submit_and_keyboard(void)
{
    GameState game;

    game_init(&game);
    strcpy(game.word, "array");
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
    strcpy(game.word, "civic");
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

static void test_all_grid_sizes_select_matching_words(void)
{
    GameState game;

    game_init(&game);
#ifdef ZX48
    game_new_round(&game, 6u);
    assert(game.length == 5u);
    assert(strlen(game.word) == 5u);
#else
    game_new_round(&game, 6u);
    assert(game.length == 6u);
    assert(strlen(game.word) == 6u);
    game_new_round(&game, 7u);
    assert(game.length == 5u);
    assert(strlen(game.word) == 5u);
#endif
    assert(game.attempt == 0u);
}

static void assert_attempt_budget(
    const char *answer, const char *guess, uint8_t length)
{
    GameState game;
    uint8_t attempt;

    game_init(&game);
    strcpy(game.word, answer);
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
    test_all_grid_sizes_select_matching_words();
    test_attempt_budget_matches_grid_size();
    return 0;
}
