# Native browser automation, Playwright-local execution, and server-side retrieval in AI coding agents

**Benchmark date:** 2026-09-26 · **Branch:** `arena/01a0dcb8-arena` · **Question:** practical differences between (A) native/browser-tool automation built into agents, (B) Playwright-driven local execution inside an agent sandbox, and (C) server-side webpage retrieval (native `fetch_page`, shell HTTPS), and what each implies for technical SEO, accessibility testing, JavaScript rendering, network inspection and source-grounded research.

**Method:** 14 external sources retrieved with the native `fetch_page` tool, every chunk of every multi-chunk document fetched (largest: 9/9 chunks × 2); `web_search` used only for discovery, never as evidence. Three execution records (E1–E3) were produced this session. Classifications follow `OFFICIAL_DOCUMENTATION | EXECUTION_EVIDENCE | THIRD_PARTY_REPORT | INFERENCE | UNVERIFIED`. Full ledger: [sources.json](sources.json); claim-by-claim checks: [verification.md](verification.md).

## 1. The three modes, concretely

| Axis | Native browser tool (agent-hosted) | Playwright local execution (sandbox) | Server-side retrieval (`fetch_page`, shell HTTP) |
|---|---|---|---|
| JavaScript executed | Yes, in a real browser the agent drives | Yes, in a browser the agent launches and scripts | No (shell); `fetch_page` JS behavior untested — **UNVERIFIED** (C34) |
| DOM observed | Accessibility snapshot / screenshot of rendered state [S08][S12] | Full `page.content()`, evaluators, a11y tree, screenshots [E1] | Extracted text/HTML of the response only [E1] |
| Network visibility | Request list + per-request headers/bodies (MCP tools) [S08][S12] | Every request/response, WebSocket, route/abort/fulfill [S01][S05] | Exactly the one request the retriever makes [E1] |
| Cookies/state | Persistent or isolated profiles, cookie tools [S08] | Whatever the context has; WRS-like statelessness must be simulated manually [S03] | Per-request headers only; no jar unless the client keeps one |
| Egress in this session | Not exposed as a tool this session | Local pages OK; public navigation `ERR_CONNECTION_CLOSED` [E3] | Shell failed on 3 of 5 hosts; native `fetch_page` reached all source hosts [E2] |
| Evidence class | EXECUTION_EVIDENCE when run | EXECUTION_EVIDENCE when run | OFFICIAL_DOCUMENTATION for docs; EXECUTION_EVIDENCE for runs |

**Key structural point:** each mode observes a *different projection* of the same page. Server-side retrieval sees the initial response; browsers see a post-execution state; agent-native wrappers (Playwright MCP, Chrome DevTools MCP) see a *lossy, token-bounded* projection of that state (accessibility tree, truncated network lists) chosen to fit model context [S08][S12].

## 2. JavaScript rendering

- Google's pipeline is crawl → render → index; queued 200-status pages are rendered by headless Chromium and the *rendered HTML* is what gets indexed [S02, C04–C05]. So "what's in the HTTP response" and "what gets indexed" are different artifacts — the same split that separates server-side retrieval from browser modes.
- E1 makes the split observable on a controlled fixture: the plain fetch received `<div id="app"></div>` and `<ul id="data-list"></ul>` with no data and caused the server to log exactly one `GET /`; Playwright's Chromium produced a DOM with 1 injected child and 3 list items, a changed `document.title`, a second request `GET /api/data`, and the page's console output [E1, C29]. A retriever structurally *cannot* see JS-injected content, XHR-loaded data, or client-side routing results.
- Googlebot is not a general browser: WRS clears localStorage, sessionStorage and cookies across page loads [S03, C07]; it declines permission prompts, lacks WebGL, and speaks HTTP only — no WebSockets/WebRTC [S03, C08]. It also "caches aggressively" and "may ignore caching headers" [S03, C09]. A local Playwright audit that replays authenticated, cookie-bearing, WebSocket-connected state therefore does *not* reproduce what Google renders — and neither does a server-side fetch.
- Google still recommends server-side or pre-rendering "because … not all bots can run JavaScript" [S02, C05] — the risk surface for any agent that validates pages only through mode (C).

## 3. Technical SEO

