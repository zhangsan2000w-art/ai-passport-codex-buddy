#include "buddy_sound_logic.h"

#include <string.h>

void buddy_sound_tracker_init(buddy_sound_tracker_t *tracker,
                              const buddy_state_t *state)
{
    if (tracker == NULL) {
        return;
    }
    memset(tracker, 0, sizeof(*tracker));
    if (state != NULL) {
        tracker->approval_sequence = state->approval_sequence;
        tracker->completion_sequence = state->completion_sequence;
    }
    tracker->initialized = true;
}

buddy_sound_cue_t buddy_sound_tracker_update(buddy_sound_tracker_t *tracker,
                                             const buddy_state_t *state)
{
    buddy_sound_cue_t cue = BUDDY_SOUND_CUE_NONE;
    if (tracker == NULL || state == NULL) {
        return BUDDY_SOUND_CUE_NONE;
    }
    if (!tracker->initialized) {
        buddy_sound_tracker_init(tracker, state);
        return BUDDY_SOUND_CUE_NONE;
    }

    if (state->settings.sound_enabled && state->settings.sound_volume_percent != 0U &&
        state->approval_sequence > tracker->approval_sequence) {
        cue = (buddy_sound_cue_t)(cue | BUDDY_SOUND_CUE_APPROVAL);
    }
    if (state->settings.sound_enabled && state->settings.sound_volume_percent != 0U &&
        state->completion_sequence > tracker->completion_sequence) {
        cue = (buddy_sound_cue_t)(cue | BUDDY_SOUND_CUE_COMPLETE);
    }

    tracker->approval_sequence = state->approval_sequence;
    tracker->completion_sequence = state->completion_sequence;
    return cue;
}
