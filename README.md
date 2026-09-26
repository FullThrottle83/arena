# Arena Agent Mode — field guide

A concise, evidence-based reference for using [Arena Agent Mode](https://arena.ai/agent) for **any project**: coding, GitHub changes, research, static-site QA and file delivery.

**Start here:** [Data handling](docs/data-handling.md) → [Agent instructions](AGENTS.md) → [Capability matrix](docs/capabilities.md) → [Workflows](docs/workflows.md). Read only the topic you need. The detailed 2026-09-26 experiments and long research reports are archived, not loaded by default.

## Current observed capabilities (2026-09-26)

- **Verified in tested sessions:** native web search/page retrieval, bash, Python/Node, npm/pip from reachable registries, local HTTP servers, file creation, image generation/editing, and GitHub commit/push/PR via `git`/`gh`.
- **Browser proven on a local fixture after installation:** Playwright Core 1.63.0 + npm-bundled Chromium 153.0.8010.0; real DOM/JS, screenshots, responsive checks, interactions, console, requests and PDF. See [browser recipe](docs/browser.md) and [evidence](docs/evidence.md).
- **Not proven:** arbitrary public-site navigation in Chromium (one test failed with `ERR_CONNECTION_CLOSED`), full WCAG/Lighthouse/CWV audits, unlimited quotas, cross-session `/tmp` persistence, complete long-form Deep Research, or general compatibility across all Arena sessions.

**Do not mistake a package, model claim, AI-generated report, HTTP response or generated image for execution evidence.** Capabilities can differ between sessions and over time.

## Pick a workflow

| Task | Read |
|---|---|
| GitHub coding / Astro / UI tests | [Workflows](docs/workflows.md), [GitHub](docs/github.md), [Browser](docs/browser.md) |
| Research / source verification | [Research](docs/research.md) |
| Public website audit | [Limitations](docs/limitations.md), [Browser](docs/browser.md) |
| Assess a new tool or claim | [Evidence rules](docs/evidence.md), [Capability matrix](docs/capabilities.md) |
| Reusable prompts | [prompts/](prompts/README.md) |
| Data rights / customer data | [Data handling](docs/data-handling.md) |
| Task usefulness & repeatability | [Benchmark protocol](docs/benchmark.md) |

## Repository layout

- `AGENTS.md` — short, portable instructions for agents using this knowledge base.
- `docs/` — curated facts, recipes, limitations and open questions.
- `prompts/` — ready-to-run, task-specific prompts.
- `docs/archive/` — historical probe logs and original reports. Archival content is **not** a current capability guarantee.
- [PR #2](https://github.com/FullThrottle83/arena/pull/2) and [PR #3](https://github.com/FullThrottle83/arena/pull/3) — original experimental delivery history.

## Using this from another project

Tell your agent: “Read `https://github.com/FullThrottle83/arena/blob/main/AGENTS.md` and the linked capability docs before planning. This repo is a reference, **not** the target codebase. Verify tools and permissions in your own Arena session; work only in my explicitly selected project repository.”

Last curated: 2026-09-26. This is a field guide, not an official Arena product specification.
