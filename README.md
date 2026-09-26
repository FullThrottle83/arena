# Arena Agent Mode — human-initiated delegation kit

**Purpose:** give an AI assistant a lightweight, evidence-based way to prepare work for Arena Agent Mode and review the result. Arena is a supplementary research/coding executor, **not** an automated API backend.

**Important:** [Arena Terms §5](https://help.arena.ai/articles/5629909088-terms-of-use) restrict automated/programmatic access to the Arena service. A delegating assistant may prepare a GitHub task brief and later review its PR, but **the user opens Arena, connects the selected repo and submits the task manually**. Do not script Arena's UI, scrape credits or invent an Agent Mode API. Read the [data policy](docs/data-handling.md) before linking a repository.

## Two different readers

| Your role | Read first | Responsibility |
|---|---|---|
| Claude, ChatGPT, Codex, Gemini, etc. **preparing and reviewing a task** | [DELEGATE.md](DELEGATE.md) | Choose bounded work, write a brief, give the user one launch instruction, review actual PR/diff/tests. |
| **Arena Agent** executing a task in its connected repo | [EXECUTOR.md](EXECUTOR.md) | Check actual branch/permissions, run the work, deliver a short result file and PR. |
| Exploring actual Arena capabilities | [AGENTS.md](AGENTS.md) → [capabilities](docs/capabilities.md) | Distinguish observed operations from documentation and untested claims. |

## Manual handoff, end to end

1. Delegator writes `.arena/tasks/0007.md` (or an issue) in the **target project repo**, following [templates/task.md](templates/task.md).
2. User opens [Arena Agent Mode](https://arena.ai/agent), connects that same project repo and sends the one-line [launch instruction](EXECUTOR.md#one-line-launch).
3. Arena reads the brief, performs bounded work on the **actual assigned branch**, runs checks and delivers a PR and `.arena/results/0007.md`.
4. Delegator reads the [result](templates/result.md), actual diff and test evidence, and tells the user whether acceptance criteria were met. User decides whether to merge.

No step requires programmatic access to Arena itself. GitHub is the coordination and artifact channel.

## Where Arena has been useful

- GitHub commit/push/PR, native public research, npm/pip, Python/Node and local servers were demonstrated.
- Local Chromium checks were demonstrated both on a synthetic fixture and on the real generated **Design Spells static build** ([PR #43](https://github.com/FullThrottle83/design-spells/pull/43)). Its `npm run build` executes `python3 scripts/build.py`, and the existing `npm test` suite was **not run in PR #43**; this was not proof of an Astro runtime or an Astro CLI build.
- A 14-source research exercise with a 36-claim ledger is in [PR #6](https://github.com/FullThrottle83/arena/pull/6); those verification counts are the agent's recorded checks, not an independent accuracy score.
- Design Spells PR #43 recorded `--no-sandbox` and `--disable-web-security` in the effective launch args but did **not** commit the launch script, so the latter flag's origin is unverified. Playwright normally adds `--no-sandbox` unless `chromiumSandbox: true`. See [browser caveat](docs/browser.md).

**Not established:** unrestricted public browser access, exact Agent Mode quotas, a fixed model identity, customer-data confidentiality, or full Lighthouse/WCAG/CWV compliance. Read [limitations](docs/limitations.md) and [modes](docs/modes.md).

## Reference library

[Capability matrix](docs/capabilities.md) · [GitHub](docs/github.md) · [Research](docs/research.md) · [Browser](docs/browser.md) · [Data handling](docs/data-handling.md) · [Benchmark](docs/benchmark.md) · [Lightweight job ledger](docs/ledger.csv) · [Historical evidence](docs/archive/README.md)

Last curated: 2026-09-26. This is an independent field guide, not official product documentation.
