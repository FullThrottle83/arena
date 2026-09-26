# High-value follow-up experiments

Do not rerun another giant generic inventory. Run bounded, reproducible tests and update [capabilities](capabilities.md) only with evidence.

1. **Real Astro project:** in a fresh Arena session connected to an explicit sample repo, `npm ci`/install, `astro build`, run local server, browser screenshots at mobile/desktop and compare with expected output. Record build log, errors, changed files and actual PR.
2. **Branch isolation:** start two simultaneous sessions on the *same* test repo; record actual `git branch --show-current`, `origin` refs and PR ownership before writing; do not push if shared unexpectedly.
3. **Browser persistence:** in a new session repeat pinned npm bootstrap without root; measure setup time and test OS-level sandbox status independently rather than assuming flag absence proves it.
4. **Research depth:** require 5 full, dissimilar sources including a multi-chunk page and a PDF; verify 10 claim-source pairs manually, mark snippets and missing pages. Compare against Gemini Deep Research on the *same question*.
5. **Live-site access:** on a harmless owned domain, separately test shell HTTP, native `fetch_page`, browser `page.goto`; no synthetic local render masquerading as production evidence.
6. **Document output:** open generated PDF/XLSX with independent renderer and validate visible pages/recalculated formulas, not merely ZIP/PDF structure.
7. **Actual quota:** log manual start/end time, outputs, visible account usage and interruptions for 3 repeated bounded tasks; do not invent token savings.

Use [prompts/](../prompts/README.md) for full prompts.
