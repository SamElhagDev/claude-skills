---
name: code-health-audit
description: Use when asked to run a code audit, code health check, code cleanup review, or a scan for improvements on the current repository
allowed-tools:
  - Bash(git status *)
  - Bash(git diff *)
  - Bash(git ls-files *)
  - Bash(python -m flake8 *)
  - Bash(python -m py_compile *)
  - Bash(python -m pytest *)
  - Bash(python -m unittest *)
  - Bash(dotnet build *)
  - Bash(dotnet test *)
  - Bash(dotnet list package *)
---

# Code Health Audit

## Overview

Scores Python and .NET problems 0 to 10, reports them by severity, and offers each fix one at a time. Nothing is staged or committed.

## Audit Sequence

1. **Scope:** `git ls-files`, or the path given. Leave out `tests/`, `.specify/`, `wwwroot/lib/`, `node_modules/`, `Migrations/`, `.venv/`, `venv/` and generated or minified files.
2. **Working tree:** if `git status --short` shows modified files, ask `You have uncommitted changes in <n> files; fixes will mix with them in the diff. Continue? [yes / no]`
3. **Stacks:** Python when `requirements*.txt`, `pyproject.toml` or `.py` files exist; .NET when `*.csproj`, `*.sln` or `*.slnx` exist. Neither: reply `No Python or .NET code found. This audit covers those two stacks.` and stop.
4. **Baseline:** run the CI workflow's lint, build and test commands, as `python -m ...`. No workflow: `python -m flake8 . --count --select=E9,F63,F7,F82 --statistics`; `python -m pytest tests -q` if `tests/conftest.py` exists or tests import pytest, else `python -m unittest discover -s tests -t .`; `dotnet build`; `dotnet test`. Record counts. If the .NET build fails, ask before continuing.
5. **Detection:** in parallel, run `python "<skill base directory>/scripts/py_checks.py" <repo root> [path]` and each module's Data Collection for the detected stacks. Missing tools, unreachable NuGet and py_checks `NOT-CHECKED` files go under Not checked.
6. **Reading:** quick mode reads flagged lines, entry points (`bot.py`, `main.py`, `Program.cs`) and config (`config.py`, `appsettings.json`). For "deep audit", first ask `Deep audit reads <n> files (~<lines> lines). Continue? [yes / no]`, then read every file in scope.
7. **Findings:** a hit becomes a finding only when reading confirms a Risk Indicator. Dead-code and comments findings are one per file.

| Module | Fixes |
|---|---|
| `modules/bugs.md` | `remediation/bugs-fixes.md` |
| `modules/error-handling.md` | `remediation/error-handling-fixes.md` |
| `modules/concurrency.md` | `remediation/concurrency-fixes.md` |
| `modules/performance.md` | `remediation/performance-fixes.md` |
| `modules/duplication.md` | `remediation/duplication-fixes.md` |
| `modules/dead-code.md` | `remediation/dead-code-fixes.md` |
| `modules/dependencies.md` | `remediation/dependencies-fixes.md` |
| `modules/comments.md` | `remediation/comments-fixes.md` |

## Scoring

| Factor | Values |
|---|---|
| Impact | outage, data loss or data exposure 1.0 · breaks 0.7 · degrades 0.4 · maintainability 0.1 |
| Likelihood | normal use 1.0 · conditions 0.6 · rare 0.3 · future change 0.1 |
| Reach | whole app 1.0 · one feature 0.7 · one user 0.4 |

Score = 10 × Impact × (0.5 + 0.5 × Likelihood) × (0.6 + 0.4 × Reach), one decimal. 9.0+ Critical · 7.0+ High · 4.0+ Medium · else Low. Vulnerable packages use the advisory: Critical 9.5, High 8.0, Moderate 5.5, Low 2.0.

## Report Format

```
═══════════════════════════════════════════════════
  CODE HEALTH AUDIT: <repo>
  <date>  |  Mode: <quick|deep>  |  Modules: 8  |  Findings: <n>
═══════════════════════════════════════════════════
BASELINE  tests <n> passed · flake8 blocking <n> · build <result>
EXECUTIVE SUMMARY
  Critical : <n>   High : <n>   Medium : <n>   Low : <n>
  Total risk score: <sum>
  Not checked: <tools or files, when any>

─── <BAND> ──────────────────────────────────────────
[<score>] <title>                               (<module>)
  <file>:<line>  <one-line description>
  Vector: <impact> / <likelihood> / <reach>
  Fix available: <yes|no>  <⚠ BEHAVIOR CHANGE when tagged>
```

Highest score first. Vulnerable packages show `Vector: advisory: <severity>`.

## Fix Loop

Work down the report; skip findings with `Fix available: no`.

```
[<score>] <title>                               (<module>)
  <file>:<line>
  Change: <one sentence>
  Files:  <every file the fix touches>
  Test:   <test id> (fails now, passes after)
Apply this fix? [yes / no / skip-severity / stop]
```

- `yes`: if Impact is 0.7+ and the baseline ran a test, write the test and confirm it fails (otherwise omit the Test line). Apply the remediation recipe, then run the test and `python -m py_compile <files>` or `dotnet build`.
- `no` skips the finding, `skip-severity` skips the rest of the band, `stop` goes to the summary.
- For a **⚠ BEHAVIOR CHANGE** fix, after `yes` ask `⚠ <what changes>. Confirm? [yes / no]`
- Failed check: undo that fix's own edits newest first, including its test, report the error, continue. Never retry, `git checkout` or `git stash`.
- Change only what the finding covers; read only needed lines; comments follow `modules/comments.md`; no helper scripts; never stage or commit.

## Verification

Rerun the baseline commands, then print:

```
Remediation complete.
  Fixed   : <n>  (risk reduced by <x> pts)
  Skipped : <n>  (still open: <scores>)
  Failed  : <n>  (see errors above)
  Tests   : <n> added · <n> passed (baseline <n>)
  Lint    : flake8 blocking <n> (baseline <n>)
  Build   : <result> (baseline <result>)
  Remaining risk score: <sum>
Changes are unstaged and uncommitted.
```

If a check that passed at baseline now fails, name the fixes that touched those files and ask `Undo those fixes? [yes / no]`. Note fixes without a test, or that no test suite exists.