- **JS-injected metadata is invisible to server-side checks.** Google documents JavaScript-set titles, meta descriptions, canonicals (picked up during rendering) and robots meta tags [S02]; an agent grepping raw HTML via `curl` will miss all of them. The verification path Google provides is the Rich Results Test / URL Inspection Tool, which expose loaded resources, console output/exceptions and the rendered DOM [S03, C10].
- **Crawler constraints belong in retrieval tooling.** RFC 9309 (Sep 2022) requires crawlers to obey robots.txt groups matched case-insensitively against a product token that SHOULD appear in the User-Agent header; robots.txt 4xx → crawler may fetch anything, 5xx → MUST assume complete disallow; robots.txt cache ≤24 h; parsing limit ≥500 KiB [S09, C23–C24]. It also states the rules are "not a form of access authorization" [S09, C24] — robots compliance is a policy layer of server-side retrieval, not a security control, and it applies to mode (C) fetchers whether or not an agent wraps them in a browser.
- **Lab audits are browser-mode jobs.** Lighthouse runs audits against a page (public or authenticated) via PageSpeed Insights, DevTools, CLI or Node [S10]; its accessibility score is a weighted average of pass/fail axe-based audits, with manual audits excluded from the score [S14, C28]. None of this is reachable from HTML-only retrieval — and this session did **not** run Lighthouse (C36 UNVERIFIED).

## 4. Accessibility testing

- The decisive constraint: an axe-class engine needs a live DOM in a browser — "Axe-core needs a browser to work" (DWP) [S13, C27]. In E1, axe-core 4.11.0 injected into the *rendered* fixture flagged `button-name`, `color-contrast`, `image-alt`, `landmark-one-main`, `region` (13 passes) [E1, C30]; the `color-contrast` verdict depends on computed styles that do not exist in raw HTML.
- Standards guidance draws the automation boundary explicitly: automated tests can tell you alt is missing, but appropriateness "you need to see the image and judge it in context"; and W3C's checks "are not definitive" [S04, C11–C12]. Keyboard navigation, focus visibility and resize behavior are interaction checks that require driving the page [S04] — mode (C) cannot perform them at all; modes (A)/(B) can.
- Scoring nuance: Lighthouse weights come from axe user-impact assessments, audits are pass/fail, and manual audits never affect the score [S14, C28]. A green Lighthouse accessibility score is therefore a statement about a weighted subset of automated rules on one rendered state — not WCAG conformance.
- Academic practice confirms browser-in-the-loop testing: the ACCESS paper collected violations via the Playwright API (≈25 URLs, 171 rows) and measured a 51.303% severity-score reduction after LLM DOM corrections [S07, C17].

## 5. Network inspection

- **Playwright (local scripting):** monitor/modify all HTTP(S) traffic including XHR/fetch, mock/abort/fulfill requests, inspect WebSockets [S01, C01/C03]; Puppeteer's equivalent stalls every request until continued/responded/aborted [S05, C14]. Blind spot documented by Playwright itself: service workers can hide events from `page.route()`/`browserContext.route()` unless `serviceWorkers: 'block'` is set [S01, C02].
- **Agent-native wrappers:** Playwright MCP exposes `browser_network_requests` (list since page load) and `browser_network_request` (full headers + body), plus console capture, with route-mocking behind `--caps=network` [S08, C21]; Chrome DevTools MCP adds DevTools-grade inspection — Cookie/Set-Cookie headers, Lighthouse audit tool, performance traces with Core Web Vitals, CPU/network throttling and UA/viewport emulation [S12, C26]. Its README-level caveat: Playwright MCP "is **not** a security boundary" [S08, C22].
- **Server-side retrieval:** by construction observes one request/response pair. E1: the node fetch produced a single `GET /` (UA `node`), while the browser run produced `GET /` + `GET /api/data` (UA `HeadlessChrome/153.0.8010.0`) [E1, C29]. Subresources, analytics pings, XHR endpoints and redirect chains of the *page* are simply absent from mode (C).
- E2 shows a second-order effect: the *retriever itself* is observable and variable — shell curl failed (000) on playwright.dev, developers.google.com, example.com but passed on github.com, while native `fetch_page` retrieved every cited host in full [E2, C31].

## 6. Source-grounded research

