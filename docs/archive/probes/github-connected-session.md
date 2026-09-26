# Arena Agent Mode — GitHub-Connected Session Probe

**Probe date:** 2026-09-26 (UTC)
**Session type:** Arena Agent Mode **with a GitHub repository connected**
**Connected repository:** [FullThrottle83/arena](https://github.com/FullThrottle83/arena)
**Working branch:** `arena/01a0dc7e-arena` (assigned by Arena, preserved — see §3.2)
**Base commit:** `12630762fd28d6fdad782bd99964b961de7f9dd0` (= `origin/main` at probe time)

> **Scope and honesty rule.** Every capability below is labelled from what actually ran in this
> session. `EXECUTION_VERIFIED` means a real command or tool call produced the quoted output.
> `PARTIALLY_VERIFIED` means the mechanism ran but not the full claim. `DOCUMENTED_ONLY` means
> official documentation describes it and this session did not exercise it. `NOT_TESTED` means it
> was deliberately skipped. `UNAVAILABLE` means this session proved it is absent or refused.
>
> This is a snapshot of **one** session on **one** account, plan, model and date. It is not a
> statement about every Arena account or future release.

---

## 1. Session and environment information

### 1.1 Connection confirmation

The probe requirement was to confirm GitHub is enabled and that the selected repository is
`FullThrottle83/arena`, and to stop if it was not. Both were confirmed **before** any write
operation, by three independent reads:

| Check | Command | Observed result |
|---|---|---|
| Remote URL | `git remote -v` | `origin https://github.com/FullThrottle83/arena.git` (fetch + push) |
| Auth identity | `gh auth status` | `✓ Logged in to github.com as arena-ai-coding-agent[bot] (GH_TOKEN)`; `✓ Git operations for github.com configured to use https protocol` |
| Repository metadata | `gh repo view --json …` | `nameWithOwner: FullThrottle83/arena`, `defaultBranchRef.name: main` |

The connection was genuine, so the probe continued. **No unrelated local workspace was
substituted.**

The credential is an injected `GH_TOKEN` for the GitHub App bot `arena-ai-coding-agent[bot]`.
Per the working rules, the token value was never read, printed, or logged. `gh auth status`
masks it as `Token: ************************` and that masked form is the only representation
reproduced here.

### 1.2 Sandbox snapshot

All values below are `uname`/`nproc`/`free`/`df` observations at one moment, not quotas.

| Item | Observed value | Command |
|---|---|---|
| OS | Debian GNU/Linux 12 (bookworm) | `cat /etc/os-release` |
| Kernel | `Linux e2b.local 6.1.158+ #1 SMP PREEMPT_DYNAMIC … x86_64` | `uname -a` |
| CPU cores | `2` | `nproc` |
| Memory | `3939` MB total, `3683` MB available | `free -m` |
| Disk | `/dev/root` 21 G total, 814 M used, 20 G available | `df -h /home/user` |
| Workspace root | `/home/user/arena` | `pwd` |
| Repo checkout | `/home/user/arena` (a real git clone, `.git` present) | `ls -la` |

The host name `e2b.local` and the E2B-shaped environment indicate a containerised sandbox
provider. This is an inference from the hostname, **not** confirmed documentation.

### 1.3 Installed toolchain

Probed with `command -v` plus `--version`; `pytest` is a deliberate "look past the bare
`command -v`" case.

| Tool | Result |
|---|---|
| `git` | 2.39.5 |
| `gh` | 2.23.0 (2023-02-27, Debian package) |
| `python3` | 3.11.2 |
| `node` | v22.22.3 |
| `npm` / `npx` | 10.9.8 |
| `make` | GNU Make 4.3 |
| `gcc` / `g++` | 12.2.0 (Debian 12.2.0-14+deb12u1) |
| `pytest` | **NOT_FOUND** on `PATH`, but installable — see §2.6 |

### 1.4 Network egress from bash

This session **corrects a generalisation in the earlier probe**. `ARENA_AGENT_PROBE_RESULTS.md`
records `curl https://example.com` failing with `SSL_ERROR_SYSCALL` and warns against
generalising it. This probe mapped the boundary instead of assuming it:

| Target | HTTP result | Verdict |
|---|---|---|
| `https://api.github.com` | `200` (0.25 s) | allowed |
| `https://codeload.github.com` | `301` | allowed |
| `https://registry.npmjs.org` | `200` | allowed |
| `https://pypi.org` | `200` | allowed |
| `https://example.com` | `000`, `curl: (35) OpenSSL SSL_connect: SSL_ERROR_SYSCALL` | blocked |
| `https://astro.build` | `000` | blocked |
| `https://docs.astro.build` | `000` | blocked |
| `https://fonts.googleapis.com` | `000` | blocked |
| `https://en.wikipedia.org/wiki/Astro_%28web_framework%29` | `000` | blocked |
| `https://api.npmjs.org` | `000` | blocked |
| `https://deno.land` | `000` | blocked |
| `https://registry.npmmirror.com` | `000` | blocked |

**Reading:** egress is **not** blanket-blocked. It behaves like a narrow allowlist covering
GitHub endpoints and the two canonical package registries (npm, PyPI). Arbitrary web hosts fail
at the TLS handshake. Consequences:

- Package installs work (§2.6), so real dependency-driven builds are possible.
- Mirror registries are **not** reachable — only the canonical ones.
- Reaching project docs, fonts, APIs, or webhooks from bash generally will **not** work. Use the
  dedicated `web_search` / `fetch_page` tools instead; those retrieved pages that `curl` could not
  (§2.7).
- A blocked `curl` is therefore **not** evidence that the sandbox is offline, and a working
  `curl` is not evidence that arbitrary egress is open.

---

## 2. Actual exposed tools

### 2.1 Tool registry visible to this session

These are the tools actually callable here, grouped by role. Names are as exposed.

**Repository, shell, files**

| Tool | Role | Status in this session |
|---|---|---|
| `bash` | Run a command in the sandbox; optional `cwd` and `timeout` (default 30 s, max 1800 s). No controlling terminal, stdin closed. Returns stdout, stderr, exit code, duration, truncation flags. | `EXECUTION_VERIFIED` — used for ~15 probe calls |
| `read_file` | Read a workspace file by path, with line offset/limit; renders images, returns metadata for other binaries. | `EXECUTION_VERIFIED` — §2.3 |
| `write_file` | Create or overwrite a file from full content; creates parent directories. | `EXECUTION_VERIFIED` — §2.3 |
| `edit_file` | Replace the first fuzzy match of a search string; tolerates whitespace/indent drift. | `EXECUTION_VERIFIED` — §2.3 |
| `present_file` | Open one workspace file in the user's viewer. | `EXECUTION_VERIFIED` — deliverable opened |

**Processes and preview**

| Tool | Role | Status |
|---|---|---|
| `start_process` | Start a long-lived background process with a user-facing name, `cwd`, `startup_wait` (max 30 s). Returns process id, log tail, listening ports, warnings. | `EXECUTION_VERIFIED` — §2.5 |
| `get_process_output` | Read log tail/liveness; can block on `port`, `log`, or `exit` (max wait 180 s). | `EXPOSED_TOOL`, `NOT_TESTED` (not needed; `start_process` already reported the port) |
| `stop_process` | Terminate the process group (SIGTERM then SIGKILL); returns final log tail. | `EXECUTION_VERIFIED` — §2.5 |

**Research**

| Tool | Role | Status |
|---|---|---|
| `web_search` | Query the web with `depth` 1–3; returns ids, titles, URLs, snippets, sometimes `pageAge`. | `EXECUTION_VERIFIED` — §2.7 |
| `fetch_page` | Retrieve a URL as Markdown text, paginated by `chunkIndex`; PDFs parsed to 30 pages. | `EXECUTION_VERIFIED` — §2.7 |

**Media and interaction** (exposed, deliberately not exercised to avoid interrupting the probe)

| Tool | Role | Status |
|---|---|---|
| `generate_image` | Generate or edit one standalone image. | `EXPOSED_TOOL`, `NOT_TESTED` here |
| `image_search` | Search images into workspace paths. | `EXPOSED_TOOL`, `NOT_TESTED` |
| `add_voice` / `generate_speech` | Audition a voice, then synthesise speech. | `EXPOSED_TOOL`, `NOT_TESTED` |
| `ask_user` | Show a clarification UI with predefined options. | `EXPOSED_TOOL`, `NOT_TESTED` |

**Parallel dispatch.** Independent tool calls were issued in the same block repeatedly
(e.g. two `write_file` calls plus one `start_process`; two `bash` probes at once). All returned
correctly and concurrently — `EXECUTION_VERIFIED` for the mechanism, `PARTIALLY_VERIFIED` for any
claim about actual scheduling speedup.

### 2.2 What is **not** an exposed tool here

- **No dedicated GitHub tool.** This is the headline difference from the earlier non-connected
  probe, which reported "no dedicated GitHub function appears … remote operations were not
  tested." In *this* session, GitHub works — but through **`git` and `gh` inside `bash`**, driven
  by an injected `GH_TOKEN`. There is still no `github_connect` / `push_changes` / `open_pr`
  function in the callable registry, contrary to the tool names listed in the research
  transcription at `docs/arena-agent-mode-research-2026-09-26.md`. Treat those names as
  `DOCUMENTED_ONLY`.
- **No browser automation, Playwright, or screenshot tool.** Not re-probed here; the earlier
  inventory found no browser executable or Playwright package. Carried forward as
  `NOT_TESTED` in this session.
- **No usage/token meter.** Nothing exposes credit balance, per-model quota, or token accounting.
  See §8.
- **No merge/close authority exercised.** Per the working rules, `gh pr merge` and
  `gh pr close` were never run. Whether the token *could* merge is untested and intentionally so.

### 2.3 File operations (create, edit, read, multi-file)

Scratch files were written under `/tmp` so the repository stayed untouched (§3.3).

| Operation | Call | Observed result |
|---|---|---|
| Parallel multi-file create | two `write_file` calls in one block (`/tmp/probe_files/a.md`, `b.md`) | both `{"status":"success"}` |
| Edit by fuzzy match | `edit_file` replacing `ORIGINAL_VALUE` → `EDITED_VALUE` | `{"status":"success","message":"Edited /tmp/probe_files/a.md."}` |
| Read back | `read_file /tmp/probe_files/a.md` | `lines: 4`, `size: 48`, content contained `Line under test: EDITED_VALUE` |
| Parent-dir creation | `write_file` to a non-existent directory | succeeded without a pre-created directory |

`write_file` creates missing parents and overwrites wholesale; `edit_file` replaces only the
**first** fuzzy match, so it is not a semantic merge and not safe for repeated identical anchors.

### 2.4 Repository reading and traversal

| Operation | Command | Observed result |
|---|---|---|
| List tracked files | `find . -path ./.git -prune -o -type f -print` | 7 files: `README.md`, 4 root `ARENA_AGENT_*` files, `docs/arena-agent-mode-research-2026-09-26.md`, `docs/next-research-batch.md` |
| Size inventory | `wc -c` | `README.md` is 8 bytes; inventory 68 086 B; research 34 884 B; probe results 24 995 B; workflows 17 228 B; next-batch 12 030 B |
| Structure scan | `grep -nE '^#{1,3} '` over all 5 docs | recovered every heading; used to navigate without loading 157 KB into context |
| Remote tree | `git ls-tree -r origin/main --name-only` | matched the working tree exactly |
| Read | `read_file` / `sed -n` / `cat` | full-text reads succeeded |

**Technique worth keeping:** heading-first navigation (`grep -nE '^#{1,3} '`) plus ranged
`sed -n 'A,Bp'` reads let a 157 KB documentation set be reviewed without consuming the whole
context window. This is the practical answer to "context persistence during a longer task" —
the lever is *what you load*, not a bigger window.

### 2.5 Build tools, test runners, background processes, preview

**Test runners and compilers — all executed:**

| Runner | Command | Observed result |
|---|---|---|
| Python `unittest` | `python3 -m unittest -v t.py` | `Ran 1 test in 0.000s` / `OK` |
| Node test runner | `node --test` (after rename to `t.test.mjs`) | `# tests 1`, `# pass 1`, `# fail 0` |
| Node explicit file | `node --test t.test.mjs` | `# tests 1`, `# pass 1`, `# fail 0` |
| GCC + Make | `make` on a one-line C program | `gcc c.c -o c`, produced a 15 832-byte executable |
| pytest | `venv/bin/pytest --version` after `pip install pytest` | `pytest 9.1.1` |

`node --test` initially reported **0 tests** because the file was `t.mjs`; Node's default
discovery wants `*.test.mjs` / `test-*.mjs` / a `test/` directory. Renaming fixed it (§7, F-2).

**Package installation — both ecosystems work:**

| Operation | Command | Observed result |
|---|---|---|
| npm install | `npm install --no-audit --no-fund chalk` | `added 1 package in 325 ms` |
| npm require | `node -e "require('chalk')"` | `chalk loaded ok object` |
| npm metadata | `npm view astro version` | `7.3.5` |
| Python venv | `python3 -m venv probe_venv` | created cleanly |
| pip install | `probe_venv/bin/pip install -q pytest` | installed; `pytest 9.1.1` |

**Background process + live preview — the full cycle ran:**

| Step | Call | Observed result |
|---|---|---|
| Start | `start_process` → `python3 -m http.server 8811 --bind 0.0.0.0`, cwd `/tmp/probe_preview`, `startup_wait: 6` | `status: running`, `pid: 1649`, `listening_ports: [{port: 8811, address: "0.0.0.0"}]`, `duration_ms: 429`, **no warnings** |
| Serve | `curl http://127.0.0.1:8811/` | `http_code=200 bytes=350` |
| Serve JSON | `curl http://127.0.0.1:8811/health.json` | `{"status":"ok","probe":"arena-github-connected-session"}` |
| Error path | `curl http://127.0.0.1:8811/nope` | `http_code=404` |
| Stop | `stop_process probe-static-preview-d35565d5` | `status: stopped`; log tail contained the three real requests: `GET / HTTP/1.1" 200`, `GET /health.json HTTP/1.1" 200`, `GET /nope HTTP/1.1" 404` |

The absence of a warning on `start_process` matters: the platform actively probes new ports for
preview-breaking responses (host/origin rejection, iframe-embedding blocks) and reports them in
`warnings`. A clean result means the server was reachable through the preview proxy. Ports bound
to `127.0.0.1` would **not** be user-visible.

The server was stopped and the scratch directory left in `/tmp`, outside the repository.

### 2.6 Capability ledger

Fields per the probe spec. `evidence_reference` points at the section above or the external
artefact.

| capability_id | operation | tool_or_command | observed_result | execution_status | limitations | evidence_reference |
|---|---|---|---|---|---|---|
| GH-001 | Confirm repository connection | `git remote -v` | `origin https://github.com/FullThrottle83/arena.git` | `EXECUTION_VERIFIED` | Shows config, not live reachability | §1.1 |
| GH-002 | Confirm auth identity | `gh auth status` | `Logged in … as arena-ai-coding-agent[bot] (GH_TOKEN)` | `EXECUTION_VERIFIED` | Token value masked and never read | §1.1 |
| GH-003 | Confirm default branch | `gh repo view --json defaultBranchRef` | `main` | `EXECUTION_VERIFIED` | — | §1.1 |
| GH-004 | Read repository metadata | `gh api repos/FullThrottle83/arena` | `open_issues: 0`; all `permissions` booleans `false` | `PARTIALLY_VERIFIED` | `permissions` block is meaningless under an App installation token | §5.2 |
| GH-005 | Query authenticated user | `gh api user` | `403 Resource not accessible by integration` | `UNAVAILABLE` | By design for installation tokens; blocks "who am I" introspection | §7, F-3 |
| GH-006 | Read remote refs | `git ls-remote --heads origin` | `main` + `arena/01a0dc43-arena` (concurrent session) | `EXECUTION_VERIFIED` | Read-only view of branch names | §3.4 |
| GH-007 | Check API quota | `gh api rate_limit` | `limit: 6650, remaining: 6646` | `EXECUTION_VERIFIED` | GitHub API quota ≠ Arena credits | §5.2 |
| GH-008 | List pull requests | `gh pr list --state all` | PR #1 `MERGED`, head `arena/01a0dc43-arena` | `EXECUTION_VERIFIED` | — | §5.3 |
| GH-009 | Commit | `git add` + `git commit` | see §5.4 | `EXECUTION_VERIFIED` | Author is the preconfigured bot identity | §5.4 |
| GH-010 | Push branch | `git push -u origin arena/01a0dc7e-arena` | see §5.4 | `EXECUTION_VERIFIED` | Only to the session's own branch | §5.4 |
| GH-011 | Open a pull request | `gh pr create --draft` | see §5.5 | `EXECUTION_VERIFIED` | Draft used; not marked ready, not merged | §5.5 |
| GH-012 | Merge or close a PR | `gh pr merge` / `gh pr close` | never invoked | `NOT_TESTED` | Prohibited by the working rules | §2.2 |
| GH-013 | Push to `main` | `git push origin main` | never invoked | `NOT_TESTED` | Prohibited by the working rules | §2.2 |
| REPO-001 | Repository read + traversal | `find`, `wc`, `git ls-tree` | 7 tracked files enumerated, sizes measured | `EXECUTION_VERIFIED` | — | §2.4 |
| REPO-002 | Targeted doc reading | `grep -nE '^#{1,3} '`, `sed -n 'A,Bp'` | all headings from 5 docs without full load | `EXECUTION_VERIFIED` | Manual; no semantic index | §2.4 |
| FILE-001 | File creation | `write_file` | `status: success` | `EXECUTION_VERIFIED` | Whole-file overwrite only | §2.3 |
| FILE-002 | File editing | `edit_file` | `Edited /tmp/probe_files/a.md.` | `EXECUTION_VERIFIED` | First fuzzy match only | §2.3 |
| FILE-003 | File reading | `read_file` | `lines: 4, size: 48`, edit confirmed | `EXECUTION_VERIFIED` | — | §2.3 |
| FILE-004 | Multi-file write | 2× `write_file` in one block | both succeeded | `EXECUTION_VERIFIED` | No atomic multi-file transaction | §2.3 |
| GIT-001 | Status | `git status` | `On branch arena/01a0dc7e-arena / nothing to commit, working tree clean` | `EXECUTION_VERIFIED` | — | §3.1 |
| GIT-002 | Diff review | `git diff --cached --stat`, `git diff --cached` | see §6 | `EXECUTION_VERIFIED` | Agent-side text diff, not Arena's Diff tab | §6 |
| GIT-003 | Commit creation | `git commit -m` | see §5.4 | `EXECUTION_VERIFIED` | — | §5.4 |
| GIT-004 | Log / history | `git log --oneline` | single commit `1263076 docs: run all Arena probes…` | `EXECUTION_VERIFIED` | Shallow history (1 commit) | §3.1 |
| BUILD-001 | Python tests | `python3 -m unittest` | `OK` | `EXECUTION_VERIFIED` | Trivial synthetic test | §2.5 |
| BUILD-002 | Node tests | `node --test` | `# pass 1` | `EXECUTION_VERIFIED` | Needs `*.test.mjs` naming | §2.5, §7 F-2 |
| BUILD-003 | C build | `make` + `gcc` | 15 832-byte binary | `EXECUTION_VERIFIED` | Trivial program | §2.5 |
| BUILD-004 | npm install | `npm install chalk` | `added 1 package in 325 ms` | `EXECUTION_VERIFIED` | Canonical registry only | §2.5 |
| BUILD-005 | pip install in venv | `pip install pytest` | `pytest 9.1.1` | `EXECUTION_VERIFIED` | `pytest` not preinstalled | §2.5 |
| BUILD-006 | Astro project build | `npm create astro` / `astro build` | not run | `NOT_TESTED` | Registry reachable and `astro@7.3.5` resolves, but no project was scaffolded | §9 |
| PROC-001 | Background process | `start_process` | `running`, `pid 1649`, port 8811 | `EXECUTION_VERIFIED` | `startup_wait` max 30 s | §2.5 |
| PROC-002 | Log/liveness read | `stop_process` returned log tail | 3 real requests logged | `EXECUTION_VERIFIED` | `get_process_output` itself not called | §2.5 |
| PROC-003 | Process stop | `stop_process` | `status: stopped` | `EXECUTION_VERIFIED` | — | §2.5 |
| PREVIEW-001 | Local HTTP server | `python3 -m http.server 8811 --bind 0.0.0.0` | `200`, 350 bytes | `EXECUTION_VERIFIED` | Must bind `0.0.0.0` | §2.5 |
| PREVIEW-002 | Preview-host acceptance | `start_process` warnings field | empty — no origin/iframe rejection | `PARTIALLY_VERIFIED` | No browser rendered it; visual layout unverified | §2.5 |
| PREVIEW-003 | Browser rendering of preview | — | — | `NOT_TESTED` | No browser/Playwright tool exposed | §2.2 |
| NET-001 | Egress mapping | 12× `curl` | GitHub/npm/PyPI `200`; 8 other hosts `000` | `EXECUTION_VERIFIED` | Allowlist contents inferred, not documented | §1.4 |
| RES-001 | Web search | `web_search` depth 1 | returned official Arena help article with `pageAge` | `EXECUTION_VERIFIED` | Snippets only | §2.7 |
| RES-002 | Page fetch | `fetch_page` | chunk 0 of 3, `hasMore: true` | `EXECUTION_VERIFIED` | Long pages need repeated chunks | §2.7 |
| CTX-001 | Context persistence | whole session | facts from turn 1 reused verbatim at the end | `EXECUTION_VERIFIED` | No numeric window or usage counter exposed | §2.8 |
| USAGE-001 | Token/credit accounting | — | no such tool or file | `UNAVAILABLE` | Blocks any token-savings estimate | §8 |
| SEC-001 | Secret non-disclosure | `gh auth status` output | token shown only as `************************` | `EXECUTION_VERIFIED` | Agent discipline, not a platform guarantee | §1.1 |

### 2.7 Research tools in a connected session

Confirmed present and working **alongside** GitHub — so research and delivery compose in one
session:

- `web_search` (depth 1) for `Arena.ai Agent Mode GitHub integration pull request docs` returned
  the first-party help article *How to use Agent Mode on Arena* (`help.arena.ai`, `pageAge`
  "Sunday, September 20, 2026") plus two unrelated GitHub PRs.
- `fetch_page` retrieved that help article: `chunkIndex 0`, `totalChunks 3`, `hasMore true`.
- Note that `curl https://help.arena.ai` was not attempted; §1.4 shows arbitrary hosts are
  blocked, which is precisely why the dedicated research tools matter.

The retrieved help page states the connected-repo delivery model verbatim: *"A repository
connected: The assistant works directly in a copy of your repo, so there's no zip download. Your
changes are delivered to GitHub instead: the assistant commits to a working branch and opens a
pull request. Review them in the **Diff** tab, then merge or pull that branch to get your
files."* And the constraint that shapes every workflow: *"Once the pull request is merged or
closed, the session can no longer push to GitHub. Any files created after that point stay in the
session but can't be pushed, downloaded, or carried into a new session."* It also documents a
`/download-workspace` URL suffix as an emergency workspace download.

### 2.8 Context persistence

Assessed by behaviour, not by a number: identifiers from the first turn were reused correctly
much later — branch `arena/01a0dc7e-arena`, base SHA `1263076…`, the port `8811`, the process id
`probe-static-preview-d35565d5`, and the concurrent branch `arena/01a0dc43-arena`. No fact was
re-derived from scratch and no earlier finding was contradicted.

What is **not** verifiable: the token budget, how much remains, or where summarisation begins.
Nothing in the session exposes it. So `CTX-001` is `EXECUTION_VERIFIED` for *retention across a
multi-step task* and silent on capacity.

---

## 3. Repository and branch information

### 3.1 Repository state at start

| Item | Value |
|---|---|
| Owner / name | `FullThrottle83` / `arena` |
| Default branch | `main` |
| Local workspace path | `/home/user/arena` |
| Git status at start | `On branch arena/01a0dc7e-arena` / `nothing to commit, working tree clean` |
| HEAD at start | `12630762fd28d6fdad782bd99964b961de7f9dd0` |
| HEAD commit message | `docs: run all Arena probes in parallel GitHub-connected sessions` |
| HEAD author / date | Jonas Pudas, Sat Sep 26 08:51:59 2026 +0200 |
| History depth | 1 commit visible (`git log --oneline` returned a single line) |
| Commits ahead/behind `origin/main` | `0	0` (`git rev-list --left-right --count origin/main...HEAD`) |
| Commit identity | `FullThrottle83 <110360247+FullThrottle83@users.noreply.github.com>` |

### 3.2 Branch — requested vs. assigned

The task preferred `arena/probe-github`. **Arena assigned `arena/01a0dc7e-arena`**, and the
working rules say to preserve an Arena-assigned branch and record its actual name. The session is
also bound to that branch: all commits and the push go to `arena/01a0dc7e-arena`, and no other
branch was created, checked out, or pushed.

`git ls-remote --heads origin` at probe time returned exactly two branches — `main` and
`arena/01a0dc43-arena`. The latter belongs to a **concurrent** Arena session (its PR #1 was
already `MERGED`). It was not read, modified, or interfered with.

### 3.3 Write scope

The only path written inside the repository was `docs/probes/github-connected-session.md`, which
did not exist before (`docs/` contained only the research and next-batch files; `docs/probes/` was
created by this probe). Every other artefact — the C program, the Python/Node tests, the venv,
`node_modules`, the preview site — was written under `/tmp` and is not part of the commit. No
existing research file was modified.

### 3.4 Concurrency observations

- `docs/probes/github-connected-session.md` is a **new** file, so no conflict with any existing
  research file was possible.
- Two Arena sessions worked the same repository in parallel on separate branches. Arena isolates
  them by branch; the merge is a human decision. `docs/next-research-batch.md` anticipates exactly
  this with a "Parallel coordination and merging" section.
- Risk to note: two sessions editing the *same* file would produce a real merge conflict that
  Arena does not resolve automatically. Disjoint output paths are what made this safe.

---

## 4. Executed commands and operations

Representative commands, in the order run. Outputs are quoted elsewhere in this document.

```bash
# Connection confirmation (read-only, before any write)
git remote -v
gh auth status                      # token value masked, never printed
gh repo view --json nameWithOwner,defaultBranchRef,viewerPermission,sshUrl,url

# Repository inspection
git status
git log -1 --format='%H%n%an%n%ad%n%s'
git log --oneline -15
git ls-tree -r origin/main --name-only
find . -path ./.git -prune -o -type f -print | sort
wc -c README.md docs/*.md *.md
grep -nE '^#{1,3} ' <each of the 5 docs>
sed -n '1,60p;85,145p' docs/arena-agent-mode-research-2026-09-26.md

# Environment and toolchain
uname -a; cat /etc/os-release; nproc; free -m; df -h /home/user
for c in git gh python3 node npm npx make gcc g++ pytest; do command -v "$c" && $c --version | head -1; done

# Egress mapping (12 targets)
curl -sS -o /dev/null -w "%{http_code}\n" --max-time 12 "<target>"

# Build and test runners
python3 -m unittest -v t.py
node --test                 # 0 tests -> renamed to t.test.mjs
node --test t.test.mjs      # 1 pass
make                        # gcc c.c -o c
python3 -m venv probe_venv && probe_venv/bin/pip install -q pytest
npm init -y && npm install --no-audit --no-fund chalk
npm view astro version

# Preview server (start_process / stop_process, not bash)
python3 -m http.server 8811 --bind 0.0.0.0
curl -sS -o /dev/null -w "http_code=%{http_code} bytes=%{size_download}\n" http://127.0.0.1:8811/

# GitHub API surface
gh api repos/FullThrottle83/arena --jq '{full_name,default_branch,permissions,open_issues}'
gh api rate_limit --jq '{limit:.rate.limit,remaining:.rate.remaining}'
gh pr list --state all --limit 20 --json number,title,headRefName,state,isDraft,url
gh pr list --state all --head arena/01a0dc7e-arena --json number,state,url

# Delivery
git fetch origin
mkdir -p docs/probes
# write_file docs/probes/github-connected-session.md
git add docs/probes/github-connected-session.md
git diff --cached --stat
git diff --cached
git commit -m "…"
git push -u origin arena/01a0dc7e-arena
gh pr create --draft --base main --head arena/01a0dc7e-arena --title "…" --body-file …
```

---

## 5. GitHub integration results

### 5.1 What works

The connected session delivers a complete `clone → read → write → test → commit → push → PR`
cycle without the user leaving the browser. Concretely verified: remote discovery, authenticated
API reads, branch listing, PR listing, commit, push to the session branch, and PR creation.

### 5.2 Permission model observed

| Query | Result | Interpretation |
|---|---|---|
| `gh api user` | `403 Resource not accessible by integration` | Installation token, not a user OAuth token. Identity introspection is unavailable; identity came from `gh auth status` instead. |
| `gh api repos/FullThrottle83/arena` → `permissions` | `admin: false, maintain: false, pull: false, push: false, triage: false` | **Misleading if read naively.** These booleans describe the authenticated *user* context and are meaningless for an App installation token. Real push access was proven empirically by §5.4, not by this field. |
| `gh api rate_limit` | `limit: 6650, remaining: 6646` | A GitHub App installation rate limit, consumed 4 calls by this probe. This is **not** an Arena credit meter. |

Practical consequence: **do not infer GitHub capabilities from the `permissions` object.** Probe
with the actual operation instead.

### 5.3 Pre-existing repository state

`gh pr list --state all` returned one PR: **#1 "Add Arena Agent Mode capability inventory"**,
head `arena/01a0dc43-arena`, state `MERGED`, not a draft,
`https://github.com/FullThrottle83/arena/pull/1`. That is the concurrent session's PR. It was
left untouched — not merged, closed, commented on, or rebased.

### 5.4 Commit and push

The commit and push were executed for this file. Concrete identifiers live in **Appendix D**,
appended by a follow-up commit on the same branch *after* the operations succeeded. They are
deliberately not written here: a document cannot truthfully contain the SHA of the commit that
introduces it, and guessing one would be fabrication.

Operations performed, in order:

1. `git add docs/probes/github-connected-session.md`
2. `git diff --cached --stat` and `--numstat` — reviewed before committing (§6.1)
3. `git commit -m "docs: add GitHub-connected session probe findings"`
4. `git push -u origin arena/01a0dc7e-arena`
5. `gh pr create --draft --base main --head arena/01a0dc7e-arena …`
6. follow-up commit recording the verified SHA, push result, and PR URL (Appendix D)

**Files changed:** `docs/probes/github-connected-session.md` (new file, pure addition).

### 5.5 Pull request

`gh pr create --draft --base main --head arena/01a0dc7e-arena` was used. Draft was chosen because
the task allowed it and because the documented lifecycle makes a draft the safer default (§8.1).
The PR was **not** merged, closed, or marked ready.

The PR URL is recorded in **Appendix D**, copied from `gh pr create`'s own stdout rather than
constructed from an assumed PR number.

### 5.6 The lifecycle constraint that matters most

From the first-party help page (§2.7): once the PR is **merged or closed**, the session can no
longer push, and files created afterwards cannot be pushed, downloaded, or carried into a new
session. Combined with §5.4, the operating rule is:

> **Push everything before you merge. Merge last, not first.** If more work is wanted after a
> merge, start a new session.

This is the single most important workflow difference between Arena and a long-lived local coding
agent, and it was **not** captured in the earlier non-connected probe because that session had no
GitHub connection to exercise.

---

## 6. Diff inspection results

Two distinct diff surfaces exist, and only one was testable from inside the session.

### 6.1 Agent-side diff (this session) — `EXECUTION_VERIFIED`

Inspected the staged change before committing:

```
$ git diff --cached --numstat
776	0	docs/probes/github-connected-session.md

$ git diff --cached --stat
 docs/probes/github-connected-session.md | 776 +++++++++++++++++++++++++++++++
 1 file changed, 776 insertions(+)

$ wc -l docs/probes/github-connected-session.md
776 docs/probes/github-connected-session.md
```

The inspection ran **twice**, and the second pass is the reason this section exists in its
current form. The first staging reported 737 insertions; reviewing that draft showed it contained
a commit SHA, an insertion count, and a PR URL that had been written **before** the operations ran
— invented values. They were removed and replaced with references to Appendix D, which is written
only after `gh` and `git` return real ones. The file was then re-staged and re-inspected, giving
the 776 above.

Reviewed with `git diff --cached`. The review confirmed:

- exactly **one** file, and it is inside the allowed output path;
- **776 insertions, 0 deletions** — a pure addition, so no existing research content could have
  been altered;
- no stray artefacts (`node_modules`, venv, binaries, `.pyc`) — all scratch work stayed in `/tmp`;
- no credential material: the only token reference is the masked `************************`
  string exactly as `gh auth status` prints it.

Also available and used: `git status`, `git log`, `git rev-list --left-right --count` for
ahead/behind, `git ls-tree` for remote-tree comparison, `git diff origin/main...HEAD`.

### 6.2 Arena's Diff tab (user-side) — `DOCUMENTED_ONLY` from inside the session

The help page documents a **Diff** tab for reviewing the agent's proposed changes line by line.
That is a browser UI element; an agent running in the sandbox cannot open, read, or assert
anything about it. Its existence here is `DOCUMENTED_ONLY`, corroborated by the fact that this
session's push and PR succeeded, which is the workflow the Diff tab fronts. **User action
required:** confirm the Diff tab renders this commit line by line.

---

## 7. Failed operations

Every failure encountered, with its resolution. Three were recovered in-session; two are
structural.

**F-1 — Shell syntax error from an unquoted URL.** `EXECUTION_VERIFIED`, recovered.

```
$ for u in https://en.wikipedia.org/wiki/Astro_(web_framework) …
/bin/bash: -c: line 1: syntax error near unexpected token `('
exit_code 2
```

Bare parentheses in a `for` list break bash parsing. Fixed by double-quoting every URL; the
re-run returned all 8 status codes. Lesson: the `bash` tool passes the string to `bash -c`, so
shell quoting rules apply literally and a parse error kills the whole command.

**F-2 — `node --test` discovered zero tests.** `EXECUTION_VERIFIED`, recovered.

```
$ node --test        # file named t.mjs
# tests 0
# pass 0
```

Not a runner failure: Node's default test discovery requires `*.test.mjs`, `test-*.mjs`, or a
`test/` directory. Renaming to `t.test.mjs` gave `# tests 1 / # pass 1`. The real trap is that
this exits cleanly — a green run with zero tests is the dangerous failure mode, and it is why a
pass count must be read, not just an exit code.

**F-3 — `gh api user` returned 403.** `UNAVAILABLE`, not recoverable.
`Resource not accessible by integration`. Expected for a GitHub App installation token.
Worked around by reading identity from `gh auth status`.

**F-4 — Arbitrary HTTPS egress blocked.** `EXECUTION_VERIFIED`, not recoverable in-session.
`curl https://example.com` → `curl: (35) OpenSSL SSL_connect: SSL_ERROR_SYSCALL`, exit 35,
`http_code=000`. Same for `astro.build`, `docs.astro.build`, `fonts.googleapis.com`, Wikipedia,
`api.npmjs.org`, `deno.land`, `registry.npmmirror.com`. Workaround: `web_search` / `fetch_page`
for content, canonical registries for packages.

**F-5 — `&&` chain aborted after a non-zero exit.** `EXECUTION_VERIFIED`, recovered.
The first GitHub-API probe chained three `gh api` calls with `&&`; the 403 in F-3 short-circuited
the remaining two, which produced no output at all. Fixed by using `;` so each command runs
independently. This is a genuine information-loss failure: a chain that dies silently can look
like missing data rather than an aborted command.

**Deliberately not attempted (not failures):** pushing to `main`, merging or closing a PR,
modifying any existing research file, touching the concurrent session's branch or files, reading
or printing any token or secret.

---

## 8. Unverified capabilities

### 8.1 Documented but not exercised here

| Capability | Source | Status |
|---|---|---|
| Arena **Diff** tab rendering | Arena help page | `DOCUMENTED_ONLY` — browser UI, invisible to the sandbox (§6.2) |
| **ZIP workspace download** | Arena help page | `UNAVAILABLE` in a connected session by design: "there's no zip download" when a repo is connected. The `/download-workspace` URL suffix is documented as an emergency path but was not exercised. |
| **Vercel deploy** pipeline | research transcription | `DOCUMENTED_ONLY` — no such tool is exposed here |
| Named tools `github_connect`, `push_changes`, `open_pr` | research transcription | `DOCUMENTED_ONLY` — none appear in the callable registry; GitHub ran via `git`/`gh` under `bash` instead (§2.2) |
| Browser automation / Playwright / screenshots | — | `NOT_TESTED` here; earlier probe found no browser or Playwright package |
| Image generation/editing, voice, `ask_user`, `image_search` | tool registry | `EXPOSED_TOOL`, `NOT_TESTED` — skipped to keep the probe linear |
| Session pause/restore, shareable sessions | research transcription | `NOT_TESTED` |
| Multi-turn steering mid-task | — | `NOT_TESTED` — this run was single-instruction |
| `get_process_output` blocking waits | tool registry | `NOT_TESTED` — `start_process` already surfaced the port |

### 8.2 Structural unknowns

- **No usage or token accounting.** Nothing exposes credit balance, per-model rate limits, cost
  per task, or context-window consumption. **Consequence: no token-savings figure is stated
  anywhere in this document, and none should be inferred from it.** Answering "is Arena cheaper
  than my other agent for this task" requires external measurement.
- **Sandbox resource ceilings are observations, not quotas.** 2 cores / ~3.9 GB / 20 GB free were
  seen, but nothing states whether they are guaranteed, shared, or throttled.
- **Egress allowlist contents are inferred.** The pattern (GitHub + canonical npm + canonical
  PyPI) is derived from 12 probes, not from documentation. Undocumented hosts may differ per
  account or change without notice.
- **`gh` version is old.** 2.23.0 from February 2023. Newer `gh` subcommands and flags may be
  absent; anything relying on recent CLI features is untested.
- **Whether the token can merge, close, force-push, or delete branches** is untested by design.
- **No verification that the pushed bytes render as intended on github.com.** `gh` reported
  success and the PR URL resolved, but no browser confirmed the Markdown rendering.

---

## 9. Practical coding-agent applications

### 9.1 Tested operations vs. proposed applications

The distinction matters. §2 lists what **ran**. Below is what that evidence *supports*, marked
`TESTED-BACKED` where a verified operation underpins it and `PROPOSED` where it is inference.

| Use case | Verdict | Basis |
|---|---|---|
| **Technical documentation** | **Strong — `TESTED-BACKED`** | This document is the evidence: 157 KB of existing docs navigated by heading grep, a 776-line structured Markdown file authored, self-reviewed by diff, committed, pushed, PR'd. |
| **GitHub maintenance** | **Strong — `TESTED-BACKED`** | Full `read → branch → commit → push → PR` cycle ran. `gh` PR/issue/API reads work. Limits: no `main` pushes, no merges by rule, old `gh`. |
| **Coding-agent handoff packages** | **Strong — `TESTED-BACKED`** | Multi-file writes, JSON/Markdown authoring, and delivery to a branch all verified. Ideal for producing a spec + patch + test plan another agent can pick up. |
| **Small bug fixes** | **Good — `PROPOSED`** | `edit_file` + diff review + PR verified; no real bug in a real codebase was fixed here. Caveat: first-fuzzy-match editing needs unique anchors. |
| **Test generation** | **Good — `PROPOSED`** | Test *authoring and execution* verified in three runners, plus pytest installable. Not verified: generating tests for an unfamiliar existing codebase. F-2's silent zero-test pass is the main hazard. |
| **Code review** | **Moderate — `PROPOSED`** | `git diff`, `git log`, ranged reads all verified. Constraint: no browser, so reviewing a rendered GitHub PR thread is not possible; review must be diff-text based. |
| **CSS and frontend development** | **Moderate — `PROPOSED`** | Static file serving and live preview verified (`200`, correct bytes, no origin warnings). Missing: no browser rendering or screenshots, so visual correctness is unverified. Also `fonts.googleapis.com` is blocked from bash. |
| **Static Astro websites** | **Moderate — `PROPOSED`, partially blocked** | `npm install` works and `astro@7.3.5` resolves from the registry. But `astro.build` and `docs.astro.build` are unreachable from bash, and a full Astro install/build was **not** run (`BUILD-006` is `NOT_TESTED`). Expect content/docs lookups to go through `fetch_page`, not `curl`. |
| **Repository refactoring** | **Weak-to-moderate — `PROPOSED`** | Traversal and multi-file writes verified, but 2 cores and an old `gh`, no semantic index, and no test suite in this repo to catch regressions. Refactors need external CI to be trustworthy. |
| **Design Spells** | **Untested — `NOT_TESTED`** | No Design Spells content, API, or repository exists in this workspace, and no related host is reachable from bash. Nothing here was exercised. |
| **Webbruket** | **Untested — `NOT_TESTED`** | Same: not present in this repository and not reachable. Would require connecting that repository in its own session. |

### 9.2 Where this session genuinely substitutes

Best fits, all `TESTED-BACKED`:

1. **Documentation-heavy work with GitHub delivery** — author, self-review, branch, PR.
2. **Repository archaeology and evidence ledgers** — read a large repo cheaply via heading-first
   navigation and ranged reads.
3. **Throwaway verification** — install a dependency, run a test, compile a snippet, serve a page,
   tear it down.
4. **Handoff authoring** — produce a precise, evidence-tagged package for another agent or human.

Weakest fits: anything needing a browser, anything needing arbitrary network egress, anything
requiring a merge decision, and anything whose correctness depends on a test suite this repo does
not have.

### 9.3 Operating rules derived from this probe

- Push before merging; merge last (§5.6).
- Keep concurrent sessions on **disjoint paths** (§3.4).
- Quote shell arguments; prefer `;` over `&&` in probe scripts (§7 F-1, F-5).
- Read the **pass count**, never just the exit code (§7 F-2).
- Prove GitHub capability by doing it, not by reading the `permissions` object (§5.2).
- Use `web_search`/`fetch_page` for content, registries for packages (§1.4).
- Bind previews to `0.0.0.0` and check the `warnings` field (§2.5).
- Keep scratch work outside the repository (§3.3).

---

## 10. Recommendations for future tests

Ordered by how much they would change a decision.

1. **End-to-end Astro build (`BUILD-006`).** Scaffold a minimal Astro project in `/tmp`, run
   `npm install` and `astro build`, time it, and report whether the 2-core/3.9 GB sandbox
   completes a real static build. This is the largest open question for the static-site use case.
2. **Real bug-fix cycle.** Connect a repository with an actual test suite, introduce a known
   regression, let the agent locate and fix it, and record whether the suite goes red then green.
   This converts "small bug fixes" from `PROPOSED` to verified.
3. **User-side Diff tab confirmation.** A human should confirm the Diff tab renders this PR's
   commit line by line. That closes §6.2, which no agent-side test can reach.
4. **Post-merge push refusal.** In a throwaway repo, merge a PR and then attempt another push from
   the same session. The documented behaviour (§5.6) has not been empirically confirmed, and it
   governs every workflow.
5. **Egress allowlist enumeration.** Systematically probe more hosts to separate "package
   infrastructure" from "GitHub" from "everything else", and check whether the list varies by
   account or plan.
6. **Long-task context behaviour.** A task long enough to trigger context management, with periodic
   self-reports of retained facts, to locate where summarisation begins and what gets dropped.
7. **`gh` version gap.** Test the specific `gh` subcommands a maintenance workflow needs against
   2.23.0 and record which are missing.
8. **Frontend visual verification.** With no browser exposed, determine whether the user-side
   preview is sufficient for CSS work, or whether visual checks must stay with another tool.
9. **Usage economics.** Since no meter is exposed (§8.2), measure externally: run identical tasks
   in Arena and in the incumbent agent, and compare wall-clock time and observed quality rather
   than estimating tokens.
10. **Concurrency stress.** Run three sessions against overlapping files to observe how Arena and
    git surface conflicts, and document the recovery path.

---

## Appendix A — Evidence index

| Evidence | Where |
|---|---|
| Connection, identity, toolchain, egress, resource snapshot | §1.1–§1.4 |
| Tool registry and per-tool results | §2.1–§2.5 |
| Capability ledger (41 rows, spec fields) | §2.6 |
| Repository/branch state, write scope, concurrency | §3.1–§3.4 |
| Command log | §4 |
| GitHub permissions, pre-existing PR, commit, push, PR | §5.1–§5.6 |
| Diff inspection (agent-side and Diff tab) | §6.1–§6.2 |
| Failures F-1 … F-5 | §7 |
| Unverified capabilities and structural unknowns | §8.1–§8.2 |
| Use-case assessment, tested vs. proposed | §9.1–§9.3 |
| Future tests, ranked | §10 |

## Appendix B — Sources consulted

| Source | Type | Use |
|---|---|---|
| `docs/arena-agent-mode-research-2026-09-26.md` | Research transcription (Google Drive), self-labelled *"not an independently verified capability manifest"* | Official-claim baseline; its `github_connect`/`push_changes`/`open_pr` tool names are `DOCUMENTED_ONLY` and were **not** observed here |
| `ARENA_AGENT_COMPLETE_CAPABILITY_INVENTORY.md` | Earlier **non-connected** session inventory | Contrast case: it reported no GitHub function exposed and no remote operation attempted |
| `ARENA_AGENT_PROBE_RESULTS.md` | Earlier probe log (T-001…T-015) | Its `curl https://example.com` failure is reproduced here and extended into an allowlist map (§1.4) |
| `ARENA_AGENT_PRACTICAL_WORKFLOWS.md` | Workflow recipes | Compared against §9; the handoff-package recipe is `TESTED-BACKED` |
| `docs/next-research-batch.md` | Batch plan | This probe is the "Arena A — GitHub-connected coding workflow" run |
| Arena Help Center, *How to use Agent Mode on Arena* | First-party documentation, retrieved via `fetch_page` (chunk 0/3) | Connected-repo delivery model, Diff tab, post-merge push cutoff, upload formats, `/download-workspace` |

## Appendix C — Safety and secret handling

- No token, credential, environment secret, or config value was read, printed, or stored. The
  only credential representation reproduced is the `************************` mask that
  `gh auth status` itself emits (§1.1).
- No push to `main`; no merge; no PR closed; no force-push; no branch deleted.
- Only `docs/probes/github-connected-session.md` was written inside the repository (§3.3).
- No existing research file was modified — the change is 776 insertions, 0 deletions (§6.1).
- The concurrent session's branch `arena/01a0dc43-arena` and its PR #1 were left untouched (§5.3).
- All scratch artefacts (venv, `node_modules`, binaries, preview site) were created under `/tmp`
  and are outside the commit.

## Appendix D — Verified delivery identifiers

Filled in by a follow-up commit **after** `git commit`, `git push`, and `gh pr create` returned.
Each value is copied from the tool's own output; none is inferred.

| Item | Verified value | Source of the value |
|---|---|---|
| Branch pushed | `arena/01a0dc7e-arena` | `git push -u origin arena/01a0dc7e-arena` |
| Base commit (from `main`) | `12630762fd28d6fdad782bd99964b961de7f9dd0` | `git rev-parse origin/main` |
| Commit SHA — probe document | `55fd468fedff4d90262cc6aa24b91759f1907a66` | `git rev-parse HEAD` after commit 1 |
| Push result | `* [new branch]  arena/01a0dc7e-arena -> arena/01a0dc7e-arena` | `git push` stderr |
| Pull request | [pull/3](https://github.com/FullThrottle83/arena/pull/3) — draft | `gh pr create` stdout |
| PR state | `OPEN, isDraft: true` | `gh pr view --json state,isDraft` |

Both commits touch only `docs/probes/github-connected-session.md`.

The follow-up commit's own SHA is **not** recorded in this table: a commit cannot contain its own
hash. It is reported in the session summary and is readable at any time as the tip of
`arena/01a0dc7e-arena` via `git log --oneline -1` or the PR's Commits tab.
