include_guard(GLOBAL)

function(stm32_gdbtest_register id timeout labels)
    add_test(NAME hw.${id}
        COMMAND "${Python3_EXECUTABLE}" "${STM32_GDBTEST_MODULE_ROOT}/stm32_gdbtest/cli.py" run
            --session "${STM32_GDBTEST_SESSION}" --test "${id}")
    # GDB deadline plus preparation, server startup, recovery and process cleanup.
    math(EXPR outer_timeout "${timeout} + 90")
    set_tests_properties(hw.${id} PROPERTIES TIMEOUT ${outer_timeout}
        LABELS "hw;${labels}" RESOURCE_LOCK stm32_swd)
    # ТЗ 5.13.14: host-side preparation of the same scenario, without debugger access.
    add_test(NAME prepare.${id}
        COMMAND "${Python3_EXECUTABLE}" -B "${STM32_GDBTEST_MODULE_ROOT}/stm32_gdbtest/cli.py" run
            --session "${STM32_GDBTEST_SESSION}" --test "${id}" --prepare-only)
    set_tests_properties(prepare.${id} PROPERTIES TIMEOUT 90 LABELS "host;prepare"
        ENVIRONMENT "PYTHONDONTWRITEBYTECODE=1")
endfunction()

function(stm32_gdbtest_attach target)
    cmake_parse_arguments(HW "SELF_TESTS" "PROFILE_DIR;PROFILE;SESSION_CONFIG" "MANIFEST_INPUTS;TEST_DIRS" ${ARGN})
    if(HW_KEYWORDS_MISSING_VALUES)
        message(FATAL_ERROR "Missing stm32_gdbtest_attach values: ${HW_KEYWORDS_MISSING_VALUES}")
    endif()
    if(HW_UNPARSED_ARGUMENTS)
        message(FATAL_ERROR "Unknown stm32_gdbtest_attach arguments: ${HW_UNPARSED_ARGUMENTS}")
    endif()
    # ТЗ 5.13.2: PROFILE selects a target description outside PROFILE_DIR, so several MCU
    # variants of one firmware share PROFILE_DIR/tests (scenarios, requirements, contracts).
    find_package(Python3 3.11 COMPONENTS Interpreter REQUIRED)
    get_filename_component(STM32_GDBTEST_MODULE_ROOT "${CMAKE_CURRENT_FUNCTION_LIST_DIR}/../.." ABSOLUTE)
    if(HW_SESSION_CONFIG)
        if(HW_PROFILE)
            message(FATAL_ERROR "SESSION_CONFIG conflicts with PROFILE")
        endif()
        get_filename_component(HW_SESSION_CONFIG "${HW_SESSION_CONFIG}" ABSOLUTE)
        execute_process(COMMAND "${Python3_EXECUTABLE}" -B -m stm32_gdbtest.configuration "${HW_SESSION_CONFIG}"
            WORKING_DIRECTORY "${STM32_GDBTEST_MODULE_ROOT}"
            RESULT_VARIABLE config_rc OUTPUT_VARIABLE HW_PROFILE OUTPUT_STRIP_TRAILING_WHITESPACE)
        if(NOT config_rc EQUAL 0)
            message(FATAL_ERROR "Invalid SESSION_CONFIG")
        endif()
        set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${HW_SESSION_CONFIG}")
    elseif(NOT HW_PROFILE)
        set(HW_PROFILE "${HW_PROFILE_DIR}/target.toml")
    endif()
    # ТЗ 5.13.2: the scenario directory is PROFILE_DIR/Tests or PROFILE_DIR/tests.
    set(hw_tests_root "${HW_PROFILE_DIR}/tests")
    if(NOT IS_DIRECTORY "${hw_tests_root}" AND IS_DIRECTORY "${HW_PROFILE_DIR}/Tests")
        set(hw_tests_root "${HW_PROFILE_DIR}/Tests")
    endif()
    if(NOT HW_PROFILE_DIR OR NOT IS_DIRECTORY "${hw_tests_root}" OR NOT EXISTS "${HW_PROFILE}")
        message(FATAL_ERROR "stm32_gdbtest_attach requires PROFILE_DIR with tests/ (or legacy Tests/) and a target "
            "description (PROFILE_DIR/target.toml or PROFILE)")
    endif()
    find_package(Python3 3.11 COMPONENTS Interpreter REQUIRED)
    get_filename_component(STM32_GDBTEST_MODULE_ROOT "${CMAKE_CURRENT_FUNCTION_LIST_DIR}/../.." ABSOLUTE)
    set(STM32_GDBTEST_ROOT "${PROJECT_SOURCE_DIR}")
    set(STM32_GDBTEST_TESTS "${hw_tests_root}/board")
    # ТЗ API 5.7: extra scenario directories, searched after PROFILE_DIR/tests. Each one has the layout of
    # PROFILE_DIR/tests: board/test_*.py, requirements.md and an optional contracts.json. The cache variable
    # adds directories without editing CMakeLists.txt (a preset or -D on the command line).
    set(STM32_GDBTEST_TEST_DIRS "" CACHE STRING "Extra scenario roots (board/, requirements.md), searched after PROFILE_DIR/tests")
    set(hw_extra_roots)
    foreach(extra IN LISTS HW_TEST_DIRS STM32_GDBTEST_TEST_DIRS)
        get_filename_component(extra "${extra}" ABSOLUTE BASE_DIR "${CMAKE_CURRENT_SOURCE_DIR}")
        if(NOT IS_DIRECTORY "${extra}/board" OR NOT EXISTS "${extra}/requirements.md")
            message(FATAL_ERROR "stm32_gdbtest_attach TEST_DIRS entry needs board/ and requirements.md: ${extra}")
        endif()
        list(APPEND hw_extra_roots "${extra}")
    endforeach()
    list(REMOVE_DUPLICATES hw_extra_roots)
    set(hw_collect_args --tests "${STM32_GDBTEST_TESTS}")
    set(hw_trace_args --tests "${STM32_GDBTEST_TESTS}" --requirements "${hw_tests_root}/requirements.md")
    set(hw_test_globs "${STM32_GDBTEST_TESTS}/test_*.py")
    set(hw_test_dirs_json "[]")
    set(hw_index 0)
    foreach(extra IN LISTS hw_extra_roots)
        list(APPEND hw_collect_args --tests "${extra}/board")
        list(APPEND hw_trace_args --tests "${extra}/board" --requirements "${extra}/requirements.md")
        list(APPEND hw_test_globs "${extra}/board/test_*.py")
        string(REPLACE "\\" "/" extra_json "${extra}/board")
        string(JSON hw_test_dirs_json SET "${hw_test_dirs_json}" ${hw_index} "\"${extra_json}\"")
        math(EXPR hw_index "${hw_index} + 1")
    endforeach()
    set(STM32_GDBTEST_PROFILE "${HW_PROFILE}")
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
    string(JSON session SET "${session}" test_dirs "${hw_test_dirs_json}")
    if(HW_SESSION_CONFIG)
        string(REPLACE "\\" "/" config_path "${HW_SESSION_CONFIG}")
        string(REPLACE "\"" "\\\"" config_path "${config_path}")
        string(JSON session SET "${session}" session_config "\"${config_path}\"")
    endif()
    file(GENERATE OUTPUT "${STM32_GDBTEST_SESSION}" CONTENT "${session}\n")
    execute_process(COMMAND "${Python3_EXECUTABLE}" "${STM32_GDBTEST_MODULE_ROOT}/stm32_gdbtest/cli.py" collect
        ${hw_collect_args} --workspace "${STM32_GDBTEST_ROOT}" --cmake "${CMAKE_BINARY_DIR}/hwtest/tests.cmake"
        RESULT_VARIABLE rc)
    if(NOT rc EQUAL 0)
        message(FATAL_ERROR "Hardware test collection failed")
    endif()
    include("${CMAKE_BINARY_DIR}/hwtest/tests.cmake")
    file(GLOB test_sources CONFIGURE_DEPENDS ${hw_test_globs})
    set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS ${test_sources}
        "${STM32_GDBTEST_MODULE_ROOT}/stm32_gdbtest/collect.py")
    add_test(NAME host.traceability COMMAND "${Python3_EXECUTABLE}" "${STM32_GDBTEST_MODULE_ROOT}/stm32_gdbtest/cli.py"
        trace ${hw_trace_args})
    set_tests_properties(host.traceability PROPERTIES LABELS host TIMEOUT 30
        WORKING_DIRECTORY "${STM32_GDBTEST_ROOT}" ENVIRONMENT "PYTHONDONTWRITEBYTECODE=1")
    if(HW_SELF_TESTS)
        add_test(NAME host.hwtest COMMAND "${Python3_EXECUTABLE}" -B -m unittest discover
            -s "${STM32_GDBTEST_MODULE_ROOT}/tests/host" -v)
        set_tests_properties(host.hwtest PROPERTIES LABELS host TIMEOUT 30
            WORKING_DIRECTORY "${STM32_GDBTEST_MODULE_ROOT}" ENVIRONMENT "PYTHONDONTWRITEBYTECODE=1")
    endif()
    add_custom_target(check-hw
        COMMAND "${CMAKE_CTEST_COMMAND}" --test-dir "${CMAKE_BINARY_DIR}" --output-on-failure
            --output-junit "${CMAKE_BINARY_DIR}/hwtest/ctest-junit.xml"
        DEPENDS ${target} USES_TERMINAL)
endfunction()
