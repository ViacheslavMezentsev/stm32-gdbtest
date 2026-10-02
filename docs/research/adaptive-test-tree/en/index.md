# Research 2: adaptive scenario tree

[Documentation](../../../en/index.md) · [Русский](../ru/index.md)

Simulated Python model of dynamic branch activation. No GDB, MCU, debugger or
production runner access. Public API and project specification remain unchanged.

- [Plan and semantics](plan.md) — directory structure, inputs/outputs and test selection.
- [S1 report](s1.md) — expected transitions, checks, limitations and reproduction.
- [HTML player](../results/player.html) — timeline slider and Play/Pause over recorded states.
- [Complete snapshots](../results/snapshots.json), [oracle verification](../results/verification.json).
- [Engine](../../../../tools/research/adaptive_tree/engine.py),
  [example tree](../../../../tools/research/adaptive_tree/fixtures/bringup/tree/node.json),
  [independent oracle](../../../../tools/research/adaptive_tree/fixtures/bringup/expected.json).

Branch `codex/adaptive-test-tree` starts from local main `da42cd7`. Two fetch attempts
ended with connection resets, so GitHub freshness was not confirmed. The first
GDB Python research remains on `codex/rc3-api-r1` at `fffa11d`, not merged here.

[Check summary](../results/checks.json): model14/14, Windows/Linux host, docs CI and browser.
