# HAL F030 hardware acceptance

[Documentation](index.md) → HAL F030 · [Русский](../ru/F030_HAL_VALIDATION.md)

Stage record: case counts and plans below refer to the stated revision.
Current scope: [STATUS](STATUS.md); release preparation: [rc.2](RC2_READINESS.md).

The standalone [fixture](../../tests/hal-f030/README.en.md) passed hardware checks
on NUCLEO-F030R8 with native ST-Link V2J45M31, SWD 1 MHz and OpenOCD 0.12.0.
Local date: 2026-10-01; evidence start: 20260930T195222.241532Z (UTC).
Windows host, xPack GCC 13.3.1-1.1, GDB 14.2.90.20240526-git.
Module base cc2cf19, firmware imported at a3898ff; the new run_hw.py executes
acceptance through the standard CLI. [Plan and provenance](F030_HAL_REGRESSION.md).

## Results

| Check | Result |
| --- | --- |
| Main HAL cases | 17/17 PASS |
| ADC, TIM3, RTC after each of the two ADC injections | 6/6 PASS |
| Python stall after reaching loop, 5 s timeout | Expected ERROR, TimeoutExpired, reset_run (host recovery) |
| ADC after recovery | PASS |
| Original consumer HAL firmware restored, boot and blink | 2/2 PASS, MCU left running |

The first boot flashed and verified the fixture. Every positive run records
image_verified and reset_run. The stall-entered.txt marker confirms that timeout
occurred inside the reached scenario, rather than during server startup. This is
an artificial Python stall, not an MCU hardware fault. There are 27 stages including
an expected ERROR; describing this as “27/27 PASS” would be incorrect.

Fixture ELF SHA256:
`f2a2a2a98d8b95d080a78071543f7fd7d2a1f828dfaf3764c1ae53da39202fed`.
Restored consumer 0c8c966 ELF SHA256:
`cdf421fdad7c6b2637e1c8ce0a257097b373db084c7bb702587b423a3e1323d6`.
Local evidence: tests/hal-f030/build/validation/20260930T195222.241532Z/summary.json;
it references every result.json, with stage logs alongside. Artifacts and the
private stand are not committed. This run has no new visual LED confirmation.

## Repeating the protocol

First build the fixture as described in its README and verify that the restore
project manifest is current. From the module root, with an explicitly selected,
confirmed stand:

```sh
python -B tests/hal-f030/run_hw.py --stand <private-stand.toml> --restore-session <consumer-session.json>
```

The script requires OpenOCD, flash=if-different and two STM32F030R8T6 sessions;
it validates both manifests before starting the first server. It uses fixture
build/debug, stops at the first unexpected result and attempts to restore the
original firmware with boot/blink checks in finally. Restoration failure yields
ERROR, not a claim of successful restoration. This explicit hardware command writes
Flash; it is not part of automatic offline CI. Do not run another runner/IDE concurrently.

## Limits and next steps

Preserved [TECH-001, TECH-003, TECH-004, TECH-007](TESTING_TECHNIQUES.md) cover
HAL macros, callbacks/IRQ, force_return injections and numeric vectors.
HAL Sleep cases do not replace the separate CMSIS interrupted-WFI proof.
Results do not cover ST server/J-Link, Linux HW, GCC14/15, Release/LTO or other MCUs.
This stage changes neither the public API nor firmware.

After publication verify Docs and the complete Offline workflow for the final SHA;
land fixture → CI → validation in order, then update the consumer gitlink.
Removing the old HAL profile is a separate step after integration, not part of this acceptance.
