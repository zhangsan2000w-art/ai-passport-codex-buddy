#pragma once

#include <stdbool.h>
#include <stdint.h>

#include "buddy_state.h"

typedef enum {
    BUDDY_SOUND_CUE_NONE = 0,
    BUDDY_SOUND_CUE_APPROVAL = 1U << 0,
    BUDDY_SOUND_CUE_COMPLETE = 1U << 1,
} buddy_sound_cue_t;

typedef struct {
    uint64_t approval_sequence;
    uint64_t completion_sequence;
    bool initialized;
} buddy_sound_tracker_t;

void buddy_sound_tracker_init(buddy_sound_tracker_t *tracker,
                              const buddy_state_t *state);
buddy_sound_cue_t buddy_sound_tracker_update(buddy_sound_tracker_t *tracker,
                                             const buddy_state_t *state);
