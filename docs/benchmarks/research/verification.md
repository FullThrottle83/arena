# Verification log — browser-research benchmark

**Date:** 2026-09-26 · **Branch:** `arena/01a0dcb8-arena` · **Ledger:** [sources.json](sources.json) · **Report:** [browser-research.md](browser-research.md)

Verification means: the claim's quoted evidence was re-checked against the retrieved chunk(s) recorded in the ledger (retrieval = native `fetch_page`, every chunk fetched). Search snippets were never used as evidence.

## 1. Structural validation

| Check | Method | Result |
|---|---|---|
| `sources.json` parses as JSON | `python3 -m json.tool docs/benchmarks/research/sources.json` | **PASS** |
| Every claim's `source_ids` resolves to a listed source or execution record | Python cross-check of `claims[].source_ids` vs `sources[].source_id` / `execution_evidence[].evidence_id` | **PASS** (0 dangling IDs) |
| Every source has `chunks_retrieved == chunks_total` | Python cross-check | **PASS** (14/14 external sources complete; 44 chunk fetches in total) |
| Every report citation `[Sxx]`/`[E#]` exists in the ledger | Manual cross-check of report reference set vs ledger IDs | **PASS** |
| No invented dates/figures | Dates only recorded where the retrieved page states them; absent dates recorded as `null` with a note (S01, S04, S05, S06, S10, S12, S13) | **PASS** |

## 2. Claim verification (36 total: 31 VERIFIED, 5 UNRESOLVED)

| ID | Claim (abridged) | Source | Evidence location | Result |
|---|---|---|---|---|
| C01 | Playwright monitors/modifies all page HTTP(S) traffic incl. XHR/fetch | S01 | chunk 0, Introduction | VERIFIED |
| C02 | Service workers can hide events from Playwright routing; `serviceWorkers:'block'` workaround | S01 | chunk 1, Missing Network Events | VERIFIED |
| C03 | WebSocket inspection/mocking/modification out of the box | S01 | chunk 1, WebSockets | VERIFIED |
| C04 | Google crawl→render→index phases; headless Chromium rendering | S02 | chunk 1 | VERIFIED |
| C05 | Google recommends SSR/prerender; "not all bots can run JavaScript" | S02 | chunk 1 | VERIFIED |
| C06 | JS SEO basics "Last updated 2026-03-04 UTC" | S02 | chunk 2 footer | VERIFIED |
| C07 | WRS clears localStorage/sessionStorage/cookies across page loads | S03 | chunk 1, item 05 | VERIFIED |
| C08 | Googlebot: HTTP only, no WebSocket/WebRTC; no WebGL; declines permission requests | S03 | chunks 0–1, items 03/07/08 | VERIFIED |
| C09 | Googlebot caches aggressively; WRS may ignore caching headers | S03 chunk 1 item 06; S02 chunk 2 | same text in both | VERIFIED |
| C10 | Rich Results Test/URL Inspection expose resources, console, rendered DOM; page updated 2025-12-18 | S03 | chunk 0 step 01; chunk 1 footer | VERIFIED |
| C11 | Automated tests detect missing alt; appropriateness needs human judgment | S04 | chunk 1, alt text section | VERIFIED |
| C12 | W3C easy checks "not definitive"; pages can pass and still have barriers | S04 | chunk 8, Next steps | VERIFIED |
| C13 | Minimum default contrast 4.5:1 for normal-size text | S04 | chunk 3, Contrast ratio | VERIFIED |
| C14 | Puppeteer: every request stalls unless continued/responded/aborted | S05 | chunk 0 | VERIFIED |
| C15 | Deque 57.38% of issues automated; 169,242/294,958; 13,000+ pages; axe-core; FP excluded | S06 | HTML chunks 0–2 + PDF chunks 1–2 | VERIFIED |
| C16 | Deque: 16/50 WCAG 2.1 AA SC automated; concedes 20–30% SC-based claims | S06 | HTML chunk 0 / PDF chunk 0 | VERIFIED |
| C17 | ACCESS paper used Playwright API (25 URLs, 171 rows); 51.303% ReAct reduction | S07 | PDF chunk 1 §2.1; PDF chunk 2 Table 2 | VERIFIED |
| C18 | arXiv:2401.16450 submitted 28 Jan 2024, rev. 10 Feb 2024; 11 pages | S07 | abs page | VERIFIED |
| C19 | Playwright MCP: LLMs act via accessibility snapshots, bypassing screenshots | S08 | chunk 0 | VERIFIED |
| C20 | README advises CLI+SKILLS vs MCP for token efficiency | S08 | chunk 0, MCP vs CLI section | VERIFIED |
| C21 | `browser_network_requests` / `browser_network_request` (headers+body), console tool, `--caps=network` | S08 | chunks 4–6 (tools) | VERIFIED |
| C22 | "Playwright MCP is **not** a security boundary." | S08 | chunk 4, Security | VERIFIED |
| C23 | RFC 9309 obey-groups rule, UA product token, 5xx→full disallow, 4xx→open access; Sep 2022 | S09 | chunks 0–2 | VERIFIED |
| C24 | "not a form of access authorization"; robots cache ≤24 h; parsing ≥500 KiB | S09 | chunks 0, 3 | VERIFIED |
| C25 | Vigo et al.: ≤50% SC coverage, 14–38% completeness, 66–71% correctness; published 13 May 2013 | S11 | chunk 0 abstract; chunk 2 pub history | VERIFIED |
| C26 | Chrome DevTools MCP: Cookie/Set-Cookie inspection, lighthouse_audit (excl. perf), traces/CWV, emulation | S12 | chunks 1–2 | VERIFIED |
| C27 | DWP: axe-core+PA11Y ≈35%; axe needs a browser; PA11Y uses Puppeteer headless Chrome | S13 | single chunk | VERIFIED |
| C28 | Lighthouse a11y score = weighted avg of pass/fail axe-impact-weighted audits; manual audits excluded; updated 2025-10-22 | S14 | chunks 0–1 | VERIFIED |
| C29 | E1: server-side fetch saw empty containers/one request; Playwright rendered JS+XHR+title; UA `node` vs `HeadlessChrome` | E1 | `results.json`, `server-log.ndjson` | VERIFIED |
| C30 | E1: axe-core on rendered page → 5 violation rules, 13 passes; valid 24,044-byte PNG (sha256 recorded) | E1 | `results.json` (PNG signature checked programmatically) | VERIFIED |
| C31 | E2/E3: curl 000 on 3 hosts / 200 on github.com; Chromium `ERR_CONNECTION_CLOSED`; `fetch_page` retrieved all cited hosts | E2, E3 | session command logs; fetch_page chunk receipts | VERIFIED |
| C32 | Deque report publication date | S06 | all 6 chunks: no date present | **UNRESOLVED** — search metadata (2021-03-10) not accepted as source evidence |
| C33 | axe-core version used in Deque dataset | S06 | all 6 chunks: only "version 3.5" of a rule change mentioned | **UNRESOLVED** — not stated |
| C34 | Whether native `fetch_page` executes JavaScript | — | no controlled test run | **UNRESOLVED** — NOT_TESTED |
| C35 | Local Playwright can audit arbitrary live public sites | E3 | one failed probe (`ERR_CONNECTION_CLOSED`) | **UNRESOLVED** — single FAILED attempt; no general claim either way |
| C36 | Full Lighthouse / WCAG / CWV results | E1, E3 | not executed; no reachable target | **UNRESOLVED** — NOT_TESTED |

