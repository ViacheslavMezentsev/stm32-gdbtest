# M5: first-package requirements

[Research](index.md) · [Русский](../ru/m5-contract.md)

On 2026-10-03 the owner accepted first-package scope and versions (Q16).
[API spec 0.2.0](../../../TECHNICAL_SPECIFICATION_API.md) retains the rc.2 baseline
and adds normative requirements; [system spec 0.60](../../../TECHNICAL_SPECIFICATION.md)
defines configuration loading and transport. Core remains rc.2.

## Accepted decisions and requirements

| Decision | Requirements |
| --- | --- |
| record/records: copies, types, sequence, filters, lifetime | API spec 3.3, 4.9–4.10 |
| Public RecordError, code/limit, rejection without journal changes | API spec 4.9.3, 5.3–5.4 |
| config/config_props: immutable effective values/defaults and source properties | API spec 4.11–4.12 |
| Configurable limits, accounting and cost measurements | API spec 6.3–6.5; numbers open |
| api.toml schema, unknown/user, independent versions | API spec 7.1–7.5 |
| session.toml, CMake/JSON, conflicts, capture, transport, legacy | System spec 5.20 |
| Module target 0.2.0, API_VERSION=1, api.toml schema=1 | System spec 8.48 |

The exact prerelease will be selected before release. read, context/stack/caller
and finish are excluded from this package. Accepted requirements do not authorize
core integration.

## Verification status

M5 documents requirements without new hardware runs. Both specifications include
acceptance criteria and traceability matrices. Existing evidence:
[E1](e1.md), [F0/F1](portability.md), [M2/M3](config-loader.md),
[M4 transport](config-transport.md), [M4 pipeline](config-pipeline.md).
These results apply to research prototypes.

M5 validation in Docker CI: docs 4/4 PASS (both specifications in strict mode,
links, RU/EN pairs); three-component revision-checker regression 2/2 PASS.
No runtime changes or new hardware runs.

RecordError.code/limit still needs implementation even in the prototype. Legacy
views, journal isolation and future Target lifecycle interaction need integration
verification. Public import location and exception base class remain undecided.
The internal envelope format and defaults-comparison algorithm will be specified
during integration; raw TOML+SHA256 transport and rejection of incompatibility
are already accepted.

## Next steps

1. Measure record/records costs for typical and boundary inputs in Python/GDB,
   justify defaults and upper bounds, and propose a Q6/Q19 decision.
2. Resolve RecordError import/base-class details; obtain separate permission
   to integrate the accepted scope.
3. Once authorized, perform M6: integrate, verify legacy mode, new contracts and
   adapted scenarios, and retain a separate acceptance report.

128/4096/8/65536/256 remain prototype parameters. First-package acceptance is
incomplete until costs are agreed and integration regression is completed.
