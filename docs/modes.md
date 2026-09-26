# Arena modes — don't transfer capability claims between products

**Checked:** 2026-09-26. Product/account features change; use first-party docs and test your signed-in UI. The [data handling](data-handling.md) and Terms apply to content regardless of the mode.

| Mode | Intended job | Model/credit/delivery note | Relevance |
|---|---|---|---|
| **Agent Mode** | Multi-step research/coding with tools, files and sandbox; optionally connect a repo. | Orchestrator assigned per chat and normally hidden; may switch for recovery. GitHub-connected delivery via branch/PR. Exact credit cost/session limits unverified. | Main human-initiated delegation path. |
| **Direct** | Converse with a user-selected model. | [Official model selector](https://help.arena.ai/articles/1858200927-arena-experiments-new-model-selector); this does not make it a GitHub coding agent. | Short analysis or reviewing an output when model choice matters. |
| **Side-by-Side** | Compare two selected models on a prompt. | Separate from Agent Mode and its toolchain. | Compare explanations/drafts, not proof of repo execution. |
| **Battle (Text / Code Arena)** | Compare two anonymously selected responses or coding outputs; vote based on actual preference. | [Official credit help](https://help.arena.ai/articles/5476762589-credit-sytem): Battle in Text Arena/Code Arena does **not** count toward daily credit balance. This does not imply unlimited usage or free Agent Mode. | Optional comparison/prototyping, not programmatic job delegation. |
| **Fullstack Code Arena** | Build/compare full-stack app generations, previews, DB/auth and Vercel flow. | [Separate product announcement](https://arena.ai/blog/fullstack-code-arena). Do not infer these tools are exposed in an Agent Mode session. | Prototype/evaluation if terms and data classification permit. |
| **Image/Video Arena** | Generate/compare modality-specific outputs. | Distinct access and rate rules; verify mode-specific help rather than assuming the Agent Mode credit rule applies. | Public/synthetic visual experiments. |

**Credit interval:** official [credit help](https://help.arena.ai/articles/5476762589-credit-sytem) says the daily 24-hour period starts when the first prompt is sent. The remaining balance is shown near the limit; per-tool credit price is not established here.

**Automation restriction:** [Terms §5](https://help.arena.ai/articles/5629909088-terms-of-use) prohibits automated/programmatic service access. GitHub task briefs and PR review are external coordination; the user starts the Arena session manually. No endorsed Agent Mode API is established by this repository.
