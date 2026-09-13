# Code Health Audit Skill: Design Spec

**Date:** 2026-09-13
**Status:** Design approved in chat; awaiting written-spec review

---

## 1. Overview

A periodic code audit for the user's Python (discord.py bots) and .NET (Blazor sites) repositories. When invoked, Claude records a baseline (lint, build, tests), runs eight detection modules, scores every finding on a 0 to 10 scale, presents a severity-sorted report in the network-audit layout, then walks the findings one at a time with `[yes / no / skip-severity / stop]`. Approved bug fixes come with a regression test when the repo has a test suite. Everything stays unstaged and uncommitted.

It follows the network-audit structure: a lean `SKILL.md` orchestrator, `modules/` that define what to collect and flag, and `remediation/` files that define how to fix each flagged item.

**Scope:** the current repository only, Python and .NET code only.

---

## 2. Evidence

The user asked for this six times (2026-06-22 to 2026-09-11), often sending the same prompt to several repos in the same minute:

| Date | Repos | Prompt |
|---|---|---|
| 2026-06-22 | usvotemap.dev | "Do a fully audit and code cleanup ... Keep all existing functionality." |
| 2026-08-07 | DiscordServerAudit, DiscordServerVote, DiscordVoiceDatabase | "Periodic code clean up, do a general audit and identify some possible sources of improvement. apply a light touch." |
| 2026-09-11 | DiscordServerAudit, DiscordVoiceDatabase | "Do a scan and keep the general structure the same, but suggest improvements please." |

**What those audits found** (the findings this skill must be able to reproduce):
- Latent bugs: a config summary that never printed (logging configured after an import-time `log.info`); `>history mystats` overflowing Discord's 1024-character field limit (HTTP 400); `VoiceRecorder.voice_client` first set in `start()` but read in `stop()`
- Silent failures: background loops logging `f"...: {e}"` without a traceback; `except Exception: pass`
- Concurrency: an 11.5 MB PCM flush running synchronously on the event loop (the bot went grey); missing locks around Whisper and playback
- Performance: an `import` inside a function called about 50 times a second per speaking user; `np.argsort` over every vector to take the top 10; a vector index that never shrank
- Duplication: embedding model and dimension defaults copied into three call sites; vote-row conversion open-coded in five functions
- Dead code: unused imports and an optional parameter no caller ever passed
- Dependencies: unpinned requirements (DiscordServerVote pins 0 of 3; DiscordServerAudit 3 of 7)

**Cost:** measured from the transcripts, counting each API response once, each audit used 17k to 30k output tokens and 1.4M to 5.2M context tokens. Both 2026-09-11 scans hit the usage limit while reading every source file, before producing a report, at 17k to 24k output and about 1.7M context tokens each, on a day when several other long sessions were running.

**User behavior:** on 2026-08-07 Claude applied fixes directly and the user accepted them; on 2026-09-11 the user answered a 14-item list with "Make all changes, do not commit anything"; on 2026-06-22 the user deferred two optional cleanups.

---

## 3. Decisions

| Decision | Choice |
|---|---|
| Structure | Self-contained, network-audit layout; no references to other skills' files |
| Detection | The skill's own modules (not a wrapper around the built-in `/code-review`) |
| Depth | Quick by default; "deep audit" reads every in-scope file |
| Applying fixes | One finding at a time: `[yes / no / skip-severity / stop]` |
| Scoring | 0 to 10 from weighted factors; fix risk shown as a ⚠ marker, not scored |
| Tests | One regression test per approved bug fix when a test suite exists; no "missing test" findings |
| Stacks | Python and .NET, detected per repo |
| House rules | Light touch, keep structure, never stage or commit, minimal comments, no leftover scripts |
| Spec location | `code-health-audit/DESIGN.md`, plan in `code-health-audit/PLAN.md` |

---

## 4. Repository Structure

