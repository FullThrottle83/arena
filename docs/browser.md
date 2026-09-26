# Local browser testing in Arena

**What passed:** a 2026-09-26 Arena session installed `playwright-core@1.63.0` and `@sparticuz/chromium@153.0.0`, started Chromium headless shell 153.0.8010.0 on a synthetic local fixture; its probe *reported* no script-supplied security-bypass flags, rendered a local HTTP fixture, read DOM/JS state, captured and validated screenshots, tested viewport overflow, input/focus, console and requests, and generated a PDF. [Raw log B01–B15](archive/probes/browser-probe.md) · [JSON](archive/probes/browser-probe.json).

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
5. Launch Playwright Core with the returned executable path only after inspecting package defaults. **Do not blindly pass `@sparticuz/chromium.args`**: its inspected defaults include `--no-sandbox` and `--disable-web-security`. The earlier synthetic probe reported only two non-security script flags; however, the [real Design Spells benchmark](https://github.com/FullThrottle83/design-spells/pull/43) recorded that **effective Chromium launch arguments contained both security-bypass flags internally despite the script not passing them**. Therefore we cannot claim a sandboxed or web-security-enforced browser from either run. Record the full effective args and seek approval before running untrusted pages or recommending a reusable bootstrap script.
6. Start a harmless local HTTP fixture, inspect DOM/JS and capture a real PNG. Validate PNG signature, dimensions and SHA-256. Test desktop/mobile, console and requests separately.
7. Test remote navigation separately. If blocked, state that limitation; do not claim a live public-site screenshot. Native Arena webpage retrieval and browser egress have differed in tests.

Installed packages and `/tmp` binaries are **session-local until demonstrated otherwise**. A screenshot of a locally rehosted page is not proof that cookies, authentication, security headers, remote JS, third-party requests or network behavior match the production site.

No one-command browser script is shipped yet: a secure launch preflight must first be verified against the **effective** flags, not merely the invocation arguments. This repo does not ship/install a browser automatically. See [limitations](limitations.md) and [evidence](evidence.md).
