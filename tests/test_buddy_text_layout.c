#include <assert.h>
#include <string.h>

#include "buddy_text_layout.h"

static unsigned width(const char *text, size_t length, void *context)
{
    (void)text; (void)context;
    return (unsigned)length;
}

static unsigned utf8_width(const char *text, size_t length, void *context)
{
    unsigned result = 0;
    size_t i = 0;
    (void)context;
    while (i < length) {
        unsigned char value = (unsigned char)text[i];
        if (value < 0x80U) {
            ++result;
            ++i;
        } else {
            result += 2;
            i += value < 0xe0U ? 2U : value < 0xf0U ? 3U : 4U;
        }
    }
    return result;
}

int main(void)
{
    char output[64];
    buddy_text_result_t result = buddy_text_wrap("ONE TWO THREE FOUR", output,
                                                 sizeof(output), 7, 2, width, NULL);
    assert(strcmp(output, "ONE TWO\nTHRE...") == 0);
    assert(result.lines == 2 && result.truncated);
    result = buddy_text_wrap("SUPERCALIFRAGILISTIC", output, sizeof(output), 8, 1, width, NULL);
    assert(strcmp(output, "SUPER...") == 0 && result.truncated);
    result = buddy_text_wrap("任务完成", output, sizeof(output), 4, 2, utf8_width, NULL);
    assert(strcmp(output, "任务\n完成") == 0);
    assert(result.lines == 2 && !result.truncated);
    assert(BUDDY_UI_STATUS_Y == 0 && BUDDY_UI_STATUS_H == 26);
    assert(BUDDY_UI_STAGE_Y == 26 && BUDDY_UI_STAGE_H == 132);
    assert(BUDDY_UI_INFO_Y == 158 && BUDDY_UI_INFO_H == 138);
    assert(BUDDY_UI_ACTION_Y == 296 && BUDDY_UI_ACTION_H == 24);
    assert(utf8_width(BUDDY_ACTION_HOME, strlen(BUDDY_ACTION_HOME), NULL) * 8U <= 224U);
    assert(utf8_width(BUDDY_ACTION_PET, strlen(BUDDY_ACTION_PET), NULL) * 8U <= 224U);
    assert(utf8_width(BUDDY_ACTION_INFO, strlen(BUDDY_ACTION_INFO), NULL) * 8U <= 224U);
    assert(utf8_width(BUDDY_ACTION_SETTINGS, strlen(BUDDY_ACTION_SETTINGS), NULL) * 8U <= 224U);
    assert(utf8_width(BUDDY_ACTION_CONFIRM, strlen(BUDDY_ACTION_CONFIRM), NULL) * 8U <= 204U);
    assert(utf8_width(BUDDY_ACTION_APPROVAL, strlen(BUDDY_ACTION_APPROVAL), NULL) * 8U <= 204U);
    assert(buddy_overlay_select(true, true, true, true) == BUDDY_OVERLAY_CONFIRMATION);
    assert(buddy_overlay_select(false, true, true, true) == BUDDY_OVERLAY_PAIRING);
    assert(buddy_overlay_select(false, false, true, true) == BUDDY_OVERLAY_APPROVAL);
    assert(buddy_overlay_select(false, false, false, true) == BUDDY_OVERLAY_MENU);
    return 0;
}
