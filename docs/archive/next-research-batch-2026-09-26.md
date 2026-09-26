# Arena Agent Mode — next research batch

**Prepared:** 2026-09-26  
**Repo:** [FullThrottle83/arena](https://github.com/FullThrottle83/arena)  
**Primary source:** [Drive research transcription](arena-agent-mode-research-2026-09-26.md)  
**Empirical baseline:** [Capability Inventory](../ARENA_AGENT_COMPLETE_CAPABILITY_INVENTORY.md) · [Probe Results](../ARENA_AGENT_PROBE_RESULTS.md) · [Capability Manifest](../ARENA_AGENT_CAPABILITY_MANIFEST.json)

## Baseline and unresolved conflicts

The initial empirical session exposed 15 functions plus a parallel wrapper; web search/page retrieval, bash, Python/Node smoke tests, local HTTP server, image generation/editing, and file creation worked. It did **not** expose Playwright or a browser executable in checked paths, a dedicated GitHub function, or numerical credit limits. Python/Node Playwright packages were absent. One shell HTTPS request failed, while dedicated web tools fetched external pages. Synthetic PDF/Office artifacts passed bounded structural checks, **not** end-user download or application validation.

The separate Drive research document contains broader claims. Its statements about unrestricted bash/network, automatically installable browser automation, live visual preview, or evaluation-specific turn caps must **not** be promoted to account-specific execution facts without direct evidence. Arena's GitHub integration is documented but was expressly not connected in the baseline session.

Each new investigation must preserve this distinction: **documented product feature ≠ exposed tool ≠ executable operation ≠ deliverable artifact**.

## Run order: GitHub connected in every Arena session

Run **Arena A, B, and C in three distinct GitHub-connected Agent Mode chats**, which can be started concurrently if the account's live usage/rate limits permit it. Each session selects `FullThrottle83/arena`, starts from `main`, works on its **own branch**, edits **non-overlapping paths**, and creates **at most one PR**. Do not work in three prompts inside one chat: Arena's help currently specifies one PR per session. Do not merge/close any PR while its session still needs to push; review all diffs before merging.

Each session must explicitly verify GitHub is toggled on and the repository is selected. A connected session has its own sandbox clone. If the UI chooses a generated working-branch name, record that real name rather than inventing a branch. Request a draft PR if the UI supports it, otherwise an ordinary PR marked "not ready for merge." Never push directly to `main`.

Suggested non-overlapping ownership:

| Session | Branch name if selectable | Owned paths | Deliverable |
| --- | --- | --- | --- |
| A — GitHub | `arena/probe-github` | `docs/probes/github-connected-session.md` | One PR with GitHub workflow findings |
| B — Browser | `arena/probe-browser` | `docs/probes/browser-probe.md`, `docs/probes/browser-probe.json`, optional `docs/probes/assets/browser-fixture.png` | One PR with real browser evidence or blocker |
| C — Research/artifacts | `arena/probe-artifacts` | `docs/probes/research-artifacts/` only | One PR with sources, generated fixtures and validation |

Run **Gemini DR-1 through DR-6 simultaneously** in separate topic lanes. Avoid launching 20 copies of generic research.

### Arena A — GitHub-connected coding workflow

Open a fresh GitHub-connected Arena Agent session and select `FullThrottle83/arena`.

```text
Use the GitHub Connector for the already-selected FullThrottle83/arena repository. Work from main on a dedicated working branch (suggested: arena/probe-github); if Arena assigns a different branch, record it. Do not push to main, touch B/C owned paths, overwrite existing documents, merge or close a PR. Inspect the live connected repo and exact available GitHub operations, sandbox clone, selected branch, and Diff/Checks panels. Read README.md and docs/arena-agent-mode-research-2026-09-26.md. Create ONLY docs/probes/github-connected-session.md with the exact tools/commands used, observed results, safe permission observations, repository and branch details, diff behavior, and what is still unverified. Verify the file exists and review the diff. Commit and push it on this session's branch; create this session's one PR (draft if available). Return its REAL URL or the exact blocker. Stop while the PR is still open.
```

**Acceptance:** observed branch and diff; successful commit/push/PR or a clearly documented failure.

### Arena B — Browser/Playwright investigation with GitHub delivery

Open a DIFFERENT GitHub-connected Arena Agent session and select the same repo, starting from main. Do not install anything in the initial probe.

```text
Use the connected FullThrottle83/arena repo on a separate branch (suggested: arena/probe-browser). Own ONLY docs/probes/browser-probe.md, docs/probes/browser-probe.json, and optionally docs/probes/assets/browser-fixture.png. Do not touch Session A/C files or main. Inspect the ACTUAL exposed browser-specific tools, Python/Node metadata for Playwright/Puppeteer/Selenium, available browser executables and paths. Record exact results. If a compatible driver and executable exist, attempt a bounded headless launch, render a harmless LOCAL fixture, check its h1, capture an actual PNG screenshot, and validate its signature/dimensions. Do not pretend a preview iframe or generated image is a screenshot. Test public navigation only after local tests pass; distinguish shell networking from native page retrieval. No downloads, browser installs, package installs or sandbox-flag bypasses without my separate approval. Mark blocked dependent checks NOT_TESTED. Commit findings and any genuine small image artifact to this branch and create one PR (draft if available). Provide real PR URL or exact blocker; do not merge/close the PR.
```

**Acceptance:** actual probe evidence; screenshot only if produced by a real browser; one isolated PR.

### Arena C — Research and artifact delivery with GitHub

Open a THIRD GitHub-connected Arena Agent session and select `FullThrottle83/arena` from main.

```text
Use the connected FullThrottle83/arena repo on a separate branch (suggested: arena/probe-artifacts). Work ONLY under docs/probes/research-artifacts/. Do not modify Session A/B files or main. Research Arena Agent Mode using at least three distinct first-party pages and preserve URLs and access dates. Create research.md, sources.json, sample.csv, and a small sample.pdf if real binary PDF generation and GitHub delivery are possible. Produce a validation-results.md with genuine Markdown checks, JSON parse, CSV readback and PDF integrity result; never claim application-level PDF validity from a header-only check. Verify all intended files are in the Git diff; commit and push them to your working branch and open this session's single PR (draft if supported). GitHub is the PRIMARY delivery path; do not rely on a ZIP download. If an artifact cannot be committed, mark it UNDELIVERED and preserve its metadata, rather than inventing a link. Return the actual PR URL or exact blocker. Do not merge/close the PR.
```

**Acceptance:** source-grounded files and validation, a real PR, clear classification of binary artifact delivery.

### Parallel coordination and merging

- Start each task in a **separate chat**, not one shared conversation; each gets its own sandbox and working branch.
- Confirm GitHub is enabled in EACH chat and each sees the same repo. The platform may still apply account-level usage/rate limits; simultaneous completion is not guaranteed.
- Branches must not share file paths. All three PRs should initially target `main`.
- Preserve each PR unmerged while its Arena session is active; Arena warns that closing/merging ends GitHub push capability for that session.
- Review PRs and merge **one at a time** only after each is finished; refresh/rebase if GitHub reports a conflict.
- One PR per chat is the currently documented constraint. If a task needs another independent PR, start a fresh chat.
- A later consolidation session may read the merged reports and create `docs/capability-matrix.md`; it should use a fresh branch/PR.

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

`capability | official_source | arena_baseline_unconnected | arena_github_a | arena_github_b | arena_github_c | tool_or_package | test_id | output_artifact | confidence | recommended_workload | remaining_gap`.

Also record which work requires live browser evidence, native web retrieval, a repo, a manual UI step or explicit authorization. Decide ownership of tasks only after these data are available.

**Do not launch another broad, repetitive “complete capability inventory” prompt.** The current evidence makes targeted counter-tests more valuable.
