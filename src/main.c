/* Hallmark · pre-emit critique: P5 H5 E4 S5 R5 V4
 * macrostructure: Workbench · genre: playful · theme: Hum
 * Spectrum tokens: cyan=active, green=correct, yellow=present,
 * blue=absent, red=error. Tile shapes duplicate every colour signal. */
#include <arch/z80.h>
#include <conio.h>
#include <stdint.h>

#include "dictionary_meta.h"
#include "game.h"
#include "locale.h"
#include "screen.h"
#include "game_sound.h"

#define UI_NORMAL ZX_ATTR(ZX_INK_WHITE, ZX_INK_BLACK, 0u)
#define UI_BRIGHT ZX_ATTR(ZX_INK_WHITE, ZX_INK_BLACK, 1u)
#define UI_ACCENT ZX_ATTR(ZX_INK_CYAN, ZX_INK_BLACK, 1u)
#define UI_CORRECT ZX_ATTR(ZX_INK_BLACK, ZX_INK_GREEN, 1u)
#define UI_PRESENT ZX_ATTR(ZX_INK_BLACK, ZX_INK_YELLOW, 1u)
#define UI_ABSENT ZX_ATTR(ZX_INK_WHITE, ZX_INK_BLUE, 1u)
#define UI_GOOD ZX_ATTR(ZX_INK_GREEN, ZX_INK_BLACK, 1u)
#define UI_BAD ZX_ATTR(ZX_INK_RED, ZX_INK_BLACK, 1u)
#define UI_WARN ZX_ATTR(ZX_INK_YELLOW, ZX_INK_BLACK, 1u)

/* These markers are also read by the emulator smoke test. */
volatile uint8_t zx_boot_stage;
volatile uint8_t zx_selected_word_length;
volatile uint8_t zx_render_count;
volatile uint8_t zx_last_redraw_rows;
volatile uint8_t zx_full_render_count;
volatile uint8_t zx_last_sound;
volatile uint8_t zx_last_submit_result;
volatile char zx_solution[SPECTRLE_MAX_LENGTH + 1u];

static uint8_t wait_key(void)
{
    uint8_t key;

    do {
        key = (uint8_t)getk();
        random_tick();
    } while (key == 0u);

    while (getk() != 0)
        random_tick();

    if (key >= 'a' && key <= 'z')
        key = (uint8_t)(key - 'a' + 'A');
    return key;
}

static uint8_t append_text(char *target, uint8_t position, const char *text)
{
    while (*text && position < 31u)
        target[position++] = *text++;
    target[position] = '\0';
    return position;
}

static uint8_t append_number(char *target, uint8_t position, uint16_t value)
{
    char digits[5];
    uint8_t count = 0u;

    do {
        digits[count++] = (char)('0' + value % 10u);
        value /= 10u;
    } while (value != 0u && count < 5u);

    while (count != 0u && position < 31u)
        target[position++] = digits[--count];
    target[position] = '\0';
    return position;
}

static uint8_t grid_left(uint8_t length)
{
    return (uint8_t)((33u - (length << 2)) >> 1);
}

static uint8_t tile_attr(uint8_t state)
{
    if (state == TILE_CORRECT)
        return UI_CORRECT;
    if (state == TILE_PRESENT)
        return UI_PRESENT;
    if (state == TILE_ABSENT)
        return UI_ABSENT;
    return UI_BRIGHT;
}

static void tile_brackets(uint8_t state, char *left, char *right)
{
    if (state == TILE_PRESENT) {
        *left = '(';
        *right = ')';
    } else if (state == TILE_ABSENT) {
        *left = ' ';
        *right = ' ';
    } else {
        *left = '[';
        *right = ']';
    }
}

static void render_tile(const GameState *game, uint8_t row, uint8_t column)
{
    uint8_t state = row < game->attempt ? game->tiles[row][column] : TILE_EMPTY;
    uint8_t letter = game->guesses[row][column];
    char left;
    char right;
    uint8_t x = (uint8_t)(grid_left(game->length) + (column << 2));
    uint8_t y = (uint8_t)(3u + (row << 1));

    tile_brackets(state, &left, &right);
    if (state == TILE_CORRECT)
        letter = game->word[column];
    screen_char(x, y, left, tile_attr(state));
    if (letter != 0u)
        screen_letter((uint8_t)(x + 1u), y, letter, tile_attr(state));
    else
        screen_char((uint8_t)(x + 1u), y, ' ', tile_attr(state));
    screen_char((uint8_t)(x + 2u), y, right, tile_attr(state));
}

