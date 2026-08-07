#ifndef WORDLE_DICTIONARY_H
#define WORDLE_DICTIONARY_H

#include <stdint.h>

#define MAX_WORD_LENGTH 15u

uint16_t dictionary_count(void);
void dictionary_get(uint16_t index, char *word);
uint8_t dictionary_contains(const char *word);

#endif
