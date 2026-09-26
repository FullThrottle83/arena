# Evidence and source policy

This is a **curated operational reference**, not a claim that every feature is available to every Arena account.

## Classify every claim

- `OFFICIAL`: dated first-party product documentation; not an execution result.
- `EXPOSED`: named callable tool visible in this session; does not prove execution.
- `OBSERVED`: a recorded operation in a named earlier session; note environment/date.
- `EXECUTED_NOW`: current-session command/tool output and artifact match.
- `PARTIAL`: only a bounded portion passed, or validation was structural.
- `FAILED`: a real attempted operation failed; retain the error.
- `NOT_TESTED`: absent evidence or dependency blocked; not a negative universal claim.
- `UNKNOWN`: no reliable public or session-specific measurement.

A source URL in a bibliography is not proof the cited claim is in that source. Research reports may have speculative descriptions of internal architecture, quotas, package availability or model routing. Prefer direct operation logs and product-specific first-party documentation.

## Primary execution ledger

| Record | What it supports |
|---|---|
| [Original capability inventory](archive/initial-probe/ARENA_AGENT_COMPLETE_CAPABILITY_INVENTORY.md) / [manifest](archive/initial-probe/ARENA_AGENT_CAPABILITY_MANIFEST.json) / [raw probe](archive/initial-probe/ARENA_AGENT_PROBE_RESULTS.md) | Unconnected baseline, tool list, shell, web, files, initial browser absence. |
| [Browser report](archive/probes/browser-probe.md) / [test manifest](archive/probes/browser-probe.json) / [actual PNG](archive/probes/browser-fixture.png) | Playwright/Chromium via npm package, local browser test B01–B15, failed external navigation. Original [PR #2](https://github.com/FullThrottle83/arena/pull/2). |
| [GitHub-connected probe](archive/probes/github-connected-session.md) | `git`/`gh`, npm/pip, preview server and delivery; original [PR #3](https://github.com/FullThrottle83/arena/pull/3). |
| [Research probe](archive/probes/research.md) / [source ledger](archive/probes/sources.json) / [validation](archive/probes/validation-results.md) | Small research and binary artifact experiment; shared [PR #2](https://github.com/FullThrottle83/arena/pull/2). |
| [Six long research reports](research/README.md) | Hypotheses, links and investigatory leads, **not** verified tool manifests. |

## What must accompany a new capability

Record: `date, session type, selected repo/branch, command/tool, input fixture, actual output/exit code, artifact path/hash where applicable, negative results, and scope`. Include a stable PR or commit URL. If a tool output is summarized, label it a summary rather than verbatim stdout.

For source-grounded research, fetch all relevant chunks, distinguish search snippets from retrieved pages, attach a source ID and URL to each material claim, and mark contradictions unresolved where appropriate.

For PDFs/Office files distinguish: created → parsed structurally → rendered/opened in a real application → user-accessible.

## Reproducibility correction — 2026-09-26

[Design Spells PR #43](https://github.com/FullThrottle83/design-spells/pull/43) contains a report, JSON and six screenshots but **not the code that launched Chromium**, and it did not run the project's `npm test`. Effective flags in the report do not establish their origin. A new run must commit the actual harness, effective (redacted) command line and existing-suite result before claiming a reproducible browser setup.
