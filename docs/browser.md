# Local browser testing in Arena

**What passed:** a 2026-09-26 Arena session installed `playwright-core@1.63.0` and `@sparticuz/chromium@153.0.0`, started Chromium headless shell 153.0.8010.0 on a synthetic local fixture; its probe *reported* no explicitly supplied security-bypass flags, rendered a local HTTP fixture, read DOM/JS state, captured and validated screenshots, tested viewport overflow, input/focus, console and requests, and generated a PDF. [Raw log B01–B15](archive/probes/browser-probe.md) · [JSON](archive/probes/browser-probe.json).

**What did not pass:** public browser navigation to `https://example.com/` (`net::ERR_CONNECTION_CLOSED`). This is **local-rendering evidence**, not arbitrary live-site audit evidence.

## Reproduce carefully in a fresh session

1. Check whether a browser tool, Playwright, browser executable and dependent shared libraries already exist. Record version/path before installing anything.
2. If required, request approval for installation. The standard Playwright browser CDN and Debian apt mirror were inaccessible in one tested sandbox.
3. After approval, use a scratch location (the successful session used `/tmp/pwnode`) and install the exact tested packages:
   ```sh
   mkdir -p /tmp/pwnode && cd /tmp/pwnode
   npm install playwright-core@1.63.0 @sparticuz/chromium@153.0.0
   ```
4. From a script within `/tmp/pwnode`, invoke the package's `executablePath()`; it inflates the included headless-shell binary. The recorded session needed the package's bundled `al2023`/SwiftShader shared libraries in `LD_LIBRARY_PATH`. Check `ldd` and the current package API; do not copy unverified paths.
5. Record the **effective Chromium command line**. [Playwright's `chromiumSandbox` defaults to `false`](https://playwright.dev/docs/api/class-browsertype#browser-type-launch-option-chromium-sandbox), so it normally adds `--no-sandbox` itself. [`@sparticuz/chromium.args`](https://github.com/Sparticuz/chromium/blob/master/source/index.ts) separately contains `--disable-web-security`; do not pass that list wholesale. PR #43 recorded both flags but did **not** check in the test script: the origin of `--disable-web-security` remains unverified, and must not be attributed to internal package behavior without code and logs. An independent `chromiumSandbox: true` attempt failed; whether that is reproducible in Arena itself is not verified.
   - For a deliberately unsandboxed test, restrict pages to **trusted local loopback builds only**; block off-loopback navigation and all subresource requests, with service workers disabled. Never pass GH_TOKEN or other session secrets into the spawned browser environment.
   - Check redacted effective args; fail if `--disable-web-security` or `--allow-running-insecure-content` appears. If true sandboxing is required but fails, report `BLOCKED` rather than silently falling back.
   - Execute the project's existing test suite before supplemental screenshot checks. Commit every evidence-producing script/configuration. PR #43 only ran custom checks on 3 pages × 2 viewports, not the existing `npm test` suite.

6. Start a harmless local HTTP fixture, inspect DOM/JS and capture a real PNG. Validate PNG signature, dimensions and SHA-256. Test desktop/mobile, console and requests separately.
7. Test remote navigation separately. If blocked, state that limitation; do not claim a live public-site screenshot. Native Arena webpage retrieval and browser egress have differed in tests.

Installed packages and `/tmp` binaries are **session-local until demonstrated otherwise**. A screenshot of a locally rehosted page is not proof that cookies, authentication, security headers, remote JS, third-party requests or network behavior match the production site.

No one-command browser script is shipped yet: task 0001 should create and verify a reproducible local-only harness that checks effective launch flags, not merely its invocation arguments. This repo does not ship/install a browser automatically. See [limitations](limitations.md) and [evidence](evidence.md).
