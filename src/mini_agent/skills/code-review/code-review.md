---
name: code-review
description: Workflow for reviewing code changes — pull requests, diffs, or a set of edited files — for correctness, safety, and quality before they're merged or shipped. Use this skill whenever asked to "review," "check," "look over," or give feedback on code changes, not just when the word "review" is used explicitly. Distinct from the developer skill: this is for evaluating someone else's (or your own already-written) code, not writing new code from scratch.
---

# Code Review

A workflow for reviewing code changes thoroughly and giving actionable feedback.

## Operating loop

1. **Understand the intent first.** Read the PR description, commit messages, or task context before the diff itself. Know what the change is supposed to do before judging whether it does it well.

2. **Read the whole diff, not just the additions.** Understand what was removed or changed, not only what's new. If a change touches a file you don't have full context on, read the surrounding unchanged code too — a correct-looking diff can still break things nearby.

3. **Review in priority order:**
   - **Correctness** — Does it do what it claims? Are there logic errors, off-by-ones, unhandled edge cases (empty input, null, concurrent access, network failure)?
   - **Safety** — Any risk of data loss, security issues (injection, auth bypass, secrets in code), or breaking existing behavior/API contracts?
   - **Tests** — Do tests exist for the new/changed behavior? Do they actually test the behavior, or just exercise the code without meaningful assertions? Are edge cases covered, or only the happy path?
   - **Design** — Is this the right level of abstraction for the problem? Is anything duplicated that should be shared, or over-abstracted for a one-off need?
   - **Readability/style** — Clear naming, consistent with the codebase's existing conventions, no dead code or leftover debug statements.

   Don't spend equal time on all five — correctness and safety issues matter far more than style nits.

4. **Verify claims, don't just read them.** If the PR says "tests pass" or "verified locally," and you have the tools to check, actually run the tests/build rather than taking the description at face value.

## Giving feedback

- **Be specific.** Point to the exact line/function and explain the concrete problem, not "this could be cleaner." Include a suggested fix when it's not obvious.
- **Distinguish severity.** Separate must-fix (bugs, security, broken tests) from should-consider (design tradeoffs) from nit (style, naming) so the author can prioritize.
- **Explain the "why."** A rule without reasoning invites pushback; a clear rationale ("this will throw on empty arrays") gets fixed faster.
- **Don't nitpick everything.** If the change is otherwise sound, don't manufacture objections. Approve with minor comments rather than blocking on style preferences.
- **Ask instead of assuming when intent is unclear.** If a change looks intentional but odd, ask why rather than declaring it wrong outright — there may be context you're missing.

## What to flag as blocking

- Bugs that will affect real usage, not just theoretical edge cases.
- Security issues: secrets/credentials in code, unsanitized input, broken auth checks, unsafe deserialization.
- Missing tests for non-trivial new logic or bug fixes.
- Breaking changes to public APIs/contracts without a clear migration path or version bump.
- Silent failure modes — errors swallowed, exceptions caught and ignored.

## What not to block on

- Pure style preferences already handled by a linter/formatter.
- Alternative designs that are equally valid to what's proposed, absent a concrete problem with the chosen approach.
- Scope creep requests ("also fix X while you're here") — note them as follow-ups instead of blocking the current change.
