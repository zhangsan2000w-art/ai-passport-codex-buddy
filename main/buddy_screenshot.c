#include "buddy_screenshot.h"

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "driver/usb_serial_jtag.h"
#include "driver/usb_serial_jtag_vfs.h"
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#include "bsp_display.h"
#include "buddy_ui.h"

#define SCREENSHOT_COMMAND "FAP_SCREENSHOT_V1"
#define SCREENSHOT_TASK_STACK_SIZE 3072U
#define SCREENSHOT_TASK_PRIORITY 4U
#define SCREENSHOT_RX_SIZE 64U
#define SCREENSHOT_TX_BUFFER_SIZE 4096U
#define SCREENSHOT_RX_BUFFER_SIZE 256U

static const char *TAG = "buddy_capture";
static TaskHandle_t s_task;

static bool screenshot_write_all(const void *data, size_t length)
{
    const uint8_t *cursor = data;
    size_t written = 0;

    while (written < length) {
        int result = usb_serial_jtag_write_bytes(cursor + written, length - written,
                                                 pdMS_TO_TICKS(2000));
        if (result <= 0) {
            return false;
        }
        written += (size_t)result;
    }
    return true;
}

static void screenshot_send(void)
{
    uint8_t row[BUDDY_UI_SCREEN_WIDTH * 2U];
    char header[96];
    esp_log_level_t previous_level;
    bool success = true;
    uint16_t y;
    int header_length;

    if (!bsp_lvgl_lock(1000)) {
        ESP_LOGW(TAG, "screen capture could not lock the UI");
        return;
    }
    if (!buddy_ui_copy_rgb565le_row(0, row, sizeof(row))) {
        bsp_lvgl_unlock();
        ESP_LOGW(TAG, "screen capture requested before the first frame");
        return;
    }

    previous_level = esp_log_level_get("*");
    esp_log_level_set("*", ESP_LOG_NONE);
    (void)usb_serial_jtag_wait_tx_done(pdMS_TO_TICKS(2000));

    header_length = snprintf(header, sizeof(header),
                             "FAP_SCREENSHOT_V1 %u %u RGB565LE %u\n",
                             (unsigned)BUDDY_UI_SCREEN_WIDTH,
                             (unsigned)BUDDY_UI_SCREEN_HEIGHT,
                             (unsigned)(BUDDY_UI_SCREEN_WIDTH *
                                        BUDDY_UI_SCREEN_HEIGHT * 2U));
    if (header_length <= 0 || (size_t)header_length >= sizeof(header) ||
        !screenshot_write_all(header, (size_t)header_length)) {
        success = false;
    }
    for (y = 0; success && y < BUDDY_UI_SCREEN_HEIGHT; ++y) {
        if (!buddy_ui_copy_rgb565le_row(y, row, sizeof(row)) ||
            !screenshot_write_all(row, sizeof(row))) {
            success = false;
        }
    }
    (void)usb_serial_jtag_wait_tx_done(pdMS_TO_TICKS(5000));
    esp_log_level_set("*", previous_level);
    bsp_lvgl_unlock();

    if (!success) {
        ESP_LOGW(TAG, "screen capture transfer failed");
    }
}

static void screenshot_task(void *context)
{
    char line[SCREENSHOT_RX_SIZE];
    size_t used = 0;
    uint8_t input[32];

    (void)context;
    for (;;) {
        int count = usb_serial_jtag_read_bytes(input, sizeof(input),
                                               pdMS_TO_TICKS(1000));
        int index;

        if (count <= 0) {
            continue;
        }
        for (index = 0; index < count; ++index) {
            uint8_t value = input[index];

            if (value == '\r') {
                continue;
            }
            if (value == '\n') {
                line[used] = '\0';
                if (strcmp(line, SCREENSHOT_COMMAND) == 0) {
                    screenshot_send();
                }
                used = 0;
            } else if (used + 1U < sizeof(line)) {
                line[used++] = (char)value;
            } else {
                used = 0;
            }
        }
    }
}

esp_err_t buddy_screenshot_start(void)
{
    esp_err_t result = ESP_OK;

    if (s_task != NULL) {
        return ESP_OK;
    }
    if (!usb_serial_jtag_is_driver_installed()) {
        usb_serial_jtag_driver_config_t config = {
            .tx_buffer_size = SCREENSHOT_TX_BUFFER_SIZE,
            .rx_buffer_size = SCREENSHOT_RX_BUFFER_SIZE,
        };

        result = usb_serial_jtag_driver_install(&config);
        if (result != ESP_OK) {
            return result;
        }
    }
    usb_serial_jtag_vfs_use_driver();
    if (xTaskCreate(screenshot_task, "buddy_capture", SCREENSHOT_TASK_STACK_SIZE,
                    NULL, SCREENSHOT_TASK_PRIORITY, &s_task) != pdPASS) {
        s_task = NULL;
        return ESP_ERR_NO_MEM;
    }
    return ESP_OK;
}
