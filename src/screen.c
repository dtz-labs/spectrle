#include "screen.h"

#define PIXELS ((volatile uint8_t *)0x4000)
#define ATTRIBUTES ((volatile uint8_t *)0x5800)
#define ROM_FONT ((const uint8_t *)0x3d00)

static volatile uint8_t *pixel_address(uint8_t x_byte, uint8_t y)
{
    uint16_t address = 0x4000u;

    address |= (uint16_t)(y & 0xc0u) << 5;
    address |= (uint16_t)(y & 0x07u) << 8;
    address |= (uint16_t)(y & 0x38u) << 2;
    address += x_byte;
    return (volatile uint8_t *)address;
}

void screen_clear(uint8_t attr)
{
    uint16_t i;

    for (i = 0u; i < 6144u; ++i)
        PIXELS[i] = 0u;
    for (i = 0u; i < 768u; ++i)
        ATTRIBUTES[i] = attr;
}

void screen_clear_cells(uint8_t column, uint8_t row, uint8_t count, uint8_t attr)
{
    while (count-- != 0u && column < 32u)
        screen_char(column++, row, ' ', attr);
}

void screen_clear_text_row(uint8_t row, uint8_t attr)
{
    screen_clear_cells(0u, row, 32u, attr);
}

void screen_char(uint8_t column, uint8_t row, char ch, uint8_t attr)
{
    const uint8_t *glyph;
    uint8_t line;

    if (column >= 32u || row >= 24u)
        return;
    if (ch < 32 || ch > 127)
        ch = '?';

    glyph = ROM_FONT + ((uint16_t)(uint8_t)(ch - 32) << 3);
    for (line = 0u; line < 8u; ++line)
        *pixel_address(column, (uint8_t)((row << 3) + line)) = glyph[line];
    ATTRIBUTES[(uint16_t)row * 32u + column] = attr;
}

void screen_text(uint8_t column, uint8_t row, const char *text, uint8_t attr)
{
    while (*text && column < 32u)
        screen_char(column++, row, *text++, attr);
}

void screen_text_center(uint8_t row, const char *text, uint8_t attr)
{
    uint8_t length = 0u;
    const char *scan = text;

    while (*scan++)
        ++length;
    screen_text(length < 32u ? (uint8_t)((32u - length) >> 1) : 0u,
                row, text, attr);
}