## 3. Source-to-claim ledger integrity

- 36 claims → sources: S01×3, S02×4 (shared), S03×5 (shared), S04×3, S05×1, S06×3 (incl. 2 unresolved), S07×2, S08×4, S09×2, S10×0 direct (cited in report via Lighthouse claims under S14/S10), S11×1, S12×1, S13×1, S14×1, E1–E3×3, unresolved-only×3.
- Every source in `sources.json` is cited by ≥1 claim or by the report's tables; no claim lacks a quotation (unresolved claims record the absence of evidence explicitly).
- Classification tally: OFFICIAL_DOCUMENTATION 10 sources / THIRD_PARTY_REPORT 4 sources (2 academic) / EXECUTION_EVIDENCE 3 records / INFERENCE used only for the projection table in the report / UNVERIFIED used for the 5 unresolved claims.

## 4. Retrieval failures (5)

| ID | Attempt | Outcome | Resolution |
|---|---|---|---|
| FR1 | `fetch_page https://pptr.dev/guides/network` | 404 page body | Correct URL `/guides/network-interception` retrieved 3/3 (S05) |
| FR2 | `curl https://playwright.dev/` | HTTP 000 | Host fully retrieved via `fetch_page` (S01) |
| FR3 | `curl https://developers.google.com/` | HTTP 000 | Host fully retrieved via `fetch_page` (S02, S03) |
| FR4 | `curl https://example.com/` | HTTP 000 | Transport probe only |
| FR5 | Chromium `page.goto('https://example.com/')` | `net::ERR_CONNECTION_CLOSED` | No live-site browser claims made (E3, C35) |

A partial re-fetch of `github.com/microsoft/playwright-mcp` (HTML view, 15 noisy chunks) was abandoned after chunk 0 in favor of the raw README, which was then retrieved 9/9 — recorded as a source-selection change, not a failure.

## 5. Bottom line

All 14 cited external sources correspond to actual retrieved evidence (every chunk fetched); **31/36 claims verified** against that evidence; **5 claims unresolved** for explicitly recorded reasons; **5 retrieval attempts failed** (all have documented resolutions or are logged as environment limits). No date, quotation, capability or performance figure appears in the report without a ledger entry.
