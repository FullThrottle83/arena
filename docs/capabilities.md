# Capability matrix

**Scope:** observations from Arena Agent Mode sessions on 2026-09-26. `OBSERVED` means a named operation succeeded in at least one session, **not** preinstalled or universally accessible. The canonical raw test logs are listed in [evidence](evidence.md).

| Capability | Status | Evidence / boundary |
|---|---|---|
| Native web search and webpage retrieval | OBSERVED | [Initial probe](archive/initial-probe/ARENA_AGENT_PROBE_RESULTS.md), T-002–T-005; URLs and snippets, paginated page content. |
| PDF text retrieval | PARTIAL | One-page fixture plus arXiv PDF text; long/scanned/figure-heavy PDFs unverified. [Research probe](archive/probes/research.md). |
| Research with multi-chunk sources and citations | OBSERVED in a bounded run | [PR #6](https://github.com/FullThrottle83/arena/pull/6): 14 external documents, 44 chunk fetches, 36-claim ledger (31 marked verified and 5 unresolved by the executing agent). Not independently accuracy-scored or a guarantee for arbitrary long research. |
| Bash, Python, Node, subprocesses | OBSERVED | [Initial probe](archive/initial-probe/ARENA_AGENT_PROBE_RESULTS.md) T-001/T-007/T-010. |
| Package installation | OBSERVED | npm and pip reachable in tested session; apt/browser CDNs blocked in browser session. Check each session. |
| Local server and process control | OBSERVED | [T-011](archive/initial-probe/ARENA_AGENT_PROBE_RESULTS.md), [GitHub session](archive/probes/github-connected-session.md). Browser-side preview not proven by HTTP 200 alone. |
| GitHub read/edit/commit/push/PR | OBSERVED | [PR #2](https://github.com/FullThrottle83/arena/pull/2), [PR #3](https://github.com/FullThrottle83/arena/pull/3); through `git`/`gh` in bash. |
| Dedicated GitHub agent function | NOT EXPOSED in tested session | `gh` and injected auth were used; do not invent `open_pr` function. |
| Automatic isolated branch per simultaneous chat | DISPROVEN in these runs | Two sessions shared `arena/01a0dc7f-arena` and PR #2. Verify the actual branch. |
| Image generation and editing | OBSERVED | [Initial probe](archive/initial-probe/ARENA_AGENT_PROBE_RESULTS.md) T-012. Not a browser screenshot. |
| Markdown/JSON/CSV delivery via GitHub | OBSERVED | [PR #2](https://github.com/FullThrottle83/arena/pull/2) and [PR #3](https://github.com/FullThrottle83/arena/pull/3). |
| PDF/XLSX/PNG synthetic artifacts | PARTIAL | Committed/parsed; PDF and XLSX **not application-rendered**. [Validation](archive/probes/validation-results.md). |
| Preinstalled Playwright/Chromium | NOT FOUND at start | Probes checked Python/Node and common executable paths; may change by session. |
| Installed Playwright Core + Chromium | OBSERVED after installation | npm packages `playwright-core@1.63.0`, `@sparticuz/chromium@153.0.0`; [B04](archive/probes/browser-probe.json). |
| Local browser: DOM/JS/viewport/interactions/console/requests/screenshots/PDF | OBSERVED | B04–B13 on a fixture and six real static-page/viewport checks in [Design Spells PR #43](https://github.com/FullThrottle83/design-spells/pull/43). **Effective launch args included `--no-sandbox` and `--disable-web-security` in PR #43; the script is missing, so the latter's origin is unverified. Playwright defaults explain the former.** |
| Browser access to arbitrary public websites | FAILED in one test | B14 `https://example.com/` → `net::ERR_CONNECTION_CLOSED`; no general live-browser guarantee. |
| Full Lighthouse, WCAG or Core Web Vitals | NOT TESTED | One controlled axe-core fixture in [PR #6](https://github.com/FullThrottle83/arena/pull/6) is not an audit of a public target or WCAG conformance. |
| Real project build + local UI QA | OBSERVED on a **generated static** project | [Design Spells PR #43](https://github.com/FullThrottle83/design-spells/pull/43): `npm ci`, `npm run build` → Python `scripts/build.py`, local server, 3 pages × 2 viewports and 6 PNGs. **Existing `npm test` not run.** Not an Astro CLI/runtime build; not the live site. |
| Session quotas / exact token savings | UNKNOWN | The official daily period starts with the first prompt; no trustworthy account-specific per-task token/credit figure from probes. |
| `/tmp` across new sessions | NOT RELIED ON | Browser install was under `/tmp`; rerun/bootstrap on each new session. |

**Rule:** read [evidence.md](evidence.md) before promoting a capability to `verified`; use `EXECUTED_NOW` only with current-session outputs.
