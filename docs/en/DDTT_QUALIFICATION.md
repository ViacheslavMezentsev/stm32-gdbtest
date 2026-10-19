# DDTT condition qualification

[Documentation](index.md) · [Русский](../ru/DDTT_QUALIFICATION.md)

The first 0.5.0 package checks assertion applicability in the external exporter.
It neither qualifies the entire board nor rewrites result.json. The neutral
[example](../../examples/ddtt-qualification/README.en.md) includes **synthetic host data**
and a separate Renode route with a modeled receiver journal. No hardware measurements.

## Separate outcomes

- raw_state: the original CONFIRMED/FAILED/UNKNOWN projection; the scenario verdict
  remains in evidence.status and result.json.
- applicability: APPLICABLE, VIOLATED, UNKNOWN, NOT_APPLICABLE or NOT_REQUIRED.
- state: final coloring; missing applicability yields UNKNOWN even for raw FAILED.

UNKNOWN is omitted from numeric LCOV/Cobertura rather than exported as DA=0. An applicable
failure remains red. Shared lines prioritize applicable FAILED, then UNKNOWN, then
CONFIRMED. A newer attempt without admission never revives old green evidence.
An empty required set does not count as accepted.

## Map schema 2

Schema 1 remains compatible but rejects qualification fields rather than ignoring them.
Every schema 2 point explicitly declares requires=["clock"] or [] for independent checks;
required is a boolean defaulting to true. The top-level qualification has exactly context
and conditions:

```json
{
  "context": {
    "instance": "local-board-alias",
    "environment": "hardware",
    "elf_sha256": "<64 hex>",
    "inputs_sha256": "<64 hex>"
  },
  "conditions": {
    "clock": {"unit": "Hz", "min": 24900000, "max": 25100000, "max_age_s": 60}
  }
}
```

Environment and ELF must match the map. The organizer computes inputs_sha256 over a
canonical input inventory: board revision, scenarios, profile, SVD, stand, tools, wiring
and measurement chain. The project owns that inventory; the exporter compares hashes,
it does not infer physical identity or oscillator frequency. Changing conditions such
as supply must be checked immediately before dependent actions and monitored over the
relevant interval. A validity period is a measurement-procedure claim, not proof of
continuous observation.

Conditions use finite numeric intervals, explicit units and positive max_age_s.
Optional kind="capability" requires unit=present, min=max=1, and a measured 0/1 with zero
uncertainty. Proven absence gives NOT_APPLICABLE only for required=false points;
required points get VIOLATED. Unknown is not SKIP. Other predicates and scheduling
are outside this package.

## Snapshot and attempt binding

Snapshot JSON schema=1 has exactly schema, context, measurements. Context must match
the map. Each measurement contains:

| Field | Value |
|---|---|
| condition | conditions ID |
| value, uncertainty | finite numbers, uncertainty >= 0 |
| unit | exact rule match, no implicit conversion |
| observed_utc, valid_until | timezone-aware ISO timestamps |
| invalidated_utc | timestamp or null: a known invalidation event |
| method | measured for admission; declared does not establish applicability |
| evidence_sha256 | original measurement record hash, 64 hex |

Exactly one record must exist per required ID; missing/duplicate records are UNKNOWN.
The entire value ± uncertainty interval inside bounds gives APPLICABLE; entirely outside
gives VIOLATED; boundary overlap gives UNKNOWN. Admission must cover the whole result
interval started_utc + duration_s. Missing duration, future observation, expired age or
valid_until, and invalidation before the end block the assertion. Historical export uses
the attempt time, not the current export time.

The external organizer calls tools.ddtt_qualification.bind(result_path, snapshot), creating
admission.json next to result.json without overwriting an existing file. Fields:
schema=1, result_sha256, snapshot_sha256, snapshot. Snapshot hash is SHA-256 of JSON with
sort_keys=True, separators=(',', ':'), allow_nan=False, default ensure_ascii=True,
encoded as UTF-8. Result hash covers exact file bytes. Binding is created after the attempt
using conditions obtained beforehand; the hash itself cannot prove when they were obtained.

`ddtt_provenance seal` records the admission hash or its absence. Portable export checks it;
addition, deletion or modification after seal causes ERROR and invalidates previous output.
Unsealed export checks internal consistency, not deliberate simultaneous forgery of all
inputs. Original measurement records are not automatically loaded by hash; keep them locally.

## Reports and boundaries

Evidence/public-data schema=2 adds raw_state, applicability and acceptance: required count,
blocked count and accepted. Acceptance requires a nonempty required set whose points are
all CONFIRMED. This accepts selected assertions, not the entire firmware. Exit 0 still
means export succeeded; CI must separately check acceptance.accepted.

HTML line panels show raw outcomes, applicability and reasons. Portable output excludes
context, measurements, actual/expected and personal paths; it includes statuses, condition
IDs, reason codes and snapshot hash. Condition identifiers must be suitable for publication.

Runner and Target are unchanged. No automatic qualification, skip/scheduler or JSON injection
into [data] is provided. A consumer may prepare a corresponding TOML snapshot for existing
[data]; the neutral example now demonstrates that route. Next: a hardware pilot and measurement-chain validation. reach(main), HSE_VALUE
and virtual button injection do not prove physical characteristics.

## Renode check

The [executable example](../../examples/ddtt-qualification/README.en.md#renode-independent-receiver-journal)
uses a separate peripheral journal as the delivery reference. One ELF and scenario:
nominal, dropped word, nominal repeated; raw PASS is retained, and only the dependent
point is blocked when the condition is violated. This validates a deterministic model,
not physical MCU properties. The first package contract and schemas are unchanged.

The consumer example carries the JSON snapshot as a TOML string, records a
qualification_input receipt and verifies it before bind. This is a consumer convention
over existing APIs; raw PASS/FAIL and records remain unmodified.

## Reanalysing saved HSE evidence

Keep interpretation separate from the original hardware result: verify input
hashes, create a derived host projection and change map expectations, not the
measurement. Interval 24.987985–25.015135 MHz is APPLICABLE for 25 MHz ±1%, but
VIOLATED for 16 MHz ±1%; only the dependent assertion becomes UNKNOWN. Independent
memory comparison remains CONFIRMED. Boundary overlap or ended epoch yields
UNKNOWN, which LCOV must not turn red or retain as an old green point.

If the hardware protocol is not a runner result.json, do not replace its format.
Preserve it and create a mode=host analysis record containing its hash. Host
analysis timestamps describe import, not invented physical measurement times.
This tests exporter interpretation; it cannot admit hardware after restoration
or ELF changes. An actual subsequent scenario needs a prior snapshot within its
valid epoch.
