cmake_minimum_required(VERSION 3.16)
include($ENV{IDF_PATH}/tools/cmake/project.cmake)

# ESP-IDF configures the bootloader as a nested CMake project. Forward explicit
# tool locations so restricted shells and portable tool bundles do not have to
# expose Ninja or the cross-compiler globally through PATH.
if(CMAKE_MAKE_PROGRAM)
    idf_build_set_property(EXTRA_CMAKE_ARGS
        "-DCMAKE_MAKE_PROGRAM=${CMAKE_MAKE_PROGRAM}" APPEND)
endif()
if(CMAKE_PROGRAM_PATH)
    idf_build_set_property(EXTRA_CMAKE_ARGS
        "-DCMAKE_PROGRAM_PATH=${CMAKE_PROGRAM_PATH}" APPEND)
endif()

set(PROJECT_VER "0.1.4")
project(Codex-Buddy)
