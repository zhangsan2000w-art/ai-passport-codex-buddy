#include "buddy_sprite.h"

#include <stddef.h>

/* The 16-colour framebuffer palette is shared with buddy_ui.c. Indices 10-14
 * are reserved for BSOD so no decoded raster asset is needed in RAM. */
enum {
    PIX_BG = 0,
    PIX_INK = 1,
    PIX_DIM = 2,
    PIX_LINE = 3,
    PIX_ORANGE = 4,
    PIX_RED = 5,
    PIX_GREEN = 6,
    PIX_YELLOW = 7,
    PIX_BLUE = 8,
    PIX_WHITE = 9,
    PIX_SCREEN = 10,
    PIX_SCREEN_DARK = 11,
    PIX_CASE_SHADE = 12,
    PIX_GLOW = 13,
    PIX_BLUSH = 14,
    PIX_PANEL = 15,
};

static void rect(buddy_i4_surface_t *surface, const buddy_i4_clip_t *clip,
                 int x, int y, int width, int height, uint8_t colour)
{
    buddy_i4_fill_rect(surface, clip, x, y, width, height, colour);
}

static void rounded_rect(buddy_i4_surface_t *surface, const buddy_i4_clip_t *clip,
                         int x, int y, int width, int height, uint8_t colour)
{
    if (width < 5 || height < 5) {
        rect(surface, clip, x, y, width, height, colour);
        return;
    }
    rect(surface, clip, x + 2, y, width - 4, height, colour);
    rect(surface, clip, x, y + 2, width, height - 4, colour);
    rect(surface, clip, x + 1, y + 1, width - 2, height - 2, colour);
}

static void heart(buddy_i4_surface_t *surface, const buddy_i4_clip_t *clip,
                  int x, int y, uint8_t colour)
{
    rect(surface, clip, x + 1, y, 3, 2, colour);
    rect(surface, clip, x + 5, y, 3, 2, colour);
    rect(surface, clip, x, y + 2, 9, 3, colour);
    rect(surface, clip, x + 2, y + 5, 5, 2, colour);
    rect(surface, clip, x + 4, y + 7, 1, 1, colour);
}

static void warning_mark(buddy_i4_surface_t *surface, const buddy_i4_clip_t *clip,
                         int x, int y, uint8_t colour)
{
    buddy_i4_line(surface, clip, x + 3, y, x, y + 5, colour);
    buddy_i4_line(surface, clip, x + 3, y, x + 6, y + 5, colour);
    buddy_i4_line(surface, clip, x, y + 5, x + 6, y + 5, colour);
    rect(surface, clip, x + 3, y + 2, 1, 2, colour);
}

static void x_eye(buddy_i4_surface_t *surface, const buddy_i4_clip_t *clip,
                  int x, int y)
{
    buddy_i4_line(surface, clip, x, y, x + 4, y + 4, PIX_PANEL);
    buddy_i4_line(surface, clip, x + 4, y, x, y + 4, PIX_PANEL);
}

static void draw_face(buddy_i4_surface_t *surface, const buddy_i4_clip_t *clip,
                      uint8_t state, uint32_t tick, int x, int y)
{
    int glance = state == 2 ? (int)(tick % 3U) - 1 : 0;

    warning_mark(surface, clip, x + 2, y + 2, PIX_WHITE);
    if (state == 5) {
        x_eye(surface, clip, x + 10, y + 8);
        x_eye(surface, clip, x + 25, y + 8);
        rect(surface, clip, x + 17, y + 16, 6, 1, PIX_PANEL);
        rect(surface, clip, x + 16, y + 17, 1, 2, PIX_PANEL);
        rect(surface, clip, x + 23, y + 17, 1, 2, PIX_PANEL);
        return;
    }
    if (state == 6) {
        heart(surface, clip, x + 15, y + 7, PIX_BLUSH);
        return;
    }
    if (state == 0) {
        rect(surface, clip, x + 10, y + 11, 6, 1, PIX_PANEL);
        rect(surface, clip, x + 25, y + 11, 6, 1, PIX_PANEL);
    } else if (state == 4) {
        buddy_i4_line(surface, clip, x + 10, y + 12, x + 13, y + 9, PIX_PANEL);
        buddy_i4_line(surface, clip, x + 13, y + 9, x + 16, y + 12, PIX_PANEL);
        buddy_i4_line(surface, clip, x + 25, y + 12, x + 28, y + 9, PIX_PANEL);
        buddy_i4_line(surface, clip, x + 28, y + 9, x + 31, y + 12, PIX_PANEL);
    } else if (state == 3) {
        rect(surface, clip, x + 13, y + 7, 2, 7, PIX_PANEL);
        rect(surface, clip, x + 27, y + 7, 2, 7, PIX_PANEL);
        rect(surface, clip, x + 13, y + 16, 2, 2, PIX_PANEL);
        rect(surface, clip, x + 27, y + 16, 2, 2, PIX_PANEL);
    } else {
        rect(surface, clip, x + 12 + glance, y + 8, 3, 7, PIX_PANEL);
        rect(surface, clip, x + 27 + glance, y + 8, 3, 7, PIX_PANEL);
    }

    if (state != 3) {
        rect(surface, clip, x + 7, y + 15, 5, 3, PIX_BLUSH);
        rect(surface, clip, x + 30, y + 15, 5, 3, PIX_BLUSH);
        if (state == 4) {
            rect(surface, clip, x + 18, y + 16, 6, 1, PIX_PANEL);
            rect(surface, clip, x + 19, y + 17, 4, 1, PIX_PANEL);
        } else {
            rect(surface, clip, x + 19, y + 16, 3, 1, PIX_PANEL);
        }
    }
}