```
~/.claude/skills/code-health-audit/
  SKILL.md                      orchestrator: scope, stacks, baseline, module order, scoring, report, loop, verification, edge cases
  DESIGN.md                     this spec (not read at runtime)
  PLAN.md                       implementation plan (not read at runtime)
  modules/
    bugs.md
    error-handling.md
    concurrency.md
    performance.md
    duplication.md
    dead-code.md
    dependencies.md
    comments.md
  remediation/
    bugs-fixes.md
    error-handling-fixes.md
    concurrency-fixes.md
    performance-fixes.md
    duplication-fixes.md
    dead-code-fixes.md
    dependencies-fixes.md
    comments-fixes.md
  scripts/
    py_checks.py                standard-library Python checks (section 7)
    test_py_checks.py           unittest suite for py_checks.py
```

Each module file has the same parts: **Data Collection** (Python and .NET subsections, commands to run in parallel), **Risk Indicators** (condition, factor values, score), and **Analysis Notes** (what to read and how to judge candidates). Each remediation file has one entry per finding type: the fix recipe, a `⚠ BEHAVIOR CHANGE` tag where it applies, and a **Verify** step.

`SKILL.md` references only `modules/`, `remediation/` and `scripts/`. It never references `DESIGN.md` or `PLAN.md`.

---

## 5. Run Sequence

### 5.1 Trigger and arguments

- Description (frontmatter): `Use when asked to run a code audit, code health check, code cleanup review, or a scan for improvements on the current repository`
- "deep audit" (or `deep`) selects deep mode
- A path argument limits scope to that path

### 5.2 Scope

Every tracked file from `git ls-files`, or the named path. Excluded from findings: `tests/` (and other test projects), `.specify/`, `wwwroot/lib/`, `node_modules/`, `Migrations/`, `.venv/`, `venv/`, and generated or minified files. Tests are still run for verification.

### 5.3 Stack detection

- Python: `requirements*.txt`, `pyproject.toml`, or tracked `.py` files
- .NET: `*.csproj` or `*.sln`/`*.slnx`
- Both present: run both. Neither: reply `No Python or .NET code found. This audit covers those two stacks.` and stop.

### 5.4 Baseline

Before any detection, run the repo's own checks and record the numbers for the BASELINE line.

- Prefer the commands in the repo's CI workflow (`.github/workflows/*.yml`), run in `python -m` form so the pre-approved permissions match. Current repos use `python -m flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics`, `python -m unittest discover -s tests -t .` or `python -m pytest tests -q`, and `dotnet build` / `dotnet test`.
- Without a workflow: flake8 blocking selection; pytest when `tests/` contains `conftest.py` or imports pytest, otherwise unittest discovery; `dotnet build` plus `dotnet test` when a test project exists.

### 5.5 Detection

Run every module's data-collection commands for the detected stacks in parallel, including one `py_checks.py` run whose output is split by module.

### 5.6 Reading

- **Quick:** read only the flagged regions, plus entry points (`bot.py`, `main.py`, `Program.cs`) and config modules (`config.py`, `appsettings.json`).
- **Deep:** first reply `Deep audit reads <n> files (~<lines> lines). Continue? [yes / no]`, then read every in-scope file before judging.

### 5.7 Scoring, report, loop, verification

Sections 8 to 11.

---

## 6. Modules

Source tags: **[flake8]** lint rule, **[ast]** `py_checks.py`, **[build]** `dotnet build` warning, **[search]** the Grep tool, **[read]** Claude's judgment while reading.

