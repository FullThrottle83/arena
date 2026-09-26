# Data handling and terms — operational gate

**Checked:** 2026-09-26. Read the [official Terms of Use](https://help.arena.ai/articles/5629909088-terms-of-use) (agreement dated 2026-02-23) and [Arena privacy FAQ](https://arena.ai/faq) before connecting a repository or uploading files. Product-specific supplemental terms and account settings, if applicable, may change the applicable rules. This is a conservative working policy, not legal advice.

## What the published terms actually say

- **Ownership is not transferred outright:** §3.2 says the user retains ownership as between the user and Arena, subject to the license in §3.3.
- **License is very broad:** §3.3 describes a non-exclusive, transferable, perpetual, irrevocable, worldwide, royalty-free and sublicensable license for input and output, with extensive permitted uses including distribution, display and improvement.
- **Third-party processing:** §3.4 permits sharing provided content with AI service providers and says they may not be required to keep it confidential; additional provider terms may apply.
- **Research disclosure:** the official FAQ says conversations may enter de-identified public research datasets or private model-provider evaluations. This does **not** mean every conversation is necessarily published, nor that de-identification creates a contractual confidentiality guarantee.
- **Input restrictions:** §3.5 restricts submitting personal/sensitive information, including financial or medical information. Do not rely on redaction being automatic or sufficient.
- **Restrictions on access:** §5 restricts programmatic/automated access to the Arena service. Ordinary authorized agent tool execution is different from scripting the Arena interface; do not build unauthorized bulk requests or scraping.

## Manual start and access boundary

[Arena Terms §5](https://help.arena.ai/articles/5629909088-terms-of-use) prohibits accessing the Arena service by programmatic/automated means or automatically querying it. The current handoff therefore uses a GitHub task brief and PR for coordination; **the human user opens Arena and submits the task**. Do not drive Arena's UI with another bot, scrape its account state or assert an undocumented Agent Mode API. This does not prohibit legitimate coding/terminal actions *within an authorized Arena session*.

## Material decision matrix

| Material | Default action | Rationale / gate |
|---|---|---|
| Synthetic fixtures and fake identities | **Allowed for controlled experiments** | No actual secrets, personal information or third-party rights. |
| Public documentation, open-source test code and public repos | **Use after inspecting repo contents and licenses** | Public visibility does not establish a right to grant an expansive downstream license for third-party contributions; scan for accidentally committed secrets and private data. |
| Your own non-public source or unpublished product plans | **Do not connect by default** | Requires your informed acceptance of the data-use/license terms and a risk/rights review. Use a sanitized minimal repro instead where possible. |
| Client code, private client repositories, contracts, unreleased assets | **Do not use by default** | Confidentiality, contractual/IP rights and potential third-party processing need explicit authorization and suitable terms. Prefer synthetic reproductions. |
| Personal data, health/financial data, credentials, production secrets, tokens, private keys | **Do not submit** | Sensitive input, policy/contract and security risks. Never request token values in chat or commit them. |

Before enabling GitHub, inspect the repository and its history for `.env`, credentials, logs, client records, sample personal data and unpublished assets. Even if the requested diff is small, connected repo content may be available to the agent. Use a purpose-built public fixture repo when uncertain.

## Account settings and privacy requests

Check actual, current account controls and any applicable supplemental terms. The existence of a general opt-out or deletion mechanism must not be treated as permission to upload prohibited/confidential material or as a retroactive guarantee for previously shared copies. Keep this page dated and recheck terms when Arena updates them.

**Sources:** [Terms §§3.2–3.5 and §5](https://help.arena.ai/articles/5629909088-terms-of-use) · [FAQ: conversation use and de-identification](https://arena.ai/faq) · [Agent Mode guide](https://help.arena.ai/articles/5432423882-how-to-use-agent-mode).
