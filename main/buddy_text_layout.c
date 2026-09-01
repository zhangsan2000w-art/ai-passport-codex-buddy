#include "buddy_text_layout.h"

#include <stdbool.h>
#include <string.h>

static bool is_utf8_continuation(unsigned char value)
{
    return (value & 0xc0U) == 0x80U;
}

static size_t utf8_character_length(const char *text)
{
    unsigned char first = (unsigned char)text[0];
    size_t expected;
    size_t i;

    if (first < 0x80U) return 1;
    if ((first & 0xe0U) == 0xc0U) expected = 2;
    else if ((first & 0xf0U) == 0xe0U) expected = 3;
    else if ((first & 0xf8U) == 0xf0U) expected = 4;
    else return 1;

    for (i = 1; i < expected; ++i) {
        if (text[i] == '\0' || !is_utf8_continuation((unsigned char)text[i])) return 1;
    }
    return expected;
}

static size_t previous_utf8_boundary(const char *text, size_t length)
{
    if (length == 0) return 0;
    --length;
    while (length > 0 && is_utf8_continuation((unsigned char)text[length])) --length;
    return length;
}

static bool contains_multibyte(const char *text, size_t length)
{
    size_t i;
    for (i = 0; i < length; ++i) {
        if ((unsigned char)text[i] >= 0x80U) return true;
    }
    return false;
}

static void append(char *output, size_t size, size_t *used, const char *text, size_t length)
{
    size_t room = size > *used ? size - *used - 1U : 0;
    if (length > room) {
        length = room;
        while (length > 0 && is_utf8_continuation((unsigned char)text[length])) --length;
    }
    if (length) memcpy(output + *used, text, length);
    *used += length;
    if (size) output[*used < size ? *used : size - 1U] = '\0';
}

buddy_text_result_t buddy_text_wrap(const char *input, char *output, size_t output_size,
                                    unsigned max_width, unsigned max_lines,
                                    buddy_text_measure_fn measure, void *context)
{
    buddy_text_result_t result = {0};
    const char *cursor = input != NULL ? input : "";
    size_t used = 0;
    if (output_size) output[0] = '\0';
    if (!measure || max_width == 0 || max_lines == 0) return result;
    while (*cursor && result.lines < max_lines) {
        const char *line = cursor;
        const char *last_space = NULL;
        const char *end = cursor;
        while (*end && *end != '\n') {
            size_t character_length = utf8_character_length(end);
            size_t candidate_length = (size_t)(end - line) + character_length;
            if (measure(line, candidate_length, context) > max_width) break;
            if (character_length == 1 && *end == ' ') last_space = end;
            end += character_length;
        }
        if (*end == ' ') last_space = end;
        if (*end == '\n') {
            append(output, output_size, &used, line, (size_t)(end - line));
            cursor = end + 1;
        } else if (*end == '\0') {
            append(output, output_size, &used, line, (size_t)(end - line));
            cursor = end;
        } else if (last_space != NULL) {
            append(output, output_size, &used, line, (size_t)(last_space - line));
            cursor = last_space + 1;
        } else if (end > line && contains_multibyte(line, (size_t)(end - line))) {
            /* Chinese text normally has no spaces. Wrap it at a complete UTF-8
             * character instead of treating the whole sentence as one long word. */
            append(output, output_size, &used, line, (size_t)(end - line));
            cursor = end;
        } else {
            size_t fit = (size_t)(end - line);
            unsigned ellipsis_width = measure("...", 3, context);
            while (fit > 0 && measure(line, fit, context) + ellipsis_width > max_width)
                fit = previous_utf8_boundary(line, fit);
            append(output, output_size, &used, line, fit);
            append(output, output_size, &used, "...", 3);
            while (*end && *end != ' ' && *end != '\n') end += utf8_character_length(end);
            cursor = *end ? end + 1 : end;
            result.truncated = true;
        }
        ++result.lines;
        if (*cursor && result.lines < max_lines) append(output, output_size, &used, "\n", 1);
    }
    if (*cursor) {
        char *last_line = strrchr(output, '\n');
        size_t prefix;
        size_t length;
        last_line = last_line != NULL ? last_line + 1 : output;
        prefix = (size_t)(last_line - output);
        length = strlen(last_line);
        while (length && last_line[length - 1] == ' ') last_line[--length] = '\0';
        while (length && measure(last_line, length, context) + measure("...", 3, context) > max_width)
            length = previous_utf8_boundary(last_line, length);
        used = prefix + length;
        output[used] = '\0';
        append(output, output_size, &used, "...", 3);
        result.truncated = true;
    }
    return result;
}

buddy_overlay_kind_t buddy_overlay_select(bool confirmation, bool pairing,
                                          bool approval, bool menu)
{
    if (confirmation) return BUDDY_OVERLAY_CONFIRMATION;
    if (pairing) return BUDDY_OVERLAY_PAIRING;
    if (approval) return BUDDY_OVERLAY_APPROVAL;
    if (menu) return BUDDY_OVERLAY_MENU;
    return BUDDY_OVERLAY_NONE;
}