- **Retriever choice is part of the methodology.** Because shell HTTPS, hosted `fetch_page` and browser egress diverge (E2/E3), each ledger entry must record *how* it was retrieved; a host failing curl is not evidence of unreachability.
- **Chunk discipline:** several core sources were multi-chunk (W3C Easy Checks 9/9, Playwright MCP README 9/9, RFC 9309 5/5, Chrome DevTools MCP reference 5/5, Google JS docs 4/4). Citing a search snippet instead would have missed, e.g., the Google page footer dates (2026-03-04, 2025-12-18) and Deque's own 16/50-SC concession that frames the whole coverage disagreement [S02][S03][S06].
- **Cost trade-off inside browser modes:** Microsoft's own README recommends that coding agents consider Playwright CLI+SKILLS over MCP because MCP loads "large tool schemas and verbose accessibility trees into the model context" [S08, C20] — token cost is a first-order design constraint for agent research loops.
- **What browser evidence does not prove:** a screenshot of a locally rehosted page says nothing about production cookies/headers/third-party scripts (in-repo `docs/browser.md`), and E3 confirms this session has no live-site browser evidence.

## 7. Disagreements and limitations (5 recorded)

1. **Automated accessibility coverage (D1):** Deque reports **57.38%** of *issues* automated while conceding only **16/50** WCAG 2.1 AA success criteria show automated issues ("supports the 20 to 30% … claims") [S06]; Vigo et al. measured **≤50% SC coverage, 14–38% completeness, 66–71% correctness** [S11]; UK DWP guidance says axe-core+PA11Y find **~35%** of issues [S13]; W3C says automated checks are non-definitive [S04]. Denominators and datasets differ — **unresolved, not averaged**.
2. **Does JS rendering "just work"? (D2):** Google documents a working render pipeline [S02] while the same docs warn "not all bots can run JavaScript" and enumerate WRS limits (state cleared, cache-header ignoring, no WebGL/WebSocket/WebRTC, permission prompts declined) [S02][S03]. Third-party "Googlebot can't click"-style claims surfaced in search but were **not** found in the official pages and are excluded.
3. **Where accessibility risk lives (D3):** vendor framing (automation catches a majority of real issues by volume [S06]) vs independent measurement (half of success criteria never analyzed [S11]) vs standards guidance (human judgment required [S04]) — three incompatible stories about the same tool category.
4. **Browser network inspection has blind spots too (D4):** service-worker masking in Playwright [S01], origin rules that are "not a security boundary" in Playwright MCP [S08], versus the complementary blindness of server-side fetch (no XHR ever issued) [E1].
5. **Observation modality (D5):** Playwright MCP deliberately avoids screenshots ("bypassing the need for screenshots or visually-tuned models", vision opt-in) [S08] while Chrome DevTools MCP pairs a11y snapshots with DevTools traces/Lighthouse [S12] — accessibility-tree fidelity vs visual/telemetry fidelity, with different token costs.

**Session limitations:** no native browser tool was exposed in this session (browser evidence comes from locally launched Playwright); Chromium could not navigate public sites (E3); no Lighthouse/WCAG/CWV run (C36); `fetch_page` JS behavior untested (C34); Deque report date and axe-core version not stated in source (C32–C33).

## 8. Practical selection guide

| Task | Use | Why |
|---|---|---|
| Verify meta/canonical/structured data on CSR pages | Rendered-DOM check (A or B), cross-check with Rich Results Test [S02][S03] | JS-injected tags absent from raw HTML [E1] |
| robots.txt / crawl-policy audits | Server-side retrieval + RFC 9309 logic [S09] | Header/status-level; no rendering needed |
| Accessibility rule runs | Playwright/axe or Lighthouse (B or A) [S13][S14][E1] | Rules need computed DOM; manual checks need human/interaction [S04] |
| Network debugging, auth flows, WebSocket traffic | Playwright route/events or Chrome DevTools MCP [S01][S12] | Only browsers generate that traffic; mind service-worker caveats [S01] |
| Source-grounded literature research | `fetch_page` with full-chunk retrieval + ledger | Reached all 14 sources this session; shell reached only some [E2] |
| Live third-party site audits in this environment | **Not established** — probe first [E3] | Public navigation failed; do not claim screenshots |

## Counts

- Retrieved sources: **14** external (all chunks complete; 10 official-documentation, 2 academic) + 5 in-repo reference docs; 3 execution records.
- Claims in ledger: **36** — **31 verified**, **5 unresolved** (C32–C36).
- Failed retrievals: **5** (1 wrong doc URL → corrected; 3 shell HTTPS hosts; 1 browser navigation), all logged in `sources.json → failed_retrievals`.
- Deliverables: `docs/benchmarks/research/browser-research.md`, `sources.json`, `verification.md`.
