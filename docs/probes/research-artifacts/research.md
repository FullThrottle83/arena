# Arena Agent Mode: Research & Artifact Capability Probe

- Investigation date: 2026-09-26
- Repository: `FullThrottle83/arena` (origin `https://github.com/FullThrottle83/arena.git`)
- Branch: `arena/01a0dc7f-arena`. Arena assigned this branch and it cannot be changed, so the requested `arena/probe-artifacts` was not used. It was created from `main` @ `1263076`.
- Scope: all outputs are in `docs/probes/research-artifacts/`

## 1. Executive summary

Arena Agent Mode completed a small, source-grounded research task and delivered validated artifacts through GitHub in one session. Verified points:

- **Research tools work.** Web search returns snippets with a `pageAge` field. Full-page fetch returns markdown in numbered chunks. Academic PDFs from arXiv are parsed into structured text, including LaTeX.
- **Delivery through GitHub works.** Arena's first-party docs say a session connected to a repo delivers files through a working branch and a pull request (PR), not a zip download. This session behaved that way.
- **Sources disagree on pushing to main.** Arena's blog and X post say the agent can "push directly to your main branch". The runtime in this session restricts pushes to one assigned branch. Both are recorded; neither is treated as the answer for every session.
- **Sandbox networking is selective.** The fetch tool retrieved help.arena.ai and arxiv.org, but `curl` to the same hosts from the sandbox failed with a TLS error, while PyPI worked.
- **No browser automation** was documented or installed. **Usage limits** are documented only as existing; no numbers are given.
- **File generation is limited by installed libraries.** PDF, XLSX and PNG files were generated after installing Python packages. No office suite or browser was available, so none of these files could be opened in a real application.

## 2. Methodology

1. Confirmed the repo remote, branch and base commit with `git`.
2. Ran `web_search` at depth 2 for Arena Agent Mode docs, GitHub integration, rate limits and browser automation.
3. Retrieved full pages with `fetch_page` for the primary sources (S1 chunks 0–1 of 3; S2 chunk 0 of 2). Sources available only as search snippets are labelled that way (S3–S7) and were not treated as full documents.
4. Tested PDF and academic-document retrieval on arXiv:1706.03762 (S8).
5. Collected runtime evidence in the sandbox (R1): `curl` reachability, `pip`, installed binaries and resources.
6. Generated the artifacts and validated each one with a parser (see `validation-results.md`).
7. Scanned the changes for secrets, committed only this directory, pushed and opened a draft PR.

Dates are taken only from the pages themselves or from the search result's `pageAge` field, and the source of each date is stated.

## 3. Research findings (by capability)

| Capability | Result | Evidence |
|---|---|---|
| Web search | Demonstrated | 3 queries; results include title, URL, snippet and `pageAge` |
| Full-page retrieval | Demonstrated | S1 and S2 fetched as markdown with page metadata (for example "Last updated 6 days ago" and "Published on 24 Aug 2026") |
| Long-page chunking | Demonstrated | S1 = 3 chunks, S2 = 2, S8 = 6; chunks are fetched by index, and content continues across the chunk boundary (S1 chunk 0 ended mid-word, "tha", and chunk 1 continued with "t gives") |
| PDF retrieval | Demonstrated | S8 PDF parsed to headings, author block, abstract and LaTeX; the tool documents a 30-page cap |
| Academic documents | Partial | Open-access arXiv works through the fetch tool; direct sandbox access to arxiv.org failed; paywalled sources were not tested |
| Citation handling | Demonstrated (manual) | The tools return URLs and ids; the agent keeps the source-to-claim mapping (see `sources.json`); nothing is automatic |
| Contradiction detection | Demonstrated (manual) | 3 tensions found (section 5); this came from the agent's reasoning, not from a tool |
| Source freshness | Partial | Search `pageAge` and on-page dates are available; S1 has only a relative date |
| Structured output | Demonstrated | JSON, CSV and Markdown tables produced and parsed back |
| File creation & delivery | Demonstrated | Files written in the sandbox and delivered through a git commit and PR |

## 4. Claim / evidence ledger

