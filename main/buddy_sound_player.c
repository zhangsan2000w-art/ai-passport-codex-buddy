#include "buddy_sound_player.h"

#include <stddef.h>
#include <stdint.h>
#include <string.h>

#include "freertos/FreeRTOS.h"
#include "freertos/queue.h"
#include "freertos/task.h"

#include "esp_log.h"

#include "bsp_audio.h"

#define BUDDY_SOUND_SAMPLE_RATE 16000U
#define BUDDY_SOUND_CHUNK_SAMPLES 160U
#define BUDDY_SOUND_TASK_STACK 4096U
#define BUDDY_SOUND_TASK_PRIORITY 4U
#define BUDDY_SOUND_QUEUE_DEPTH 8U
#define BUDDY_SOUND_QUEUE_WAIT_MS 100U
#define BUDDY_SOUND_WARMUP_MS 30U
#define BUDDY_SOUND_DRAIN_MS 80U
#define BUDDY_SOUND_AMPLITUDE 9000
#define BUDDY_SOUND_FADE_SAMPLES 80U

typedef struct {
    uint16_t frequency_hz;
    uint16_t duration_ms;
} buddy_sound_note_t;

typedef struct {
    buddy_sound_cue_t cue;
    uint8_t volume_percent;
} buddy_sound_request_t;

static const char *const TAG = "buddy_sound";
static QueueHandle_t s_sound_queue;

static const int16_t s_sine[32] = {
    0, 6393, 12539, 18204, 23170, 27245, 30273, 32137,
    32767, 32137, 30273, 27245, 23170, 18204, 12539, 6393,
    0, -6393, -12539, -18204, -23170, -27245, -30273, -32137,
    -32767, -32137, -30273, -27245, -23170, -18204, -12539, -6393,
};

static const buddy_sound_note_t s_approval_notes[] = {
    {880, 85}, {0, 55}, {660, 145},
};

static const buddy_sound_note_t s_complete_notes[] = {
    {523, 70}, {659, 80}, {784, 170},
};

static esp_err_t buddy_sound_write_note(const buddy_sound_note_t *note)
{
    int16_t samples[BUDDY_SOUND_CHUNK_SAMPLES];
    uint32_t total_samples =
        ((uint32_t)note->duration_ms * BUDDY_SOUND_SAMPLE_RATE) / 1000U;
    uint32_t written = 0;
    uint32_t phase = 0;
    uint32_t phase_step = note->frequency_hz == 0U
                              ? 0U
                              : (uint32_t)(((uint64_t)note->frequency_hz << 32) /
                                           BUDDY_SOUND_SAMPLE_RATE);

    while (written < total_samples) {
        uint32_t count = total_samples - written;
        uint32_t index;

        if (count > BUDDY_SOUND_CHUNK_SAMPLES) {
            count = BUDDY_SOUND_CHUNK_SAMPLES;
        }
        for (index = 0; index < count; ++index) {
            uint32_t absolute = written + index;
            uint32_t remaining = total_samples - absolute;
            uint32_t gain = 256U;
            int32_t value = 0;

            if (absolute < BUDDY_SOUND_FADE_SAMPLES) {
                gain = (absolute * 256U) / BUDDY_SOUND_FADE_SAMPLES;
            }
            if (remaining < BUDDY_SOUND_FADE_SAMPLES) {
                uint32_t fade_out = (remaining * 256U) / BUDDY_SOUND_FADE_SAMPLES;
                if (fade_out < gain) {
                    gain = fade_out;
                }
            }
            if (note->frequency_hz != 0U) {
                value = ((int32_t)s_sine[phase >> 27] * BUDDY_SOUND_AMPLITUDE) / 32767;
                value = (value * (int32_t)gain) / 256;
                phase += phase_step;
            }
            samples[index] = (int16_t)value;
        }
        if (bsp_audio_write(samples, count * sizeof(samples[0])) != ESP_OK) {
            return ESP_FAIL;
        }
        written += count;
    }
    return ESP_OK;
}

static esp_err_t buddy_sound_play_notes(const buddy_sound_note_t *notes, size_t count,
                                        uint8_t volume_percent)
{
    size_t index;
    esp_err_t err;

    err = bsp_audio_init();
    if (err != ESP_OK) {
        return err;
    }
    err = bsp_audio_set_format(BUDDY_SOUND_SAMPLE_RATE, 16, 1);
    if (err != ESP_OK) {
        return err;
    }
    err = bsp_audio_set_volume(volume_percent);
    if (err != ESP_OK) {
        (void)bsp_audio_close();
        return err;
    }
    vTaskDelay(pdMS_TO_TICKS(BUDDY_SOUND_WARMUP_MS));
    for (index = 0; index < count; ++index) {
        err = buddy_sound_write_note(&notes[index]);
        if (err != ESP_OK) {
            break;
        }
    }
    vTaskDelay(pdMS_TO_TICKS(BUDDY_SOUND_DRAIN_MS));
    if (bsp_audio_set_volume(0) != ESP_OK && err == ESP_OK) {
        err = ESP_FAIL;
    }
    if (bsp_audio_close() != ESP_OK && err == ESP_OK) {
        err = ESP_FAIL;
    }
    return err;
}

static void buddy_sound_task(void *context)
{
    buddy_sound_request_t request;

    (void)context;
    for (;;) {
        if (xQueueReceive(s_sound_queue, &request, portMAX_DELAY) != pdTRUE) {
            continue;
        }
        if (request.cue == BUDDY_SOUND_CUE_APPROVAL) {
            if (buddy_sound_play_notes(
                    s_approval_notes,
                    sizeof(s_approval_notes) / sizeof(s_approval_notes[0]),
                    request.volume_percent) != ESP_OK) {
                ESP_LOGW(TAG, "approval cue failed");
            }
        } else if (request.cue == BUDDY_SOUND_CUE_COMPLETE) {
            if (buddy_sound_play_notes(
                    s_complete_notes,
                    sizeof(s_complete_notes) / sizeof(s_complete_notes[0]),
                    request.volume_percent) != ESP_OK) {
                ESP_LOGW(TAG, "completion cue failed");
            }
        }
    }
}

esp_err_t buddy_sound_player_init(void)
{
    if (s_sound_queue != NULL) {
        return ESP_OK;
    }
    s_sound_queue = xQueueCreate(BUDDY_SOUND_QUEUE_DEPTH, sizeof(buddy_sound_request_t));
    if (s_sound_queue == NULL) {
        return ESP_ERR_NO_MEM;
    }
    if (xTaskCreate(buddy_sound_task, "buddy_sound", BUDDY_SOUND_TASK_STACK, NULL,
                    BUDDY_SOUND_TASK_PRIORITY, NULL) != pdPASS) {
        vQueueDelete(s_sound_queue);
        s_sound_queue = NULL;
        return ESP_ERR_NO_MEM;
    }
    return ESP_OK;
}

bool buddy_sound_player_enqueue(buddy_sound_cue_t cue, uint8_t volume_percent)
{
    buddy_sound_request_t request = {
        .cue = cue,
        .volume_percent = volume_percent,
    };

    if (s_sound_queue == NULL || cue == BUDDY_SOUND_CUE_NONE ||
        volume_percent == 0U || volume_percent > 100U) {
        return false;
    }
    if (xQueueSend(s_sound_queue, &request,
                   pdMS_TO_TICKS(BUDDY_SOUND_QUEUE_WAIT_MS)) != pdTRUE) {
        ESP_LOGW(TAG, "sound queue full; cue dropped");
        return false;
    }
    return true;
}
