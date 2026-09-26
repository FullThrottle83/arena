# Where Arena fits

Use this as a decision guide, not a model ranking or guarantee of quota availability. **Before selecting a repo or uploading files, apply the [data-handling gate](data-handling.md).** Compare real value with the [benchmark protocol](benchmark.md).

| Workload | How to use Arena | Important gate |
|---|---|---|
| GitHub repository changes | Connect **that project's** repo; inspect, edit, test, diff, push, PR. | Check actual branch and concurrent sessions. |
| Astro / static-site work | Install dependencies if permitted; build, run local server; use the [browser recipe](browser.md) for local UI tests. | A real Astro scaffold/build remains unverified in the original probes. |
| Design/CSS demos | Render local pages, test viewport overflow, interactions and screenshot hash. | Don't confuse local render with live deployment. |
| Technical research | Search/fetch and deliver source ledger + concise Markdown. | All chunks, accurate citations; depth benchmark remains open. |
| Uploaded crawl exports | Use scripts to parse/filter/deduplicate, then generate JSON/CSV/MD results. | Test actual file size/coverage and avoid inventing crawl data. |
| Public website audit | Native page retrieval for preliminary research; live browser only if navigation to target actually succeeds. | No arbitrary public-browser access proven; no Lighthouse/CWV/WCAG claim by default. |
| Reporting | MD/JSON/CSV proven; small PDF/XLSX structurally checked. | Application rendering/formula recalculation separately required. |
| Agent handoff | Record source files, decision log, tests and blocker; deliver via PR. | No credentials, no unverifiable “done” claims. |

## Standard acceptance contract for all projects

Specify target repo and allowed paths, expected outputs, test commands, evidence and stop conditions. Ask the agent to return **actual branch, commit, PR, changed files, tests passed/failed/not run, and manual steps**. A successful PR is not proof the requested product works unless the relevant build/functional checks pass.

Reusable complete prompts: [project implementation](../prompts/project.md), [research](../prompts/research.md), [local website audit](../prompts/site-qa.md).
