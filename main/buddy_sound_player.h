#pragma once

#include "esp_err.h"

#include "buddy_sound_logic.h"

esp_err_t buddy_sound_player_init(void);
bool buddy_sound_player_enqueue(buddy_sound_cue_t cue, uint8_t volume_percent);
