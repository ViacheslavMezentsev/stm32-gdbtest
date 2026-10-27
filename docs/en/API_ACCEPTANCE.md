# Accepted API: results and reproducible checks

[Documentation](index.md) · [Русский](../ru/API_ACCEPTANCE.md)

This is a public summary of accepted behavior and acceptance, not a development diary.
Contract: [API specification](../TECHNICAL_SPECIFICATION_API.md); guide: [API](API.md).

## Release 0.5.0 — P5b campaign, 2026-10-20

Final acceptance commit `a7b0951`, API_VERSION=3. All P5 matrix rows passed with recorded
limits; rule 4 transfers some rows from `8fdbb58` (only live-observer and CHANGELOG changed).
[Outcomes and limits](../development/release-050-acceptance.md). Sections below retain
evidence for their own revisions, not a pending release gate.

## P4: neutral API 3 example — 2026-10-19

[Package and limits](LIVE_OBSERVER.md): Renode 1.17 Windows/Linux — 8 expected outcomes
per OS (5 PASS, 2 intentional ERROR, 1 intentional FAIL), cleanup VERIFIED and three
confirmed DDTT links. Four remap cases are NOT_SUPPORTED in the model.
The research F411/OpenOCD pilot on 085f089 produced 12/12 expected outcomes
(8 PASS, 3 intentional ERROR, 1 intentional FAIL). Flash/SRAM, PC/SP/xPSR/PRIMASK,
FPB/VTOR and saved NVIC blocks were independently compared. The MCU remained halted
after reset; its live context and all peripherals were not restored. Public transfer
was verified without a board and does not replace hardware acceptance of the release SHA.

## P3: six-board summary — 2026-10-19

Hardware live-window acceptance is complete: **78/78 expected outcomes**, artifact
audit **222/222**. These are six campaigns of 13 outcomes, not 78 unique scenarios
or 78 PASS verdicts. Each board produced 9 PASS, 1 intentional FAIL, 2 ERROR and 1 SKIP.

| MCU | Transport | Expected outcomes | Audit | Flash/SRAM |
| --- | --- | --- | --- | --- |
| F030 | OpenOCD / ST-Link | 13/13 | 37/37 | restored, verified |
| F103 | OpenOCD / ST-Link | 13/13 | 37/37 | restored, verified |
| F401 | OpenOCD / ST-Link | 13/13 | 37/37 | restored, verified |
| F411 | OpenOCD / ST-Link | 13/13 | 37/37 | restored, verified |
| F429 | OpenOCD / ST-Link | 13/13 | 37/37 | restored, verified |
| AT32F403A | Artery OpenOCD / J-Link WinUSB | 13/13 | 37/37 | restored, verified |

Checks cover synchronous compatibility, asynchronous resume, passive wait and its
timeout, halt, repeated windows, rejected operations while running, and cleanup
for different scenario outcomes. The neutral ELF uses neither RTOS nor peripherals.
After restoration, cores remain halted after reset: prior live execution is not resumed.

AT32 initially required USB reconnects and recovery; those ERROR results remain
preserved. A separate 13/13 repeat used fix `c5452b6` and the original vendor target:
all OpenOCD exits were zero without forced kill. This repeat is not added to the 78
as new capability coverage. The other five campaigns preceded this fix; their ST-Link
route was unchanged. Final release acceptance is documented above. USB loss
and universal recovery are not claimed to be solved.


Earlier campaign history: [release transitions](RELEASE_CHANGES.md).
