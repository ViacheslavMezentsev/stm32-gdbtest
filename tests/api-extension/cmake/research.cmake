# Experimental wrapper around the unmodified production attachment function.
# The production descriptor remains untouched; an explicit second descriptor is
# generated for host tests. This is not a shipped SESSION_CONFIG implementation.
function(research_attach target)
    cmake_parse_arguments(R "" "PROFILE_DIR;PROFILE;SESSION_CONFIG" "" ${ARGN})
    if(R_UNPARSED_ARGUMENTS)
        message(FATAL_ERROR "Unknown research arguments: ${R_UNPARSED_ARGUMENTS}")
    endif()
    if(NOT R_SESSION_CONFIG)
        stm32_gdbtest_attach(${target} PROFILE_DIR "${R_PROFILE_DIR}" PROFILE "${R_PROFILE}")
        return()
    endif()
    if(R_PROFILE)
        message(FATAL_ERROR "SESSION_CONFIG conflicts with PROFILE")
    endif()
    find_package(Python3 3.11 COMPONENTS Interpreter REQUIRED)
    get_filename_component(config "${R_SESSION_CONFIG}" ABSOLUTE)
    execute_process(COMMAND "${Python3_EXECUTABLE}" -B
        "${CMAKE_CURRENT_FUNCTION_LIST_DIR}/../session_bridge.py" --select "${config}"
        RESULT_VARIABLE code OUTPUT_VARIABLE selected OUTPUT_STRIP_TRAILING_WHITESPACE
        ERROR_VARIABLE detail)
    if(NOT code EQUAL 0)
        message(FATAL_ERROR "Configuration selection failed: ${detail}")
    endif()
    stm32_gdbtest_attach(${target} PROFILE_DIR "${R_PROFILE_DIR}" PROFILE "${selected}")
    set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${config}" "${selected}")
    # Produce a separate research descriptor: ordinary registered CTest commands
    # still use the production JSON and do not execute this research path.
    file(GENERATE OUTPUT "${CMAKE_BINARY_DIR}/hwtest/research-session.json"
        CONTENT "{\"session_config\":\"${config}\",\"profile\":\"${selected}\"}\n")
endfunction()
