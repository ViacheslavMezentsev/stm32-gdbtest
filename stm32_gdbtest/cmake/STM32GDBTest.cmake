include_guard(GLOBAL)

function(stm32_gdbtest_register id timeout labels)
    add_test(NAME hw.${id}
        COMMAND "${Python3_EXECUTABLE}" "${STM32_GDBTEST_MODULE_ROOT}/stm32_gdbtest/cli.py" run
            --session "${STM32_GDBTEST_SESSION}" --test "${id}")
    # GDB deadline plus preparation, server startup, recovery and process cleanup.
    math(EXPR outer_timeout "${timeout} + 90")
    set_tests_properties(hw.${id} PROPERTIES TIMEOUT ${outer_timeout}
        LABELS "hw;${labels}" RESOURCE_LOCK stm32_swd)
endfunction()

function(stm32_gdbtest_attach target)
    cmake_parse_arguments(HW "SELF_TESTS" "PROFILE_DIR" "MANIFEST_INPUTS" ${ARGN})
    if(HW_UNPARSED_ARGUMENTS)
        message(FATAL_ERROR "Unknown stm32_gdbtest_attach arguments: ${HW_UNPARSED_ARGUMENTS}")
    endif()
    if(NOT HW_PROFILE_DIR OR NOT EXISTS "${HW_PROFILE_DIR}/target.toml")
        message(FATAL_ERROR "stm32_gdbtest_attach requires PROFILE_DIR with target.toml")
    endif()
    find_package(Python3 3.11 COMPONENTS Interpreter REQUIRED)
    get_filename_component(STM32_GDBTEST_MODULE_ROOT "${CMAKE_CURRENT_FUNCTION_LIST_DIR}/../.." ABSOLUTE)
    set(STM32_GDBTEST_ROOT "${PROJECT_SOURCE_DIR}")
    set(STM32_GDBTEST_TESTS "${HW_PROFILE_DIR}/Tests/board")
    set(STM32_GDBTEST_PROFILE "${HW_PROFILE_DIR}/target.toml")
    set(STM32_GDBTEST_SESSION "${CMAKE_BINARY_DIR}/hwtest/session.json")
    if(NOT CMAKE_GENERATOR STREQUAL "Ninja")
        message(FATAL_ERROR "HWTEST build manifest currently requires Ninja")
    endif()
    set_property(TARGET ${target} PROPERTY EXPORT_COMPILE_COMMANDS ON)
    set(STM32_GDBTEST_MANIFEST "${CMAKE_BINARY_DIR}/hwtest/build-manifest.json")
    set(manifest_script "${STM32_GDBTEST_MODULE_ROOT}/stm32_gdbtest/build_manifest.py")
    file(GLOB manifest_ioc "${HW_PROFILE_DIR}/*.ioc")
    set(manifest_inputs ${HW_MANIFEST_INPUTS})
    if(EXISTS "${STM32_GDBTEST_ROOT}/stm32_config.yml")
        list(APPEND manifest_inputs "${STM32_GDBTEST_ROOT}/stm32_config.yml")
    endif()
    set(manifest_input_args)
    foreach(input IN LISTS manifest_inputs)
        list(APPEND manifest_input_args --input "${input}")
    endforeach()
    set_property(TARGET ${target} APPEND PROPERTY LINK_DEPENDS
        "${manifest_script}" "${STM32_GDBTEST_PROFILE}" ${manifest_inputs} ${manifest_ioc})
    add_custom_command(TARGET ${target} POST_BUILD
        COMMAND "${Python3_EXECUTABLE}" -B "${manifest_script}"
            --root "${STM32_GDBTEST_ROOT}" --build "${CMAKE_BINARY_DIR}"
            --elf "$<TARGET_FILE:${target}>" --profile "${STM32_GDBTEST_PROFILE}"
            --out "${STM32_GDBTEST_MANIFEST}" --ninja "${CMAKE_MAKE_PROGRAM}"
            --target "${target}" ${manifest_input_args}
        BYPRODUCTS "${STM32_GDBTEST_MANIFEST}" VERBATIM)
    set(STM32_GDBTEST_STAND "" CACHE FILEPATH "Local stand TOML; select explicitly before HW runs")
    get_filename_component(compiler_bin "${CMAKE_C_COMPILER}" DIRECTORY)
    find_program(STM32_GDBTEST_GDB NAMES arm-none-eabi-gdb-py3 arm-none-eabi-gdb
        HINTS "${compiler_bin}" REQUIRED)
    set(session "{}")
    foreach(key IN ITEMS elf gdb tests root out stand profile build_manifest)
        if(key STREQUAL "elf")
            set(value "$<TARGET_FILE:${target}>")
        elseif(key STREQUAL "gdb")
            set(value "${STM32_GDBTEST_GDB}")
        elseif(key STREQUAL "tests")
            set(value "${STM32_GDBTEST_TESTS}")
        elseif(key STREQUAL "root")
            set(value "${STM32_GDBTEST_ROOT}")
        elseif(key STREQUAL "out")
            set(value "${CMAKE_BINARY_DIR}/hwtest/runs")
        elseif(key STREQUAL "profile")
            set(value "${STM32_GDBTEST_PROFILE}")
        elseif(key STREQUAL "build_manifest")
            set(value "${STM32_GDBTEST_MANIFEST}")
        else()
            set(value "${STM32_GDBTEST_STAND}")
        endif()
        string(REPLACE "\\" "/" value "${value}")
        string(REPLACE "\"" "\\\"" value "${value}")
        string(JSON session SET "${session}" "${key}" "\"${value}\"")
    endforeach()
    file(GENERATE OUTPUT "${STM32_GDBTEST_SESSION}" CONTENT "${session}\n")
    execute_process(COMMAND "${Python3_EXECUTABLE}" "${STM32_GDBTEST_MODULE_ROOT}/stm32_gdbtest/cli.py" collect
        --tests "${STM32_GDBTEST_TESTS}" --workspace "${STM32_GDBTEST_ROOT}" --cmake "${CMAKE_BINARY_DIR}/hwtest/tests.cmake"
        RESULT_VARIABLE rc)
    if(NOT rc EQUAL 0)
        message(FATAL_ERROR "Hardware test collection failed")
    endif()
    include("${CMAKE_BINARY_DIR}/hwtest/tests.cmake")
    file(GLOB test_sources CONFIGURE_DEPENDS "${STM32_GDBTEST_TESTS}/test_*.py")
    set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS ${test_sources}
        "${STM32_GDBTEST_MODULE_ROOT}/stm32_gdbtest/collect.py")
    add_test(NAME host.traceability COMMAND "${Python3_EXECUTABLE}" "${STM32_GDBTEST_MODULE_ROOT}/stm32_gdbtest/cli.py"
        trace --tests "${STM32_GDBTEST_TESTS}" --requirements "${HW_PROFILE_DIR}/Tests/requirements.md")
    set_tests_properties(host.traceability PROPERTIES LABELS host TIMEOUT 30
        WORKING_DIRECTORY "${STM32_GDBTEST_ROOT}" ENVIRONMENT "PYTHONDONTWRITEBYTECODE=1")
    if(HW_SELF_TESTS)
        add_test(NAME host.hwtest COMMAND "${Python3_EXECUTABLE}" -B -m unittest discover
            -s "${STM32_GDBTEST_MODULE_ROOT}/Tests/host" -v)
        set_tests_properties(host.hwtest PROPERTIES LABELS host TIMEOUT 30
            WORKING_DIRECTORY "${STM32_GDBTEST_MODULE_ROOT}" ENVIRONMENT "PYTHONDONTWRITEBYTECODE=1")
    endif()
    add_custom_target(check-hw
        COMMAND "${CMAKE_CTEST_COMMAND}" --test-dir "${CMAKE_BINARY_DIR}" --output-on-failure
            --output-junit "${CMAKE_BINARY_DIR}/hwtest/ctest-junit.xml"
        DEPENDS ${target} USES_TERMINAL)
endfunction()
