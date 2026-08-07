#include "game.h"

static uint16_t random_state = 0x6d2bu;

static uint8_t text_length(const char *text)
{
    uint8_t length = 0u;

    while (*text++)
        ++length;
    return length;
}

void random_tick(void)
{
    uint16_t value = random_state;

    value ^= (uint16_t)(value << 7);
    value ^= value >> 9;
    value ^= (uint16_t)(value << 8);
    if (value == 0u)
        value = 0x6d2bu;
    random_state = value;
}

uint16_t random_word_index(uint16_t count)
{
    random_tick();
    return random_state % count;
}

void game_init(GameState *game)
{
    uint8_t row;
    uint8_t column;

    for (column = 0u; column <= MAX_WORD_LENGTH; ++column)
        game->word[column] = '\0';
    for (row = 0u; row < SPECTRLE_MAX_ATTEMPTS; ++row) {
        for (column = 0u; column <= SPECTRLE_MAX_LENGTH; ++column)
            game->guesses[row][column] = '\0';
        for (column = 0u; column < SPECTRLE_MAX_LENGTH; ++column)
            game->tiles[row][column] = TILE_EMPTY;
    }
    for (column = 0u; column < 26u; ++column)
        game->keyboard[column] = TILE_EMPTY;
    game->input_length = 0u;
    game->attempt = 0u;
    game->length = SPECTRLE_MIN_LENGTH;
    game->won = 0u;
    game->rounds = 0u;
    game->wins = 0u;
}

void game_new_round(GameState *game, uint8_t length)
{
    uint8_t row;
    uint8_t column;
    uint16_t count = dictionary_count();

    if (length < SPECTRLE_MIN_LENGTH || length > SPECTRLE_RELEASE_MAX_LENGTH)
        length = SPECTRLE_MIN_LENGTH;
    game->length = length;
    game->input_length = 0u;
    game->attempt = 0u;
    game->won = 0u;
    for (row = 0u; row < SPECTRLE_MAX_ATTEMPTS; ++row) {
        for (column = 0u; column <= SPECTRLE_MAX_LENGTH; ++column)
            game->guesses[row][column] = '\0';
        for (column = 0u; column < SPECTRLE_MAX_LENGTH; ++column)
            game->tiles[row][column] = TILE_EMPTY;
    }
    for (column = 0u; column < 26u; ++column)
        game->keyboard[column] = TILE_EMPTY;

    do {
        dictionary_get(random_word_index(count), game->word);
    } while (text_length(game->word) != length);
}

uint8_t game_add_letter(GameState *game, char letter)
{
    char *guess;

    if (game_won(game) || game_lost(game) || game->input_length >= game->length)
        return 0u;
    if (letter >= 'A' && letter <= 'Z')
        letter = (char)(letter - 'A' + 'a');
    if (letter < 'a' || letter > 'z')
        return 0u;

    guess = game->guesses[game->attempt];
    guess[game->input_length++] = letter;
    guess[game->input_length] = '\0';
    return 1u;
}

uint8_t game_delete_letter(GameState *game)
{
    char *guess;

    if (game_won(game) || game_lost(game) || game->input_length == 0u)
        return 0u;
    guess = game->guesses[game->attempt];
    --game->input_length;
    guess[game->input_length] = '\0';
    return 1u;
}

void game_score_word(const char *answer, const char *guess, uint8_t length,
                     uint8_t *tiles)
{
    uint8_t remaining[26u];
    uint8_t i;

    for (i = 0u; i < 26u; ++i)
        remaining[i] = 0u;

    for (i = 0u; i < length; ++i) {
        if (guess[i] == answer[i]) {
            tiles[i] = TILE_CORRECT;
        } else {
            tiles[i] = TILE_EMPTY;
            ++remaining[(uint8_t)(answer[i] - 'a')];
        }
    }

    for (i = 0u; i < length; ++i) {
        uint8_t index;

        if (tiles[i] == TILE_CORRECT)
            continue;
        index = (uint8_t)(guess[i] - 'a');
        if (remaining[index] != 0u) {
            tiles[i] = TILE_PRESENT;
            --remaining[index];
        } else {
            tiles[i] = TILE_ABSENT;
        }
    }
}

uint8_t game_submit(GameState *game)
{
    char *guess;
    uint8_t *tiles;
    uint8_t i;
    uint8_t solved = 1u;

    if (game->input_length != game->length)
        return SUBMIT_INCOMPLETE;
    guess = game->guesses[game->attempt];
    if (!dictionary_contains(guess))
        return SUBMIT_UNKNOWN;

    tiles = game->tiles[game->attempt];
    game_score_word(game->word, guess, game->length, tiles);
    for (i = 0u; i < game->length; ++i) {
        uint8_t letter = (uint8_t)(guess[i] - 'a');

        if (tiles[i] != TILE_CORRECT)
            solved = 0u;
        if (tiles[i] > game->keyboard[letter])
            game->keyboard[letter] = tiles[i];
    }

    ++game->attempt;
    game->input_length = 0u;
    if (solved) {
        game->won = 1u;
        return SUBMIT_WON;
    }
    if (game->attempt >= game->length)
        return SUBMIT_LOST;
    return SUBMIT_ACCEPTED;
}

uint8_t game_won(const GameState *game)
{
    return game->won;
}

uint8_t game_lost(const GameState *game)
{
    return !game->won && game->attempt >= game->length;
}
