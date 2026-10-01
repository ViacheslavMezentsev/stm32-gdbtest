cmake_minimum_required(VERSION 3.25)
project(rc3_api_experiments LANGUAGES C)
include(CTest)
find_package(Python3 3.11 COMPONENTS Interpreter REQUIRED)
get_filename_component(MODULE "${CMAKE_CURRENT_SOURCE_DIR}/../.." ABSOLUTE)
add_executable(api_firmware src/startup.c src/app.c src/processing.c)
set_target_properties(api_firmware PROPERTIES SUFFIX .elf)
set(arch -mcpu=cortex-m4 -mthumb -mfloat-abi=soft)
target_compile_options(api_firmware PRIVATE ${arch} -std=c11 -Og -g3 -fno-lto
    -ffunction-sections -fdata-sections -Wall -Wextra -Werror)
target_link_options(api_firmware PRIVATE ${arch} -fno-lto -nostdlib
    "-T${CMAKE_CURRENT_SOURCE_DIR}/firmware_FLASH.ld" -Wl,--gc-sections)
target_link_libraries(api_firmware PRIVATE gcc)
include("${MODULE}/stm32_gdbtest/cmake/STM32GDBTest.cmake")
stm32_gdbtest_attach(api_firmware PROFILE_DIR "${CMAKE_CURRENT_SOURCE_DIR}/profile"
    MANIFEST_INPUTS "${CMAKE_CURRENT_SOURCE_DIR}/firmware_FLASH.ld"
    "${CMAKE_CURRENT_SOURCE_DIR}/CMakeLists.txt" "${MODULE}/tests/firmware/cmake/arm-gcc.cmake")
add_test(NAME host.research COMMAND "${Python3_EXECUTABLE}" -B -m unittest discover
    -s "${CMAKE_CURRENT_SOURCE_DIR}/host" -v)
set_tests_properties(host.research PROPERTIES LABELS host
    WORKING_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}")