| # | Module | Python | .NET |
|---|---|---|---|
| 1 | bugs | Attributes first set outside `__init__` [ast]; import-time side effects [ast]; mutable default arguments [ast]; text sent to Discord without a length check [search+read]; `datetime.now()`/`utcnow()` without a timezone [search] | Nullable warnings CS86xx [build]; JS interop inside `OnInitialized`/`OnInitializedAsync` [search]; `+=` event subscriptions in components that never dispose [search+read]; `new HttpClient(` [search] |
| 2 | error-handling | Bare `except` E722 [flake8]; broad `except` whose body only passes or continues, or logs without a traceback [ast]; `create_task` results discarded [ast] | Empty `catch {}`, catch-all blocks that neither log nor rethrow [search]; `async void` outside event handlers [search] |
| 3 | concurrency | Blocking calls inside `async def`, including one level into repo functions that block [ast]; shared state mutated by several handlers [read] | `.Result`, `.Wait()`, `GetAwaiter().GetResult()` [search]; CS4014 unawaited calls [build]; writable `static` fields in services and components [search+read] |
| 4 | performance | Imports inside functions, judged by call frequency [ast]; database calls inside loops [ast]; grows-only containers [ast+read]; full sorts to take the top few [search] | EF queries inside loops [search+read]; `.ToList()` before filtering [search] |
| 5 | duplication | One config key read with its default copied in several call sites [ast]; near-identical blocks [read] | Near-identical blocks [read] |
| 6 | dead-code | F401, F811, F841 [flake8]; optional parameters no caller passes [ast]; functions never referenced [ast+search] | CS0168, CS0219, CS0162 [build]; private members never referenced [search] |
| 7 | dependencies | Requirements without `==` pins; third-party imports missing from requirements [ast] | `dotnet list package --vulnerable --include-transitive` |
| 8 | comments | Own copy of the trim-comments rules | Same |

**Grouping:** dead-code and comments findings are grouped one per file (for example `cogs/polls.py: 17 banners, 1 em-dash`). flake8 hits and build warnings are grouped per file and rule. All other findings are one per problem.

