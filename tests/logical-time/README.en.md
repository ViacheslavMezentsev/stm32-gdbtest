# State machine with logical time

[Русский](README.md) · [TECH-022](../../docs/en/TESTING_TECHNIQUES.md#tech-022)

One neutral C++ module runs on the host and Cortex-M3 in Renode. No board or core changes.
`start(now, delay)` accepts IDLE/DONE/FAILED and enters WAITING; `poll(now)` completes
at elapsed >= delay; `fail()` only changes WAITING to FAILED. Repeated completion/failure
must not double-count. Restart after failure establishes a fresh epoch without reset.
Rejected starts (busy or delay outside 1..2^31-1) leave every object byte unchanged.

Time is uint32_t. The caller supplies monotonic modular ticks and polls before a full
wrap since start. Backward time and an entirely missed wrap cannot be distinguished
from these values. The delay bound does not detect a missed wrap.

Independent timelines: start(100,10), poll 109/110/111 => WAITING/DONE/DONE;
start(0xfffffff8,10), poll 0xffffffff/1/2/3 => WAITING/WAITING/DONE/DONE;
failed attempt then start(1000,10), poll 1009/1010/1011 => WAITING/DONE/DONE.
Additional checks cover rejected starts, a skipped threshold, repeated failure and
restart after success. Counters and guards are checked independently.

DEFECT 1 uses > instead of >= (three failing scenarios); 2 compares absolute deadlines
(one failure at wrap); 3 retains the old start after failure (one failed retry).
DEFECT 0 is corrected. Renode runs four scenarios for variants 1,2,3,0,0: 20 outcomes,
including five intended FAILs. Exact failing check names, capture, full POD restoration
using ELF symbol size and verified cleanup are required. Campaign PASS never rewrites FAIL.

Run `python tests/logical-time/run.py --host-only`, or add `--toolchain <ARM GCC root>`
and `--renode <executable>`. Requires host g++, Python 3.11+, GDB-Python and Renode 1.17.
Inputs, hashes, logs and summary are in build/logical-time/<id>. Windows Docker uses
one volume for source and builds; see [local CI](../../docs/guides/en/local-ci.md).

Correct: call returns an operation dictionary; check outcome/return_state, then compare
return_value. In async def, await call. Record observations before check; restore in finally.
Incorrect: compare the whole call dictionary to an integer, use a hidden call in read,
reset between failure and retry, or repeat a side-effecting call just to inspect its value.
A returned zero is an application rejection (check), not an API exception (refused).
Call timeout uses host seconds; logical tick values do not measure host or MCU duration.
Neither host sleep nor await wait advances this model's explicit clock. No claim about
physical timing, DMA/IRQ, scheduling, watchdogs or board recovery is made.

Validated on 2026-10-27: four host variants on Windows/Linux; Renode 1.17 on both
platforms produced 20/20 expected outcomes (15 PASS, 5 FAIL), including two corrected
runs, with ARM GCC 14.2.1 / GDB 15.2.90. Capture and POD restoration were checked
for every outcome. An initial scenario-author error comparing the call dictionary
to an integer was preserved separately and excluded from mutation acceptance.
