# AGENTS.md

This repository uses the following workflow and style rules.

## Commit Workflow

- Do not bump the package version manually.
- The repo-local pre-commit hook in `.githooks/pre-commit` bumps the patch
  version in `pyproject.toml` automatically.
- Do not bypass the hook when committing.
- Keep commits focused on a single coherent change.
- Before committing, run the relevant verification commands for the files you
  changed.
- For broad changes, prefer:
  `python3 -m unittest discover -s test -v`
- Also run:
  `python3 -m compileall webmaus test`
- After a successful commit, push the current branch when the task requires the
  remote to be updated.

## Coding Style

- Match the existing style of the file you are editing.
- In legacy modules, keep the current lightweight formatting style instead of
  reformatting to Black-style layouts.
- Use single quotes unless the surrounding code clearly uses double quotes.
- Keep functions small and direct.
- Prefer explicit code over clever abstractions.
- Avoid unrelated refactors while making a requested change.
- Keep docstrings short and practical.
- Preserve the current public API unless the task explicitly calls for a change.

## Testing

- Add or update regression tests for bug fixes and new public helpers.
- Prefer the standard library `unittest` style already used in `test/`.
- Do not add new dependencies for testing unless there is a clear need.

## Repo Notes

- The package version lives in `pyproject.toml`.
- The Git hook path for this repo is `.githooks`.
- Convenience alignment helpers live in `webmaus/simple_align.py`.
