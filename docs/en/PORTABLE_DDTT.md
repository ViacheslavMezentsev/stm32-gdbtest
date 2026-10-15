# Portable DDTT reports

[Documentation](index.md) · [Русский](../ru/PORTABLE_DDTT.md)

P1 tools do not change Target API. ddtt_coverage.py retains its interface. The optional map
environment selects hardware (default), emulator or host. Other environments and purpose=manual
are excluded; this does not implement interactive runner mode. The latest automated attempt
in the selected environment wins. ERROR/incomplete data is UNKNOWN. FAILED takes precedence
on a line; otherwise UNKNOWN prevents green DA. Comment-only anchors are rejected.

## Sealed campaign

From the consumer root, M is the module path:

```text
python M/examples/ddtt-coverage/bind_map.py --project . --elf build/app.elf --template hil/map.template.json --out build/map.json
python M/tools/ddtt_provenance.py begin --project . --revision FULL_SHA --map build/map.json --runs build/campaign/runs --out build/campaign/campaign.json --inputs src/app.cpp hil/test_app.py hil/map.template.json
# Run scenarios into the new runs directory; retain FAIL/ERROR.
python M/tools/ddtt_provenance.py seal --project . --runs build/campaign/runs --out build/campaign/campaign.json
python M/tools/ddtt_report.py --project . --map build/map.json --runs build/campaign/runs --campaign build/campaign/campaign.json --repository OWNER/REPO --out build/public-ddtt --annotations
```

Create build/campaign first. List all relevant tracked inputs, including configuration/model
and scenarios. Use a full revision SHA and a freshly built ELF. Before/after snapshots cannot
prove an arbitrary supplied ELF was built from these files. Do not edit inputs during the run.
The campaign binds the map, inputs and result hashes, validates timestamps and run.json.
Do not retroactively attribute old results to a new campaign.

The report recomputes outcomes from results. Public files are index.html, public-data.json,
lcov.info, coverage.xml and .nojekyll. Only allowlisted fields, relative paths and revision
links are exported, never arbitrary actual/expected/records. Scenario links use line 1 or an
explicit scenario_line. The author approves mappings. This detects accidental stale inputs,
not a deliberate forgery of all evidence; it is not a signed attestation.

## Viewing and CI

Open the consumer root in VS Code. Local ddtt_coverage LCOV uses absolute paths; the portable
LCOV uses relative paths. HTML needs no server/CDN: select a file and click a line for checks.
Dark/light/auto themes are available. UNKNOWN is excluded from numeric coverage. --annotations
emits GitHub notice/error/warning commands with source lines. Successful export exit 0 does
not imply scenario PASS; CI must separately propagate scenario failure.

Publish only public-ddtt as a static Pages artifact. Select Settings → Pages → GitHub Actions,
then use an explicitly triggered deploy workflow with pages:write and id-token:write after
tests pass. Its environment URL or Visit site opens the report. Publication/account settings
are not performed by the tool. Do not replace an existing site without authorization.
Workflow example: examples/ddtt-coverage/pages.yml.

See [Renode](RENODE_PROBES.md) and the [coverage skill](../../skills/stm32-gdbtest-coverage/SKILL.md).
