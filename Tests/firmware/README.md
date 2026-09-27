# CI firmware

Minimal CMSIS-only firmware used by CI to check stm32-gdbtest up to the GDB server:
build, build manifest, collection, traceability, offline ELF contracts and
`run --prepare-only`. Profiles `f030r8` (Cortex-M0), `f103c8` (Cortex-M3) and
`f411ce` (Cortex-M4) mirror boards validated in stm32-hwtest-blackpill, but the
scenarios here were not run on hardware and are not evidence of HAL behaviour.

Toolchain: `ARM_TOOLCHAIN_ROOT`; CMSIS: `STM32CUBE_REPOSITORY` with
`STM32Cube_FW_F0_V1.11.6`, `STM32Cube_FW_F1_V1.8.7`, `STM32Cube_FW_F4_V1.28.3`.
Usually run through `ci/run_checks.py` inside the CI Docker image.
