#include <assert.h>
#include <stdio.h>
#include <string.h>

#include "buddy_sound_logic.h"

static void test_distinct_cues_only_fire_on_new_transitions(void)
{
    buddy_settings_snapshot_t settings = {
        .sound_enabled = true,
        .sound_volume_percent = 50,
    };
    buddy_state_t state;
    buddy_sound_tracker_t tracker;
    buddy_sound_cue_t cue;

    buddy_state_init(&state, &settings);
    buddy_sound_tracker_init(&tracker, &state);
    assert(buddy_sound_tracker_update(&tracker, &state) == BUDDY_SOUND_CUE_NONE);

    ++state.approval_sequence;
    cue = buddy_sound_tracker_update(&tracker, &state);
    assert((cue & BUDDY_SOUND_CUE_APPROVAL) != 0);
    assert((cue & BUDDY_SOUND_CUE_COMPLETE) == 0);
    assert(buddy_sound_tracker_update(&tracker, &state) == BUDDY_SOUND_CUE_NONE);

    ++state.completion_sequence;
    cue = buddy_sound_tracker_update(&tracker, &state);
    assert((cue & BUDDY_SOUND_CUE_COMPLETE) != 0);
    assert((cue & BUDDY_SOUND_CUE_APPROVAL) == 0);
    assert(buddy_sound_tracker_update(&tracker, &state) == BUDDY_SOUND_CUE_NONE);
}

static void test_muted_transitions_are_not_replayed_when_enabled(void)
{
    buddy_settings_snapshot_t settings = {
        .sound_enabled = false,
        .sound_volume_percent = 0,
    };
    buddy_state_t state;
    buddy_sound_tracker_t tracker;

    buddy_state_init(&state, &settings);
    buddy_sound_tracker_init(&tracker, &state);
    ++state.approval_sequence;
    ++state.completion_sequence;
    assert(buddy_sound_tracker_update(&tracker, &state) == BUDDY_SOUND_CUE_NONE);

    state.settings.sound_enabled = true;
    state.settings.sound_volume_percent = 50;
    assert(buddy_sound_tracker_update(&tracker, &state) == BUDDY_SOUND_CUE_NONE);
}

int main(void)
{
    test_distinct_cues_only_fire_on_new_transitions();
    test_muted_transitions_are_not_replayed_when_enabled();
    puts("buddy sound logic tests passed");
    return 0;
}
