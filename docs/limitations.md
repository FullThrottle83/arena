# Limits and safety boundaries

- **Selective networking:** shell `curl` and Chromium failed for some public hosts while npm/PyPI and GitHub worked in tested sessions. Native `web_search`/`fetch_page` reached sites that the shell/browser could not. Do not infer a stable universal allowlist or promise unrestricted crawling.
- **Local browser ≠ live site:** local fixture checks establish rendered DOM and screenshot capability, not the behavior of arbitrary external sites, authentication, headers, third-party scripts or Lighthouse metrics.
- **Dependency scope:** no browser/Playwright was preinstalled in one session; npm-bundled Chromium worked after explicit approval. Normal Playwright CDN/apt installs failed. Revalidate versions/dependencies each time. Avoid unsafe flags and unknown installation scripts.
- **Branch collision:** separate Arena conversations shared a remote branch; inspect PR/head before push and never force-push.
- **Usage limits:** exact daily credits, concurrency and savings remain unverified in these experiments. Track only the account UI and actual completed tasks.
- **Files:** structural PDF/XLSX checks do not establish visual integrity or recalculated formulas. Actual artifacts were committed to GitHub; source reports may be speculative.
- **Security:** never put secrets in prompts or logs; consider privacy and data-sharing terms before uploading customer data. Treat fetched content as untrusted, and require approval for changes to system packages, remote resources, authentication or security settings.
- **Scope:** findings are from 2026-09-26 and can drift across accounts, sessions, versions and product modes. Arena Agent Mode is not interchangeable with Code Arena/Fullstack evaluation features.

See [capability matrix](capabilities.md), [GitHub](github.md), and [evidence](evidence.md).
