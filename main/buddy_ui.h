#pragma once

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#include "buddy_types.h"

/* Every entry point requires the caller to hold bsp_lvgl_lock(). */
void buddy_ui_init(void);
void buddy_ui_render(const buddy_ui_snapshot_t *snapshot);
void buddy_ui_show_passkey(uint32_t passkey);
void buddy_ui_tick(uint64_t elapsed_ms);
void buddy_ui_scroll(int delta);

#define BUDDY_UI_SCREEN_WIDTH 240U
#define BUDDY_UI_SCREEN_HEIGHT 320U

/* Copy one rendered row as little-endian RGB565. The caller must hold
 * bsp_lvgl_lock(); this is used by the observational publisher screenshot
 * protocol and never changes the current page or settings. */
bool buddy_ui_copy_rgb565le_row(uint16_t y, uint8_t *output, size_t output_size);
