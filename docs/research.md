# Research in Arena

**Observed:** `web_search` returned titles, URLs, snippets and sometimes relative age; `fetch_page` returned paginated text from full pages and extracted text from a small PDF and an arXiv paper. A small report, JSON source ledger and artifacts were delivered via GitHub. This was a **limited benchmark**, not proof of an exhaustive Deep Research service.

## Repeatable workflow

1. Define a bounded question, date range, source types and output. Search multiple distinct phrasings.
2. Keep every URL, publisher, retrieval date and whether evidence is a snippet, full fetched page, PDF text or independent test.
3. Fetch every relevant page chunk (`hasMore` / `chunkIndex`); one prior experiment did **not** fetch all chunks.
4. Write claims into `sources.json` with `source_id, url, exact supported claim, evidence type, uncertainty`; check each citation against its source.
5. Find at least one contrary or limiting source; report disagreement instead of averaging away contradictions.
6. Produce `research.md` plus a short `validation.md`: actual retrievals, missing materials, tests and remaining questions.
7. Use GitHub delivery for connected sessions. Validate file existence and source links before claiming completion.

**Boundaries:** native `fetch_page` is not a raw HTTP header/HTML/JavaScript rendering capture; PDF text is not figure/table/OCR verification; shell HTTPS may fail where native fetch succeeds. Never invent exact usage quotas or source dates. For website audits, distinguish a research review from a live crawl or browser audit.
