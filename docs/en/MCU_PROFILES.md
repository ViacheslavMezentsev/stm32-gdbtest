# MCU profiles

[Documentation](index.md) → MCU profiles · [Русский](../ru/MCU_PROFILES.md)

A profile is a `target.toml` file describing a specific MCU: Flash, DEV_ID, number of
hardware breakpoints, fault handlers, diagnostic registers, the OpenOCD target. The
module has no ready-made profile library "for any STM32": the consumer writes a profile
for their board, using one of the existing ones as a template. Several MCU variants of
one firmware can share scenarios, each with its own `session.toml` selecting the profile through `config.target`.

Templates in the repository: the CI firmware `tests/firmware/profiles/` (F030R8,
F103C8, F401CC, F411CE, F429ZI — Cortex-M0, M3, M4; AT32F403A — a compatible Cortex-M4) and the example
`examples/minimal-consumer/profile/` (F411CE).

| MCU | Debugger / GDB server | Verified in |
| --- | --- | --- |
| STM32F030R8 | ST-Link (NUCLEO) / OpenOCD, st-util; J-Link GDB Server | CI firmware, HAL fixture, stand project |
| STM32F103C8 | J-Link / J-Link GDB Server; ST-Link / st-util | CI firmware, stand project |
| STM32F103CB | J-Link CE / J-Link GDB Server | demo project [stm32-hwtest-bluepill](https://github.com/ViacheslavMezentsev/stm32-hwtest-bluepill) |
| STM32F401CC | ST-Link / OpenOCD; ST-LINK GDB Server; st-util | CI firmware, stand project |
| STM32F411CE | ST-Link / OpenOCD; ST-LINK GDB Server; st-util | CI firmware, example, stand project |
| STM32F429ZI | ST-Link / OpenOCD; ST-LINK GDB Server; st-util | CI firmware, stand project |
| STM32G474CE | ST-Link / OpenOCD on Orange Pi 5 | consumer project (Arduino Core STM32) |
| AT32F403ACGU7 (Artery) | J-Link / J-Link GDB Server; ST-Link / st-util | CI firmware, after 0.3.0 |

OpenOCD, ST-LINK GDB Server and st-util need only the profile. J-Link GDB Server requires a
device name: the profile sets it (`jlink_device`), and the module knows it for STM32F103C8T6,
STM32F030R8T6 and STM32F103CBT6. H503 is not supported. Support is defined by the specific combination
of MCU, HAL, GDB and backend, not by the family: [current status](STATUS.md).

**Compatible MCUs from other vendors.** The module is not tied to ST: it needs a Cortex-M core and a
GDB server that connects to the chip. Such an MCU (Artery AT32, GigaDevice GD32, Geehy APM32, etc.) is
attached with its own profile and the vendor CMSIS, without module changes. One is verified so far —
AT32F403ACGU7 on the WeAct AT32F4 Core Board via J-Link; it is not part of the 0.3.0 hardware campaign
but is included in the six 0.4.0 models. The profile, the SDK, scenario specifics and the procedure for your own MCU are in
[compatible MCUs](COMPATIBLE_MCU.md). Every new chip needs its own acceptance on a board.

