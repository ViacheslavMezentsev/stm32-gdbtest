# Accepted API: results and reproducible checks

[Documentation](index.md) · [Русский](../ru/API_ACCEPTANCE.md)

This is a public summary of accepted behavior and acceptance, not a development diary.
Contract: [API specification](../TECHNICAL_SPECIFICATION_API.md); guide: [API](API.md).

## Current summary — 2026-10-10

The candidate is unpublished. Current versions: stm32-gdbtest 0.4.0, API_VERSION=2, target schema 2,
general specification 0.90, API specification 0.3.16. Latest local reconciliation: `a6b6dbd`.
Separate campaigns follow: six Windows OpenOCD/J-Link stands, Windows/st-util,
short recovery/idle checks and full SSH/st-util suites on five STM32 boards. Their counts must
not be summed as unique scenarios or treated as latest-SHA CI evidence.
[Release gates and open limits](RELEASE040_SCOPE.md#4-evidence-and-open-limits).

## 0.4.0 candidate — acceptance open

Rechecked on 2026-10-10: runtime `b1264c1`, stm32-gdbtest 0.4.0, API_VERSION=2,
target schema 2. Fixed schema 1/OpenOCD compatibility, the reset command source,
and recovery independence from overrides. Schema/API checks do not establish USB reliability.

Windows 10 AMD64, GCC 13.3.1-1.1, GDB 14.2.90/Python 3.11.4,
OpenOCD 0.12.0, J-Link 8.32. Six physical boards passed the lifecycle 10/10 each,
then 280 scenarios and 608 stages: 602 PASS and 6 expected timeout ERROR outcomes
with recovery. Final BOOT/GPIO: 12/12 PASS. The table counts one completed successful
suite per board; the additional F411/OpenOCD repeat is excluded from the total.

| MCU / backend | Scenarios | Stages | ELF SHA-256 |
| --- | ---: | ---: | --- |
| STM32F030R8T6 / OpenOCD | 45 | 98 | `8909baf64a2b09ace0eb3879e58c16dc53db7a6d52ee41c94fe9d25301d34efa` |
| STM32F103C8T6 / OpenOCD | 47 | 102 | `b221cdbc2fbec7dabd2760d0a45356266d501331bd07a59e9479e77ae25fa971` |
| STM32F401CCU6 / OpenOCD | 47 | 102 | `2e5e677ed52fa7f914b44f91807ee69769ae60e87a6304800952bb409adff404` |
| STM32F411CEU6 / OpenOCD | 47 | 102 | `b018f21c89406eb889d952a7266532c234a48cab7de158facd4765afac97932d` |
| STM32F429ZIT6 / OpenOCD | 47 | 102 | `fdec05542e41b323c34fe25c2392a7b53113b822b3304f4b26bf5804adb41bc4` |
| AT32F403ACGU7 / J-Link | 47 | 102 | `4e1e5888178b65b3ec69eb3bcac9ae2089febdf7e563004503574f13d58d7a9a` |

Additional checks:

- Clean Docker snapshot `b1264c1`: 26/26, including 18 MCU/GCC 13/14/15 combinations
  and HAL F030. Windows host and Linux host in a separate volume passed; subsequent
  consumer-example and CI-output fixes have separate host regressions.
- F411 and F429 packages built and prepared in Linux ran on Windows/OpenOCD:
  10/10 each. This checks package relocation, not remote USB or Orange Pi.
- Independent minimal-consumer with a real `b1264c1` gitlink: configure, build,
  3/3 offline and hardware GPIO passed. Its relative CTest module-path failure was
  fixed; repeating the original command passed 3/3. F411 restoration was verified.
- All result.json references in completed suites were checked, with no unexpected
  errors inside successful suites. GDB 14 `inferred_stop` warnings remain: these
  infer a stop reason from state rather than establish a GDB event reason.

Unaccepted results and limits:

- F411/ST-LINK GDB Server 7.14.0: lifecycle 10/10; two full suites ended with
  `Target USB comms error` (94 and 68 stages). Server 7.9.0 also passed 10/10,
  but its full suite stopped at 73 stages. Each contains three ERROR outcomes,
  including failed restoration. The owner noted possible physical contact disturbance;
  the cause is unknown and a server-version regression is not established.
  After reconnection, OpenOCD restored F411: build/BOOT/GPIO 3/3.
- Initial AT32/J-Link: 2/10, stuck opening the probe; a separate run after USB
  reconnection passed 10/10 and the full suite. The original failure is retained.
- A direct bind mount of the Windows working directory hit the 600-second host
  timeout. A clean Linux volume passed in 26 seconds. These are different storage
  layouts; no speedup ratio is established. Use the [volume recipe](local-docker-testing.md).
- GitHub Hardware 38008347735: F429 passed 10/10; F103 strict failed after reading
  AT32 ID `0x70050347` instead of STM32 ID `0x410`. Fix the remote profile/probe
  mapping before the next run; strict identity remains enabled.

### st-util 1.9.0: five STM32 boards on Windows

2026-10-10, working snapshot of `codex/release-040` after `429098b`, xPack 13.3.1,
GDB 14.2.90/Python 3.11.4, st-util 1.9.0 (Scoop). The new backend ran on the same
five ST-Link probes: lifecycle 10/10 each, followed by 233 scenarios and 506 stages —
501 PASS and 5 expected timeout ERROR outcomes. Every timeout confirmed scenario entry
and host recovery; final BOOT/GPIO passed 10/10. No USB reconnection was needed during
these series. The table includes the last full suite per board, including F0/F1 repeats with final setup.

| MCU | Scenarios | Stages | ELF SHA-256 |
| --- | ---: | ---: | --- |
| STM32F030R8T6 | 45 | 98 | `13335372db8090b2b7f8a47fa1617fbccf34a73c50f935a71a439cc129b3f03b` |
| STM32F103C8T6 | 47 | 102 | `76ea87e6f8459f52a3bb6e0ee741dc697cfb62598e55127695662da4b7d482fd` |
| STM32F401CCU6 | 47 | 102 | `c02f1b0906e7199dfbf762eed79f27e1f493f928c459936e2ecb226785dd69e3` |
| STM32F411CEU6 | 47 | 102 | `bc04a22df7e0a0d5501d567e1fb4b36dbc0342a586b1668bc72d144dcb48bf2d` |
| STM32F429ZIT6 | 47 | 102 | `bf0f7c08f59052e549ad21538c979e123578930425dd7a8f946042cb6b98f742` |

All result.json references, expected exit codes, image checks, absence of failed checks
inside PASS, reset/run and timeout recovery were audited. Host: 411 tests on Windows
(14 expected skips) and Linux/Docker (4 skips); Docker docs+host passed 6/6.
This validates the named snapshot, not a future release SHA.

The first F411 lifecycle passed 3/10: the st-util memory map omits the factory register
at `0x1fff7a22`. Reading it on the same connection succeeded after
`set mem inaccessible-by-default off`; this setup is applied only to this backend.
Flash-capacity and identity checks remain enabled. F411 then passed 10/10 and its full suite;
the original errors are retained. F103 still reports 128 KiB against the profile's 64 KiB:
an explicit warning, with the image fitting both bounds and strict mode tested separately.

Runtime server version may be `null` when stdout is not flushed before termination;
doctor confirms 1.9.0 separately. st-util and ST-LINK GDB Server are distinct backends:
this PASS does not close question 11.2.27 about the ST server. OrangePi/Linux/SSH for
st-util has configuration host tests only, without a hardware run.
[Setup and limits](BACKENDS.md#st-util-v040), [installation](LINUX_STAND.md#st-util).

### Comparing GDB clients on F411/ST-LINK

Server 7.14.0, one probe, one GCC13 ELF with SHA-256
`f93547938335e12fee86509ee29b68202b808e91d26961f80f052945cea22105`.
Only the gdb field of a session.json copy changed for the newer clients; firmware was not rebuilt.

| xPack | GDB / Python | Full-suite result |
| --- | --- | --- |
| 13.3.1-1.1 | 14.2.90 / 3.11.4 | Two initial attempts: 94 and 68 stages, USB ERROR |
| 14.2.1-1.1 | 15.2.90 / 3.12.8 | 96 stages: 93 PASS, 3 ERROR; first failure HW_CI_WAIT_CHANGES |
| 15.2.1-1.1 | 16.3.90 / 3.13.12 | 73 stages: 70 PASS, 3 ERROR; first failure HW_CI_CALL_PREDICATE |

In every case the next scenario's server reported `Target USB comms error` before
GDB connected; the two subsequent ERROR outcomes were restoration attempts.
Changing the client did not eliminate the observed failure. After the final USB
reconnection, BOOT/GPIO through OpenOCD passed 2/2. No full ST-LINK PASS is claimed.

### Another probe: Nucleo-F030R8

2026-10-10, runtime unchanged from `b1264c1`, server 7.14.0,
GDB 14.2.90/Python 3.11.4 from xPack 13.3.1. The Nucleo ST-Link firmware is
V2J45M31; the compared F411 probe uses V2J43M28. F030 ELF:
`19004fbb238ab96c54e29d9090f981ec73e00cd5ad37960419e00670b1d79628`.

Lifecycle: 10/10. The full suite stopped before `HW_CI_INJECT_ZERO`:
76 stages, 73 PASS (47 preparations and 26 hardware scenarios), 3 ERROR
(the initial failure and two restoration attempts). Again, `Target USB comms error`
occurred while opening the probe, before GDB connected. No second long suite was run.

Before reconnection, OpenOCD could not restore the board either: BOOT/GPIO 0/2,
an invalid V8J0S0 / VID:PID 0000:0001 version response, then initialization failure.
After physically reconnecting USB, BOOT/GPIO passed 2/2.
The original ERROR results and separate successful restoration were retained.

The symptom therefore reproduces on two different probes and MCUs; it is not
limited to the F411 unit. This does not isolate the cause among the server,
driver, USB connection, probe firmware and process lifecycle.
Probe firmware and reset code were not changed for the comparison.

Next diagnostic experiment: isolate server startup/shutdown and USB access, also
comparing another probe/cable. The current Windows path runs the server with `-e`
and forcibly stops it after GDB exits; an effect of this lifecycle is a hypothesis,
not an established cause. Reset commands were not changed to address a USB failure.

Full F411/F030/ST-LINK suites remain an open acceptance condition. Latest-SHA CI,
remote Orange Pi layouts and final release are not yet accepted. The consumer check
above covers minimal-consumer, not the private mcu_power_board project. Boards are
currently connected to Windows; historical Linux/SSH results below do not automatically
apply to this revision. The owner pushes and lands after CI.

## 0.3.0 package

API specification 0.3.6, general specification 0.68. `profile` (project data, build facts, case, stand, GDB)
replaces `config`/`config_props`; one `check` with matchers and a table, `refused`, `write(rows)` with an
expression as the value, `symbol`, `memory`, `locals`/`arguments`, C strings, navigation (`reach`, `finish`,
`step`, `until`, `watch`, `Point`), `ret`, `call`, `reset`, `execute`. A shared scenario directory with nine
showcase scenarios; the techniques are described in the [techniques catalogue](TESTING_TECHNIQUES.md).

Campaigns of 2026-10-05, five boards (F030R8 and F401CC/F411CE/F429ZI — ST-Link/OpenOCD, F103C8 — J-Link),
full suite: F030R8 48 scenarios, the others 50 each.

| Scheme | Runner and GDB → server | Outcome |
| --- | --- | --- |
| Local on Windows | Windows, GDB 14.2.90/15.2.90/16.3.90 (xPack 13.3.1/14.2.1/15.2.1) | 15 of 15 suites PASS |
| Local on a Linux stand | Orange Pi 5, Ubuntu 20.04 aarch64 | 5 of 5 PASS |
| Remote server | Windows → Orange Pi 5 over SSH | 5 of 5 PASS |
| Remote server | WSL2 → Orange Pi 5 over SSH | 5 of 5 PASS |
| Prepared-run package | built in WSL2, run on the Orange Pi 5 | 5 of 5 lifecycles at 10/10 |
| GitHub hardware CI | packages of the `prepare` job (ubuntu-24.04), run on the Orange Pi 5 self-hosted runner | 5 of 5 lifecycles at 10/10 |

In every suite the only non-PASS is the intended `timeout` check with its expected ERROR. The Linux-stand runs
found and closed two problems: a Cortex-M0 watch point stopping in a function epilogue (`HW_CI_WHO_WRITES`)
and a busy server port on the stand host (general specification 0.68). The F030 HAL fixture check without a
board, `python ci/run_checks.py hal`, passes. The package schemes check the lifecycle: build, prepare, boot, strict
identity, full and partial flashing, an image verification refusal, a timeout and the recovery.

## First package: record/records and config

Historical 0.2.0 acceptance; in 0.3.0 `profile` replaces `config`/`config_props`.


record/records and RecordError provide a per-invocation journal of copied ordinary
Python values with atomic limit failures. config/config_props expose immutable
selected configuration and its provenance. session.toml links external files;
SESSION_CONFIG is explicit. Legacy operation remains supported.
Journal export, additional frame/context operations and adaptive scheduling are excluded.

## Verified scenarios of the first package

Campaign dated 2026-10-03, working tree based on 7ed6d0a: CMSIS F030R8 19/19;
F103C8/F401CC/F411CE/F429ZI each 21/21, total 103. HAL F030 22/22,
minimal consumer 1/1. Windows, GCC13, GDB14; F103/J-Link, other boards
ST-Link/OpenOCD. Restoration BOOT/GPIO PASS. F103: profile Flash 64 KiB,
observed 128 KiB, image fits both. Separately: 31 positive repeats/restorations
and six expected timeout ERRORs. This is bounded historical evidence, not coverage
or verification of every later SHA.

44 table blocks (282 checks) have paired host regression for call order and first
failure: tests/host/test_scenario_tables.py. Five production
[test_measurements.py](../../tests/firmware/common/tests/board/test_measurements.py)
scenarios use config, record/records, mean and sample stdev. Numerical anchors and
negative cases: tests/host/test_measurement_scenarios.py.
Reproduce HW suites with [run_suite.py](../../tests/firmware/run_suite.py): explicit
session, restore-session and stand; without execute only prepare runs.

Current release acceptance is in [RC020_READINESS](RC020_READINESS.md).
Historical campaigns and release lifecycle are counted separately.

## Journal cost regression

The public [benchmark](../../tests/benchmarks/measure_records.py) uses only core code.
From the root: `python tests/benchmarks/measure_records.py build/records-cost.json`.
In GDB-Python, import the module by path and call run with the output path; no ELF,
server or MCU is required. Outputs remain local.

13 shapes: 10/128/1024 measurement pairs, lists with 4096/32768 nodes,
65536/524288-byte text, Unicode near 65536 bytes, a 4096-node dictionary,
depths 8/32 and 256/1024-bit integers. Five exact boundaries and atomic rejection
of excess are checked. After warmup: nine batches of ten operations, GC enabled;
compare medians of write/read batch means. Save an accepted-version baseline in
the same environment and compare the new implementation; investigate >2× slowdown
under API specification 6.5. These are not worst-case latency or RSS guarantees.
tracemalloc and reachable-object size are measured separately with preallocated inputs.

Initial integration passed in CPython and GDB14/GDB16: 13 shapes and five boundaries
per environment, without >2× regression. This is integration evidence, not portable
absolute timing. Standard records host tests check contractual limits independently.

## Composite technique and example verification — 2026-10-09

A separate series, not a recount of historical API acceptance: the three common scenarios
`HW_CI_EVENT_INTERVALS`, `HW_CI_WAIT_CHANGES`, `HW_CI_EVENT_INJECTION` passed 18 prepare and 18 HW runs.
The standalone `HW_CPP_CONTEXT` passed 12 builds, 12 prepare and 12 HW runs (Og/O2).
Boards: F030R8, F103C8, F401CC, F411CE, F429ZI through OpenOCD and AT32F403A through J-Link.
Original CI images were restored after both series: 24 BOOT/GPIO PASS, image_verified=true,
teardown=reset_run. GCC 14.2.1, GDB 15.2.90.20241130-git/Python 3.12.8, OpenOCD 0.12.0, J-Link 8.32.

Limits: nominal ticks do not establish timing accuracy; watchpoint IDs may be inferred.
C++ arguments remained available at O2; no hardware optimized-out case was observed.
The published wait scenario does not include an intentional timeout.
[Technique catalogue](TESTING_TECHNIQUES.md), [C++ example](../../tests/cpp-context/README.en.md).

### Single-quoted reach — 2026-10-09

C++ example rerun on the same six stands/tool versions: Og/O2, 12 prepare, 12 HW PASS,
original CI image restoration and BOOT/GPIO 12/12 PASS. Each run checks unquoted int and
single-quoted float, retaining the original location. Host also checks surrounding whitespace,
wrong-frame refusal and point cleanup. This is a focused reach regression, not full API acceptance;
complex linespec syntax is outside scope.


## SKIP — Unreleased

F030 SKIP, F411 PASS; skip after navigation on both, BOOT/GPIO recovery4/4. Stock package and actual CTest: F030 skipped, F411 passed. Local verification, not a release.

Additional: SKIP after navigation on F030/F103/F401/F411/F429/AT32, recovery12/12. run_hw rejects unexpected skip and accepts explicit allowance; stock recovery2/2. Docker host:381 tests, OK (4 existing skips); documentation PASS.

## st-util over SSH: recovery/idle — 2026-10-10

Runtime `4cb5e0a`: Windows → OrangePi, F030R8/F103C8/F401CC/F411CE/F429ZI.
xPack GCC13.3.1-1.1 (GDB14.2.90/Python3.11.4), helper Python3.11.16,
st-util1.9.0 with libusb1.0.27, OpenOCD xPack0.12.0-7.
Per board: smoke BOOT/GPIO, running/halted MCU timeout, BOOT/GPIO after each, OpenOCD restoration.
Total60 PASS and10 expected timeout ERROR with recovery; all70 outcomes expected.
st-util40 exit0 completions with helper idle; OpenOCD30 requested SIGTERM/exit-15. Release15/15 and final5/5.

The first run on previous runtime stopped on F030: parser did not recognize the Listening ellipsis.
After2/2 restoration checks the format was fixed and host regression passed (426 tests, Docker docs+host6/6).
Redirected Windows doctor required explicit UTF-8 ([HOWTO](HOWTO.md)). Disconnect, GDB encoding, missing
recovery ELF, SWD speed and F103 Flash capacity diagnostics are retained. F429 SP/SRAM anomaly did not
recur in this series; its previous cause remains unknown. This is a short lifecycle check; full suites
on new runtime, long series and deliberate SSH loss with real USB remain separate checks. Absence of
USB failures does not guarantee safe forced cleanup.


## Full st-util suites over SSH — 2026-10-10

The same runtime and tools completed F030R8 (45 scenarios), F103C8, F401CC, F411CE and F429ZI
(47 each):233 main scenarios. Including prepare, post-fault checks, timeout/recovery and restoration,
there are516 stages:243 prepare, 268 HW PASS and 5 expected timeout ERROR outcomes.
All263 st-util completions returned actual exit0 with confirmed idle. OpenOCD BOOT/GPIO10/10;
all five stands released their locks, with no server processes remaining after the suites.

The first full F411 run hit the60-second ADC_INVALID deadline although GDB saved140 passing checks.
That ERROR was not converted to PASS. A120-second diagnostic completed in61.625s.
The equivalent F401/F411/F429 matrix budget was therefore raised to120s; assertions and runtime are unchanged.
Repeated full F411/F429 suites passed; ADC_INVALID took61.657/58.890s. The changed F401 scenario
was checked separately:60.047s,140 checks PASS, OpenOCD BOOT/GPIO2/2 and clean release.
Durations include overhead outside GDB; they do not measure MCU function execution time.
F030/F103 and unchanged F401 scenarios were not rerun.

Logs retain disconnect, GDB encoding, inferred_stop, SWD speed and F103 Flash diagnostics.
No USB ERROR/libusb assertion was observed. The earlier F429 SP/SRAM anomaly did not recur;
its cause, earlier ST-LINK GDB Server failures and forced USB cleanup safety remain unresolved.
Docker docs+host6/6 (426 tests,6 expected skips); scenario style2/2.
This is local hardware acceptance for specific configurations, not a replacement for GitHub CI on the release SHA.

New selective campaign: [API 0.4.0 scenarios](API040_SCENARIOS.md), five STM32 boards including expected SKIP.

GitHub Hardware at `c23f8fe`: five boards, 20 PASS + 5 expected SKIP; 75 files reverified.
[Selected-suite evidence](API040_SCENARIOS.md#github-hardware-the-new-040-suite).

WSL2 → OrangePi/SSH at `d1a9361`: 20 PASS + 5 expected SKIP, 65 records; server shutdown confirmed 25/25.
[WSL2](API040_SCENARIOS.md).

Local Windows/st-util at `c156db5`: 20 PASS + 5 SKIP; 65 records. The first long-path attempt
is retained separately (10 PASS + 5 preflight ERROR); the repeat used a short directory.
[Windows](API040_SCENARIOS.md).

External package dispatcher on F411/OrangePi: finite cycles, STOP and unexpected SKIP;
[stand_loop](STAND_LOOP.md).

AT32/J-Link/OrangePi at `da5c4cb`: new 0.4.0 scenarios — 4 PASS + 1 SKIP, 13 records;
the initial probe connection ERROR is retained. [Sixth stand](API040_SCENARIOS.md).

GitHub Hardware #14 at `ba10b12`: AT32 — 4 PASS + 1 SKIP, 13 records; archive and 15 files verified. [API040](API040_SCENARIOS.md).
