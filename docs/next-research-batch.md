# Arena Agent Mode — next research batch

**Prepared:** 2026-09-26  
**Repo:** [FullThrottle83/arena](https://github.com/FullThrottle83/arena)  
**Primary source:** [Drive research transcription](arena-agent-mode-research-2026-09-26.md)  
**Empirical baseline:** [Capability Inventory](../ARENA_AGENT_COMPLETE_CAPABILITY_INVENTORY.md) · [Probe Results](../ARENA_AGENT_PROBE_RESULTS.md) · [Capability Manifest](../ARENA_AGENT_CAPABILITY_MANIFEST.json)

## Baseline and unresolved conflicts

The initial empirical session exposed 15 functions plus a parallel wrapper; web search/page retrieval, bash, Python/Node smoke tests, local HTTP server, image generation/editing, and file creation worked. It did **not** expose Playwright or a browser executable in checked paths, a dedicated GitHub function, or numerical credit limits. Python/Node Playwright packages were absent. One shell HTTPS request failed, while dedicated web tools fetched external pages. Synthetic PDF/Office artifacts passed bounded structural checks, **not** end-user download or application validation.

The separate Drive research document contains broader claims. Its statements about unrestricted bash/network, automatically installable browser automation, live visual preview, or evaluation-specific turn caps must **not** be promoted to account-specific execution facts without direct evidence. Arena's GitHub integration is documented but was expressly not connected in the baseline session.

Each new investigation must preserve this distinction: **documented product feature ≠ exposed tool ≠ executable operation ≠ deliverable artifact**.

## Run order

Run **Arena A, B, and C in separate sessions**. Connect GitHub only in Arena A. Start **Gemini DR-1 through DR-6 simultaneously**, each in its own topic lane. Do not launch 20 overlapping general investigations; use their findings to choose second-wave gaps.

### Arena A — GitHub-connected coding workflow

Connect only the `FullThrottle83/arena` repository using Arena's GitHub Connector. Work on a new branch, not `main`.

```text
Investigate the GitHub-connected capabilities of this exact Arena Agent Mode session using the connected FullThrottle83/arena repo. Do not alter existing files, merge, or push to main. Identify actual exposed tool calls and the cloned workspace. Read README.md and docs/arena-agent-mode-research-2026-09-26.md. Create one harmless documentation file docs/probes/github-connected-session.md containing the visible repo/branch, exact commands and tool operations, results, permissions that can be safely observed, current limitations, and whether the diff UI works. Run a Markdown/file-existence check. If GitHub delivery is supported, commit to the working branch and create a draft PR for review. Do not invent a PR URL or claim a push succeeded without actual confirmation. Record whether the session exposes a dedicated GitHub tool that the unconnected session did not. Stop after returning a real PR link or an explicit blocker.
```

**Acceptance:** actual branch, diff, commit and draft PR or an accurately described failure. Do not merge automatically.

### Arena B — Playwright/browser capability by environment

Use a new session without GitHub. Do not install anything in the initial probe.

```text
Perform a narrow forensic browser capability probe in THIS Arena Agent Mode session. Identify whether a browser automation tool is exposed. Inspect Python and Node package metadata for Playwright/Puppeteer/Selenium, check browser executable paths, and record exact command outputs. If an executable and driver already exist, attempt a bounded headless launch; render a small local HTML fixture, inspect its h1, capture a real PNG screenshot, then check whether the output file can be presented. Test external navigation only after local tests pass, and distinguish shell networking from native page-retrieval tools. Do not confuse the preview iframe or image generation with actual browser automation. Do not install packages or browser binaries. Write docs/probes/browser-probe.md and browser-probe.json in the workspace. Mark dependency-blocked checks NOT_TESTED, not FAIL. Stop with exact evidence and a separate optional installation plan that requires my approval.
```

**Acceptance:** actual import/path/launch outcomes and no fabricated screenshots. Compare with the first session, which did not have the packages/binaries.

### Arena C — research and artifact delivery

Use a new session without GitHub.

```text
Prove that Arena can deliver a usable source-grounded technical research package. Research the official Arena Agent Mode and coding documentation, retrieve at least three distinct first-party pages, keep URLs and access dates, and note one disagreement or unresolved fact where relevant. Create research.md, sources.json, sample.pdf, and sample.csv using supported tools. Validate Markdown content, JSON syntax, CSV parsing, and PDF structure. Present each generated file through the workspace/file tool where available. Do not claim that I downloaded the files until I confirm it in the UI. Explain the no-GitHub ZIP download path and the limitations of your observed toolset. Return file paths, validation outputs and outstanding checks.
```

**Acceptance:** real files; source ledger; demonstrated downstream presentation. User manually confirms ZIP download.

## Shared Gemini Deep Research requirements

Every DR run should begin with:

> Research as of 2026-09-26. Treat the linked repository's empirical inventory and probe log as session-specific observations, not universal platform behavior. Separate first-party documentation, direct public examples, third-party reports and hypotheses. Give a URL and publication/update date for material claims, quote sparingly, and explicitly flag missing information. Do not treat Code Arena, Direct, Battle, Max, Agent Arena evaluation harness or Gemini/Opal capabilities as interchangeable with Arena Agent Mode. Produce a self-contained Markdown report with a claim/evidence ledger and an actionable list of tests. No invented usage limits, token savings, screenshots, package availability or browser access.

### DR-1 — Product and mode separation

Scope: Agent Mode vs Code Arena/WebDev/Fullstack, Direct, Battle, Side-by-Side, Max and external API/CLI products. Build a product-by-feature matrix and dated changelog. Check which features are actually accessible in Agent Mode.

Output: `ARENA_DR_01_PRODUCT_MODE_MATRIX.md`.

### DR-2 — Browser and Playwright capabilities

Scope: native browser/screenshot tools vs optional package installation; browser executables; preview proxy vs actual screenshot; JavaScript rendering, console/network, accessibility and PDF rendering. Verify official claims and document safe experiments; do not assert all Arena sessions contain Playwright.

Output: `ARENA_DR_02_BROWSER_AND_PLAYWRIGHT.md`.

### DR-3 — GitHub and workspace lifecycle

Scope: connector activation, OAuth scopes, repo/branch selection, sandbox clone, diff, commits, draft PR, merge/close lifecycle, files created after PR close, workspace ZIP and /download-workspace. Distinguish current documentation and obsolete experimental help results.

Output: `ARENA_DR_03_GITHUB_WORKSPACE.md`.

### DR-4 — Research quality and retrieval boundaries

Scope: source search and full retrieval, PDF handling and page limits, long-page chunking, academic materials, citations, contradictory evidence, context compaction, reproducibility, source/date capture, downloadable .md/.json outputs. Provide a repeatable five-source research benchmark.

Output: `ARENA_DR_04_RESEARCH_AND_SOURCES.md`.

### DR-5 — Compute, artifacts, networking and security

Scope: actual sandbox vs product promises; filesystem/process/dev-server limits, external shell HTTPS vs native web tools, package installs, binary artifacts, HTML/PDF/DOCX/XLSX validation, preview security, credentials, logs, data privacy and model/provider exposure. Avoid equating generic host information with account quotas.

Output: `ARENA_DR_05_SANDBOX_ARTIFACTS_PRIVACY.md`.

### DR-6 — Usage economics and practical fallback strategy

Scope: Arena daily credits, per-model/session limits, concurrency, reset behavior, documented vs account-only usage information, restrictions on automated/bulk use, file/PR retention and model disclosure. Contrast specific workflows among Arena, Google Opal, Gemini Deep Research and dedicated coding agents. Do not invent cost savings; propose a small measurement plan.

Output: `ARENA_DR_06_LIMITS_AND_FALLBACKS.md`.

## Integration gate

After the first wave, create `docs/capability-matrix.md` with columns:

`capability | official_source | arena_unconnected | arena_github_connected | tool_or_package | test_id | output_artifact | confidence | recommended_workload | remaining_gap`.

Also record which work requires live browser evidence, native web retrieval, a repo, a manual UI step or explicit authorization. Decide ownership of tasks only after these data are available.

**Do not launch another broad, repetitive “complete capability inventory” prompt.** The current evidence makes targeted counter-tests more valuable.
