# Arena task <ID>: <short title>

**Goal:** <one sentence>  
**Target repo:** <owner/name>  
**Base commit / branch:** <immutable SHA and intended base branch>  
**Data classification:** public/synthetic only; confirm [policy](https://github.com/FullThrottle83/arena/blob/main/docs/data-handling.md).  
**In scope:** <exact paths and operations>  
**Out of scope:** <exact paths, production actions, secrets, unrelated refactors>  
**Inputs:** <links to actual checked-in files; no private tokens>  
**Allowed installs / permissions:** <explicitly specified; otherwise ask first>  

## Acceptance criteria

- <exact command → expected exit code or structured assertion>
- <another check or source-to-claim requirement>
- No unrelated changes; review the actual diff.

## Deliverables

- One branch/PR against <base>.
- `.arena/results/<ID>.md` following [result template](https://github.com/FullThrottle83/arena/blob/main/templates/result.md).
- <specific evidence paths, if required>.

## Stop conditions

Stop with PARTIAL/BLOCKED if required inputs, safe dependencies, network, permissions or branch ownership are unavailable. Do not force-push, write to main, use unsafe browser flags without approval, or merge.
