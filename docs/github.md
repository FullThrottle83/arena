# GitHub-connected Arena sessions

## Tested delivery path

Arena assigned working branches and exposed bash, `git`, `gh`, and injected GitHub authentication. Actual commits and draft PRs succeeded: [PR #2](https://github.com/FullThrottle83/arena/pull/2) and [PR #3](https://github.com/FullThrottle83/arena/pull/3). This does not establish a callable dedicated GitHub function.

**Before work:** verify `git remote -v`, `git branch --show-current`, `git status`, `git rev-parse HEAD` and existing remote PRs. Record any Arena-assigned branch name; do not assume the preferred name is accepted.

**Parallel-session hazard confirmed:** browser and artifact sessions shared `arena/01a0dc7f-arena`, producing one PR with both sets of changes. A third session used `arena/01a0dc7e-arena`. Separate chats do **not** guarantee distinct remote branches. Check branch ownership before a push; avoid force-push. If branches collide, pause or deliberately coordinate non-overlapping paths and PR ownership.

## Safe operating sequence

1. Connect only the target project repo. Make no direct changes to `main`.
2. Inspect the actual branch, `origin/main`, `git status`, and remote PR/head.
3. Restrict work to explicit paths. Avoid unrelated formatting/refactors.
4. Execute tests and review the actual diff, including binary files and secrets.
5. Commit and push to the confirmed branch. A rejected push is a coordination signal; inspect remote history before rebasing.
6. Create/reuse the correct PR; verify real URL and changed files. No fabricated commit SHA or PR number.
7. Do not merge or close a PR while its Arena session still needs to push. Once finished, review CI and merge deliberately.

A product blog mentioning “push to main” does not override the behavior and branch restrictions in the current session. Do not paste personal access tokens into prompts.
