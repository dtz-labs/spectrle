#ifndef WORDLE_GAME_H
#define WORDLE_GAME_H

#include <stdint.h>
#include "dictionary.h"

#define WORDLE_MIN_LENGTH 5u
#define WORDLE_MAX_LENGTH 6u
#define WORDLE_MAX_ATTEMPTS 6u

#ifndef WORDLE_128_MAX_LENGTH
#define WORDLE_128_MAX_LENGTH 6u
#endif

#ifdef ZX48
#define WORDLE_RELEASE_MAX_LENGTH 5u
#else
#define WORDLE_RELEASE_MAX_LENGTH WORDLE_128_MAX_LENGTH
#endif

#define TILE_EMPTY 0u
#define TILE_ABSENT 1u
#define TILE_PRESENT 2u
#define TILE_CORRECT 3u

#define SUBMIT_INCOMPLETE 0u
#define SUBMIT_UNKNOWN 1u
#define SUBMIT_ACCEPTED 2u
#define SUBMIT_WON 3u
#define SUBMIT_LOST 4u

typedef struct GameState {
    char word[MAX_WORD_LENGTH + 1u];
    char guesses[WORDLE_MAX_ATTEMPTS][WORDLE_MAX_LENGTH + 1u];
    uint8_t tiles[WORDLE_MAX_ATTEMPTS][WORDLE_MAX_LENGTH];
    uint8_t keyboard[26u];
    uint8_t input_length;
    uint8_t attempt;
    uint8_t length;
    uint8_t won;
    uint16_t rounds;
    uint16_t wins;
} GameState;

void game_init(GameState *game);
void game_new_round(GameState *game, uint8_t length);
uint8_t game_add_letter(GameState *game, char letter);
uint8_t game_delete_letter(GameState *game);
uint8_t game_submit(GameState *game);
void game_score_word(const char *answer, const char *guess, uint8_t length,
                     uint8_t *tiles);
uint8_t game_won(const GameState *game);
uint8_t game_lost(const GameState *game);

void random_tick(void);
uint16_t random_word_index(uint16_t count);

#endif