static void render_grid(const GameState *game)
{
    uint8_t row;
    uint8_t column;

    for (row = 0u; row < game->length; ++row) {
        for (column = 0u; column < game->length; ++column)
            render_tile(game, row, column);
        column = (uint8_t)(grid_left(game->length) +
                           (game->length << 2) - 1u);
        screen_clear_cells(column, (uint8_t)(3u + (row << 1)),
                           (uint8_t)(32u - column), UI_NORMAL);
    }
}

static void render_header(const GameState *game)
{
    char line[32];
    uint8_t position = 0u;

    position = append_number(line, position, game->length);
    position = append_text(line, position, "X");
    position = append_number(line, position, game->length);
    position = append_text(line, position, "  ");
    position = append_text(line, position, TXT_TRY_LABEL);
    position = append_number(line, position,
                             game->attempt < game->length
                                 ? (uint16_t)(game->attempt + 1u)
                                 : game->attempt);
    position = append_text(line, position, "/");
    position = append_number(line, position, game->length);
    position = append_text(line, position, "  ");
    position = append_text(line, position, TXT_WINS_LABEL);
    append_number(line, position, game->wins);
    screen_clear_text_row(1u, UI_NORMAL);
    screen_text_center(1u, line, UI_NORMAL);
}

static void render_message(const char *message, uint8_t attr)
{
    screen_clear_text_row(17u, UI_NORMAL);
    screen_text_center(17u, message, attr);
}

static void render_alphabet(const GameState *game)
{
    uint8_t family;
    uint8_t position = 0u;

    for (family = 1u; family <= 26u; ++family) {
        uint8_t symbol;

        for (symbol = family; symbol <= DICTIONARY_ALPHABET_SIZE;
             ++symbol) {
            uint8_t state;
            uint8_t row;
            uint8_t column;
            uint8_t attr;

            if (symbol != family && symbol <= 26u)
                continue;
            if (dictionary_fold_letter(symbol) != family)
                continue;
            state = game_keyboard_symbol_state(game, symbol);
            row = (uint8_t)(19u + (position >> 4));
            column = (uint8_t)(1u + ((position & 15u) << 1));
            attr = state == TILE_EMPTY ? UI_ACCENT : tile_attr(state);
            screen_letter(column, row, symbol, attr);
            ++position;
        }
    }
}

static void render_game_full(const GameState *game, const char *message)
{
    screen_clear(UI_NORMAL);
#ifdef ZX48
    screen_text_center(0u, TXT_TITLE_48, UI_ACCENT);
#else
    screen_text_center(0u, TXT_TITLE_128, UI_ACCENT);
#endif
    render_header(game);
    render_grid(game);
    render_alphabet(game);
    screen_text_center(23u, TXT_KEYBOARD, UI_NORMAL);
    render_message(message, UI_NORMAL);
    zx_last_redraw_rows = 24u;
    ++zx_full_render_count;
    ++zx_render_count;
}

static void update_input_tile(const GameState *game, uint8_t column)
{
    render_tile(game, game->attempt, column);
    render_message(TXT_TYPE_WORD, UI_NORMAL);
    zx_last_redraw_rows = 2u;
    ++zx_render_count;
}

static void update_after_submit(const GameState *game, uint8_t result)
{
    uint8_t column;

    zx_last_submit_result = result;
    if (result == SUBMIT_INCOMPLETE) {
        sound_reject();
        zx_last_sound = 1u;
        render_message(TXT_NOT_ENOUGH, UI_WARN);
        zx_last_redraw_rows = 1u;
    } else if (result == SUBMIT_UNKNOWN) {
        sound_reject();
        zx_last_sound = 1u;
        render_message(TXT_NOT_IN_DICTIONARY, UI_BAD);
        zx_last_redraw_rows = 1u;
    } else {
        uint8_t row = (uint8_t)(game->attempt - 1u);
        uint8_t length = game->length;

        for (column = 0u; column < length; ++column)
            render_tile(game, row, column);
        column = (uint8_t)(grid_left(length) + (length << 2) - 1u);
        screen_clear_cells(column, (uint8_t)(3u + (row << 1)),
                           (uint8_t)(32u - column), UI_NORMAL);
        render_header(game);
        render_alphabet(game);
        if (result == SUBMIT_WON) {
            sound_win();
            zx_last_sound = 3u;
        } else if (result == SUBMIT_LOST) {
            sound_loss();
            zx_last_sound = 4u;
        } else {
            sound_accept();
            zx_last_sound = 2u;
            render_message(TXT_NEXT_GUESS, UI_NORMAL);
        }
        zx_last_redraw_rows = 5u;
    }
    ++zx_render_count;
}

