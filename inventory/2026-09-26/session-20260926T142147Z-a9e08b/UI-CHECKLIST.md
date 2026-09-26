# Arena interface — items that must be verified manually

Nothing below is observable from inside the sandbox; the engine cannot confirm any of it. `NOT_TESTED` means unobserved, **not** absent.

| UI capability | Status | How to check in Arena |
|---|---|---|
| Visible credits / usage meter | `NOT_TESTED` | Arena UI near the usage limit; no in-session value is authoritative |
| Credit reset time / daily period | `NOT_TESTED` | official credit help says the 24 h period starts with the first prompt; confirm the countdown in your UI |
| Model identity shown for this chat | `NOT_TESTED` | Agent Mode normally hides the orchestrator model; record UNKNOWN unless the UI displays it |
| Available product modes for this account (Agent / Direct / Side-by-Side / Battle / Fullstack / Image-Video) | `NOT_TESTED` | mode dropdown in the Arena UI |
| Concurrent-session or parallel-chat limits | `NOT_TESTED` | start two sessions and observe whether branches/limits collide; in-session evidence only shows branch sharing risk |
| Preview panel renders a sandbox server | `PARTIAL` | the sandbox server was reachable and the platform probed port 8099, but the rendered preview itself is only observable in your browser |
| File upload into the session | `NOT_TESTED` | attach a file to a prompt in the UI (not exercised in this session) |
| File download from the workspace panel | `NOT_TESTED` | workspace panel -> Download (no repo connected) — documented, not verified here |
| Workspace ZIP export via /download-workspace | `NOT_TESTED` | append /download-workspace to the chat URL; documented in the Agent Mode help article, not verified by this session (and with a repo connected the docs state changes are delivered via PR instead) |
| Account privacy / data-sharing controls | `NOT_TESTED` | account settings page; must be checked in the UI, terms are dated 2026-02-23 |
| PR/diff tab shows this session's changes | `PARTIAL` | the PR will be created by this session; visual confirmation of the Diff tab is a manual step |

- Do not script or scrape the Arena UI (Terms §5 restrict automated/programmatic access); check these visually yourself.
- Model identity may be hidden by design — record `UNKNOWN` rather than guessing.
- Credits/usage and reset time are account state only; no in-session value is authoritative.
