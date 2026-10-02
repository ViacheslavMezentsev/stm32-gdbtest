# Proposal: named execution context

[Documentation](index.md) · [Русский](../ru/execution-context.md)

2026-10-02. **Contract proposal for discussion, not implemented API.** Yes,
scenario authors can be given `context['PC']`: a Python named mapping rather than
a C array. Proposed representation: an immutable snapshot of one stop, with
explicit provenance and data availability.

## Proposed shape

This only illustrates reading the proposed object after capture; current Target
has no method to obtain it. Method name and final schema are not approved.

```python
pc = context['PC']                       # int, physical stopped core PC
sp = context['SP']                       # int, active physical stack pointer
stop_id = context['meta']['stop_id']
frames = context['frames']               # immutable bounded sequence
if context['availability']['MSP'] == 'available':
    msp = context['MSP']
```

| Field/group | Proposed semantics | Evidence and limitation |
| --- | --- | --- |
| PC, SP | Required integer addresses of the physically stopped core, not a selected older frame | R1/R11/R16; independent of prior select-frame |
| LR, xPSR, MSP, PSP, CONTROL | Requested Cortex-M registers; capability profile defines names/widths | xPSR and basic MSP used in R10/R11; general contract for all fields remains untested |
| registers | Explicitly requested extra registers with type/width; no automatic full FP-state read | Scalar ABI R17/R18 does not prove complete FPU context preservation |
| stop | GDB event kind, all associated point numbers, signal and expectedness relative to an operation | R1/R2/R16; PC does not explain stop reason; multiple reasons must not collapse arbitrarily |
| frames | Bounded snapshots: index, kind, function, pc, source, availability; separate selected_index | R6/R15: recursion and inline; identical PCs allowed, name is not frame ID |
| interrupted | Separately requested interrupted context with hardware-frame decoding provenance | R11 only basic MSP; does not replace handler PC at top level; PSP/RTOS remain debt |
| values | Explicit locals/arguments/this with type, width and originating frame | R1/R15/R18; distinguish scope, optimized_out and unreadable |
| memory | Explicit bounded RAM ranges only: address/size/bytes | R1; SP alone is neither a dump nor stack boundary; consumer profile supplies bounds |
| meta | Schema version, run/image ID, stop_id, state_revision, inferior/thread/core IDs, architecture and capabilities | Proposed schema; GDB thread is not declared an RTOS task |
| availability | Status for each schema-defined field and requested element | available / not_captured / unsupported / optimized_out / out_of_scope / unreadable; separate failure detail |

Direct access returns a value only when `available`. Unknown keys raise `KeyError`;
known unavailable fields raise a dedicated availability error with code/reason
(class name undecided). Never substitute `0`, `False` or `None`. Unavailable required
PC/SP make base capture fail explicitly; partial diagnostics are kept separately
from successful context. Optional groups require explicit requests; no request
means `not_captured`.

## Freshness and consistency

1. Capture runs on the main GDB thread only after confirming the selected core is
   stopped. It neither resumes execution nor calls MCU functions. C expressions
   with possible writes/calls are outside base capture.
2. `stop_id` identifies a stop within a run; `state_revision` also changes on
   interventions without continue: register/RAM writes, forced return and similar
   operations make previous snapshots historical. Reset/reconnect/load invalidate
   live context even with identical PC. This extends R1: its continue-only epoch
   is insufficient for a general API.
3. Historical snapshots remain readable for comparison/reporting. Interventions
   using one as a precondition check run/stop/revision and reject stale snapshots.
   Reading saved `context['PC']` never accesses the MCU.
4. No live `gdb.Frame`/`gdb.Value` or lazy reads. Nested mappings/sequences are also
   immutable; JSON export creates a copy. Serialization preserves widths, large
   integers and special floats without precision loss or ambiguous JSON NaN;
   exact encoding remains to be agreed.
5. CPU registers and memory are read sequentially. Halt need not stop DMA,
   peripherals or other cores; this is not an atomic whole-MCU snapshot. MMIO is
   excluded by default because reads can clear flags. Profile extensions must
   specify addresses, read effects, order and bounds, retaining this limitation.
6. Raw GDB access outside the wrapper requires explicit invalidation/recapture:
   continue events cannot detect every console write. Automatic tracking of all
   external mutations is not a solved capability.

## Initial discussion scope and acceptance

Proposed minimum: PC/SP, stop, bounded frames, meta/availability. Typed values and
selected registers form the next negotiable layer. RAM/MMIO/IRQ decoding/RTOS must
not become implicit costs of every capture. Request parameters bound frames,
values, bytes and report size.

Agree key names/case, required fields, exceptions, serialization and integration
with navigation results before implementation. Before claiming readiness verify:
PC independent of selected frame; inline/recursion identity retained; distinct
unavailable statuses; resume and writes without resume invalidate freshness;
reset/reconnect cannot reuse identity; published snapshots immutable; no implicit
MMIO reads; explicit budgets/errors. Host model tests cannot prove MCU reads.
These checks are recorded in [D4](technical-debt.md) and are not being run now.

Foundation: the [consumer Research adapter](../../../../tests/api-experiments/lab/session.py)
already materializes values, bounds frames and tracks continue; R11/R15/R18 supply
hardware examples. The complete proposed `context` object does not yet exist.

The [API proposal](api-proposal.md) refines the frame group: frames/frame,
arguments/locals and caller helpers. context['frames'] and separate StackSnapshot
use identical records and innermost-to-outermost order; stack metadata include
complete and termination_reason (stack_end, depth_limit, unwind_error). Incomplete
stacks cannot prove caller absence. This is the current chain, not call history;
a graph of all calls is outside the snapshot.
