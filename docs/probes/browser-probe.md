# Arena Agent Mode — Browser & Playwright Forensic Probe

- **Probe date:** 2026-09-26
- **Repository:** `FullThrottle83/arena` (confirmed selected; `git remote -v` → `https://github.com/FullThrottle83/arena.git`)
- **Requested branch:** `arena/probe-browser` — **actual branch: `arena/01a0dc7f-arena`** (Arena assigns this session's branch; recorded per instruction). Base commit `12630762fd28d6fdad782bd99964b961de7f9dd0` (main). No work was done on `main`.
- **Machine-readable manifest:** `docs/probes/browser-probe.json`
- **Browser screenshot artifact:** `docs/probes/assets/browser-fixture.png`
- **Headline result:** Arena Agent Mode **can** perform real headless-browser audits in this session. Playwright/browsers were absent at session start, but a genuine Chromium (Chrome for Testing headless shell **153.0.8010.0**) was obtained through an allowed channel (npm package payload) and executed with the sandbox **enabled**. Tests B04–B13 PASS; B14 (public HTTPS navigation from the browser) FAIL due to host-allowlisted egress.

---

## 1. Executive summary

| Area | Result |
|---|---|
| Dedicated Arena browser tool | **None exposed** (B01) |
| Playwright/Puppeteer/Selenium at session start | **Absent** in both Python and Node (B02) |
| Browser executables/caches at session start | **None** anywhere on disk (B03) |
| Shell HTTPS egress | **Works, but host-allowlisted**: pypi.org ✅, registry.npmjs.org ✅; deb.debian.org ❌, cdn.playwright.dev ❌, storage.googleapis.com ❌, example.com ❌ |
| Playwright official browser download (`playwright install`) | **Impossible** (CDN blocked; apt mirror blocked) |
| Working browser path | `npm install @sparticuz/chromium` (browser shipped inside the npm tarball via registry.npmjs.org) + bundled NSS libs → launched by `playwright-core` |
| Headless launch (B04) | **PASS** — 120 ms, sandbox enabled, no security-bypass flags |
| DOM / JS-rendered content (B05, B06) | **PASS** |
| Screenshot + validation (B07, B08) | **PASS** — real PNG, 1456×800, sha256 `408b8755…8cd2`, committed to repo |
| Responsive + overflow (B09) | **PASS** — 375/768/1920 viewports, horizontal overflow correctly detected |
| Keyboard/pointer + focus state (B10) | **PASS** |
| Console errors (B11) | **PASS** |
| Network inspection (B12) | **PASS** (timing waterfall not collected → PARTIAL in matrix) |
| PDF (B13) | **PASS** — `%PDF-1.4`, 48 084 bytes |
| Public HTTPS navigation in browser (B14) | **FAIL** — `net::ERR_CONNECTION_CLOSED` (egress allowlist). Arena-native `fetch_page` reaches the same site successfully (separate path). |
| GitHub delivery (B15) | **PASS** — commit + push + draft PR on `arena/01a0dc7f-arena` |

Relation to the previous session's probe: its *absence* findings are reproduced exactly, but its "one failed direct shell HTTPS request" must not be read as global network failure — in this session direct HTTPS to package registries works, and that difference is precisely what made a real browser install possible.

---

## 2. Environment inventory (actual commands and outputs)

### 2.1 OS / runtimes

```
$ uname -a
Linux e2b.local 6.1.158+ #1 SMP PREEMPT_DYNAMIC Mon May 11 18:48:24 UTC 2026 x86_64 GNU/Linux
$ cat /etc/os-release | head -2
PRETTY_NAME="Debian GNU/Linux 12 (bookworm)"
NAME="Debian GNU/Linux"
$ python3 --version ; node --version ; npm --version
Python 3.11.2
v22.22.3
10.9.8
$ nproc ; free -m | head -2 ; df -h / | tail -1
2
Mem: total 3939, available ~3675
/dev/root 21G 834M 20G 5% /
```

Privileges: unprivileged user with **passwordless sudo** (`sudo whoami` → `root`, exit 0). Python is PEP 668 `EXTERNALLY-MANAGED`; per approval, a venv was used (`/tmp/pw-venv`).

### 2.2 Browser tooling discovery (B01)

The agent toolset for this session contains **no browser automation tool**: bash, file read/write/edit, `start_process`/`stop_process`/`get_process_output`, `web_search`, `fetch_page`, `image_search`, `generate_image`, `generate_speech`/`add_voice`, `present_file`, `ask_user`. Browser automation is therefore only reachable by installing tooling through bash.

### 2.3 Package/executable discovery (B02, B03) — pre-install

```
$ pip show playwright
WARNING: Package(s) not found: playwright            # exit 1
$ python3 -c "import playwright"
ModuleNotFoundError: No module named 'playwright'    # exit 1
$ node -e "require.resolve('playwright')"   → MODULE_NOT_FOUND
$ node -e "require.resolve('puppeteer')"    → MODULE_NOT_FOUND
$ python3 -c "import selenium"              → ModuleNotFoundError   # exit 1
$ npm ls -g --depth=0  → corepack@0.34.6, npm@10.9.8 (nothing else)
$ which playwright chromium chromium-browser google-chrome google-chrome-stable firefox
(no output)                                          # exit 1
$ find / -xdev \( -iname "*chromium*" -o -iname "*chrome*" -o -iname "firefox*" -o -iname "headless_shell*" \) -type f
(no output)                                          # exit 0
$ ls ~/.cache/ms-playwright ~/.cache/puppeteer ~/.cache/selenium
ls: cannot access ...: No such file or directory
```

`/usr/bin/sensible-browser` exists but is a Debian wrapper script with no configured backend; `/etc/alternatives/*browser*` absent. Shared libraries: `libnss3.so`, `libnspr4.so`, `libnssutil3.so` **not** present in `/usr/lib/x86_64-linux-gnu` (369 other `.so` files present).

### 2.4 Network egress matrix (shell vs Arena tools vs browser)

| Target | Shell curl HTTPS | Notes |
|---|---|---|
| pypi.org | **200** (0.07 s) | `pip index versions playwright` → 1.63.0 available |
| registry.npmjs.org | **200** | `npm view playwright version` → 1.63.0 |
| deb.debian.org | **000** | `:80` empty reply, `:443` SSL_ERROR_SYSCALL → apt unusable |
| cdn.playwright.dev | **000** | official Playwright browser CDN (from `playwright install --dry-run`) |
| playwright.azureedge.net | **000** | legacy CDN |
| playwright.download.prss.microsoft.com | **000** | documented ffmpeg fallback |
| storage.googleapis.com | **000** | Chrome-for-Testing / Puppeteer CDN |
| edgedl.me.gvt1.com | **000** | Google edge CDN |
| example.com | **000** | general web blocked |
| example.com via Arena `fetch_page` | **OK** | title "Example Domain" — separate egress path |
| web search (`web_search`) | **OK** | native tool |

Conclusion: shell egress is a **host allowlist** (package registries). One failed HTTPS request ≠ "networking blocked", and working `fetch_page` ≠ working browser navigation — all three paths were tested separately.

---

## 3. Installation (user-approved) and test execution B04–B14

Approval (verbatim key points): *"Approved. Proceed with the full Playwright + Chromium installation … Use a Python virtual environment … Do not use security-bypassing browser flags automatically. If Chromium requires additional security-related changes, report the issue before proceeding. … If installation fails, preserve the evidence and deliver a partial report rather than repeatedly attempting increasingly invasive workarounds."*

### 3.1 Attempted paths, in order (evidence preserved)

1. `python3 -m venv /tmp/pw-venv && /tmp/pw-venv/bin/pip install playwright` → **OK**: playwright 1.63.0 (+greenlet 3.5.6, pyee 13.0.1). `/tmp/pw-venv/bin/playwright --version` → `Version 1.63.0`.
2. `sudo apt-get update` → partial failure: `W: Failed to fetch http://deb.debian.org/... Connection failed` (mirror blocked both over http and https).
3. `sudo /tmp/pw-venv/bin/playwright install --with-deps chromium` → **FAILED**, exit code 100: `E: Unable to locate package libxdamage1 … xvfb … fonts-liberation has no installation candidate` and the browser download host `https://cdn.playwright.dev/builds/cft/153.0.8010.12/linux64/chrome-linux64.zip` (from `--dry-run`) unreachable. **Not retried with workarounds** (per instruction).
4. **Successful path (allowed host):** `npm install playwright-core@1.63.0 @sparticuz/chromium@153.0.0` in `/tmp/pwnode`. `@sparticuz/chromium` ships the browser *inside the npm tarball* (67 MB brotli: `chromium.br` 67 016 039 B, plus `al2023.tar.br` = NSS/expat libs, `swiftshader.tar.br`, `fonts.tar.br`) — download went through registry.npmjs.org only.
5. `chromium.executablePath()` inflated the payload → `/tmp/chromium` (209 022 176 B, chrome-headless-shell build, executable).
6. Dependency check: `ldd /tmp/chromium` missing only `libnspr4.so`, `libnss3.so`, `libnssutil3.so`; with `LD_LIBRARY_PATH=/tmp/al2023/lib:/tmp/swiftshader` → **ALL LIBS RESOLVED**. No apt packages required at all.

**Security-flag policy (per approval):** `@sparticuz/chromium`'s default `args` include `--no-sandbox`, `--disable-setuid-sandbox`, `--disable-web-security`, `--allow-running-insecure-content`. These were **deliberately not used**. The browser was launched with Chromium's default sandbox policy plus only `--disable-dev-shm-usage --disable-gpu`, and it launched successfully — i.e. **no security-related change was necessary**, so no escalation report was required.

Resource observations: total install footprint ≈ 350 MB in `/tmp` (venv ~60 MB, node_modules ~85 MB, inflated binary 209 MB); cold launch 120 ms; test suite (B05–B14) completed in ~1.6 s wall time; no lingering processes besides the intentionally started local fixture server.

Persistence assessment: **not persistent between sessions.** venv, node_modules, `/tmp/chromium` and `/tmp/al2023` live in `/tmp` (outside the persisted workspace); `~/.cache/ms-playwright` was never populated; apt is unusable (mirror blocked) so a system install is impossible. Only files committed to the repository persist. Recreating the capability in a future session requires the same npm route (registry.npmjs.org is allowlisted) — expected cost: one `npm install` (~4 s) + inflation (~1 s).

### 3.2 Test log (condensed verbatim stdout)

Local fixture: `/tmp/fixture/index.html` served by `python3 -m http.server 8123` (curl → `HTTP 200`). Fixture includes inline JS, a click counter, keyboard handler, focus-outline CSS, a deliberate 1400 px-wide element, deliberate console warn/error, and an in-page `fetch('/probe-network.json')`.

```
[B04] PASS: chromium 153.0.8010.0 launched via playwright-core 1.63.0
[B05] PASS: HTTP 200, title="Arena Browser Probe Fixture", url=http://127.0.0.1:8123/
[B06] PASS: h1="Arena Browser Probe Fixture", data-probe="arena-browser-2026", inline JS ran=true,
            .card count=3, in-page fetch result={"ok":true,"probe":"network"}
[B07] PASS: saved /home/user/arena/docs/probes/assets/browser-fixture.png, 27302 bytes
[B08] PASS: sig=89504e470d0a1a0a, dims=1456x800, bytes=27302,
            sha256=408b8755db460a23ea123598a28fb0707532e79d5e48a85252eac717328d8cd2
[B09] PASS: iPhone SE portrait 375x667: innerWidth=375 scrollWidth=1456 hOverflow=true |
            tablet portrait 768x1024: innerWidth=768 scrollWidth=1456 hOverflow=true |
            desktop FHD 1920x1080: innerWidth=1920 scrollWidth=1920 hOverflow=false
[B10] PASS: counter="clicks: 2", input="Arena probe", Enter keydown seen=true,
            focus={"focused":"btn","outlineWidth":"3px","outlineColor":"rgb(255, 136, 0)"},
            focus screenshot=/tmp/shot-focus.png
[B11] PASS: 3 messages: log:fixture: inline script executed ; warning:fixture: deliberate warning ;
            error:fixture: deliberate error
[B12] PASS: 2 requests: GET http://127.0.0.1:8123/ [document] -> 200 ;
            GET http://127.0.0.1:8123/probe-network.json [fetch] -> 200
[B13] PASS: 48084 bytes, header=%PDF-1.4
[B14] FAIL: browser egress likely blocked by same allowlist as shell (pypi/npm only) |
            ERR: Error: page.goto: net::ERR_CONNECTION_CLOSED at https://example.com/
```

Every B05–B14 step ran against the **local fixture first**; the only external navigation attempted was the single bounded `https://example.com/` request (B14), which failed at the network layer, exactly as the shell curl had predicted.

---

## 4. Screenshot integrity

| Property | Value |
|---|---|
| File (committed) | `docs/probes/assets/browser-fixture.png` |
| Origin | Chromium 153.0.8010.0 headless-shell rasterisation via `page.screenshot({fullPage:true})`, playwright-core 1.63.0 |
| Viewport | 1280×800 (fullPage capture widened to scrollWidth) |
| PNG signature | `89 50 4E 47 0D 0A 1A 0A` ✅ |
| IHDR dimensions | **1456 × 800** |
| Size | 27 302 bytes |
| SHA-256 | `408b8755db460a23ea123598a28fb0707532e79d5e48a85252eac717328d8cd2` (verified twice: in-browser Node `crypto` and host `sha256sum`) |
| Visual verification | inspected in-session: rendered typography, card shadows, native button/input widgets and the overflowing pink bar — a genuine render, not an AI illustration |

Supplementary (not committed, `/tmp` only): `shot-375x667.png`, `shot-768x1024.png`, `shot-1920x1080.png`, `shot-focus.png` (1280×800), `probe-fixture.pdf`.

---

## 5. Capability matrix (practical audit operations)

| Operation | Status | Evidence |
|---|---|---|
| Rendered DOM inspection | **VERIFIED_NOW** | B06 |
| JavaScript-rendered content analysis | **VERIFIED_NOW** | B06 (`__jsRan`, in-page fetch result readable) |
| Desktop screenshots | **VERIFIED_NOW** | B07/B08 |
| Mobile screenshots | **VERIFIED_NOW** | B09 (375×667 capture) |
| Responsive overflow checks | **VERIFIED_NOW** | B09 (scrollWidth vs innerWidth at 3 widths) |
| Keyboard accessibility tests | **VERIFIED_NOW** | B10 (type/Enter/focus outline) |
| Focus-state screenshots | **VERIFIED_NOW** | B10 |
| Network waterfall inspection | **PARTIAL** | B12 (requests+statuses yes; per-request timing not collected) |
| Console error analysis | **VERIFIED_NOW** | B11 |
| HTTP response observation | **VERIFIED_NOW** | B05/B12 + shell curl matrix |
| Visual regression testing | **NOT_TESTED** | baselines (PNG + sha256) now exist; no pixel-diff run performed |
| Browser-based PDF generation | **VERIFIED_NOW** | B13 |
| Auditing arbitrary public websites *in the browser* | **UNAVAILABLE_IN_THIS_SESSION** | B14; mitigations: mirror content locally or use `fetch_page` |
| WCAG / Lighthouse / Core Web Vitals scoring | **NOT_TESTED** | not performed — explicitly not claimed |

Installation feasibility of the *official* Playwright path: **UNVERIFIED/NOT POSSIBLE here** (CDN + apt blocked); the npm-bundled path is **VERIFIED_NOW**.

---

## 6. Differences vs the previous session's probe

- Confirmed: no Playwright/Puppeteer/Selenium pre-install; no browser binary; no browser tool; local HTTP server OK; native `web_search`/`fetch_page` OK.
- Contradicted: "one failed direct shell HTTPS request" — direct HTTPS **works** here for allowlisted hosts (pypi 200, npmjs 200). That single working channel was sufficient to obtain and run a real browser.
- New: browser egress = shell allowlist; Arena tool egress = separate and unrestricted; `chrome-headless-shell` needs only 3 NSS libs, satisfiable from npm-bundled payloads without root or apt.

## 7. Recommendations

1. For in-browser audits of public sites: fetch HTML via `fetch_page`, serve it locally, then audit in headless Chromium (works today).
2. Keep the npm-bundled Chromium recipe (section 3.1 step 4–6) as the canonical bootstrap; it needs no root, no apt, no CDN.
3. Collect request timing (`request.timing()`) in the next probe to upgrade waterfall inspection from PARTIAL to VERIFIED.
4. Add a pixel-diff step (pure-JS PNG decode) to enable visual regression.

## 8. GitHub delivery (B15)

- Files committed (only allowed paths): `docs/probes/browser-probe.md`, `docs/probes/browser-probe.json`, `docs/probes/assets/browser-fixture.png`.
- Branch: `arena/01a0dc7f-arena` → pushed to origin; **one draft PR against `main`** opened (not merged, not closed). PR URL: see below / `gh pr view`.

## Appendix A — fixture served for B05–B13

`/tmp/fixture/index.html` (local, not committed): HTML with `<h1 id="title">`, `<span id="probe" data-probe="arena-browser-2026">`, `<button id="btn">` + click counter, `<input id="kb">` with Enter handler + `:focus { outline: 3px solid #ff8800 }`, `.wide { width: 1400px }` overflow element, inline script emitting `console.log/warn/error`, setting `window.__jsRan`, and `fetch('/probe-network.json')`.
