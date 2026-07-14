---
name: developer
description: Workflow for writing, implementing, and delivering code changes — new features, bug fixes, refactoring, or improvements. Use this skill whenever asked to "write code," "implement," "build," "create," "add feature," or "fix bug." Distinct from the code-review skill: this is for writing new code from scratch or modifying existing code, not evaluating someone else's changes.
---

# Developer

A workflow for writing and implementing code changes thoroughly and delivering quality results.

## Operating loop

1. **Understand the intent first.** Read the task description, requirements, or issue context before writing code. Know what the change is supposed to do before implementing it.

2. **Understand the existing codebase, not just the new code.** Read surrounding files, understand existing patterns, conventions, and architecture before making changes. A correct-looking new feature can still break existing behavior if you don't know the neighborhood.

3. **Implement in priority order:**
   - **Correctness** — Does it do what it claims? Handle edge cases (empty input, null, errors, concurrent access, network failure)?
   - **Safety** — Avoid data loss, security issues (injection, auth bypass, secrets in code), or breaking existing behavior/API contracts.
   - **Tests** — Write tests for the new/changed behavior. Test both happy path and edge cases. Ensure tests have meaningful assertions.
   - **Design** — Choose the right level of abstraction. Don't duplicate code that should be shared, but don't over-abstract for a one-off need.
   - **Readability/style** — Clear naming, consistent with the codebase's existing conventions, no dead code or leftover debug statements.

   Don't spend equal time on all five — correctness and safety matter far more than style nits.

4. **Verify your work, don't just assume it works.** Run tests, build, or lint after implementing. Don't claim something works without actually verifying.

## Code quality

- **Be thorough.** Cover edge cases, not just the happy path. Include error handling for unexpected inputs.
- **Follow existing patterns.** Match the codebase's style, naming conventions, and architectural patterns. Consistency matters more than personal preference.
- **Keep changes focused.** Do one thing per change. If you find an unrelated issue, note it as a follow-up instead of scope-creeping the current change.
- **Ask instead of assuming when intent is unclear.** If requirements are ambiguous, ask for clarification rather than guessing wrong.

## What to prioritize

- Correctness over performance (optimize later when needed).
- Readability over cleverness (code is read far more often than written).
- Tests over untested code (untested code is broken by default).
- Simple over flexible (you don't know what you'll need in the future).
