# S1 plan: dynamic pruning and reactivation

[Documentation](index.md) · [Русский](../ru/plan.md)

Goal: verify the proposed model without hardware by comparing the whole tree state
after every test with predefined expectations. This is a research model contract,
not an approved stm32_gdbtest extension.

## Structure and evaluation

Each directory contains `node.json`: id, enabled, activation, output, ordered tests
and children. Children are direct subdirectories; explicit lists define order,
not filesystem enumeration. Node and scenario IDs are unique in their respective
namespaces. Directory escape/reuse, unknown fields/facts and ambiguous JSON are rejected.

Node input is the **complete output of its immediate parent**; root input is empty.
Output contains named three-valued fields evaluated from input, shared facts and
own test results. Children do not contribute to parent output, avoiding circular
waiting. Global facts carry observations across branches.

Expression language: true/false/null, `{"fact":"name"}`, `{"input":"name"}`,
`{"results":"all"}`, `{"results":"any"}`, `{"all":[...]}`, `{"any":[...]}`.
No eval, Python callbacks or hardware reads. Validate names before the first step.
Activation cannot reference own results.

| Values | All | Any |
| --- | --- | --- |
| Empty | UNKNOWN | UNKNOWN |
| TRUE, UNKNOWN | UNKNOWN | TRUE |
| FALSE, UNKNOWN | FALSE | UNKNOWN |
| TRUE, FALSE | FALSE | TRUE |
| TRUE, TRUE | TRUE | TRUE |
| FALSE, FALSE | FALSE | FALSE |

Aggregation maps PASS to TRUE, FAIL to FALSE, ERROR/unexecuted to UNKNOWN. Original
ERROR remains ERROR in results. This model treats ERROR as insufficient evidence;
it is not a universal policy for a future API.

Active = enabled AND all ancestors active AND own condition equals TRUE. UNKNOWN
does not permit execution. Nodes without tests are complete=true, but empty All/Any
remains UNKNOWN. Activation, completion and success are independent. Even inactive
nodes recompute outputs; ancestor gating still blocks descendants. Evaluation is
top-down without fixed-point iteration.

## One step

1. Recompute all inputs/outputs/activation and save initial snapshot.
2. Choose first unexecuted active test: tree preorder, then tests list order.
3. Atomically record scripted outcome/reason and effects (fact updates).
4. Recompute the entire tree, save post-step snapshot and select again.
5. Stop when no eligible test remains. This means terminal, not “all passed”.

Unexecuted statuses are PENDING, BLOCKED and DISABLED, recomputed each time.
Executed PASS/FAIL/ERROR never change. Reactivation never repeats a test. Traversal
restarts at root, so recovery resumes previously blocked remaining tests in earlier
branches first. Execution is bounded by test count and max_steps; exceeding the
budget is a model error.

Snapshots contain schema/step, all facts with step/source provenance, results,
every node with parent/input/output/condition/active/reason/complete/tests,
ordered eligible queue, next and terminal. Returned deep copies can be changed
without altering engine history. Atomicity concerns the simulated Python step,
not real MCU state.

## Checks and boundaries

S1: latch → keys; link → protocol; independent temperature/recovery; disabled branch.
The oracle specifies every full snapshot, including inactive/completed nodes.
Also check All/Any, continuous ancestor activation, ERROR, invalidation to UNKNOWN,
reactivation, invalid inputs, terminal blocked state and detection of a deliberately
broken engine.

No real tests/reset, retries, concurrency, external events between steps, automatic
diagnostic insertion, TTL, persist/resume, CTest/JUnit integration or arbitrary
condition interpreter. Reset is modeled by explicit null effects. Arbitrary-node
dependency graphs, static fact-conflict analysis and large-tree scaling are possible
future research, not promises.
