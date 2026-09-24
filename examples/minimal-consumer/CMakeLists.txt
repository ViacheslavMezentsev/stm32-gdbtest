cmake_minimum_required(VERSION 3.25)
project(minimal_consumer LANGUAGES C)
include(CTest)
find_package(Python3 3.11 COMPONENTS Interpreter REQUIRED)
set(STM32_GDBTEST_SOURCE_DIR "${CMAKE_CURRENT_LIST_DIR}/../.." CACHE PATH "HWTEST source checkout")
set(CUBE_F4_ROOT "$ENV{USERPROFILE}/STM32Cube/Repository/STM32Cube_FW_F4_V1.28.3" CACHE PATH "Installed CubeF4 package")
add_executable(consumer_app src/main.c src/startup.c)
set_target_properties(consumer_app PROPERTIES OUTPUT_NAME consumer-blink SUFFIX .elf)
target_include_directories(consumer_app PRIVATE
    "${CUBE_F4_ROOT}/Drivers/CMSIS/Include"
    "${CUBE_F4_ROOT}/Drivers/CMSIS/Device/ST/STM32F4xx/Include")
target_compile_definitions(consumer_app PRIVATE STM32F411xE)
target_compile_options(consumer_app PRIVATE -mcpu=cortex-m4 -mthumb -mfloat-abi=soft -Og -g3 -ffunction-sections -fdata-sections -Wall -Wextra -Werror)
set(linker "${CMAKE_CURRENT_SOURCE_DIR}/profile/consumer_FLASH.ld")
target_link_options(consumer_app PRIVATE -mcpu=cortex-m4 -mthumb -mfloat-abi=soft -nostdlib "-T${linker}" -Wl,--gc-sections)
include("${STM32_GDBTEST_SOURCE_DIR}/stm32_gdbtest/cmake/STM32GDBTest.cmake")
stm32_gdbtest_attach(consumer_app PROFILE_DIR "${CMAKE_CURRENT_SOURCE_DIR}/profile"
    MANIFEST_INPUTS "${linker}" "${CMAKE_CURRENT_SOURCE_DIR}/CMakeLists.txt"
    "${CMAKE_CURRENT_SOURCE_DIR}/cmake/arm-gcc.cmake")
add_test(NAME host.consumer_offline COMMAND "${Python3_EXECUTABLE}" -B
    "${CMAKE_CURRENT_SOURCE_DIR}/verify_offline.py" "${CMAKE_BINARY_DIR}/hwtest/session.json" "${STM32_GDBTEST_SOURCE_DIR}")
set_tests_properties(host.consumer_offline PROPERTIES LABELS host TIMEOUT 45)