**Discord limits** used by the bugs module, checked at `add_field(`, `Embed(`, `set_footer(`, `.send(`, `.edit(` and `SelectOption(` calls whose text is built at runtime (verify the values against Discord's developer documentation during implementation): message content 2000; embed title 256, description 4096, 25 fields, field name 256, field value 1024, footer 2048, 6000 total characters, 10 embeds per message; select menus 25 options with labels, values and descriptions up to 100; button labels 80.

**Blazor notes** for the bugs and concurrency modules: JS interop is not available during prerendering, so it belongs in `OnAfterRenderAsync(firstRender)`; static fields on Blazor Server are shared by every user and circuit, so writable static state needs a reason (usvotemap's `static SemaphoreSlim _gate` is intentional).

---

## 7. py_checks.py

Standard library only (`ast`, `tokenize`, `sys.stdlib_module_names`), Python 3.10 compatible.

**Invocation:** `python <skill-dir>/scripts/py_checks.py <repo-root> [path ...]`. It lists tracked `.py` files with `git ls-files` and applies the section 5.2 exclusions.

**Output:** one tab-separated line per hit, then a summary line. Exit code 0 when it ran, 1 only when the script itself failed.
```
<module>	<CHECK-ID>	<path>:<line>	<detail>
summary	checked=<n> hits=<m> not_checked=<k>
```

| Module | Check ID | Flags |
|---|---|---|
| bugs | `ATTR-OUTSIDE-INIT` | `self.x` assigned in a method other than `__init__`, never assigned in `__init__` or the class body, and read in another method |
| bugs | `IMPORT-SIDE-EFFECT` | Module-level call statements in non-entry modules (entry: `bot.py`, `main.py`, `app.py`, `__main__.py`, or any file with `if __name__ == "__main__"`) |
| bugs | `MUTABLE-DEFAULT` | Default argument that is a list, dict or set literal, or `list()`/`dict()`/`set()` |
| error-handling | `EXCEPT-SWALLOW` | Bare `except`, `except Exception` or `except BaseException` whose body is only `pass`, `continue`, `...` or `return None` |
| error-handling | `EXCEPT-NO-TRACEBACK` | A broad handler that logs or prints the exception without `exc_info=True`, `.exception(`, or a re-raise |
| error-handling | `TASK-UNSTORED` | `create_task(...)` used as a bare expression statement |
| concurrency | `BLOCKING-IN-ASYNC` | Inside `async def`: `time.sleep`, `open`, `sqlite3.connect`, `requests.*`, `urllib.request.urlopen`, `subprocess.*`, `os.remove`/`unlink`/`rmdir`/`mkdir`/`makedirs`/`listdir`/`scandir`/`walk`/`rename`/`replace`, `shutil.*`, and `Path.read_text`/`write_text`/`read_bytes`/`write_bytes`/`unlink`/`mkdir`/`rmdir`/`iterdir`; also calls to repo-defined sync functions that contain those calls |
| performance | `IMPORT-IN-FUNCTION` | `import` inside a function body, except under `if TYPE_CHECKING` or `try/except ImportError` |
| performance | `DB-IN-LOOP` | Inside `for`/`while`: calls named `execute`, `executemany`, `fetchone`, `fetchall`, `commit`, or awaited calls on a receiver named `db`, `database`, `conn`, `connection`, `cursor` or `session` |
| performance | `GROWS-ONLY` | A module-level or `self.` container that gains items (`append`, `add`, `[k] =`, `update`, `setdefault`) and is never shrunk or reassigned in that module |
| duplication | `DUP-CONFIG-DEFAULT` | The same string key passed with a default to `.get(...)`, `os.getenv(...)` or `os.environ.get(...)` in two or more call sites |
| dead-code | `UNUSED-OPTIONAL-PARAM` | A parameter with a default that no call site in the repo passes by keyword or position |
| dead-code | `UNREFERENCED-FUNC` | A function or method name referenced nowhere else, excluding dunder methods, `setup`, `on_*` listeners, `cog_*` hooks, and anything decorated (commands, `tasks.loop`, `ui.button`) |
| dependencies | `UNPINNED-DEP` | A requirements line without `==` or `===` (one hit per file, listing the names) |
| dependencies | `UNDECLARED-DEP` | A third-party top-level import not matching any requirement, after an import-to-package map (`discord`: discord.py, `dotenv`: python-dotenv, `yaml`: PyYAML, `PIL`: Pillow, `nacl`: PyNaCl, `google.genai`: google-genai, `whisper`: openai-whisper) |
| (meta) | `NOT-CHECKED` | A file that failed to parse with the local Python |

Every hit is a candidate: it becomes a finding only after Claude reads the flagged code (section 5.6). For example, `ATTR-OUTSIDE-INIT` on an attribute set in `setup_hook` is normal in a discord.py `Bot` subclass.

---

## 8. Scoring

### 8.1 Factors

| Factor | Value | Weight |
|---|---|---|
| **Impact** | Outage, data loss or data exposure | 1.0 |
| | A feature breaks or gives wrong results | 0.7 |
| | Errors hidden or behavior degraded | 0.4 |
| | Only harder to maintain | 0.1 |
| **Likelihood** | Normal use | 1.0 |
| | Specific but realistic conditions (busy users, large data, a restart) | 0.6 |
| | Rare edge case | 0.3 |
| | Only after a future code change | 0.1 |
| **Reach** | The whole app | 1.0 |
| | One feature, page or command | 0.7 |
| | One user or request | 0.4 |

### 8.2 Formula and bands

`Score = 10 × Impact × (0.5 + 0.5 × Likelihood) × (0.6 + 0.4 × Reach)`, rounded to one decimal.

Bands: 9.0 to 10.0 Critical · 7.0 to 8.9 High · 4.0 to 6.9 Medium · 0.1 to 3.9 Low.

Impact caps the score: maintainability findings reach at most 1.0, degraded behavior 4.0, broken features 7.0.

**Vulnerable packages** use the advisory severity instead of the formula: Critical 9.5, High 8.0, Moderate 5.5, Low 2.0.

### 8.3 Reference scores

| Finding | Vector | Score |
|---|---|---|
| Audio flush blocks the event loop | outage / normal use / whole app | 10.0 Critical |
| Static cache on Blazor Server leaks between users (example) | data exposure / conditions / whole app | 8.0 High |
| Unpinned requirements | outage / rare / whole app | 6.5 Medium |
| `mystats` over Discord's 1024-character field limit | breaks / conditions / one user | 4.3 Medium |
| Import on every audio frame | degrades / normal use / whole app | 4.0 Medium |
| Duplicated embedding defaults | breaks / future change / one feature | 3.4 Low |
| Unused imports in a file | maintainability / normal use / one user | 0.8 Low |

### 8.4 Behavior change marker

`⚠ BEHAVIOR CHANGE` marks any fix that changes observable behavior rather than only code structure (for example, making a parameter required, raising where code used to swallow, changing query results). It does not affect the score.

---

## 9. Report Format

Findings sorted by score descending, grouped by band.

```
═══════════════════════════════════════════════════
  CODE HEALTH AUDIT: <repo>
  <date>  |  Mode: quick|deep  |  Modules: 8  |  Findings: <n>
═══════════════════════════════════════════════════
BASELINE  tests <n> passed · flake8 blocking <n> · build <ok|n warnings|n/a>
EXECUTIVE SUMMARY
  Critical : <n>   High : <n>   Medium : <n>   Low : <n>
  Total risk score: <sum>
  Not checked: <tools or files skipped, when any>

─── CRITICAL ────────────────────────────────────────
[10.0] Blocking audio flush in async rotation     (concurrency)
  recording/recorder.py:214  flush_to_disk writes ~11.5 MB on the event loop.
  Vector: outage / normal use / whole app
  Fix available: yes  ⚠ BEHAVIOR CHANGE
```

---

## 10. Fix Loop

Work through findings from the highest score down. Findings reported with `Fix available: no` stay in the report and are skipped by the loop.

### 10.1 Prompt

```
[4.3] mystats field can exceed 1024 characters            (bugs)
  cogs/history.py:84
  Change: send the field through embeds.add_chunked_field, which already exists
  Files:  cogs/history.py, tests/test_history.py
  Test:   tests/test_history.py::test_mystats_long_history_splits (fails now, passes after)
Apply this fix? [yes / no / skip-severity / stop]
```

| Input | Behavior |
|---|---|
| `yes` | Write the test (when section 10.3 applies) and confirm it fails; make the change from the module's remediation recipe; run that test plus a compile or build check |
| `no` | Skip this finding |
| `skip-severity` | Skip every remaining finding in this band |
| `stop` | End the loop and show the summary |

### 10.2 Behavior change confirmation

For `⚠ BEHAVIOR CHANGE` fixes, after `yes`: `⚠ <what changes, in one sentence>. Confirm? [yes / no]`

### 10.3 Regression tests

- Applies when the finding's Impact is 0.7 or 1.0 and the repo has a test suite (the baseline test command ran at least one test)
- Uses the repo's framework and naming: `unittest` (DiscordServerAudit, DiscordServerVote), `pytest` (DiscordVoiceDatabase), xUnit for .NET data code, Playwright for .NET UI
- The test must fail before the change and pass after it
- When a meaningful test would need a live Discord gateway, network service or external server, apply the fix without a test and say so in the summary

### 10.4 Failed fixes

When a fix's check fails, undo that fix's own edits (the inverse of each edit, newest first, including any new test), report the error, and continue with the next finding. Never retry. Never use `git checkout` or `git stash`, which would also remove earlier approved fixes.

### 10.5 Light touch

- Change only what the finding covers; no drive-by refactors
- New or edited comments follow `modules/comments.md`
- Read only the lines a fix needs
- Never stage or commit; leave no helper scripts in the repo

---

## 11. Verification and Summary

After the loop, rerun the baseline commands and compare.

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

When a test or check that passed at baseline now fails, list it under the summary with the fixes that touched the same files, and ask `Undo those fixes? [yes / no]`. The summary notes fixes applied without a test and, when the repo has no test suite, that fixes were checked by compile or build only.

---

## 12. Edge Cases

| Situation | Behavior |
|---|---|
| Uncommitted changes at start | `You have uncommitted changes in <n> files; fixes will mix with them in the diff. Continue? [yes / no]` |
| Baseline already failing | Shown on the BASELINE line; pre-existing failures are not attributed to fixes |
| .NET build broken at baseline | Ask before continuing, since fixes cannot be build-checked |
| Missing tool (`flake8`, `dotnet`) or NuGet unreachable | Skip those checks, list them under "Not checked"; never install anything |
| No test suite | No regression tests; summary says fixes were compile-checked only |
| `py_checks.py` cannot parse a file | Listed under "Not checked" |
| Neither stack found | `No Python or .NET code found. This audit covers those two stacks.` and stop |
| Deep audit requested | Size confirmation first (section 5.6) |
| Zero findings | Report with `Findings: 0` and the baseline; no loop |
| One fix spans several files | Allowed; every file is listed in the prompt |
| Hundreds of lint hits | Grouped per file and rule |

---

## 13. Permissions

`SKILL.md` frontmatter `allowed-tools`:
- `Bash(git status *)`, `Bash(git diff *)`, `Bash(git ls-files *)`
- `Bash(python -m flake8 *)`, `Bash(python -m py_compile *)`, `Bash(python -m pytest *)`, `Bash(python -m unittest *)`
- `Bash(dotnet build *)`, `Bash(dotnet test *)`, `Bash(dotnet list package *)`

`Bash(python *py_checks.py *)` is added too if Claude Code's permission patterns accept a wildcard before the script name (checked during implementation); otherwise that one command prompts once per audit. File edits keep the user's normal approval. Text searches use the Grep tool, so they behave the same under Git Bash and PowerShell. `SKILL.md` stays lean (under about 800 words), with module detail in `modules/` and fix detail in `remediation/`.

---

## 14. Testing Plan

1. **py_checks.py unit tests first** (`scripts/test_py_checks.py`, `unittest`): a fixture per check ID that must be flagged, and look-alikes that must not be (a call wrapped in `asyncio.to_thread`, a handler using `exc_info=True`, an attribute set in `__init__`, a narrow `except discord.HTTPException: pass`, an unparseable file reported as `NOT-CHECKED`).
2. **Replay audits** on scratch clones checked out at pre-audit commits, never touching the user's repos:

   | Replay | Known answers |
   |---|---|
   | DiscordServerVote before the 2026-08-07 audit | Config summary never printed; `mystats` field overflow; vote-row conversion duplicated in five functions; unused imports (F401) |
   | DiscordVoiceDatabase before the 2026-09-11 audit | Blocking audio flush (Critical); unpinned dependencies. Missing locks around Whisper and playback are recorded but not required, since only reading can find them |
   | bytecraft.us before the MimeKit 4.15.1 update | Vulnerable MimeKit (or the NuGet-unreachable path) |

   Pass mark: known answers caught. Quick-mode token use is recorded and compared with the 2026-09-11 runs.
3. **Loop run** on one replay, answering `yes` (bug with a test that fails then passes), `no`, a `⚠` confirmation, `skip-severity`, then `stop`; one fix deliberately made to fail its check to exercise the undo.
4. **Automatic checks:** every `[score]` recomputed from its vector with the formula; files for skipped findings byte-identical; summary numbers matching what happened.
5. **User check** in a fresh session: "code health audit" in a real repo.

---

## 15. Out of Scope

- Languages other than Python and .NET (JavaScript, CSS and PowerShell files are not audited)
- "Missing test" findings and coverage measurement
- Installing tools or packages (so no Python vulnerability scan, since `pip-audit` is not installed)
- Committing, staging, or opening pull requests
- Report persistence and diffing between runs
- Gateway reconnect and Scheduled Task checks (the dropped discord-bot-reliability skill; Scheduled Task settings belong to deploy-host-audit)
- Secrets (secrets-audit), README drift (readme-sync), site quality and SEO (site-audit)
