cmake_minimum_required(VERSION 3.16)
project(buddy_host_tests C)

enable_testing()

if(NOT DEFINED ENV{IDF_PATH} OR "$ENV{IDF_PATH}" STREQUAL "")
    message(FATAL_ERROR "IDF_PATH must point to an ESP-IDF checkout")
endif()

file(TO_CMAKE_PATH "$ENV{IDF_PATH}" BUDDY_IDF_PATH)
set(BUDDY_CJSON_DIR "${BUDDY_IDF_PATH}/components/json/cJSON")
set(BUDDY_CJSON_SOURCE "${BUDDY_CJSON_DIR}/cJSON.c")

function(buddy_strict_warnings target)
    if(MSVC)
        # The host suite is assert-driven, so it must be built without NDEBUG.
        # Force UTF-8 because product strings are Simplified Chinese. Keep the
        # stricter warning-as-error policy on the GCC toolchain used by firmware.
        target_compile_options(${target} PRIVATE /W4 /utf-8)
        target_compile_definitions(${target} PRIVATE _CRT_SECURE_NO_WARNINGS)
    else()
        target_compile_options(${target} PRIVATE -Wall -Wextra -Werror)
    endif()
endfunction()

add_executable(test_buddy_state test_buddy_state.c ../main/buddy_state.c
               ../main/buddy_protocol.c ${BUDDY_CJSON_SOURCE})
target_include_directories(test_buddy_state PRIVATE ../main ${BUDDY_CJSON_DIR})
buddy_strict_warnings(test_buddy_state)
add_test(NAME buddy_state COMMAND test_buddy_state)

add_executable(test_buddy_line test_buddy_line.c ../main/buddy_line.c)
target_include_directories(test_buddy_line PRIVATE ../main)
buddy_strict_warnings(test_buddy_line)
add_test(NAME buddy_line COMMAND test_buddy_line)

add_executable(test_buddy_ble test_buddy_ble.c ../main/buddy_ble.c ../main/buddy_ble_store.c
               ../main/buddy_ble_lifecycle.c)
target_include_directories(test_buddy_ble PRIVATE test_shims ../main)
target_compile_definitions(test_buddy_ble PRIVATE BUDDY_BLE_HOST_TEST)
buddy_strict_warnings(test_buddy_ble)
add_test(NAME buddy_ble COMMAND test_buddy_ble)

add_executable(test_buddy_protocol test_buddy_protocol.c ../main/buddy_protocol.c
               ${BUDDY_CJSON_SOURCE})
target_include_directories(test_buddy_protocol PRIVATE ../main ${BUDDY_CJSON_DIR})
buddy_strict_warnings(test_buddy_protocol)
add_test(NAME buddy_protocol COMMAND test_buddy_protocol)

add_executable(test_buddy_settings test_buddy_settings.c ../main/buddy_settings.c)
target_include_directories(test_buddy_settings PRIVATE test_shims ../main)
target_compile_definitions(test_buddy_settings PRIVATE BUDDY_SETTINGS_TESTING)
buddy_strict_warnings(test_buddy_settings)
add_test(NAME buddy_settings COMMAND test_buddy_settings)

add_executable(test_buddy_character test_buddy_character.c ../main/buddy_character.c)
target_include_directories(test_buddy_character PRIVATE ../main)
buddy_strict_warnings(test_buddy_character)
add_test(NAME buddy_character COMMAND test_buddy_character)

add_executable(test_buddy_sound_logic test_buddy_sound_logic.c
               ../main/buddy_sound_logic.c ../main/buddy_state.c
               ../main/buddy_protocol.c ${BUDDY_CJSON_SOURCE})
target_include_directories(test_buddy_sound_logic PRIVATE ../main ${BUDDY_CJSON_DIR})
buddy_strict_warnings(test_buddy_sound_logic)
add_test(NAME buddy_sound_logic COMMAND test_buddy_sound_logic)

add_executable(test_buddy_app_logic test_buddy_app_logic.c ../main/buddy_app_logic.c)
target_include_directories(test_buddy_app_logic PRIVATE test_shims ../main)
buddy_strict_warnings(test_buddy_app_logic)
add_test(NAME buddy_app_logic COMMAND test_buddy_app_logic)

add_executable(test_buddy_orchestrator test_buddy_orchestrator.c
               ../main/buddy_orchestrator.c ../main/buddy_state.c
               ../main/buddy_protocol.c ${BUDDY_CJSON_SOURCE})
target_include_directories(test_buddy_orchestrator PRIVATE test_shims ../main
                           ${BUDDY_CJSON_DIR})
buddy_strict_warnings(test_buddy_orchestrator)
add_test(NAME buddy_orchestrator COMMAND test_buddy_orchestrator)

add_executable(test_buddy_i4 test_buddy_i4.c ../main/buddy_i4.c)
target_include_directories(test_buddy_i4 PRIVATE ../main)
add_test(NAME buddy_i4 COMMAND test_buddy_i4)

add_executable(test_buddy_sprite test_buddy_sprite.c ../main/buddy_sprite.c
               ../main/buddy_i4.c)
target_include_directories(test_buddy_sprite PRIVATE ../main)
buddy_strict_warnings(test_buddy_sprite)
add_test(NAME buddy_sprite COMMAND test_buddy_sprite)

add_executable(test_buddy_text_layout test_buddy_text_layout.c
               ../main/buddy_text_layout.c)
target_include_directories(test_buddy_text_layout PRIVATE ../main)
buddy_strict_warnings(test_buddy_text_layout)
add_test(NAME buddy_text_layout COMMAND test_buddy_text_layout)
