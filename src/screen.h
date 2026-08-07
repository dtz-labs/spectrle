#ifndef WORDLE_SCREEN_H
#define WORDLE_SCREEN_H

#include <stdint.h>

#define ZX_INK_BLACK 0u
#define ZX_INK_BLUE 1u
#define ZX_INK_RED 2u
#define ZX_INK_MAGENTA 3u
#define ZX_INK_GREEN 4u
#define ZX_INK_CYAN 5u
#define ZX_INK_YELLOW 6u
#define ZX_INK_WHITE 7u
#define ZX_ATTR(ink, paper, bright) ((uint8_t)((ink) | ((paper) << 3) | ((bright) << 6)))

void screen_clear(uint8_t attr);
void screen_clear_cells(uint8_t column, uint8_t row, uint8_t count, uint8_t attr);
void screen_clear_text_row(uint8_t row, uint8_t attr);
void screen_text(uint8_t column, uint8_t row, const char *text, uint8_t attr);
void screen_text_center(uint8_t row, const char *text, uint8_t attr);
void screen_char(uint8_t column, uint8_t row, char ch, uint8_t attr);

#endif
