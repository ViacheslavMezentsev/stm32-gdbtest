cmake_minimum_required(VERSION 3.25)
project(hal_f030 LANGUAGES C CXX ASM)
include(CTest)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)
get_filename_component(STM32_GDBTEST_SOURCE_DIR "${CMAKE_CURRENT_SOURCE_DIR}/../.." ABSOLUTE)
if(DEFINED ENV{STM32CUBE_REPOSITORY})
    set(cube_default "$ENV{STM32CUBE_REPOSITORY}")
elseif(CMAKE_HOST_WIN32)
    set(cube_default "$ENV{USERPROFILE}/STM32Cube/Repository")
else()
    set(cube_default "/opt/STM32Cube/Repository")
endif()
set(STM32CUBE_REPOSITORY "${cube_default}" CACHE PATH "STM32Cube packages")
set(cube "${STM32CUBE_REPOSITORY}/STM32Cube_FW_F0_V1.11.6")
set(hal "${cube}/Drivers/STM32F0xx_HAL_Driver")
if(NOT EXISTS "${hal}/Src/stm32f0xx_hal.c")
    message(FATAL_ERROR "Install STM32CubeF0 V1.11.6 under STM32CUBE_REPOSITORY")
endif()
add_executable(hal_f030
    startup_stm32f030x8.s
    Core/Src/adc.c Core/Src/crc.c Core/Src/dma.c Core/Src/gpio.c
    Core/Src/main.c Core/Src/rtc.c Core/Src/tim.c
    Core/Src/stm32f0xx_hal_msp.c Core/Src/stm32f0xx_it.c
    Core/Src/system_stm32f0xx.c Core/Src/syscalls.c Core/Src/sysmem.c
    src/program.cpp src/adc_units.cpp src/platform.c)
foreach(component hal hal_adc hal_adc_ex hal_cortex hal_crc hal_dma hal_flash
        hal_flash_ex hal_gpio hal_pwr hal_pwr_ex hal_rcc hal_rcc_ex hal_rtc
        hal_rtc_ex hal_tim hal_tim_ex)
    target_sources(hal_f030 PRIVATE "${hal}/Src/stm32f0xx_${component}.c")
endforeach()
set_target_properties(hal_f030 PROPERTIES SUFFIX .elf C_STANDARD 17 CXX_STANDARD 17)
target_include_directories(hal_f030 PRIVATE Core/Inc src "${hal}/Inc"
    "${hal}/Inc/Legacy" "${cube}/Drivers/CMSIS/Include"
    "${cube}/Drivers/CMSIS/Device/ST/STM32F0xx/Include")
target_compile_definitions(hal_f030 PRIVATE STM32F030x8 USE_HAL_DRIVER)
set(arch -mcpu=cortex-m0 -mthumb -mfloat-abi=soft)
target_compile_options(hal_f030 PRIVATE ${arch} -Og -g3 -fno-lto
    -ffunction-sections -fdata-sections -Wall -Wextra
    "$<$<COMPILE_LANGUAGE:CXX>:-fno-exceptions;-fno-rtti>")
set(linker "${CMAKE_CURRENT_SOURCE_DIR}/firmware_FLASH.ld")
target_link_options(hal_f030 PRIVATE ${arch} -fno-lto --specs=nano.specs --specs=nosys.specs
    "-T${linker}" -Wl,--gc-sections "-Wl,-Map=${CMAKE_CURRENT_BINARY_DIR}/hal_f030.map")
set_property(TARGET hal_f030 APPEND PROPERTY LINK_DEPENDS "${linker}")
include("${STM32_GDBTEST_SOURCE_DIR}/stm32_gdbtest/cmake/STM32GDBTest.cmake")
stm32_gdbtest_attach(hal_f030 PROFILE_DIR "${CMAKE_CURRENT_SOURCE_DIR}/profile"
    MANIFEST_INPUTS "${linker}" "${CMAKE_CURRENT_SOURCE_DIR}/CMakeLists.txt"
    "${CMAKE_CURRENT_SOURCE_DIR}/cmake/arm-gcc.cmake")

find_package(Python3 3.11 COMPONENTS Interpreter REQUIRED)
add_test(NAME host.fixture COMMAND "${Python3_EXECUTABLE}" -B "${CMAKE_CURRENT_SOURCE_DIR}/verify_fixture.py")
set_tests_properties(host.fixture PROPERTIES LABELS host TIMEOUT 30)
