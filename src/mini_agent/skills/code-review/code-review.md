---
name: code-review
description: Review code changes for correctness, safety, tests, design, and style. Use for pull requests, diffs, or edited files when asked to review or give feedback.
---

# Code Review

A concise process for reviewing code changes.

## Workflow

1. Understand the intent first: read the description or task context before the diff.
2. Read the whole change, including removals and surrounding code.
3. Prioritize:
   - Correctness: logic, edge cases, input validation.
   - Safety: security, data loss, API contract breaks.
   - Tests: coverage of new behavior and edge cases.
   - Design: right abstraction level, avoid duplication.
   - Readability/style: clear naming, consistent conventions.
4. Verify claims when possible instead of relying on descriptions.

## Feedback

- Be specific and point to the exact issue.
- Mark severity: must-fix, should-consider, nit.
- Explain why a change is needed.
- Avoid nitpicking healthy code.
- Ask about unclear intent rather than assuming a bug.

## Blocking issues

- Real bugs.
- Security problems.
- Missing tests for important changes.
- Breaking public contracts without migration.
- Silent failures or ignored errors.

## Non-blocking

- Style preferences covered by tooling.
- Equally valid alternative designs.
- Scope creep requests.
