# Arena prompt — local website QA with real browser evidence

Use THIS session's connected project repo; read https://github.com/FullThrottle83/arena/blob/main/AGENTS.md, docs/browser.md and docs/limitations.md. Inspect actual repo/branch and any existing PR; do not assume an isolated branch.

Task: audit the project's LOCAL build/preview, not an arbitrary public deployment. Determine the documented build/start commands and run them. Inspect availability of Playwright and browsers first; if absent, request approval for the pinned, npm-bundled Chromium recipe. Never silently pass sandbox or web-security bypass flags. Only claim tests that actually execute.

Check at mobile, tablet and desktop widths: rendered DOM and JS state, horizontal overflow, buttons/forms as appropriate, keyboard/focus, console messages, request failures and real browser-generated screenshots. Record viewport, URL, response, screenshot dimensions and SHA-256. Keep screenshots as files in a narrow evidence directory. If public navigation fails, say so; never rehost fetched Markdown and call it live-site browser evidence. Do not claim Lighthouse, CWV, WCAG conformance or production header checks without running those exact tools.

Deliver an evidence-rich but concise report plus machine-readable results to a dedicated project path, commit on the confirmed branch and return actual PR URL, tests, errors and exclusions. Do not force-push, write to main or merge.
