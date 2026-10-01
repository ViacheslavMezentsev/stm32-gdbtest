# CI firmware for stm32-gdbtest: one CMSIS-only project per MCU profile, no stm32-cmake-yml.
cmake_minimum_required(VERSION 3.25)
project(gdbtest_ci_firmware LANGUAGES C)
include(CTest)
find_package(Python3 3.11 COMPONENTS Interpreter REQUIRED)

set(CI_PROFILE "f411ce" CACHE STRING "CI profile: f030r8, f103c8 or f411ce")
set_property(CACHE CI_PROFILE PROPERTY STRINGS f030r8 f103c8 f411ce)
get_filename_component(STM32_GDBTEST_SOURCE_DIR "${CMAKE_CURRENT_LIST_DIR}/../.." ABSOLUTE)

if(DEFINED ENV{STM32CUBE_REPOSITORY})
    set(cube_repository_default "$ENV{STM32CUBE_REPOSITORY}")
elseif(CMAKE_HOST_WIN32)
    set(cube_repository_default "$ENV{USERPROFILE}/STM32Cube/Repository")
else()
    set(cube_repository_default "/opt/STM32Cube/Repository")
endif()
set(STM32CUBE_REPOSITORY "${cube_repository_default}" CACHE PATH "Directory with STM32Cube_FW_* packages")

if(CI_PROFILE STREQUAL "f030r8")
    set(cpu cortex-m0)
    set(device STM32F030x8)
    set(cube STM32Cube_FW_F0_V1.11.6)
    set(family STM32F0xx)
elseif(CI_PROFILE STREQUAL "f103c8")
    set(cpu cortex-m3)
    set(device STM32F103xB)
    set(cube STM32Cube_FW_F1_V1.8.7)
    set(family STM32F1xx)
elseif(CI_PROFILE STREQUAL "f411ce")
    set(cpu cortex-m4)
    set(device STM32F411xE)
    set(cube STM32Cube_FW_F4_V1.28.3)
    set(family STM32F4xx)
else()
    message(FATAL_ERROR "Unknown CI_PROFILE: ${CI_PROFILE}")
endif()

set(profile_dir "${CMAKE_CURRENT_SOURCE_DIR}/profiles/${CI_PROFILE}")
set(cube_root "${STM32CUBE_REPOSITORY}/${cube}")
if(NOT EXISTS "${cube_root}/Drivers/CMSIS/Device/ST/${family}/Include")
    message(FATAL_ERROR "CMSIS for ${family} not found in ${cube_root}")
endif()

add_executable(ci_firmware src/startup.c src/app.c src/board.c)
if(CI_PROFILE STREQUAL "f030r8")
    target_sources(ci_firmware PRIVATE src/adc_f030.c src/adc_units.c src/rtc_f030.c)
    # Cortex-M0 needs compiler runtime helpers for 32/64-bit integer division.
    target_link_libraries(ci_firmware PRIVATE gcc)
elseif(CI_PROFILE STREQUAL "f103c8")
    target_sources(ci_firmware PRIVATE src/adc_f103.c src/adc_units.c src/rtc_f103.c)
    target_link_libraries(ci_firmware PRIVATE gcc)
endif()
set_target_properties(ci_firmware PROPERTIES OUTPUT_NAME "ci-${CI_PROFILE}" SUFFIX .elf)
target_include_directories(ci_firmware PRIVATE src
    "${cube_root}/Drivers/CMSIS/Include"
    "${cube_root}/Drivers/CMSIS/Device/ST/${family}/Include")
target_compile_definitions(ci_firmware PRIVATE ${device})
set(arch_flags -mcpu=${cpu} -mthumb -mfloat-abi=soft)
target_compile_options(ci_firmware PRIVATE ${arch_flags} -std=c11 -Og -g3
    -ffunction-sections -fdata-sections -Wall -Wextra -Werror)
set(linker "${profile_dir}/firmware_FLASH.ld")
target_link_options(ci_firmware PRIVATE ${arch_flags} -nostdlib "-T${linker}" -Wl,--gc-sections)

include("${STM32_GDBTEST_SOURCE_DIR}/stm32_gdbtest/cmake/STM32GDBTest.cmake")
stm32_gdbtest_attach(ci_firmware PROFILE_DIR "${profile_dir}"
    MANIFEST_INPUTS "${linker}" "${CMAKE_CURRENT_SOURCE_DIR}/CMakeLists.txt"
    "${CMAKE_CURRENT_SOURCE_DIR}/cmake/arm-gcc.cmake")
