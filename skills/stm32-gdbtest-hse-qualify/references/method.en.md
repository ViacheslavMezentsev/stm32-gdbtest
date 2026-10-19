# Measurement and tolerance decision

[Skill](../SKILL.md) · [Русский](method.md)

## Independence and time reference

The MCU counter measures periods; host time supplies an independent interval.
HSE_VALUE, SystemCoreClock, UART baud or SysTick derived from the same HSE are not
independent references. RTT can transport counters but does not create a reference:
delivery time is not event time.

Use a monotonic clock such as perf_counter_ns on one host without sleep, VM
migration or epoch changes. Bracket each complete GDB/server/transport read.
Do not substitute wall time or command start time. Resolution and rate accuracy
are separate inputs.

A possible engineering basis is several SNTP exchanges with two different services
before and after the experiment over a sufficiently long interval. Preserve raw
requests/responses, addresses, transmit/receive/originate timestamps, monotonic
brackets, RTT, stratum, LI, root delay/dispersion/precision. Reject incorrect
originate, mode/version, unsynchronised servers, KoD, ambiguous eras or conflicting
references. Unauthenticated server quality remains a server claim.

For reference i, server time Si lies within local request [ai,bi], with server
error ±Ei. For two references form positive local duration [a2-b1,b2-a1] and
external duration [S2-S1-E1-E2,S2-S1+E1+E2]. Interval division bounds the host clock
rate relative to external time. Check the whole span and subintervals, agreement
between services and possible common upstream dependencies. Add a justified
allowance for unobserved short-term drift. Conflicting/incomplete references do
not justify reducing the budget or claiming calibration. If network references
cannot support the requested tolerance, use a more accurate external reference.

## Measurement chain

From the specific MCU reference manual confirm SYSCLK source, AHB/APB divisors,
timer multiplier, prescaler, ARR, counter mode, clock gating and debug freeze.
Derive D = f_HSE/f_counter; do not assume the timer always doubles APB frequency.
PLL or external clock input changes the derivation. Exclude bypass and fallback
to HSI when qualifying a crystal.

CNT requires one fresh read of the correct width, without caching, repeated reads
or function calls in expressions. The MMIO contract constrains module-side
requests; verify transport/peripheral behaviour separately. Matching route reads
before/after cannot exclude an intervening change that was reverted: exclusive
ownership and epoch continuity are prerequisites. DMA/timers may run while the
core is halted. Do not use RTOS waits in a halted sandbox.

For a rising 32-bit CNT capture c1 inside monotonic bracket [a1,b1], then c2
inside [a2,b2] after a wait. Capture route/epoch before and after, halt state and
confirmation that the counter continues. Let e = clock_budget_ppm / 1e6 and r be
a conservative per-timestamp error in seconds, at least the clock resolution.
For 0 ≤ e < 1:

```text
Tmin = (a2 - b1 - 2r) / (1 + e)
Tmax = (b2 - a1 + 2r) / (1 - e)
delta = (c2 - c1) modulo 2^32
fmin = max(0, delta - 1) * D / Tmax
fmax = (delta + 1) * D / Tmin
value = (fmin + fmax) / 2
uncertainty = (fmax - fmin) / 2
```

Times are seconds, all values finite, Tmin > 0. ±1 count covers quantisation.
Supply an independently justified physical counter ceiling Fmax. Require
`Tmax * Fmax + 1 < 2^32` and `delta <= Tmax * Fmax + 1`; otherwise wraps are
ambiguous or the chain violates its assumptions. Never derive Fmax from measured
delta. Zero delta does not confirm a working oscillator. Do not clip the interval
to tolerance or select a smaller budget to obtain a desired outcome.

## Decision and negative controls

Define allowed interval [L,U] before measuring, e.g. f0 × (1 ± p/1e6) for p ppm;
boundaries are inclusive. Check integrity and required precision first:

| Condition | Admission verdict |
| --- | --- |
| Entire measurement interval inside [L,U] | IN_TOLERANCE |
| Entire interval strictly below L or above U | OUT_OF_TOLERANCE |
| Boundary overlap, insufficient precision or unknown reference | UNKNOWN |
| Corrupt inputs, route/epoch change or transport failure | Measurement ERROR; admission UNKNOWN |

These are methodology terms, not new runner statuses. Retain raw scenario results
separately from analysis/admission. In DDTT, missing admission blocks only dependent
assertions; independent checks remain available.

Offline controls: identical samples against 25 and 16 MHz expectations; a boundary
crossing interval; conflicting references; unknown clock budget; a short window;
a valid single CNT rollover versus ambiguous wraps; changed epoch. Synthetic or
Renode PASS does not measure a physical crystal.

## Tested example and portability

F411/OpenOCD pilot: SYSCLK=HSE, AHB=APB1=1, TIMPRE=0, TIM2 PSC=24,
ARR=0xffffffff, TIM2 debug freeze disabled. D=25; the independent HSE ≤ 50 MHz
assumption gives Fmax=2 MHz. TIM2 runs during core halt; window about 10 seconds.
PA8 AF0 MCO1=HSE/5 was an available output for future instrument comparison,
not an independent measurement. Revalidate the chain/registers on another MCU.

With an accepted 500 ppm host engineering budget, measured HSE was 25.001560 MHz,
interval 24.987985–25.015135 MHz, relative half-width 0.0543%, entirely inside ±1%
of 25 MHz. Six repeated NTP replies from two services over about 620 seconds
bracketed the experiment; conditional estimates agreed, observed bound about
175 ppm. The 500 ppm budget was retained. This is one engineering pilot, not
universal accuracy or temperature-drift qualification. The central +62 ppm
nominal deviation is smaller than the ±543 ppm uncertainty.

## Cleanup, restoration and evidence

Before changes, agree on affected memory/pins; capture fresh double Flash/SRAM
snapshots and original CPU/debug/peripheral state, verify hashes and restoration
feasibility. Limit permitted Flash erase sectors. Archive original live state
separately from the chosen reset-halt baseline.

For this F411: halt → HSI on/ready → SYSCLK=HSI/SWS verified → TIM2 stop/interrupts
off → PA8 input → HSE off/ready cleared → restore Flash if different → full Flash
comparison → reset-halt → restore SRAM last/full comparison → verify selected
CPU/debug/config masks. Flash programming algorithms can overwrite SRAM, hence
RAM is restored last. Never replay raw RO/W1C snapshots. Reading clock-gated GPIO
does not prove its internal state; restoration here relies on reset, with masked
comparison only as an additional check.

An external supervisor bounds GDB/server execution, terminates only owned
processes and has a separate recovery entrypoint bound to fresh verified backups.
No protection removal, option-byte changes or mass erase. After failure, stop new
experiments until restoration is confirmed. An independent connection must
confirm memory and selected state; explicitly report final halt/run.

Record requirement/tolerance, clock route, ELF/SVD/scripts and hashes, tool
versions, raw counters/brackets, references and budget, uncertainty/verdict,
snapshots and separate recovery outcome. Keep serials, personal paths and backups
local. Admission does not automatically transfer across reset, changed ELF or
epoch: application applicability requires explicit justification.
