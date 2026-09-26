# Arena Agent Mode: Complete Capability Inventory

**Forensic runtime snapshot:** 2026-09-26 (UTC)  
**Scope:** the actual Agent Mode tools and sandbox exposed to this session, plus first-party Arena documentation retrieved during this investigation.  
**Bottom line:** Arena Agent Mode is a useful, multi-step research and coding workspace, but this session did **not** expose Playwright or a browser, did **not** expose a GitHub function, and did **not** reveal numeric usage/token quotas. A local HTTP preview and image generation/editing worked; a direct shell HTTPS request did not. Several advertised platform features are documented but were not exercised here.

> This is a snapshot of one session, not a claim about every Arena account, plan, experiment, model, or future release. The visible function definitions are the only tool registry available to this investigation; there is no supported way here to inspect Arena's complete internal registry.

## Table of contents

1. [Executive findings](#1-executive-findings)
2. [Evidence classification and method](#2-evidence-classification-and-method)
3. [Actual exposed tool inventory](#3-actual-exposed-tool-inventory)
4. [Runtime and sandbox inventory](#4-runtime-and-sandbox-inventory)
5. [Playwright and browser automation](#5-playwright-and-browser-automation)
6. [Research and source verification](#6-research-and-source-verification)
7. [Software engineering](#7-software-engineering)
8. [Documents and artifact formats](#8-documents-and-artifact-formats)
9. [Multimodal capabilities](#9-multimodal-capabilities)
10. [Orchestration and session behavior](#10-orchestration-and-session-behavior)
11. [Platform limits, privacy, and unknowns](#11-platform-limits-privacy-and-unknowns)
12. [Practical use-case evaluation](#12-practical-use-case-evaluation)
13. [Recommended operating posture](#13-recommended-operating-posture)
14. [Official source register](#14-official-source-register)
15. [Probe evidence index](#15-probe-evidence-index)

---

## 1. Executive findings

### What was actually verified

- **Research tools work.** `functions.web_search` returned search-result IDs, titles, URLs, excerpts, and (for some results) `pageAge`. `functions.fetch_page` retrieved first-party Arena help/blog pages, returned paginated text for long pages, and parsed a one-page public PDF. See [T-002–T-005](ARENA_AGENT_PROBE_RESULTS.md#research-and-document-retrieval).
- **Shell and local code execution work.** Python 3.11, Node 22, GCC 12, GNU Make 4.3, and subprocesses ran. A Python `unittest`, Node syntax check/run, and tiny GCC/Make build all passed. This is evidence of the tested smoke cases, not a guarantee that arbitrary project dependencies or builds will work. [T-001, T-007, T-010](ARENA_AGENT_PROBE_RESULTS.md#runtime-and-code-execution).
- **A local development server can be run and previewed.** A harmless HTTP fixture bound to `0.0.0.0:8765`; the process tool surfaced that port and a local HTTP request returned 200 with the expected HTML. The background process was stopped. No browser rendered the page, so this did **not** verify visual appearance or browser-side reachability. [T-011](ARENA_AGENT_PROBE_RESULTS.md#development-server-and-preview).
- **Image generation and editing worked.** A synthetic three-shape graphic was generated, then edited to recolor the shapes. `read_file` returned both images for visual inspection. The scratch images were removed after testing. [T-012](ARENA_AGENT_PROBE_RESULTS.md#image-generation-editing-and-inspection).
- **Workspace file operations worked.** A scratch file was written, edited with `edit_file`, and read back with the changed text. The four requested deliverables are placed in the workspace; their final validation is logged in the probe-results file. [T-013–T-015](ARENA_AGENT_PROBE_RESULTS.md#file-tools-and-final-artifact-validation).
- **Small synthetic files were created in all 12 requested formats.** Validation depth varied: JSON/CSV/PNG/ZIP had useful parser or integrity checks; PDF and Office packages received structural checks only. None was downloaded through Arena's UI. [T-009](ARENA_AGENT_PROBE_RESULTS.md#synthetic-file-format-tests).
- **Local loopback networking worked; direct shell HTTPS did not in the one test.** A temporary loopback server returned HTTP 200. `curl https://example.com` failed with an OpenSSL `SSL_ERROR_SYSCALL` (exit 35). Meanwhile the dedicated web-search/page-fetch tools successfully retrieved public Arena and W3C pages. Do not generalize one failed `curl` into a claim that all shell egress is blocked. [T-006–T-008](ARENA_AGENT_PROBE_RESULTS.md#network-and-subprocess-tests).

### Most important limits

- **No Playwright package or browser executable was found in the checked Python/Node environments, `PATH`, or common browser locations.** There is no dedicated browser-automation or screenshot-capture tool in the visible function list. PW-004 through PW-014 are therefore **NOT_TESTED**, not independent browser failures. [T-001, T-005](ARENA_AGENT_PROBE_RESULTS.md#playwright-package-and-browser-discovery).
- **No dedicated GitHub tool is exposed in this session.** `git` and `gh` command-line binaries are installed, but no remote, auth, repository, PR, or GitHub operation was attempted. First-party Arena documentation describes a GitHub connector, but its availability and behavior were not tested here. [S-03–S-05, T-001](#14-official-source-register).
- **Usage quotas are not numerically visible.** Arena help describes daily usage credits and per-model/overall rate limits, but the retrieved documentation does not give a fixed balance, per-model threshold, token ceiling, or reliable cost per task. This session exposes no account usage meter. [S-07–S-10](#14-official-source-register).
- **Don't treat the workspace as private by default.** Arena's privacy policy says user content may be shared with AI technology providers for product evaluation/improvement/development and warns that some content may be made public. Avoid secrets, credentials, private customer data, and unredacted sensitive material. [S-11](#14-official-source-register).
- **A file existing in the workspace is not proof it can be downloaded.** The file viewer and workspace files can be used here; an Arena workspace download was not exercised. Official help describes a ZIP download when no repository is connected, but that workflow is not execution evidence. [S-01, T-014–T-015](ARENA_AGENT_PROBE_RESULTS.md#file-tools-and-final-artifact-validation).

---

## 2. Evidence classification and method

### Evidence levels used throughout

| Classification | Meaning in this report |
|---|---|
| `OFFICIAL_DOCUMENTATION` | A first-party Arena (or clearly identified standards/academic host) source was returned by search or fetched. This proves the source says it; it does not independently prove the product behaves that way. |
| `EXPOSED_TOOL` | The named function and its schema were visible to this Agent Mode session. This is not execution evidence. |
| `EXECUTION_VERIFIED` | The specified operation ran and returned a recorded result in this session. The cited test ID is the supporting evidence. |
| `PARTIALLY_VERIFIED` | A bounded part was exercised, or a visible tool/runtime check was incomplete. Boundaries are stated explicitly. |
| `INFERRED` | A practical conclusion drawn from verified tools, official docs, or their absence; not a direct product promise. |
| `NOT_TESTED` | No independent test was run. This includes downstream browser tests blocked by missing Playwright/browser dependencies. |
| `UNAVAILABLE` | Not present in this session's visible tool interface or checked runtime locations. It does **not** mean Arena can never offer the feature elsewhere. |

A capability may have more than one classification. For example, GitHub repo editing is `OFFICIAL_DOCUMENTATION` in Arena's product material but `NOT_TESTED` in this session. “Not exposed here” is not the same as “does not exist anywhere on Arena.”

### Scope and safety

- The investigation used only the tools shown in this session and safe, small synthetic fixtures.
- No GitHub connection, repository fetch/push, PR, private account, credential lookup, or authentication check was made. The only Git-related runtime probes were version commands (`git --version`, `gh --version`).
- No environment-variable dump was run; no credentials or secrets were copied into these reports. No large dependencies, browsers, or system packages were installed.
- Temporary files were confined to short-lived probe directories or explicitly named scratch images/files created for the tests. Temporary directories and scratch files were cleaned up; the test server was stopped.
- The required deliverables live in the session workspace, which is backed by a local repository checkout. Their creation is the requested output; it is not evidence of connecting to GitHub or exercising repository integration. No Git operation was used to inspect or alter a remote.
- **Registry boundary:** this report inventories the `functions.*` tools and the `multi_tool_use.parallel` wrapper visible to the agent. It cannot inspect hidden backend tools, internal services, feature flags, or every UI control.

---

## 3. Actual exposed tool inventory

The current interface exposes **15 `functions.*` tools plus `multi_tool_use.parallel`**. Tool names below are copied from the visible interface; no hidden identifiers are inferred.

### Research, files, and code

| Visible identifier | Purpose / inputs / returned output / restrictions | Evidence |
|---|---|---|
| `functions.web_search` | Search the public web. Input: a query (up to 400 characters) and depth 1–3. Returns result IDs, titles, URLs, descriptions/snippets, and sometimes `pageAge`. A result is a lead, not a full source or guarantee of accuracy. | `EXPOSED_TOOL`, `EXECUTION_VERIFIED` — T-002, T-005 |
| `functions.fetch_page` | Retrieve a URL as Markdown-like text. Input: URL and optional chunk index. Returns title, URL, page text, `hasMore`, and chunk metadata. Long pages can require additional chunk calls. Tool instructions state that PDFs are parsed up to 30 pages; the one-page PDF smoke test returned extracted text. | `EXPOSED_TOOL`, `EXECUTION_VERIFIED` — T-003–T-005 |
| `functions.bash` | Run a command in the sandbox. Input: command, optional working directory, timeout (schema default 30 seconds; maximum 1,800 seconds). Output includes stdout, stderr, exit code/status, duration, and truncation flags. No controlling terminal; stdin is closed. It can run child processes and ordinary local toolchains. | `EXPOSED_TOOL`, `EXECUTION_VERIFIED` — T-001, T-006–T-011 |
| `functions.read_file` | Read workspace files. Input: path, line offset, and line limit. Text is returned as text; images are rendered visibly; other binary files return metadata rather than decoded contents. | `EXPOSED_TOOL`, `EXECUTION_VERIFIED` — T-012–T-015 |
| `functions.write_file` | Create or overwrite a workspace file from supplied full content; parent directories are created. The interface does not itself validate the file's format. | `EXPOSED_TOOL`, `EXECUTION_VERIFIED` — T-013–T-015 |
| `functions.edit_file` | Replace the first fuzzy-matched occurrence of supplied text in a file. Whitespace/indentation differences are tolerated; it is not a general-purpose semantic merge. | `EXPOSED_TOOL`, `EXECUTION_VERIFIED` — T-013 |
| `functions.present_file` | Open one existing workspace file in the user's file viewer. It is a presentation action, not proof of a download or ZIP transfer. | `EXPOSED_TOOL`, `EXECUTION_VERIFIED` — T-014 (viewer open); download `NOT_TESTED` |

### Processes, preview, and orchestration

| Visible identifier | Purpose / inputs / returned output / restrictions | Evidence |
|---|---|---|
| `functions.start_process` | Start a long-running process with a user-facing name, command, working directory, and startup wait (maximum 30 seconds). Returns a process ID, log tail, listening ports, and warnings. For browser preview, bind to `0.0.0.0` and accept the preview host; the probe server did so. | `EXPOSED_TOOL`, `EXECUTION_VERIFIED` — T-011 |
| `functions.get_process_output` | Read process logs/liveness; can wait for a new port, matching log, or exit (maximum wait 180 seconds). | `EXPOSED_TOOL`, `EXECUTION_VERIFIED` — T-011 |
| `functions.stop_process` | Stop a started process group (SIGTERM, then SIGKILL if needed). The probe server was stopped successfully. | `EXPOSED_TOOL`, `EXECUTION_VERIFIED` — T-011 |
| `multi_tool_use.parallel` | Invoke multiple exposed developer tools in one response when independent. It was used for concurrent search/runtime and source-fetch calls. This verifies the wrapper is callable; it does not independently benchmark exact scheduling or speedup. | `EXPOSED_TOOL`, `PARTIALLY_VERIFIED` — T-002–T-005 |

### Images, audio, and user interaction

| Visible identifier | Purpose / inputs / returned output / restrictions | Evidence |
|---|---|---|
| `functions.generate_image` | Generate one standalone image; can also edit supplied image paths. Output is saved at the requested `.png`, `.jpg`, or `.jpeg` path. An `offer_options` call can pause for a user choice; the probe used one image and no options. | `EXPOSED_TOOL`, `EXECUTION_VERIFIED` — T-012 |
| `functions.image_search` | Search for images and save 1–5 results into workspace paths. Not invoked in this investigation. | `EXPOSED_TOOL`, `NOT_TESTED` |
| `functions.add_voice` | Audition two candidate voices for a short script and register the voice selected by the user. It pauses for a user vote; new audition pairs use an incremented index. Not invoked, to avoid interrupting this investigation with a voice-choice prompt. | `EXPOSED_TOOL`, `NOT_TESTED` |
| `functions.generate_speech` | Synthesize spoken-word audio to a supported audio file type. Requires a voice ID first; text limit is 1,500 characters per call and the tool documents a maximum of 10 clips per turn. It does not sing. Not invoked because no voice was registered. | `EXPOSED_TOOL`, `NOT_TESTED` |
| `functions.ask_user` | Show a clarification UI with 2–4 options per question, up to 6 questions, optionally allowing a custom response. Not invoked. | `EXPOSED_TOOL`, `NOT_TESTED` |

### What is not an exposed tool

- **Browser automation / Playwright:** no browser-specific function appears in the visible list. Runtime probes also found no Playwright package or browser executable in checked locations. See §5.
- **Screenshot capture:** no screenshot-specific function appears. `generate_image` is not a browser screenshot tool.
- **GitHub operations:** no dedicated GitHub function appears. Local `git` and `gh` executables are present under Bash, but their remote operations were not tested and must not be confused with Arena's documented GitHub connector.
- **Deep Research, subagent, scheduler, database, OCR, PDF-authoring, or spreadsheet-authoring tools:** no function with those names/capabilities appears. Research, code, and document tasks can still be orchestrated from the tools actually listed, but that is not proof of a dedicated service.

---

## 4. Runtime and sandbox inventory

All measurements below are **observations at one moment**, not a service-level resource guarantee or quota.

| Area | Observed result | Evidence / caveat |
|---|---|---|
| OS / kernel / architecture | Debian GNU/Linux 12 (bookworm); Linux `6.1.158+`; `x86_64` | T-001 |
| Working directory | `/home/user/arena` | `pwd`, T-001 |
| Python | Python 3.11.2 at `/usr/bin/python` and `/usr/bin/python3`; pip 23.0.1 | T-001 |
| JavaScript runtime | Node.js v22.22.3; npm/npx 10.9.8; Corepack 0.34.6; Yarn 1.22.22 | T-001 |
| Other package managers checked | `pnpm`, `bun`, `deno`, `uv` not found on `PATH` | T-001 |
| Shells | `/usr/bin/bash`, `/usr/bin/sh`; `zsh` and `fish` not found on `PATH` | T-001 |
| Version-control CLIs | Git 2.39.5; GitHub CLI `gh` 2.23.0 | Version only; no remote or authentication command run, T-001 |
| Compilers / build tools | GCC 12.2.0; GNU Make 4.3; Perl 5.36.0 | Tiny GCC/Make program passed, T-010 |
| Image / archive tools | ImageMagick 6.9.11-60 (`convert`, `identify`); `zip`, `unzip`, `tar`, `curl`, `wget`, `jq` found | `identify` validated the 1×1 PNG, T-009 |
| Not found in checked PATH | `pytest`, `ruff`, `black`, `mypy`, Cargo/Rust, Go, Java/Javac, .NET, PHP, Ruby, CMake, Clang, Pandoc, `pdftotext`, LibreOffice/`soffice`, Playwright CLI, Chromium, Google Chrome, Firefox, `wkhtmltopdf`, Ghostscript, `pdftoppm`, FFmpeg | T-001; absence from PATH is not a global system search |
| Python package metadata checked | No metadata found for Playwright, pytest, Ruff, Black, mypy, Pillow, pypdf/PyPDF2, pandas, openpyxl, python-docx, python-pptx, BeautifulSoup, requests, httpx, Markdown, WeasyPrint, Selenium, IPython, or Jupyter | Metadata-only; deliberately avoided imports and full package enumeration, T-001 |
| Node packages checked | `playwright`, `playwright-core`, `@playwright/test`, Puppeteer, Vite, Express, TypeScript, and ts-node not resolvable from this workspace. Global top-level packages listed only Corepack and npm. | T-001 |
| Memory / swap | `/proc/meminfo`: MemTotal 4,034,452 kB; MemAvailable 3,769,572 kB; swap 0. | Snapshot only; not a hard memory quota, T-001 |
| CPU | `nproc` = 2; cgroup v2 exposed `cpuset.cpus.effective=0-1`. | Visible scheduling set; no `cpu.max` at checked mount root, T-001/T-008 |
| cgroup / process limits | Membership `0::/user`; cgroup2 mounted. `memory.max`, `memory.current`, `cpu.max`, and `pids.max` were absent at checked root. `ulimit` reported virtual memory and CPU time unlimited, open files 1,024, max user processes 15,734, stack 8,192 kB. | These are observations; no enforceable sandbox quota was established. T-001/T-008 |
| Filesystem | `df -hT . /tmp`: `/dev/root`, ext4, 21G total, 818M used, 20G available, 4%. Python `shutil.disk_usage`: 21,834,924,032 bytes total; 20,692,344,832 free. `/tmp` and workspace showed the same filesystem. | Filesystem view only; not a user or platform storage quota, T-001 |
| Temporary storage | A harmless temporary file was written, read back as `b'harmless-temp-probe\n'`, and cleaned up. | `EXECUTION_VERIFIED`, T-001 |
| Subprocesses | Python successfully started a child process with `subprocess.run`; exit 0 and stdout `child-process-ok`. | `EXECUTION_VERIFIED`, T-007 |
| Local networking | A temporary `127.0.0.1` HTTP server returned status 200 and body `loopback-ok`. The separate preview server bound to `0.0.0.0`. | `EXECUTION_VERIFIED`, T-007/T-011 |
| External networking from Bash | `curl https://example.com` failed once during TLS with `OpenSSL SSL_connect: SSL_ERROR_SYSCALL`, HTTP code `000`, exit 35. | One endpoint/attempt only; do not infer all egress is blocked. Dedicated search/fetch tools did reach public HTTPS pages. T-006/T-002–T-005 |

### Package installation and development tooling

`pip`, npm, npx, Corepack, and Yarn executables are present. **No package was installed**: package installation was not required for this investigation, the shell HTTPS probe failed, and installing Playwright/browser dependencies would violate the requested “do not install large dependencies” constraint. Binary presence is not proof that a registry is reachable or that an install will succeed. Small tests used only the existing Python standard library, Node, GCC/Make, and ImageMagick.

---

## 5. Playwright and browser automation

The status rule requested by the user is applied strictly: downstream Playwright tests are `NOT_TESTED` when the package/browser prerequisite was absent; they are not recorded as independent functional failures.

| ID | Capability | Status | Actual evidence / boundary |
|---|---|---|---|
| PW-001 | Playwright package availability | `UNAVAILABLE` in checked environments | Python package metadata: not installed. Node package resolution: Playwright, Playwright Core, and `@playwright/test` not resolvable. No install attempted. T-001 |
| PW-002 | Exact installed version | `UNAVAILABLE` | No installed package to version; an exact Playwright version cannot be reported. T-001 |
| PW-003 | Browser executable discovery | `PARTIALLY_VERIFIED` | `chromium`, `chromium-browser`, `google-chrome`, and Firefox not on `PATH`; common `/usr/bin`, `/opt/google/chrome`, `/ms-playwright`, and user/root Playwright cache paths absent. No exhaustive filesystem search. T-001 |
| PW-004 | Headless browser launch | `NOT_TESTED` | Blocked by PW-001/PW-003; no independent launch failure was induced. |
| PW-005 | Local HTML rendering | `NOT_TESTED` | The server served HTML, but no browser rendered it. See PW-015/T-011. |
| PW-006 | DOM inspection | `NOT_TESTED` | No browser/DOM automation dependency. |
| PW-007 | Screenshot generation | `NOT_TESTED` | No browser screenshot path tested. Image generation is not screenshot capture. |
| PW-008 | Screenshot artifact delivery | `NOT_TESTED` | No browser screenshot artifact was produced or delivered. `present_file` delivery of a normal file is tested separately. |
| PW-009 | Public HTTPS navigation | `NOT_TESTED` as a browser test | `web_search`/`fetch_page` successfully accessed public HTTPS sources, but that is not browser navigation. Bash `curl` had one TLS failure; see T-006. |
| PW-010 | Responsive viewport emulation | `NOT_TESTED` | No browser context or viewport emulator. |
| PW-011 | Keyboard/pointer interaction | `NOT_TESTED` | No browser input automation. |
| PW-012 | Browser console inspection | `NOT_TESTED` | No browser console source. |
| PW-013 | Browser network request inspection | `NOT_TESTED` | No browser instrumentation. The Arena help page's human instructions for DevTools do not expose DevTools to this agent. |
| PW-014 | PDF generation through a browser | `NOT_TESTED` | No browser. A small PDF was structurally assembled by Python for file-format testing; it was not browser-generated. |
| PW-015 | Development server preview | `PARTIALLY_VERIFIED` | `start_process` exposed port 8765 on `0.0.0.0`; an HTTP request returned 200 and expected page markers; process then stopped. The live preview was surfaced by the process service, but no browser-side rendering or screenshot was checked. T-011 |

**Conclusion:** do not use this session's verified evidence to claim automated responsive QA, Playwright, DOM inspection, browser screenshots, browser console/network capture, or end-to-end browser tests. A bounded plain-HTML preview server is verified; actual viewing in a browser is not.

---

## 6. Research and source verification

### Small real research task performed

**Task:** determine what Agent Mode currently documents about its tools, workspaces, usage constraints, privacy, and GitHub workflow. The work used several web queries, then fetched first-party pages and compared them. Exact URLs and retrieval status appear in [§14](#14-official-source-register) and the raw probe log [T-002–T-005](ARENA_AGENT_PROBE_RESULTS.md#research-and-document-retrieval).

**Retrieved content (source statements, not our extrapolation):**

- Arena's September help article says Agent Mode builds plans for multi-step work and names web search, image generation, Bash/sandbox, file writing, clarification, and uploads. It lists upload formats and describes workspace/download behavior. [S-01]
- Arena's August coding announcement says its GitHub-first flow can connect a repository/branch, clone it to a sandbox, edit files, run commands, display a diff, preview the app, and push/create a PR. The product changelog also lists the GitHub update on 26 August 2026. [S-03, S-04]
- Arena's credit help article says a daily credit period begins with the first prompt, runs for 24 hours, shows an indicator as the balance is approached, and displays a reset countdown at the limit. It does not state a fixed credit amount. [S-07]
- The session-limit help article says token/context limits exist, Agent Mode has built-in conversation compaction, and a new session is the documented recovery for an exhausted session; it says context transfer between chats is not available. It does not publish a numeric context window. [S-10]
- Arena's privacy policy includes prompts/images/user content as data, says AI providers may access user content for service and other purposes, and describes possible sharing for provider evaluation/improvement/development. It also warns that some user content/inputs/outputs may be made public. [S-11]

**Our interpretation:** ordinary search + page retrieval + shell/file tools can support source-backed research and synthesis. There is no separate `Deep Research` function in the visible tool list. Arena describes deep research as a workflow/use case, not as a distinct call in this session. The user should ask for a claim-to-source table and preserve source dates rather than treating model prose as retrieved fact.

### What the research interface returns

- `web_search` exposed result IDs, result title, URL, description/snippet, and sometimes `pageAge`. IDs are local to a particular search result list, not permanent citation IDs.
- `fetch_page` returned source title/URL/content and chunk metadata (`chunkIndex`, `hasMore`, `totalChunks`). For long pages the agent must request additional chunks. It did not provide a consistent HTTP `Last-Modified` timestamp. Date information was sometimes in page content or search-result `pageAge`.
- A one-page public W3C dummy PDF was retrieved and parsed to the text `Dummy PDF file`. This validates basic PDF retrieval/text extraction, not figure extraction, OCR, table fidelity, or large-PDF processing. [T-004]
- An arXiv code-agent benchmark was surfaced by web search; its HTML first chunk included title, abstract, and date metadata. It was not a full-paper review or independent peer-review verification. [T-005]
- Citation links in these documents were assembled from returned exact URLs. There is no separate bibliography manager or guaranteed citation-verification tool exposed.

### Source comparison and contradictions found

1. **GitHub availability wording differs.** Arena's product blog and changelog describe the GitHub connector as launched/available in August 2026. A first-party Help Center search result for “GitHub Integration in Agent Mode” says the capability is still an experiment and one PR is supported per chat. Fetching that Help Center URL returned a “Page Not Found” page in this session. This is a first-party documentation inconsistency/staleness signal—not proof that any specific account has access. The current session did not connect GitHub. [S-03–S-05, T-003]
2. **A search excerpt about upload count was not confirmed by the fetched page.** A search result snippet for an Arena troubleshooting article said “up to 10 file uploads” per chat; fetching the same article did not show that claim in the returned page text. The 10-file number is therefore recorded as **unverified/stale**, not as a current hard limit. No numeric maximum file size was found in the pages fetched. [S-06, T-002–T-003]
3. **Usage documentation has different update ages.** The credit page is newer and describes daily credits; an older daily-usage-limit article describes the unified usage system rollout as still in progress. Use the newer credit page for the observed mechanics, but check the UI for today's actual balance and policy. Neither page gave this investigation a numeric account quota. [S-07–S-08]

### What this does and does not establish

`EXECUTION_VERIFIED`: multiple searches, source discovery, multi-chunk retrieval, official-source comparison, one academic-page lookup, and one PDF text extraction. `PARTIALLY_VERIFIED`: source completeness/date interpretation and the value of the synthesis. `NOT_TESTED`: paywalled sources, broad scholarly databases, comprehensive crawls, OCR/figures, citations cross-checked against every underlying sentence by a human, or research over a user-uploaded corpus. “Deep Research” is not a dedicated tool name in this session.

---

## 7. Software engineering

### Verified in this environment

- **Shell/code execution:** Python and Node scripts ran; a child subprocess ran. [T-007, T-010]
- **Tests:** a synthetic Python `unittest` test passed. `pytest` was not installed in the checked runtime. [T-010]
- **JavaScript check/run:** `node --check` passed and a Node script ran. No Vite, Express, TypeScript, or Playwright package resolved from the workspace. [T-001, T-010]
- **Build:** a tiny C program compiled and ran via a Makefile and GCC. This does not validate arbitrary application build systems. [T-010]
- **Workspace editing:** a scratch file was created, modified with `edit_file`, and read back. The final reports use the same workspace file surface. [T-013–T-015]
- **Local development server:** a minimal page was served and the port was surfaced. [T-011]

### Documented but not tested here

Arena's own coding announcement describes sandbox-based GitHub cloning, repository editing, command execution, diff review, app preview, commits, pushes, and pull requests. The Help Center how-to describes the connected-repository workflow; official sources disagree on whether all users currently have the GitHub feature. No GitHub connector was called, and no GitHub account/repository was accessed. [S-01, S-03–S-05]

### Limitations of the engineering evidence

- No installed test/lint suite such as pytest/Ruff/mypy, no browser automation, no package installation, and no project build were exercised.
- No dedicated GitHub tool or subagent appears in the visible tool list. `git`/`gh` are ordinary binaries reachable through Bash, not evidence of authenticated network access.
- Shell egress to one HTTPS host failed. Remote package installation, API calls, and arbitrary-site crawling are unverified.
- Agent-generated code can be debugged iteratively from actual command output, but that is orchestration by the agent, not a separate debugger service.
- Refactoring, multi-file edits, test generation, and documentation are practical applications of the file/shell tools; quality still depends on project context, dependency availability, test coverage, and review.

---

## 8. Documents and artifact formats

### Synthetic format smoke tests

Twelve small fixtures were created under a temporary directory inside the workspace and removed automatically after the test. The table distinguishes the four states requested by the user. `ACCESSIBLE_IN_WORKSPACE` means the temporary test path was inside the workspace **while the test ran**; it does not mean the scratch fixture is still present or that a download was tested.

| Format | `FILE_CREATED` | `FILE_VALIDATED` | `ACCESSIBLE_IN_WORKSPACE` | `DOWNLOAD_VERIFIED` | Validation depth / evidence |
|---|---|---|---|---|---|
| Markdown | Yes | Partial: UTF-8 content round-trip | Yes, transiently | No | Heading/content exact; no Markdown renderer. T-009 |
| Plain text | Yes | Yes for byte/text round-trip | Yes, transiently | No | UTF-8 content exact. T-009 |
| JSON | Yes | Yes | Yes, transiently | No | Parsed and compared with Python `json.loads`. T-009 |
| CSV | Yes | Yes for simple fixture | Yes, transiently | No | Parsed with Python `csv.reader`; 2 rows. T-009 |
| HTML | Yes | Partial | Yes, transiently | No | Python `HTMLParser` found `html`/`main`; **not browser-rendered**. T-009 |
| PDF | Yes | Partial / structural only | Yes, transiently | No | Hand-built one-page PDF; custom checks of header, xref offset/object offsets and `%%EOF`; no PDF reader/rendering application installed. T-009 |
| DOCX | Yes | Partial / package structure only | Yes, transiently | No | ZIP CRC, required package entries, XML well-formedness; not Office-opened or schema-validated. T-009 |
| XLSX | Yes | Partial / package structure only | Yes, transiently | No | ZIP CRC, required package entries, XML well-formedness; not Excel/LibreOffice-opened or schema-validated. T-009 |
| PPTX | Yes | Partial / package structure only | Yes, transiently | No | ZIP CRC, required package entries, XML well-formedness; not PowerPoint/LibreOffice-opened or schema-validated. T-009 |
| PNG | Yes | Yes for a 1×1 fixture | Yes, transiently | No | ImageMagick `identify` returned `PNG 1x1`. T-009 |
| SVG | Yes | Partial | Yes, transiently | No | XML parse succeeded and root was `<svg>`; not tested in a browser. T-009 |
| ZIP | Yes | Yes for a small fixture | Yes, transiently | No | Python `zipfile.testzip()` returned no error and member text round-tripped. T-009 |

The output files in this report are separate from those short-lived fixtures. Workspace read/view is verified; an Arena ZIP download is not. The file-format probes prove that this sandbox's local filesystem and existing tools can create small samples—not that Arena's upload UI accepts every format, that Office viewers accept these minimal packages, or that every file can be downloaded.

### Official upload formats are a separate question

Arena's current Agent Mode Help Center page lists PNG, WebP, JPEG, PDF, GIF, TXT, Markdown, CSV, HTML, XML, CSS, JavaScript, and JSON (the article repeats XML and JavaScript in its list). It does not list DOCX, XLSX, PPTX, SVG, or ZIP. This is **officially documented upload support**, not a test of the upload UI in this session. No numeric per-file size limit was found. [S-01, S-02]

---

## 9. Multimodal capabilities

| Modality / operation | What is available here | Evidence and boundary |
|---|---|---|
| Image understanding / inspection | `read_file` returns image data visibly; official help documents image uploads in Agent Mode. A generated synthetic PNG was read and its blue circle, orange square, and green triangle were visually inspected. | `EXECUTION_VERIFIED` for reading/inspecting that generated raster; user upload path and general vision accuracy only `OFFICIAL_DOCUMENTATION`/`NOT_TESTED`. T-012 |
| Image generation | `functions.generate_image` produced a PNG at the requested workspace path. | `EXECUTION_VERIFIED`, T-012 |
| Image editing | The same function accepted the generated image as input and returned an edited image with the intended color changes. | `EXECUTION_VERIFIED`, T-012 |
| Image search | `functions.image_search` is visible and supports saving 1–5 results. | `EXPOSED_TOOL`, `NOT_TESTED` |
| Screenshot interpretation | No real browser screenshot was created. The read-file image path works for a synthetic non-screenshot picture, but website screenshot QA was not tested. | `PARTIALLY_VERIFIED` for raster display; screenshot-specific assessment `NOT_TESTED` |
| PDF text / figures | A one-page PDF URL was parsed to text. No figure/OCR test; no dedicated OCR/PDF-viewer tool; `pdftotext`/PDF GUI tools not found. | `PARTIALLY_VERIFIED` for small PDF text retrieval, T-004; figures `NOT_TESTED` |
| Audio input / transcription | No audio input or speech-to-text function appears in the current tool list; audio is not among the Help Center's documented Agent Mode upload extensions. | `UNAVAILABLE` in this visible session; not a global claim about other Arena modes |
| Audio output | `add_voice` and `generate_speech` are exposed. Speech generation requires a selected voice and was not invoked. | `EXPOSED_TOOL`, `NOT_TESTED` |
| Video understanding / generation | No video input, video generation, or video tool appears in the visible list or documented Agent Mode upload list. | `UNAVAILABLE` in this visible session; no test |

**Do not conflate modes.** Arena's documentation discusses other Arena modalities and products, and the public site advertises capabilities in Battle/Image/Code/Fullstack experiences. Those features do not prove they are callable from this Agent Mode session. Here, image generation/editing tools are directly exposed; image upload is documented; audio synthesis is exposed but gated by voice registration; browser screenshots and video are not.

---

## 10. Orchestration and session behavior

| Topic | Finding | Classification |
|---|---|---|
| Multi-step planning | Arena Help says Agent Mode autonomously builds a plan; this task also required real multi-step selection of search, fetch, shell, file, image, and process tools. No standalone plan-tool function appears. | `OFFICIAL_DOCUMENTATION`; task orchestration `PARTIALLY_VERIFIED` ([S-01, S-13; T-002–T-015]) |
| Tool selection | The agent chooses among the visible tools; the multi-step source and code work demonstrates use, not a guarantee that selection is always correct. | `EXPOSED_TOOL` + bounded `EXECUTION_VERIFIED` ([T-002–T-015]) |
| Parallel execution | `multi_tool_use.parallel` was invoked on independent searches/fetches/runtime probes. Results returned from the combined call. The exact scheduling/concurrency model was not benchmarked. | `PARTIALLY_VERIFIED` ([T-002–T-005]) |
| Subagents / delegation | No subagent-spawn function is exposed. Arena's GitHub blog mentions team-agent management as a platform design capability, but that is not a callable tool in this session and was not tested. | `OFFICIAL_DOCUMENTATION` for the blog statement; current-session use `NOT_TESTED` ([S-03]) |
| Retry handling | No retry policy or retry counter is exposed. The agent can inspect an error and make another call; that does not establish automatic retry guarantees. | `NOT_TESTED`; no quantitative claim |
| Context compaction | Official Help says Agent Mode compacts earlier conversation into a summary. This session did not reach a boundary or observe a compaction event. | `OFFICIAL_DOCUMENTATION`, `NOT_TESTED` ([S-10]) |
| Session persistence | The current task's workspace/process state survived successive calls. Cross-session restoration was not tested. | Current-session persistence `EXECUTION_VERIFIED` ([T-011, T-013]); cross-session `NOT_TESTED` |
| Workspace persistence / retention | Help says files are saved to the session workspace; it does not give a general retention period. No future-session persistence or deletion workflow was exercised. | `OFFICIAL_DOCUMENTATION`, cross-session `NOT_TESTED` ([S-01]) |
| Long-running commands | Bash has a schema maximum of 1,800 seconds; `start_process` runs a background process across tool calls. A local server was started, queried, then stopped. | `EXPOSED_TOOL`, `EXECUTION_VERIFIED` ([T-011]) |
| Timeouts | Bash has a default 30-second timeout and maximum 1,800 seconds. `start_process` startup wait max 30 seconds; `get_process_output` wait max 180 seconds. No timeout was intentionally triggered. | `EXPOSED_TOOL`; timeout enforcement `NOT_TESTED` |
| Human approval / interaction | `ask_user` can request choices; `add_voice` and image-option flows can pause for user selection. We did not trigger these. No universal approval gate for every tool action was established. | `EXPOSED_TOOL`; approval behavior not tested beyond schemas |
| Usage / token information | No live balance or token counter appears in the visible tools. Official docs describe daily credits and rate/context limits but do not provide a fixed number in the pages fetched. | `OFFICIAL_DOCUMENTATION` + `NOT_TESTED` for current account state ([S-07–S-10]) |
| Scheduled work | No scheduler, cron, or durable job-queue function appears. The process tool supports a running process, not a verified scheduled/persistent service. | `UNAVAILABLE` in the visible tool list |

---

## 11. Platform limits, privacy, and unknowns

### Usage, model, and context limits

- Arena Help documents a **daily usage-credit balance** with a 24-hour period beginning at the first prompt and a displayed refresh countdown when exhausted. The retrieved page gives no universal credit amount and this investigation did not access an account balance. [S-07]
- A separate Arena rate-limit article describes **per-model** limits and **overall chat-rate** limits, with temporary restriction until reset. It gives no numeric thresholds. [S-09]
- Session token/context limits exist. The current help page says Agent Mode has built-in conversation compaction, but it does not disclose an exact context size or make the session unlimited. The same article says context cannot currently be transferred into a new chat. [S-10]
- The Agent Mode Help Center says the orchestrator model is randomly selected for a new chat, is not shown to the user, and may change automatically if the response is likely to fail. This reduces reproducibility; no model pinning or exact per-session model identity was exposed here. [S-01]
- No savings, token-rate, or cost comparison with another subscription is supported by this probe. No such estimate is made.

### Workspace, files, and GitHub

- Arena Help says that with no repository connected, files are stored in the session workspace and can be downloaded via a ZIP in the workspace panel (or `/download-workspace`). If GitHub is connected, the documented path is a repository copy, diff, working branch, and PR rather than the no-repo ZIP. [S-01]
- Help warns that after a connected PR is merged or closed, later-created files may remain in session but may no longer be pushed, downloaded, or carried into a new session. Treat this as a workflow hazard and save important deliverables before closing/merging. [S-01]
- Workspace file retention duration and cross-session guarantees were not found. This investigation's direct file read/view is not a download test.
- File uploads are documented for the extensions in §8. A search snippet about a 10-file cap was not corroborated by the fetched full page; exact size/count limits remain unknown. [S-01, S-02, S-06]
- GitHub integration is described by first-party Arena product material, with inconsistent Help Center status as noted in §6. No connector, repo, OAuth, remote, or PR was used. [S-03–S-05]

### Networking, background execution, and execution limits

- **Verified local:** loopback HTTP and a local 0.0.0.0 preview server returned the expected fixture. **Not verified:** direct shell access to arbitrary public HTTPS, package registries, authenticated APIs, or crawling a site. One `curl https://example.com` attempt failed with a TLS connection error; web-search/fetch tools still worked. [T-006–T-008, T-011]
- `start_process` keeps a process alive across tool calls; this was tested for one tiny server and stopped. No scheduled job, guaranteed persistence across chat/session closure, or always-on service is exposed/verified.
- The filesystem and memory readings are visible snapshots, not advertised limits. There was no visible cgroup memory/CPU quota at the checked root. Do not plan large jobs from those numbers alone.

### Privacy and data handling

Arena's published privacy policy (effective 2025-12-16 in the fetched copy) says prompts, images, and other user content are collected as user-content data; third-party AI technology providers may access/use personal information to provide the service and for other purposes; Arena may share user content with AI providers for evaluation, improvement, and development; and some content/inputs/outputs may be made public. It explicitly advises not to submit personal or sensitive information that the user would not want shared publicly. The deletion help page says a deleted chat is queued for deletion, typically within 30 days, with limited retention possible for legal/security reasons. Read the current policy before uploading material. [S-11, S-12]

**Operational recommendation (`INFERRED`):** redact secrets, API keys, `.env` files, personal data, confidential code, customer records, and private research before uploading. If a GitHub connector is used in a different session, grant only the minimum repository/branch scope and review the diff before merging.

---

## 12. Practical use-case evaluation

“Independent” below means **can the current visible Agent Mode toolset plausibly complete a bounded version without another agent product?** It does not mean the result is guaranteed, exhaustive, or production-grade. Every recommendation is an `INFERRED` workflow grounded in the cited evidence/tests.

### A. Deep technical research

- **Required:** multi-query discovery, source retrieval, source-quality filtering, exact citations, synthesis, optional PDF handling.
- **Verified:** `web_search` + `fetch_page`, official Arena-source research, a public one-page PDF, an academic HTML first chunk, multi-chunk retrieval, and structured report creation. [T-002–T-005, T-014]
- **Missing/unknown:** no dedicated Deep Research call, no guarantee of exhaustive coverage or publication freshness, no citation manager, no paywall access guarantee, no PDF figure/OCR test, no human source audit.
- **Suggested workflow:** define scope/date; search primary/official sources with several queries; fetch full pages and every chunk; log exact URL/date/snippet; separate quotes/facts from interpretation; compare claims and contradictions; produce a claim-source table plus uncertainty list; verify critical citations manually.
- **Likely external dependencies:** publisher access, scholarly databases, PDF OCR/viewers for scans/figures, human domain review.
- **Can Arena do it independently?** **Yes for bounded, accessible-source research; partial for exhaustive or high-stakes research.**
- **Evidence still required:** larger PDFs, figure/OCR accuracy, paywalled sources, broader coverage, independent fact-check.

### B. Research into AI tools and coding agents

- **Required:** current dated sources, vendor docs/changelogs, independent evaluations, version/model comparison.
- **Verified:** Arena official-doc research and a current ArXiv search/retrieval path; sources often include URLs and page-age/date metadata. [T-002–T-005]
- **Missing:** official sources may be stale or inconsistent; no guarantee that model names, feature flags, or pricing are complete; Agent Mode model is hidden per Arena's docs. [S-01, S-03–S-05]
- **Suggested workflow:** search official docs, changelog, status pages, and independent technical papers separately; record “published/updated/retrieved”; reconcile disagreements and label unsupported claims; avoid treating leaderboard scores as universal benchmarks.
- **Likely external dependencies:** papers, release notes, independently reproduced benchmarks, access to relevant products.
- **Can Arena do it independently?** **Yes for a source-backed briefing; no for a fully independent market/benchmark audit without outside validation.**
- **Evidence still required:** freshness and completeness of feature/pricing data; paper peer-review/version status; source-specific claim verification.

### C. Website audits

- **Required:** URL discovery, status/header checks, crawling, JavaScript rendering, form interaction, accessibility/SEO/performance checks, screenshots.
- **Verified:** public web search/page retrieval and local server preview; one external shell HTTPS request failed. [T-002–T-008, T-011]
- **Missing:** Playwright/browser, screenshot capture, DOM automation, full crawler, Lighthouse/axe, verified shell egress to target. PW-004–PW-014 are `NOT_TESTED`.
- **Suggested workflow:** audit a user-provided URL list via `fetch_page`; request read-only scope; report fetch failures; process a supplied crawl export; do not claim dynamic rendering, Lighthouse, screenshot, or form testing unless an external browser tool is actually available.
- **Likely external dependencies:** Playwright/Chromium, Lighthouse/axe, crawler/HTTP access, target site permission.
- **Can Arena do it independently?** **Partial.** It can review reachable pages and supplied exports; it cannot independently complete an automated dynamic-site audit in this tested setup.
- **Evidence still required:** target-site fetch success, site-wide crawl, JS-rendered pages, accessibility/performance results, browser screenshots.

### D. SEO analysis and crawl-data processing

- **Required:** crawl exports, URL normalization, CSV processing, metadata/content analysis, ideally a crawler and search console data.
- **Verified:** CSV upload is officially documented; Python stdlib CSV parsing works; JSON/CSV artifacts validate. [S-01, T-009]
- **Missing:** no pandas or dedicated SEO crawler/tool; shell internet not verified; upload size/data limits unknown; large data was not tested.
- **Suggested workflow:** upload a small redacted CSV; ask for schema inference, row counts, null/duplicate checks, URL/status/title/canonical summaries; return script plus reproducible CSV/JSON and caveats; chunk data rather than pasting all rows into context.
- **Likely external dependencies:** Screaming Frog/Sitebulb/crawler, Google Search Console/analytics exports, pandas/Polars for larger data, permission to access site.
- **Can Arena do it independently?** **Yes for small/medium supplied CSVs and scripts; not a substitute for crawling or large-scale SEO platforms.**
- **Evidence still required:** performance on realistically sized exports, upload limits, exact SEO-tool integration.

### E. Frontend development and responsive testing

- **Required:** multi-file edit, package/build/test chain, local server, browser at target viewports, screenshot/interaction checks.
- **Verified:** Bash/Python/Node/C execution, file writes/edits, GCC/Make smoke build, local HTML preview server. [T-010–T-013]
- **Missing:** Playwright/browser, screenshot capture, installed frontend packages, package install success, automated responsive/interaction coverage.
- **Suggested workflow:** start with plain HTML/CSS/JS or project-provided dependencies; inspect existing files; implement small increments; run existing tests/build; start server bound to `0.0.0.0`; ask the human to inspect the preview if browser visibility is available; label manual checks separately from automated tests.
- **Likely external dependencies:** project packages, a browser/Playwright, browser access through preview UI, API keys only if the app genuinely needs them (do not upload secrets).
- **Can Arena do it independently?** **Yes for bounded static/prototype work and code changes; partial for automated responsive QA.**
- **Evidence still required:** real app build, actual preview rendering, viewport screenshots, keyboard/pointer tests, package installation.

### F. GitHub repository maintenance

- **Required:** repository read/write, branch/diff/commit/PR operations, tests, permissions.
- **Verified:** Git 2.39.5 and `gh` 2.23.0 binaries exist. Only version output was run. Arena official product material describes a connector/sandbox/diff/commit/push/PR path; Help Center wording conflicts on experiment status. [T-001, S-01, S-03–S-05]
- **Missing:** no visible GitHub function; no OAuth check, repository access, remote action, commit, PR, or merge was attempted (per instruction).
- **Suggested workflow:** if enabled in another session, connect only the intended repo/branch through Arena's UI; ask for a read-only inventory first; request a narrow change; inspect full diff; run tests; push/open the documented PR only after explicit user direction; human reviews/merges.
- **Likely external dependencies:** current account feature flag, GitHub OAuth permissions, network, repo access, CI.
- **Can Arena do it independently?** **Not verified here.** Documentation describes it; this session cannot establish account availability or operation success.
- **Evidence still required:** connector visibility, least-privilege OAuth scope, clone/diff/test/push/PR lifecycle—none tested.

### G. Automated code reviews

- **Required:** source/diff access, language-aware static analysis, security/dependency checks, tests, findings with locations.
- **Verified:** file reading, shell execution, simple Python/Node compilation and test execution, source research. [T-007, T-010, T-013]
- **Missing:** dedicated code-review tool, installed linters/security scanners, subagents, browser review, repository/GitHub integration test.
- **Suggested workflow:** define review scope and risk level; read the diff and nearby tests; identify correctness/security/performance issues with exact file/line evidence; run existing tests; separate verified bugs from hypotheses; avoid broad rewrites unless requested.
- **Likely external dependencies:** language linters, Semgrep/SAST, dependency audit tools, CI, human security review.
- **Can Arena do it independently?** **Partial for bounded manual reviews; not a high-assurance replacement for CI/security review.**
- **Evidence still required:** representative real codebase, scanner availability, false-negative measurement, independent reviewer agreement.

### H. Test generation and execution

- **Required:** source context, test framework/dependencies, executable environment, reliable test output.
- **Verified:** Python stdlib `unittest`, Node `--check`/execution, GCC/Make compilation all passed. [T-010]
- **Missing:** pytest and common analysis packages absent; project-specific dependencies and internet installs not tested; no browser E2E.
- **Suggested workflow:** inspect test conventions; ask for risk-based cases before implementation; write a minimal failing test when safe; run the narrow target then whole suite; preserve command, exit code, and failures; don't report unrun tests as passing.
- **Likely external dependencies:** project requirements, test runner, service containers, browser for E2E.
- **Can Arena do it independently?** **Yes for environments with existing runnable dependencies; partial when the environment must be provisioned.**
- **Evidence still required:** real project dependencies, install/network behavior, timeouts on larger suites, coverage.

### I. Documentation and Markdown generation

- **Required:** source context, clear audience/structure, file creation, link/content validation.
- **Verified:** `write_file`, `edit_file`, and `read_file`; Markdown/text round-trip; this multi-file report generation. [T-009, T-013–T-015]
- **Missing:** no Markdown renderer/linter installed; exact workspace download transfer not verified.
- **Suggested workflow:** specify filename, audience, outline, evidence labels, exact sources, and validation checks; generate Markdown; run link/JSON/content checks; open the primary file for review; state download status precisely.
- **Likely external dependencies:** Markdown previewer or link checker for rendered formatting, if needed.
- **Can Arena do it independently?** **Yes for ordinary Markdown/text documents in the workspace.**
- **Evidence still required:** rendering behavior and actual user download path.

### J. PDF and spreadsheet reporting

- **Required:** reliable PDF/XLSX/DOCX/PPTX generator, parser/viewer, typography/tables, content validation.
- **Verified:** synthetic PDF structure, Office Open XML package ZIP/XML structure, CSV/JSON, and ZIP integrity. [T-009]
- **Missing:** no `pdftotext`, `pdfinfo`, LibreOffice, `python-docx`, `openpyxl`, `python-pptx`, or WeasyPrint metadata; Office files were not opened in an Office app; PDF was not rendered.
- **Suggested workflow:** prefer CSV/JSON/Markdown when interoperability matters; for Office/PDF, use project-provided libraries if installed; validate ZIP/XML plus open in an independent renderer; clearly label structural-only checks.
- **Likely external dependencies:** `openpyxl`, `python-docx`, `python-pptx`, LibreOffice, PDF renderer/converter.
- **Can Arena do it independently?** **Partial.** It can create simple files by code; professionally formatted, application-validated reports were not proven.
- **Evidence still required:** independent app-open validation, visual layout, fonts/page breaks, formula calculation, larger files.

### K. Screenshot capture and visual QA

- **Required:** browser rendering, capture at defined viewports, image inspection, interaction/state coverage.
- **Verified:** image tool generated/edited simple pictures; `read_file` displayed them; local server worked. [T-011–T-012]
- **Missing:** no browser/screenshot tool or Playwright; the inspected pictures were not website screenshots.
- **Suggested workflow:** request an actual screenshot file from the user or use an external browser/screenshot runner; inspect the image but distinguish visual observation from measured layout; attach viewport/browser metadata.
- **Likely external dependencies:** Playwright/Chromium or screenshot provider.
- **Can Arena do it independently?** **No for automated capture in this session; partial for looking at a supplied/generated image.**
- **Evidence still required:** real screenshot reading accuracy and browser-generated screenshot delivery.

### L. Static website development

- **Required:** HTML/CSS/JS authoring, simple local server, review, optional deploy.
- **Verified:** HTML fixture served on a preview port with expected markers; Node/Python/GCC build smokes; HTML/XML content file creation. [T-009–T-011]
- **Missing:** no Vite/frameworks resolved, no browser render, no deployment/hosting tool tested, shell external networking uncertain.
- **Suggested workflow:** build static assets without unnecessary packages; serve on `0.0.0.0`; test HTTP status/content locally; have the user inspect the preview; don't claim browser QA/deployment without evidence.
- **Likely external dependencies:** framework/build tool if desired, hosting provider for deployment, browser for visual tests.
- **Can Arena do it independently?** **Yes for small static sites/prototypes and local preview; no verified deployment.**
- **Evidence still required:** actual rendered preview, real project build, deployment, accessibility/viewport checks.

### M. Agent workflow development

- **Required:** tool orchestration, state, retries, safe boundaries, external APIs, background scheduling, observability.
- **Verified:** multiple tool types and a parallel wrapper; local process can run across tool calls and be stopped. [T-002–T-005, T-011]
- **Missing:** no subagent-spawn function, scheduler, task queue, durable database, broad shell egress verification, or retry contract.
- **Suggested workflow:** prototype a finite workflow using search/fetch/bash/files; record state in JSON; make each step idempotent; ask approval before writes/remote actions; persist a human-readable log; keep long-running work in the process tool only while the session is active.
- **Likely external dependencies:** API credentials (never paste into report), database/queue, scheduler, reliable network, deployment/runtime environment.
- **Can Arena do it independently?** **Yes for bounded prototypes and orchestration; not for an always-on agent service.**
- **Evidence still required:** process lifetime across session close, retries, concurrency guarantees, durable persistence, auth/network integrations.

### N. Processing large uploaded datasets

- **Required:** upload limits, streaming parser, disk/RAM budget, format support, reliable retrieval and validation.
- **Verified:** CSV/JSON local parsing and synthetic file creation; official Agent Mode upload list includes CSV and several text/image formats. [S-01, T-009]
- **Missing:** upload UI was not exercised; maximum file size/count not reliably established; large datasets not tested; pandas absent; RAM/disk snapshots are not quotas; current context size unknown.
- **Suggested workflow:** ask for schema/row count first; process data in chunks/streaming rather than prompt-dumping; preserve raw input; produce deterministic aggregate CSV/JSON; validate totals/checksums; report rows skipped and memory limits; split very large inputs outside Arena.
- **Likely external dependencies:** streaming libraries, object storage/data warehouse, external compute, data governance approval.
- **Can Arena do it independently?** **Yes only for modest, well-bounded datasets; not established for large uploads or heavy analysis.**
- **Evidence still required:** actual upload limits, representative file size/row count, memory profile, run duration, accuracy/reconciliation.

### O. Handoff packages for other coding agents

- **Required:** concise task context, file map, requirements, verification status, known gaps, source citations, machine-readable metadata.
- **Verified:** Markdown/JSON/CSV/ZIP creation and JSON/ZIP validation; file read/write/edit; actual reports in workspace. [T-009, T-013–T-015]
- **Missing:** workspace download not tested; no cross-session persistence guarantee; no handoff-specific API.
- **Suggested workflow:** use the practical templates in [ARENA_AGENT_PRACTICAL_WORKFLOWS.md](ARENA_AGENT_PRACTICAL_WORKFLOWS.md); include tested commands/results, untested work, exact filenames, and a manifest; ask the recipient to confirm checksums and inspect diffs.
- **Likely external dependencies:** a verified download/share route or version-controlled transfer; optional ZIP if receiver needs one bundle.
- **Can Arena do it independently?** **Yes for preparing handoff files in the current workspace; transfer/download remains unverified.**
- **Evidence still required:** actual workspace download/share, cross-session retrieval, downstream agent successfully using the package.

---

## 13. Recommended operating posture

**Good supplementary uses (evidence-backed):** bounded source research; reading/summarizing accessible web pages; writing Markdown/JSON/CSV; small scripts and test generation; local code execution using tools already installed; static-site prototypes; image generation/editing; handoff documentation.

**Use with an external verifier:** dynamic website audits, responsive/browser QA, PDF/Office report layout, big datasets, package-heavy builds, security reviews, public-site crawling, and high-stakes research.

**Do not assume:** Playwright, screenshots, repository access, a specific model, unlimited context/credits, successful package downloads, full internet egress, multi-agent delegation, a background scheduler, or private handling of uploaded data.

No comparative token-saving or subscription-cost claim is made. The evidence supports capability boundaries, not an economic benchmark.

---

## 14. Official source register

All sources below were retrieved through `web_search` or `fetch_page` on 2026-09-26 UTC unless a note says otherwise. First-party sources are classified `OFFICIAL_DOCUMENTATION`; the source's claims have not been independently audited.

| ID | Exact source URL | Source and use | Retrieval status |
|---|---|---|---|
| S-01 | https://help.arena.ai/articles/5432423882-how-to-use-agent-mode | “How to use Agent Mode on Arena.” Tools, upload formats, workspace/download/GitHub workflow, model transparency, multi-step orchestration. Help page text says “Last updated 6 days ago”; web-search result `pageAge` was Sunday, 20 Sep 2026. | `OFFICIAL_DOCUMENTATION`; fetched all 3 chunks |
| S-02 | https://help.arena.ai/articles/5595418316-arena-how-to-file-upload | “How to Upload Files into Arena.” Upload method and Agent Mode format list. | `OFFICIAL_DOCUMENTATION`; full page fetched |
| S-03 | https://arena.ai/blog/coding-in-agent-mode | “Coding in Agent Mode: From Idea to Shipping with GitHub.” Published 24 Aug 2026, updated 26 Aug 2026; GitHub OAuth/sandbox/diff/commit/push/PR claims. | `OFFICIAL_DOCUMENTATION`; both chunks fetched |
| S-04 | https://arena.ai/company/product-changelog | Arena Product Changelog. 26 Aug 2026 GitHub feature entry. | `OFFICIAL_DOCUMENTATION`; page fetched |
| S-05 | https://help.arena.ai/articles/1492254790-arena-experiments-github-integration-in-agent-mode | Help Center search excerpt says GitHub was an experiment and each session supported one PR; URL fetch returned a “Page Not Found” page. Used only as a staleness/inconsistency signal. | `OFFICIAL_DOCUMENTATION` search excerpt; fetch not retrievable |
| S-06 | https://help.arena.ai/articles/1645798556-lmarena-how-to-something-went-wrong-with-this-response-error-message?st_source=ai_mode | Search snippet said up to 10 file uploads per chat; the fetched page text did not contain that statement. | `PARTIALLY_VERIFIED` source discrepancy; do not treat 10 as current limit |
| S-07 | https://help.arena.ai/articles/5476762589-credit-sytem | “How to understand Arena's Credit System.” Daily credit period and 24-hour reset mechanics; last updated 9 days ago in fetched page. | `OFFICIAL_DOCUMENTATION`; full page fetched |
| S-08 | https://help.arena.ai/articles/3295820808-arena-troubleshooting-daily-usage-limits | “Daily Usage Limits.” Describes 24-hour reset and rollout status; page says last updated 3 months ago. | `OFFICIAL_DOCUMENTATION`; full page fetched; older than S-07 |
| S-09 | https://help.arena.ai/articles/8931786544-arena-how-to-rate-limit | “Rate Limit.” Per-model and overall chat rate limits; no numeric thresholds; page says last updated 6 months ago. | `OFFICIAL_DOCUMENTATION`; full page fetched |
| S-10 | https://help.arena.ai/articles/3975292349-arena-troubleshooting-session-token-limits | “Session Token Limits.” Context limits, built-in Agent Mode compaction, no cross-session context transfer; page says last updated 3 months ago. | `OFFICIAL_DOCUMENTATION`; full page fetched |
| S-11 | https://help.arena.ai/articles/3765052346-privacy-policy | Arena Privacy Policy. Effective/last-updated date printed in the fetched page: 2025-12-16; discusses user content, third-party AI providers, public sharing, retention. | `OFFICIAL_DOCUMENTATION`; all 7 chunks fetched |
| S-12 | https://help.arena.ai/articles/9130232616-how-to-delete-your-chat-sessions-and-data-from-arena | Session deletion flow; data queued for deletion, typically within 30 days, exceptions noted; page says last updated 3 days ago. | `OFFICIAL_DOCUMENTATION`; full page fetched |
| S-13 | https://arena.ai/blog/agent-mode | “Empowering Users to Get More Done With Agent Mode.” Published 4 Jun 2026, updated 5 Jun 2026; multi-step/deep-research marketing description. | `OFFICIAL_DOCUMENTATION`; both chunks fetched |
| S-14 | https://arena.ai/blog/agent-arena-methodology | “Agent Arena: Causal Evaluation of Agents in the Real World.” Arena's explanation of its real-session leaderboard and orchestrator evaluation. | `OFFICIAL_DOCUMENTATION`; first chunk fetched (additional chunks available) |
| S-15 | https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf | One-page public dummy PDF used to smoke-test PDF retrieval. | External first-party test fixture; one page parsed to “Dummy PDF file” |
| S-16 | https://arxiv.org/html/2510.24358v1 | “Automatically Benchmarking LLM Code Agents through Agent-driven Annotation and Evaluation,” surfaced by an academic search and fetched for a small academic-source test. | Academic page; first chunk fetched, not a complete paper review |
| S-17 | https://help.arena.ai/articles/1811908126-arena-experiments-agent-mode | Earlier Agent Mode experiments/help article appeared in search results; URL fetch returned “Page Not Found.” | `PARTIALLY_VERIFIED`; stale/inaccessible source |

---

## 15. Probe evidence index

Execution details, stdout/stderr, errors, and test classifications are in [ARENA_AGENT_PROBE_RESULTS.md](ARENA_AGENT_PROBE_RESULTS.md). Practical prompts are in [ARENA_AGENT_PRACTICAL_WORKFLOWS.md](ARENA_AGENT_PRACTICAL_WORKFLOWS.md). Machine-readable status is in [ARENA_AGENT_CAPABILITY_MANIFEST.json](ARENA_AGENT_CAPABILITY_MANIFEST.json).

| Test IDs | Subject |
|---|---|
| T-001 | Runtime, package, browser-path, resource snapshot |
| T-002–T-005 | Web search, official Arena documentation, PDF, academic-page retrieval |
| T-006–T-008 | External HTTPS error, subprocess, loopback, cgroup observations |
| T-009 | 12-format synthetic fixture creation and validation |
| T-010 | Python unittest, Node check/run, GCC/Make build |
| T-011 | Background server, preview port, HTTP fixture, process shutdown |
| T-012 | Image generation, image editing, visible image inspection, scratch cleanup |
| T-013 | Workspace write/edit/read smoke test |
| T-014–T-015 | Final deliverable presentation and post-write validation (see probe-results log) |