static uint8_t choose_mode(void)
{
    char line[32];
    uint8_t position;
    uint8_t key;

    for (;;) {
        zx_boot_stage = 0x4du;
        screen_clear(UI_NORMAL);
#ifdef ZX48
        screen_text_center(2u, TXT_TITLE_48, UI_ACCENT);
#else
        screen_text_center(2u, TXT_TITLE_128, UI_ACCENT);
#endif
        screen_text_center(4u, TXT_ASCII_NOTICE, UI_NORMAL);

        position = append_text(line, 0u, TXT_DICTIONARY_PREFIX);
        position = append_number(line, position, dictionary_count());
        append_text(line, position, TXT_DICTIONARY_SUFFIX);
        screen_text_center(6u, line, UI_WARN);

        screen_text(7u, 9u, TXT_MODE_5_LINE, UI_BRIGHT);
#if defined(ZX128) && SPECTRLE_128_MAX_LENGTH >= 6
        screen_text(7u, 11u, TXT_MODE_6_LINE, UI_BRIGHT);
#endif

        screen_text(3u, 16u, "[A]", UI_CORRECT);
        screen_text(8u, 16u, TXT_CORRECT, UI_NORMAL);
        screen_text(3u, 17u, "(A)", UI_PRESENT);
        screen_text(8u, 17u, TXT_PRESENT, UI_NORMAL);
        screen_text(3u, 18u, " A ", UI_ABSENT);
        screen_text(8u, 18u, TXT_ABSENT, UI_NORMAL);

        screen_text_center(20u,
#if defined(ZX128) && SPECTRLE_128_MAX_LENGTH >= 6
                           TXT_CHOOSE_5_6,
#else
                           TXT_CHOOSE_5,
#endif
                           UI_ACCENT);
        key = wait_key();
#if defined(ZX128) && SPECTRLE_128_MAX_LENGTH >= 6
        if (key == '1' || key == '2')
            return (uint8_t)(key - '1' + SPECTRLE_MIN_LENGTH);
#else
        if (key == '1')
            return SPECTRLE_MIN_LENGTH;
#endif
    }
}

static uint8_t finish_round(GameState *game, uint8_t won)
{
    char message[32];
    uint8_t position;
    uint8_t source;
    uint8_t key;

    ++game->rounds;
    if (won)
        ++game->wins;

    render_header(game);
    if (won) {
        render_message(TXT_WON, UI_GOOD);
    } else {
        uint8_t prefix_length;
        uint8_t left;

        position = append_text(message, 0u, TXT_WORD_PREFIX);
        prefix_length = position;
        left = (uint8_t)((32u - prefix_length - game->length) >> 1);
        screen_clear_text_row(17u, UI_NORMAL);
        screen_text(left, 17u, message, UI_BAD);
        source = 0u;
        while (game->word[source] && source < game->length) {
            screen_letter((uint8_t)(left + prefix_length + source), 17u,
                          game->word[source], UI_BAD);
            ++source;
        }
    }

    screen_clear_text_row(22u, UI_NORMAL);
    screen_text_center(22u, TXT_NEXT_PROMPT, UI_WARN);
    zx_boot_stage = 0x46u;
    zx_last_redraw_rows = 3u;
    ++zx_render_count;

    for (;;) {
        key = wait_key();
        if (key == 13u || key == 10u)
            return 0u;
        if (key == 'M')
            return 1u;
        if (key == 'Q')
            return 2u;
    }
}

int main(void)
{
    GameState game;
    uint8_t mode = SPECTRLE_MIN_LENGTH;
    uint8_t action = 1u;

    sound_init();
    game_init(&game);

    while (action != 2u) {
        uint8_t i;
        uint8_t key;

        if (action == 1u)
            mode = choose_mode();
        game_new_round(&game, mode);
        zx_selected_word_length = game.length;
        for (i = 0u; i < game.length; ++i)
            zx_solution[i] = (char)('a' +
                dictionary_fold_letter(game.word[i]) - 1u);
        zx_solution[game.length] = '\0';
        zx_last_submit_result = SUBMIT_INCOMPLETE;
        zx_boot_stage = 0x47u;
        render_game_full(&game, TXT_TYPE_WORD);

        while (!game_won(&game) && !game_lost(&game)) {
            key = wait_key();
            if (key >= 'A' && key <= 'Z') {
                uint8_t column = game.input_length;

                if (game_add_letter(&game, (char)key))
                    update_input_tile(&game, column);
            } else if (key == 8u || key == 12u || key == 127u) {
                if (game_delete_letter(&game))
                    update_input_tile(&game, game.input_length);
            } else if (key == 10u || key == 13u) {
                uint8_t result = game_submit(&game);

                update_after_submit(&game, result);
            }
        }
        action = finish_round(&game, game_won(&game));
    }

    screen_clear(UI_NORMAL);
    screen_text_center(9u, TXT_THANKS, UI_ACCENT);
    screen_text_center(12u, TXT_ANY_KEY, UI_NORMAL);
    wait_key();
    return 0;
}
