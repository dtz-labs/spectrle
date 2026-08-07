#include <conio.h>
#include <stdint.h>

#include "license.h"
#include "screen.h"

#define UI_NORMAL ZX_ATTR(ZX_INK_WHITE, ZX_INK_BLACK, 0u)
#define UI_ACCENT ZX_ATTR(ZX_INK_CYAN, ZX_INK_BLACK, 1u)
#define LICENSE_LINE(text) text "\n"

static const char license_page_1[] =
    LICENSE_LINE("WORDLE - BSD LICENSE")
    LICENSE_LINE("")
    LICENSE_LINE("ORIGINAL BSD HANGMAN")
    LICENSE_LINE("Copyright (c) 1983, 1993")
    LICENSE_LINE("The Regents of the University")
    LICENSE_LINE("of California.")
    LICENSE_LINE("All rights reserved.")
    LICENSE_LINE("")
    LICENSE_LINE("Written by Ken Arnold.")
    LICENSE_LINE("")
    LICENSE_LINE("ZX SPECTRUM VERSION")
    LICENSE_LINE("Copyright (c) 2026")
    LICENSE_LINE("Michal Pasternak")
    LICENSE_LINE("All rights reserved.")
    LICENSE_LINE("")
    LICENSE_LINE("BSD 3-Clause License")
    LICENSE_LINE("")
    LICENSE_LINE("")
    LICENSE_LINE("")
    LICENSE_LINE("")
    LICENSE_LINE("")
    LICENSE_LINE("")
    LICENSE_LINE("")
    LICENSE_LINE("ANY KEY - NEXT 1/4");

static const char license_page_2[] =
    LICENSE_LINE("BSD LICENSE - CONDITIONS 1/2")
    LICENSE_LINE("")
    LICENSE_LINE("Redistribution and use in source")
    LICENSE_LINE("and binary forms, with or")
    LICENSE_LINE("without modification, are")
    LICENSE_LINE("permitted provided that the")
    LICENSE_LINE("following conditions are met:")
    LICENSE_LINE("1. Redistributions of source")
    LICENSE_LINE("code must retain the above")
    LICENSE_LINE("copyright notice, this list of")
    LICENSE_LINE("conditions and the following")
    LICENSE_LINE("disclaimer.")
    LICENSE_LINE("2. Redistributions in binary")
    LICENSE_LINE("form must reproduce the above")
    LICENSE_LINE("copyright notice, this list of")
    LICENSE_LINE("conditions and the following")
    LICENSE_LINE("disclaimer in the documentation")
    LICENSE_LINE("and/or other materials provided")
    LICENSE_LINE("with the distribution.")
    LICENSE_LINE("")
    LICENSE_LINE("")
    LICENSE_LINE("")
    LICENSE_LINE("")
    LICENSE_LINE("ANY KEY - NEXT 2/4");

static const char license_page_3[] =
    LICENSE_LINE("BSD LICENSE - CONDITIONS 2/2")
    LICENSE_LINE("")
    LICENSE_LINE("3. Neither the name of the")
    LICENSE_LINE("University nor the names of its")
    LICENSE_LINE("contributors may be used to")
    LICENSE_LINE("endorse or promote products")
    LICENSE_LINE("derived from this software")
    LICENSE_LINE("without specific prior written")
    LICENSE_LINE("permission.")
    LICENSE_LINE("")
    LICENSE_LINE("THIS SOFTWARE IS PROVIDED BY THE")
    LICENSE_LINE("REGENTS AND CONTRIBUTORS \"AS IS\"")
    LICENSE_LINE("AND ANY EXPRESS OR IMPLIED")
    LICENSE_LINE("WARRANTIES, INCLUDING, BUT NOT")
    LICENSE_LINE("LIMITED TO, THE IMPLIED")
    LICENSE_LINE("WARRANTIES OF MERCHANTABILITY")
    LICENSE_LINE("AND FITNESS FOR A PARTICULAR")
    LICENSE_LINE("PURPOSE ARE DISCLAIMED. IN NO")
    LICENSE_LINE("EVENT SHALL THE REGENTS OR")
    LICENSE_LINE("CONTRIBUTORS BE LIABLE FOR ANY")
    LICENSE_LINE("")
    LICENSE_LINE("")
    LICENSE_LINE("")
    LICENSE_LINE("ANY KEY - NEXT 3/4");

static const char license_page_4[] =
    LICENSE_LINE("BSD LICENSE - DISCLAIMER")
    LICENSE_LINE("")
    LICENSE_LINE("DIRECT, INDIRECT, INCIDENTAL,")
    LICENSE_LINE("SPECIAL, EXEMPLARY, OR")
    LICENSE_LINE("CONSEQUENTIAL DAMAGES")
    LICENSE_LINE("(INCLUDING, BUT NOT LIMITED TO,")
    LICENSE_LINE("PROCUREMENT OF SUBSTITUTE GOODS")
    LICENSE_LINE("OR SERVICES; LOSS OF USE, DATA,")
    LICENSE_LINE("OR PROFITS; OR BUSINESS")
    LICENSE_LINE("INTERRUPTION) HOWEVER CAUSED AND")
    LICENSE_LINE("ON ANY THEORY OF LIABILITY,")
    LICENSE_LINE("WHETHER IN CONTRACT, STRICT")
    LICENSE_LINE("LIABILITY, OR TORT (INCLUDING")
    LICENSE_LINE("NEGLIGENCE OR OTHERWISE) ARISING")
    LICENSE_LINE("IN ANY WAY OUT OF THE USE OF")
    LICENSE_LINE("THIS SOFTWARE, EVEN IF ADVISED")
    LICENSE_LINE("OF THE POSSIBILITY OF SUCH")
    LICENSE_LINE("DAMAGE.")
    LICENSE_LINE("")
    LICENSE_LINE("")
    LICENSE_LINE("")
    LICENSE_LINE("")
    LICENSE_LINE("")
    LICENSE_LINE("ANY KEY - RETURN TO MENU");

static const char *const license_pages[] = {
    license_page_1,
    license_page_2,
    license_page_3,
    license_page_4,
};

static void wait_key_release(void)
{
    while (getk() == 0)
        ;
    while (getk() != 0)
        ;
}

static void draw_page(const char *page)
{
    char line[33];
    uint8_t row = 0u;

    screen_clear(UI_NORMAL);
    while (*page && row < 24u) {
        uint8_t length = 0u;

        while (*page && *page != '\n' && length < 32u)
            line[length++] = *page++;
        line[length] = '\0';
        if (*page == '\n')
            ++page;
        if (row == 0u)
            screen_text_center(row, line, UI_ACCENT);
        else
            screen_text(0u, row, line, UI_NORMAL);
        ++row;
    }
}

void license_show(void)
{
    uint8_t page;

    for (page = 0u; page < 4u; ++page) {
        draw_page(license_pages[page]);
        wait_key_release();
    }
}
