# First-package core integration

[Research](index.md) · [Русский](../ru/core-integration.md)

2026-10-03. The owner authorized integration of record/records, RecordError, config/config_props and session.toml in the current branch. Contract retained; development version 0.2.0.dev0, target 0.2.0, API_VERSION=1, api.toml schema=1. API spec 0.2.2 and system spec 0.62. No release, push or merge performed.

## Implementation

- records.py implements a GDB-independent journal; Target owns one per invocation. Public RecordError imports from the package root without GDB.
- configuration.py captures selected TOML once, validates parsed profile data and builds immutable views. Known bounds are checked; unknown api fields survive.
- CMake explicitly selects SESSION_CONFIG. session.json remains, with profile derived from TOML. Conflicting PROFILE/image overrides and stale target selection are rejected.
- runner uses captured profile/image and profile hash for manifest validation. agent receives a base64/SHA256 capsule and checks defaults/profile/image before connecting. GDB never rereads original TOML. If selected TOML is also included by --include, the package uses the same captured bytes; tested after modifying the original.
- New pack stores the capsule and captured profile; unpacking revalidates without original paths. Old JSON/packages retain legacy selection and actual config_props. New packages require a compatible receiving tool.
- TECH-010 remains a Python technique. TECH-011 core acceptance uses actual Target config/record/records; the historical facade remains for comparison.

## Checks and limits

Host: Windows 161 tests (150 PASS, 11 platform skips); Linux Docker 161 (157 PASS, 4 skips). Coverage includes independent bounds, errors/atomicity/copies, actual Target, CMake old/new/conflict, transport/package without sources, legacy and rejection before tools/lock. The first run exposed two outdated profile-read mocks, then a leftover research-facade import in a ported test; fixtures were corrected and the subsequent run passed. Intentional negative-test ERROR/FAIL output is not a hardware failure.

Docker format+host: 2/2 PASS; host+firmware GCC13 for F030/F103/F411: 4/4 PASS. Firmware checks include build/preflight, full-image and negative contracts. Final docs+host+HAL check: 6/6 PASS. New SESSION_CONFIG with full-image on the real F030 ELF: prepare PASS. Actual CLI pack of F030 ADC_UNITS and run --package --prepare-only: PASS. Source removal and TOML date/unknown transport are host-tested. A new Orange Pi/SSH hardware run was not performed.

Hardware: Windows, GCC13, GDB14/Python3.11.4; F030/OpenOCD/ST-Link, F103/J-Link CE, F411/OpenOCD/ST-Link. Each stand: 7/7 prepare and 7/7 HW covering ADC baseline, native RTC/TIM2/ADC, table pair, old series, actual Target series and two BOOT/GPIO restoration checks. Total 21 hardware PASS; the separate preliminary F030 prepare is not counted again. F030/F103 CMSIS and F411 HAL restored; image_verified/reset_run confirmed. F103 profile Flash 64 KiB versus observed 128 KiB warning retained; the image fits both.

[Sanitized results](../results/core-three-boards.json) contain ELF/manifest/restore hashes, checks, records and statistics. Table checks match completely; the series retains original checks and adds four configuration/GDB arithmetic checks. Each MCU produced 10 measurements and 11 records. integrated_api=true confirms actual Target use. This is neither VDDA/temperature calibration nor a full hardware run of every project scenario.

## Cost

Repeated 13 data shapes and five boundaries in CPython, GDB14 and GDB16, all PASS. Maximum write_batch/read_all/read_missing median ratios against the saved baseline for CPython/GDB14/GDB16: 1.23 / 1.25 / 1.13 respectively; none exceeds 2x. Python versions match the baseline: 3.11.9 / 3.11.4 / 3.13.12. Logical limits are not RSS/latency guarantees.

Results: [host](../results/core-records-cost-host.json), [GDB14](../results/core-records-cost-gdb14.json), [GDB16](../results/core-records-cost-gdb16.json). Historical prototype results remain separate.

## Next

The first package is integrated and verified within this scope. Further scenario migration should follow its practical benefit; simple checks need not create a journal. read/context/caller/finish and RTOS remain outside the package. Release preparation and remote hardware acceptance are separate stages.
