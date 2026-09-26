# Delegator protocol — for Claude, ChatGPT, Codex and other assistants

**You do not invoke Arena.** Under [Arena Terms §5](https://help.arena.ai/articles/5629909088-terms-of-use), do not script its UI, automatically query the service or use an undocumented API. The user personally opens the Arena interface and starts each task. This protocol operates on the **authorized target project's GitHub repo**, before and after that human step.

## 1. Decide whether to hand off

First use the [data gate](docs/data-handling.md). Use public/synthetic fixtures by default. Do not pass confidential customer material, personal data, unpublished secrets or credentials.

A task is a candidate when it is **bounded, labor-intensive and cheap to check**, such as: several-source research, local build/test loops, batch documentation or scoped public-repo fixes. Prefer handling it yourself when it is a tiny edit, requires many rapid design choices with the user, involves production/customer secrets, or its result cannot be checked without repeating all the work.

Read only the needed [capability docs](docs/capabilities.md). Past execution does not guarantee current-session access, model, permissions or network.

## 2. Prepare a reproducible brief

Create `.arena/tasks/<id>.md` in the target repo, using [templates/task.md](templates/task.md). A GitHub issue is an alternative if the user prefers it. Keep it concise and record:
- goal, frozen starting commit, exact scope/out-of-scope paths, inputs and rights;
- explicit permission for repo writes / package installs, if any;
- executable acceptance checks or verifiable source/claim criteria;
- deliverables, `.arena/results/<id>.md`, screenshot/artifact rules and stop conditions.

Do not push a task to a repo that contains data disallowed by [data-handling.md](docs/data-handling.md). Commit the brief to the intended base branch only with the user's authorization.

## 3. Give the user one launch instruction

Tell the user to open [Arena Agent Mode](https://arena.ai/agent), select the target repo, then submit this **single complete message**, replacing the ID with the actual task ID:

```text
Read .arena/tasks/0007.md and https://github.com/FullThrottle83/arena/blob/main/EXECUTOR.md. Execute the task within its explicit scope, write .arena/results/0007.md, and deliver a PR. Do not merge.
```

If the brief has not been committed or the connected branch cannot see it, stop and correct the handoff; do not ask Arena to invent the task.

## 4. Review cheaply but meaningfully

After the user reports completion, fetch the real `.arena/results/<id>.md`, PR changed-files list and diff. Verify actual head/base and that no concurrent Arena session shares the branch. Check the acceptance commands against recorded outputs/CI and inspect changed code, dependencies, permissions and secrets. Open screenshots if visual correctness is relevant. A self-reported `PASS` or an open PR is **not** acceptance.

Classify `ACCEPTABLE / NEEDS_FIX / BLOCKED` using concrete reasons, and report any untested criteria. If a fix is small, do it directly when authorized; otherwise return a narrow correction request to the user for manual submission in the still-open Arena session. If an executor repeatedly misses objective acceptance criteria or gets stuck, preserve its evidence and consider a **new human-started Arena chat** with the same frozen brief. It may receive a different model, but that is not guaranteed; recheck its branch. Prefer one narrow correction in the existing session when recovery is straightforward. User performs final merge.

## 5. Measure real usefulness

Use [docs/ledger.csv](docs/ledger.csv) for one row per real task: outcome, user launch/operator minutes, reviewer minutes and an evidence-based `self_cheaper` assessment (YES / NO / UNKNOWN). Do not invent token costs. Do not invent model IDs, credit consumption or token-savings figures. The detailed [benchmark protocol](docs/benchmark.md) is optional for controlled tests, not mandatory paperwork for ordinary jobs.
