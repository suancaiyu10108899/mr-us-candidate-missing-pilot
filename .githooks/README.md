# Maintainer publication hooks

These hooks are for the registered maintainer's local publishing environment.
Students do **not** need a global control tool, Windows, or hook installation to
clone the repository, run the synthetic tests, create branches or submit PRs.
Main is protected through PR review and CI on GitHub.

The scripts derive from the owner's Python project template, pre-push revision 7.
The commit-message hook and shell launcher are unchanged. The PowerShell script
keeps exact publisher-check, grant/target/ref/path binding and outgoing secret
rules R1–R6/P1. Only the following project-scoped visibility policy is adapted:

- Exact GitHub repository: `suancaiyu10108899/mr-us-candidate-missing-pilot`.
- CREATE_INITIAL_REF requires the actual repository to be private.
- UPDATE_FF/CREATE_REF require the actual repository to be public.
- Every other repository, operation, unknown visibility or provider failure blocks.
- Visibility/provider environment overrides are rejected; no bypass mode is added.

This implements the owner's explicit one-repository public exception. It does not
change any global policy or confer publishing authority. Each maintainer push
still needs a fresh applicable exact grant; hooks remain enabled. Local tool and
authority paths live in Git config outside tracked content. The initial grant
binds the actual hook hashes. No control authority or internal metadata is shipped.

Source SHA-256 and scoped adaptation evidence are in `records/F-002-publication-hook.md`.
Production visibility logic is exercised directly in `tests/test_publication_hook.py`;
provider observations in that unit test are synthetic test inputs, not live API facts.
