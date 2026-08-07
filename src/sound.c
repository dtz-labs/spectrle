#include <sound.h>
#include <arch/z80.h>

#include "game_sound.h"

#define ZX_BORDCR (*(volatile unsigned char *)0x5c48)

void sound_init(void)
{
    /* z88dk's beeper reads the ROM border shadow before every tone. */
    ZX_BORDCR = 0u;
    z80_outp(0x00feu, 0u);
}

void sound_reject(void)
{
    bit_beep(30, 58);
    sound_init();
}

void sound_accept(void)
{
    bit_beep(34, 132);
    bit_beep(42, 104);
    sound_init();
}

/* An original, short rising pickup: celebratory without copying a tune. */
void sound_win(void)
{
    bit_beep(35, 180);
    bit_beep(50, 112);
    bit_beep(70, 72);
    sound_init();
}

void sound_loss(void)
{
    bit_beep(50, 100);
    bit_beep(65, 175);
    bit_beep(80, 280);
    sound_init();
}
