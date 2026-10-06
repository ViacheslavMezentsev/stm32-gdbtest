# MCU identity and Flash size

[Documentation](index.md) → Identity and Flash · [Русский](../ru/TARGET_IDENTITY.md)

Scenarios run with an explicitly selected profile. DEV_ID, package marking, factory
Flash size and the MCU name shown by debugger software are different signs. A
mismatch never switches the profile, HAL, linker script or expectations automatically.

## Identifier of another vendor

`[identity]` sets the address, mask and value; the width is not limited to the 12-bit DEV_ID. On AT32F403ACGU7 the
same address `0xE0042000` holds the 32-bit Artery PID: mask `0xFFFFFFFF`, value `0x70050347` per the RM
([compatible MCUs](COMPATIBLE_MCU.md)).

## Identity policy

The default is `warn`: a DEV_ID mismatch gives a warning and the scenario continues.
`strict` ends the run with ERROR before the Flash size is read and before the image is
compared or programmed. A register read error is ERROR in any mode. Selection order:
CLI `--identity-policy`, the `STM32_GDBTEST_IDENTITY_POLICY` variable, then `warn`.

JSON and JUnit keep `identity` (policy, expected, observed, raw, mask, selected MCU
and profile), `warnings` and `flash_capacity`. PASS remains the scenario result and
does not mean the identity matched. The CLI prints warnings for any outcome. CTest
hides the output of passing tests by default: use `ctest -V`; warnings are also in
JSON, JUnit and `LastTest.log`. On a GDB timeout the final agent report may be
missing — a missing `identity` in such an ERROR does not mean a match.

## Flash size before programming

The `flash_size_address` field in `target.toml` (schema 1) is the address of the
16-bit Flash size register in KiB. Verified profiles: F030 — `0x1FFFF7CC`, F103 —
`0x1FFFF7E0`, F401/F411/F429 — `0x1FFF7A22` (device CMSIS). A profile without the
field can be read, but a hardware run is refused before programming. After changing
`target.toml` rebuild to get a new build manifest.

Before reading or programming the image the agent reads the size and requires
`0 < image size ≤ min(profile size, size read)`. A value of 0 or `0xFFFF`, a read
error or exceeding the limit is ERROR regardless of the identity policy. If the image
fits, a size different from the profile gives a separate warning. A larger chip does
not widen the selected profile or linker script. Example: a WeAct BluePill-Plus with
STM32F103C8 reports 128 KiB against a 64 KiB profile — a warning, and the run
continues within the profile bounds.

## Clones and remarked chips

On cheap boards (BluePill and similar) the package marking, DEV_ID and the Flash size
register often differ from the expected MCU: an STM32F103C8 with 128 KiB Flash like an
F103CB, or a compatible chip from another vendor. What to do:

- **A different Flash size with the same DEV_ID** (F103C8 and F103CB are both `0x410`) is
  only a warning: the run stays within the profile. The profile and the linker script
  describe what the firmware targets, not what the chip reported.
- **A different DEV_ID.** With the `warn` policy the scenario runs with a warning, with
  `strict` it is ERROR. If such a chip is a deliberate part of the stand, describe it with
  its own profile holding the observed `[identity]` (a separate `target.toml` or a
  `PROFILE` file) and check it there instead of relaxing the policy for every board.
- **Compatible chips from other vendors** (GD32, CKS32 and so on) may differ in debug and
  Flash registers and timing. A matching DEV_ID does not prove compatibility; such boards
  are checked as a separate MCU.

This interprets the factory register according to the selected profile; it is not a
test of the whole memory. For an unknown MCU the address may be wrong, and a warning
does not prove that the memory map and peripherals are compatible. For a new family
check the documentation and the address instead of carrying it over by analogy. The
names F103C8/CB in software do not by themselves define the available memory.

[Observations on real samples](https://github.com/ViacheslavMezentsev/stm32-hwtest-blackpill/blob/main/docs/TARGET_IDENTITY.md)
(Russian) do not automatically apply to other boards.
