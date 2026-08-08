#ifndef SPECTRLE_DICTIONARY_H
#define SPECTRLE_DICTIONARY_H

#include <stdint.h>

#define MAX_WORD_LENGTH 15u

uint16_t dictionary_count(void);
void dictionary_get(uint16_t index, uint8_t *word);
uint8_t dictionary_contains(const uint8_t *word);
uint8_t dictionary_resolve(uint8_t *word);
uint8_t dictionary_fold_letter(uint8_t letter);

#endif