| ID | Claim | Primary source | Evidence | Corroboration / contradiction | Uncertain |
|---|---|---|---|---|---|
| C1 | With a repo connected, files are delivered through a working branch + PR, with no zip | S1 (full page) | "there's no zip download. Your changes are delivered to GitHub instead" | S2 describes commit/push/PR. **R1:** this session works on an assigned branch and opens a PR | Behaviour of the Workspace panel in the UI was not observed by the agent |
| C2 | The agent can push directly to `main` | S2 (full page), S5 | "an AI developer who can push directly to your main branch" | **Contradicted by R1:** this session is limited to `arena/01a0dc7f-arena` and forbidden to push to other branches. S1 also describes a working branch | Whether direct pushes to main depend on configuration or were removed; the marketing wording may be out of date |
| C3 | Workspace files can be downloaded | S1 | Zip Download for sessions with no repo; FAQ: add `/download-workspace` to the URL | **Tension within S1:** "no zip download" for repo sessions vs. a URL workaround described for "any Agent Mode chat" | Whether `/download-workspace` works for sessions connected to a repo (not tested; the agent cannot open that URL for the user) |
| C4 | Arena usage is rate limited | S4 (snippet) | Per-model and overall chat limits; HTTP 429 | S7 (third party) lists numbers that may describe an unrelated API. No first-party figures | Actual Agent Mode quotas and turn/tool caps. At runtime: a 10-speech-clip-per-turn cap appears in tool descriptions only |
| C5 | Previews through serving ports | S2 | "serving ports for previewing and debugging" | Runtime tooling includes `start_process` with port previews (not exercised) | Not tested in this probe |
| C6 | The sandbox has general internet access | none first-party | — | **R1:** pypi.org 200; help.arena.ai and arxiv.org `SSL_ERROR_SYSCALL` | Whether an allowlist, a proxy or a temporary fault caused the failures |
| C7 | Browser automation is available | none | Not mentioned in S1–S3 | **R1:** no Chromium/Playwright binaries | Could be installable from PyPI (not tried) |

## 5. Contradictions

1. **Pushing to main (C2).** Marketing (S2, S5) says the agent can push directly to main. The help doc (S1) and runtime policy (R1) use a working branch and a PR. This is recorded as an unresolved discrepancy. The runtime restriction is observed fact for *this* session only.
2. **Downloads (C3).** S1 says repo sessions have no zip, and the same page describes a `/download-workspace` workaround for any chat. This is untested; GitHub is the only verified delivery channel here.
3. **Network access (C6).** Server-side fetching works for hosts that the sandbox cannot reach directly. Research through the fetch tool therefore does not show that sandbox scripts (crawlers, API clients) can reach the same hosts.

## 6. Practical applications

| Use case | Status | Notes |
|---|---|---|
| Deep technical research | Demonstrated at small scale | Search, fetch, chunking and a ledger; citation discipline depends on the agent |
| AI-tool research | Demonstrated | This report |
| Academic-paper analysis | Partially demonstrated | arXiv PDF parsed; 30-page cap; figures lost; paywalls untested |
| SEO audits | Plausible, not demonstrated | Fetch returns markdown, not raw HTML or headers; sandbox egress is selective |
| Processing crawler exports | Plausible | Supported uploads include CSV and JSON; Python is available; large files untested |
| Technical documentation / Markdown knowledge bases | Demonstrated | Markdown committed to the repo |
| Client reports | Partially demonstrated | PDF generated with reportlab; visual quality not checked in a viewer |
| Coding-agent handoff packages | Demonstrated | Branch + PR + structured JSON/MD |
| PDF & spreadsheet generation | Demonstrated structurally | reportlab, openpyxl; not rendered in Acrobat or Excel |

No token or cost savings were measured, so none are claimed.

## 7. Technical limitations

- The sandbox has no preinstalled PDF or Office libraries. `pip` needs `--break-system-packages` (PEP 668).
- There is no LibreOffice or browser, so rendering could not be tested at application level.
- Sandbox outbound connections to some hosts fail.
- The session branch is fixed by Arena, so a requested branch name cannot be honoured.
- Some sources were available only as snippets (S3–S7); their dates come from the search index.
- The orchestrator model is hidden and may switch during a session (S1), which affects reproducibility.

## 8. Bibliography

See `sources.json` for the full fields.

- S1 Arena Help Center, "How to use Agent Mode on Arena", https://help.arena.ai/articles/5432423882-how-to-use-agent-mode (last updated ~2026-09-20, relative)
- S2 Arena blog, "Coding in Agent Mode: From Idea to Shipping with GitHub", https://arena.ai/blog/coding-in-agent-mode (pub. 2026-08-24, upd. 2026-08-26)
- S3 Arena blog, "Empowering Users to Get More Done With Agent Mode", https://arena.ai/blog/agent-mode (snippet)
- S4 Arena Help Center, "Arena Troubleshooting: Rate Limit", https://help.arena.ai/articles/8931786544-arena-how-to-rate-limit (snippet)
- S5 Arena on X, https://x.com/arena/status/2092650905552507015 (snippet)
- S6 chatgate.ai summary (third party, snippet)
- S7 stork.ai review (third party, snippet, unverified)
- S8 Vaswani et al., "Attention Is All You Need", https://arxiv.org/pdf/1706.03762 (PDF test fixture)
- R1 Runtime observations, this session

## 9. Remaining experiments

1. Test `/download-workspace` in a session connected to a repo, from the user's browser.
2. Retrieve S3 and S4 as full pages and read chunk 2 of S1.
3. Try installing Playwright + Chromium from PyPI and test headless browsing.
4. Map sandbox egress systematically (allowlist vs. failure) across 20+ hosts.
5. Test PDFs larger than 30 pages and paywalled or DOI-resolved papers.
6. Install LibreOffice (if possible) to render DOCX/XLSX/PPTX and convert them to PDF for visual checks.
7. Stress-test with a crawler export of more than 50 MB.