static void draw_arm(buddy_i4_surface_t *surface, const buddy_i4_clip_t *clip,
                     int x, int y, bool raised, bool left)
{
    if (raised) {
        int hand_x = left ? x : x + 5;
        buddy_i4_line(surface, clip, x + (left ? 7 : 1), y + 8,
                      hand_x, y, PIX_PANEL);
        rect(surface, clip, hand_x - 1, y, 4, 4, PIX_PANEL);
        rect(surface, clip, hand_x, y, 3, 3, PIX_INK);
    } else {
        rounded_rect(surface, clip, x, y, 8, 7, PIX_PANEL);
        rounded_rect(surface, clip, x + 1, y + 1, 6, 5, PIX_INK);
    }
}

const char *buddy_sprite_name(uint8_t species)
{
    (void)species;
    return "BSOD";
}

bool buddy_sprite_bounds(uint8_t species, uint8_t state, uint32_t tick,
                         buddy_sprite_bounds_t *bounds)
{
    (void)species;
    (void)state;
    (void)tick;
    if (bounds == NULL) return false;
    bounds->x = 2;
    bounds->y = 0;
    bounds->w = 60;
    bounds->h = 64;
    return true;
}

void buddy_sprite_render(buddy_i4_surface_t *surface, const buddy_i4_clip_t *clip,
                         uint8_t species, uint8_t state, uint32_t tick,
                         int origin_x, int origin_y)
{
    int bounce;
    int x;
    int y;
    bool raised;
    uint8_t screen_colour;

    (void)species;
    if (surface == NULL) return;
    state %= BUDDY_SPRITE_STATE_COUNT;
    bounce = state == 4 && tick % 4U < 2U ? -2 : 0;
    x = origin_x + 2;
    y = origin_y + bounce;
    raised = state == 4 || state == 5;
    screen_colour = state == 5 ? PIX_RED : (state == 0 ? PIX_SCREEN_DARK : PIX_SCREEN);

    /* Bent aerial with the glowing blue fault indicator. */
    buddy_i4_line(surface, clip, x + 31, y + 9, x + 36, y + 2, PIX_PANEL);
    buddy_i4_line(surface, clip, x + 36, y + 2, x + 41, y + 4, PIX_PANEL);
    rounded_rect(surface, clip, x + 39, y + 1, 7, 7, PIX_GLOW);
    rect(surface, clip, x + 41, y + 2, 3, 2, PIX_WHITE);

    /* CRT-like head: charcoal outline, warm case, cool shadow, blue screen. */
    rounded_rect(surface, clip, x + 4, y + 8, 52, 35, PIX_PANEL);
    rounded_rect(surface, clip, x + 6, y + 10, 48, 31, PIX_INK);
    rect(surface, clip, x + 8, y + 33, 44, 6, PIX_CASE_SHADE);
    rounded_rect(surface, clip, x + 10, y + 12, 40, 25, PIX_PANEL);
    rounded_rect(surface, clip, x + 12, y + 14, 36, 21, screen_colour);
    rect(surface, clip, x + 14, y + 15, 31, 2,
         state == 5 ? PIX_ORANGE : PIX_GLOW);
    draw_face(surface, clip, state, tick, x + 9, y + 13);

    /* Small console body and gamepad-shaped chest screen. */
    draw_arm(surface, clip, x + 1, y + 43, raised, true);
    draw_arm(surface, clip, x + 51, y + 43, raised, false);
    rounded_rect(surface, clip, x + 15, y + 40, 30, 18, PIX_PANEL);
    rounded_rect(surface, clip, x + 17, y + 42, 26, 14, PIX_INK);
    rect(surface, clip, x + 19, y + 51, 22, 4, PIX_CASE_SHADE);
    rounded_rect(surface, clip, x + 23, y + 44, 14, 9, PIX_PANEL);
    rounded_rect(surface, clip, x + 25, y + 45, 10, 7, PIX_SCREEN_DARK);
    rect(surface, clip, x + 27, y + 47, 2, 2, PIX_GLOW);
    rect(surface, clip, x + 31, y + 47, 2, 2, PIX_GLOW);
    rect(surface, clip, x + 29, y + 49, 2, 2, PIX_GLOW);

    rounded_rect(surface, clip, x + 18, y + 55, 10, 8, PIX_PANEL);
    rounded_rect(surface, clip, x + 20, y + 55, 7, 6, PIX_INK);
    rounded_rect(surface, clip, x + 33, y + 55, 10, 8, PIX_PANEL);
    rounded_rect(surface, clip, x + 34, y + 55, 7, 6, PIX_INK);

    if (state == 2) {
        int phase = (int)(tick % 3U);
        rect(surface, clip, x + 25 + phase * 4, y + 53, 2, 2, PIX_GLOW);
    } else if (state == 4) {
        rect(surface, clip, origin_x + 1, origin_y + 4, 3, 3, PIX_YELLOW);
        rect(surface, clip, origin_x + 59, origin_y + 14, 3, 3, PIX_GREEN);
        rect(surface, clip, origin_x + 4, origin_y + 55, 3, 3, PIX_BLUSH);
    } else if (state == 6) {
        heart(surface, clip, origin_x + 50, origin_y + 4, PIX_BLUSH);
    }
}
