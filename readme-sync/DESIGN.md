# README Sync Skill: Design Spec

**Date:** 2026-09-13
**Status:** Design approved in chat 2026-09-13; written spec approved 2026-09-14

---

## 1. Overview

A skill that brings a repository's `README.md` back in line with its code for the user's Python (discord.py bots) and .NET (Blazor sites) repositories. A standard-library script extracts facts from the code and compares them with the README; Claude verifies prose claims by reading only the code they depend on. The result is one drift list grouped by README section, one approval (`[yes / no / all except <numbers>]`), then edits that fix wrong claims, fill missing items and add missing standard sections in the README's existing style. The skill verifies its edits and leaves everything unstaged and uncommitted.

**Scope:** the repository-root `README.md` of the current repository, Python and .NET projects only.

---

## 2. Evidence

The user sent the same prompt to four repositories within one minute on 2026-09-12: "Scan the project and update the readme to account for current code base state."

| Repo | Responses | Output tokens | Context tokens | Outcome |
|---|---|---|---|---|
| DiscordServerAudit | 37 | 114k | 8.4M | Finished after a "Try again"; committed as `5fe06cb` |
| DiscordVoiceDatabase | 24 | 94k | 4.4M | Hit the usage limit, resumed; committed as `2403ab4` |
| bytecraft.us | 24 | 56k | 3.4M | Hit the session limit before finishing; committed later as `1f098e6` |
| samelhag.dev | 29 | 54k | 5.1M | Finished; committed as `56f40c7` |

Tokens count each API response once. Each session read 19 to 58 files. The user committed all four rewrites the same day.

**What those sessions found** (the drift this skill must catch):
- Setup that would fail: the bot token documented in `config.yaml` while the code only reads the `DiscordServerAudit_TOKEN` env var; no step to sync slash commands, which DiscordVoiceDatabase never does on its own
- Renamed or undocumented commands: `/favoriteslist` renamed to `/favoritesplay`; 82 commands in DiscordServerAudit
- Configuration drift: missing or renamed env vars (`WHISPER_MODEL`, `LOG_LEVEL`), changed config values, a claim that any setting can be overridden by an env var when only 11 can
- Wrong access claims: "all commands require the admin role" while 13 commands are open to everyone; Manage Server missing from the invite permissions
- Stale versions and hosting: `MudBlazor 8.0` while the project uses 9.6.0; "Azure Ready" while the workflow deploys to IIS on a self-hosted runner
- Unverifiable claims: performance numbers copied from an "expected improvements" table that were never measured
- Wrong links: a LinkedIn URL that did not match the site; a placeholder clone URL
- Features present in code but absent from the README

**Not yet synced:** DiscordServerVote's README has not changed since before 2026-09-01, and usvotemap.dev has no README.

---

## 3. Decisions

| Decision | Choice |
|---|---|
| Run shape | Drift list grouped by section, then one approval `[yes / no / all except <numbers>]` |
| Edit scope | Fix wrong claims, fill missing items, and add missing standard sections; keep the README's structure, order and style |
| Thoroughness | Quick by default: every mechanical fact, plus prose claims only in sections whose source files changed since the README's last commit. "deep readme sync" checks every claim after a size confirmation |
| Documented commands | Run the README's build and test commands; never run install, run, Docker or deploy commands |
| Detection | Standard-library fact script plus one guide per standard section; no generated marker blocks |
| Structure | Self-contained, in the code-health-audit layout without scoring; no references to other skills' files |
| Stacks | Python and .NET, detected per repo |
| House rules | Never stage or commit; never write secret values into the README; leave no helper scripts in the repo |
| Spec location | `readme-sync/DESIGN.md`, plan in `readme-sync/PLAN.md` |

---

## 4. Repository Structure

```
~/.claude/skills/readme-sync/
  SKILL.md                 orchestrator: scope, stacks, mode, facts, claims, commands, drift list, approval, edits, verification, edge cases
  DESIGN.md                this spec (not read at runtime)
  PLAN.md                  implementation plan (not read at runtime)
  sections/
    features.md
    setup.md
    configuration.md
    commands.md
    routes.md
    deployment.md
    development.md
    license.md
  scripts/
    readme_facts.py        standard-library fact extraction and README comparison (section 6)
    test_readme_facts.py   unittest suite for readme_facts.py
```

Each section guide has the same three parts: **Facts** (the script check IDs that belong to the section), **Claims** (prose to verify and which code to read for it) and **Filling** (what a new section contains for a Python bot and for a Blazor site). `SKILL.md` references only `sections/` and `scripts/`, never `DESIGN.md` or `PLAN.md`, and stays under about 800 words.

---

## 5. Run Sequence

### 5.1 Trigger and arguments

- Description (frontmatter): `Use when asked to update, sync, refresh, or check a repository's README against its current code, including requests to scan a project and update its readme`
- "deep readme sync" (or `deep`) selects deep mode

### 5.2 Steps

1. **Scope and stacks:** the repository-root `README.md`. Python when `requirements*.txt`, `pyproject.toml` or tracked `.py` files exist; .NET when `*.csproj`, `*.sln` or `*.slnx` exist. Neither: reply `No Python or .NET project found. readme-sync covers those two stacks.` and stop.
2. **Working tree:** if `git status --short -- README.md` shows changes, ask `README.md has uncommitted changes; the sync edits will mix with them. Continue? [yes / no]`
3. **Facts:** run `python "<skill base directory>/scripts/readme_facts.py" <repo root> --since auto` in quick mode, or without `--since` in deep mode. Both print the `SINCE` line used in the drift list header.
4. **Claims:** quick mode reads the README sections named by `CHANGED` lines and the code those lines name. Deep mode first asks `Deep sync reads <n> files (~<lines> lines). Continue? [yes / no]`, then checks every claim in every section.
5. **Commands:** run the build and test commands the README documents (section 9.2). A command that is itself wrong becomes a drift item; a missing tool or a failure caused by broken code goes under Not checked.
6. **Drift list:** grouped by section with numbered items, ending in `Apply these README changes? [yes / no / all except <numbers>]` (section 8).
7. **Edit:** apply the approved items under the editing rules (section 7.3).
8. **Verify:** rerun the script and any command the edit changed, then print the summary (section 9).

---

## 6. readme_facts.py

Standard library only (`ast`, `json`, `re`, `subprocess`), Python 3.10 compatible. Every flagged item is a candidate that Claude confirms before it reaches the drift list; for example, an env var read by a third-party library is not stale.

**Invocation:** `python <skill-dir>/scripts/readme_facts.py <repo-root> [--since auto]`. It lists tracked files with `git ls-files`, skips `.venv/`, `venv/`, `node_modules/`, `bin/`, `obj/`, `.specify/`, `.claude/`, `__pycache__/` and `wwwroot/lib/`, and reads `README.md` when it exists.

**Output:** one tab-separated line per item, then a summary line. Exit code 0 when it ran, 1 only when the script itself failed.
```
<section>\t<CHECK-ID>\t<location>\t<detail>
summary\tfacts=<n> drift=<m> not_checked=<k>
```

- `<section>` is one of `features`, `setup`, `configuration`, `commands`, `routes`, `deployment`, `development`, `license`, `meta`, printed in that order. Code-side items use the section the fact belongs to; README-side items use the standard section of the README heading that contains the line, and lines under unmatched headings map to `features`. `SECTION-MISSING` uses the missing section's name.
- `<location>` is `README.md:<line>` for README-side items and `<path>:<line>` for code-side items.
- `SINCE` and `CHANGED` lines (section 6.2) are context, not drift, and do not count toward `drift=`.

### 6.1 Checks

| Section | Check ID | Flags |
|---|---|---|
| commands | `CMD-UNDOCUMENTED` | A discord.py command defined in code (`commands.command`, `commands.hybrid_command`, `commands.group`, `commands.hybrid_group`, `<group>.command`, `app_commands.command`) whose name, including any group name, appears in no README command token |
| commands | `CMD-STALE` | A README command token that matches no command in code. Command tokens are backticked text, or whole lines in code blocks, starting with `!`, `>` or `/` followed by a lowercase name, compared by name because prefixes are not always static (`">"`, an env default, a config key). Placeholder names (`command`, `cmd`, `name`, `commandname`, `subcommand`) are skipped, and `help` counts as a command unless the code sets `help_command=None`. In repos without Python, `/` tokens are routes instead; in repos with both stacks, a `/` token is stale only when it matches neither a command nor a route |
| configuration | `ENV-UNDOCUMENTED` | An env var read by code (`os.getenv`, `os.environ.get`, `os.environ[...]`, `Environment.GetEnvironmentVariable`, `Configuration["..."]` with an all-caps name) that the README never mentions |
| configuration | `ENV-STALE` | A README env-var token (a word with an underscore followed by capitals, such as `DiscordVoiceDatabase_LOG_LEVEL` or `OTEL_EXPORTER_OTLP_ENDPOINT`) that appears in no tracked code, workflow, config, `.env.example`, Dockerfile or docker-compose file. Placeholders (`YOUR_*`, `MY_*`, `EXAMPLE_*`, `XXX_*`, `*_HERE`, anything containing `PLACEHOLDER`) are skipped |
| configuration | `CONFIG-KEY-UNDOCUMENTED` | Leaf keys of a `config.yaml` (or `config.<name>.yaml`) or `appsettings*.json` file that the README never mentions, grouped into one item per file that lists every missing key, reported only when the README already documents at least one key. The ASP.NET template keys `Logging`, `AllowedHosts` and `DetailedErrors` are skipped |
| configuration | `CONFIG-KEY-STALE` | A backticked dotted (`factcheck.semantic.model`) or colon (`bytecraftSMTP:SmtpHost`) key that no config file contains; a key shown in a README ` ```yaml ` or ` ```json ` code block that the matching config file lacks (DiscordServerAudit's example showed `bot.token`); or a backticked single identifier on a README line that also names a config file or a backticked top-level config section, when that file has no key with that name and the identifier is not a name used in code. Example line: The rest of the SMTP config (`Host`, `Port`, `EnableSsl`) lives in `appsettings.json` |
| routes | `ROUTE-UNDOCUMENTED` | An `@page "..."` route, or a minimal API route mapped in a `.cs` file, that the README never mentions (.NET repos). `/`, `/error` and `/not-found` are not reported |
| routes | `ROUTE-STALE` | A backticked `/path` or a Markdown link target starting with `/` in the README that matches no route (route parameters such as `{slug}` match any segment) and is not a tracked path (.NET repos) |
| setup | `VERSION-MISMATCH` | A README mention of a runtime or package with a version (`.NET 10`, `MudBlazor 9.6`, `Python 3.12`, `discord.py 2.7`) that differs, at the README's precision, from the csproj `TargetFramework` or `PackageReference`, SDK attribute, `requirements*.txt` pin, `.python-version`, workflow `python-version` or Dockerfile `FROM` |
| development | `PATH-STALE` | A backticked repository path (contains `/` or ends in a known extension) or a relative Markdown link target that is not a tracked file or directory. A bare file name matches a tracked file of that name in any folder. Skipped: package names from requirements or `PackageReference`, `.env` names, `.log` and `.db` runtime files, paths `git check-ignore` reports as ignored, and `appsettings.<Environment>.json` when `appsettings.json` exists |
| deployment | `SECRET-UNDOCUMENTED` | A workflow `secrets.*` name the README never mentions, reported only when the README has a deployment section |
| deployment | `SECRET-STALE` | A secret name listed in the README's deployment section that no workflow uses |
| license | `LICENSE-MISMATCH` | A license named in the README (MIT, Apache 2.0, GPL, and so on) that differs from the first line of the `LICENSE` file |
| license | `REPO-URL-MISMATCH` | A GitHub URL for this repository in the README, including placeholders like `your-org`, that differs from `git remote get-url origin` |
| (any) | `SECTION-MISSING` | A standard section for the detected stack with no matching heading (section 7.1) |
| meta | `NOT-CHECKED` | A file that could not be parsed |

`config.yaml` is read with a small indentation-based parser for block mappings (comments and list items skipped), since the standard library has no YAML module.

### 6.2 Change window

The script always finds the last commit that touched `README.md` and prints one `SINCE` line; with `--since auto` it also prints a `CHANGED` line for every tracked file changed since that commit:
```
meta\tSINCE\t<short sha>\t<date> +<added> -<removed> README lines, <k> files changed since
<section>\tCHANGED\t<path>\t<why>
```
Changed files map to sections: files defining commands to `commands`; files reading env vars or config, `config.yaml`, `appsettings*.json` and `.env.example` to `configuration`; `.razor` files with `@page` and `Program.cs` route mapping to `routes`; `.github/workflows/*`, `Dockerfile` and `docker-compose*.yml` to `deployment`; dependency files, `.python-version` and entry points (`bot.py`, `main.py`, `Program.cs`) to `setup`; test files and test projects to `development`; `LICENSE*` to `license`; any other tracked code file to `features`. When `README.md` does not exist, the script prints `meta\tSINCE\tnone\tREADME.md does not exist` and SKILL.md follows the creation path (section 10). When it exists but has no commit, the script prints `meta\tSINCE\tnone\tREADME.md has no commit` and SKILL.md switches to deep mode.

---

## 7. Section Guides and Editing Rules

### 7.1 Standard sections

| Section | Python bot | Blazor site | Present when a heading contains |
|---|---|---|---|
| Features | yes | yes | features, overview |
| Setup | install, create the Discord application with intents and invite permissions, configure, run, sync slash commands when the bot does not sync on its own | prerequisites, configure, run locally | setup, getting started, installation, quick start, requirements, prerequisites |
| Configuration | env vars, config keys | appsettings, env vars, user secrets | configuration, config, environment, settings |
| Commands | when the code defines commands | no | commands, usage |
| Routes | no | when the code has routes other than `/`, `/error` and `/not-found` | routes, pages |
| Deployment | yes | yes | deploy, deployment, hosting |
| Development | tests, lint, project structure | build, test, project layout | development, contributing, contributors, testing, structure, layout |
| License | yes | yes | license |

Heading matching is case-insensitive, matches whole words and ignores emoji. Only top-level headings count: the lowest heading level used after the title (usually `##`). Subheadings belong to the section above them, so "### 3. Configure the environment" under Setup stays in Setup. A `SECTION-MISSING` candidate is dropped when another heading already covers the content; for example, bytecraft.us's "Contact form" section covers its SMTP configuration.

### 7.2 Claims each guide covers

| Guide | Claims to verify, and the code to read |
|---|---|
| features.md | Feature and behavior claims against the code they describe; numbers (limits, timings, performance) must come from code or a measurement the repo records, otherwise they are removed |
| setup.md | Where the token or credentials come from; required intents (`intents.<name> = True`) and invite permissions against permission checks in code; the run command against the entry point; the slash-command sync step when `setup_hook` never calls `tree.sync()`; prerequisites against `TargetFramework` and `.python-version` |
| configuration.md | Defaults, required or optional, and "any setting can be overridden" style claims against the config loader |
| commands.md | Access claims ("admin only", "everyone") against `has_permissions`, `is_owner` and role checks; command descriptions against `description=` and behavior |
| routes.md | Each route's page and purpose against its component |
| deployment.md | Hosting claims against the workflows (self-hosted runner, IIS under `C:\inetpub\sites`, Scheduled Task under `C:\apps`); secrets and deploy steps |
| development.md | Test framework and test command against `tests/` or the test project; project structure trees against tracked directories |
| license.md | License name; site, profile and repository links against the values the code uses |

### 7.3 Editing rules

- Change only approved items; leave every other word as it is.
- **Fix:** correct the wrong fact inside its own sentence, table row or list item.
- **Fill:** add missing items to the existing list or table in its format and order. Command descriptions come from `description=` or the docstring; env var defaults come from the code.
- **Add:** a missing standard section goes at its standard position (the order in section 7.1) relative to existing headings, using the README's heading level, heading style (including emoji headings) and list style.
- **Remove:** claims that cannot be verified are removed rather than reworded with invented values.
- Never write secret values: env var and secret names only, never values from `appsettings*.json`, `.env` files or workflows.

---

## 8. Drift List and Approval

```
README SYNC: <repo>
  Mode: <quick|deep>  |  README last changed <date> (<short sha>), <k> files changed since
  Checked: <n> facts · <command> (<ok|failed>)
  Not checked: <tools, files or commands, when any>

<Section>
  <n>. <Kind>  <what is wrong or missing, with the fix>   <evidence location>

Apply these README changes? [yes / no / all except <numbers>]
```

- Item kinds: `Missing`, `Stale`, `Wrong` (a prose claim that contradicts the code), `Mismatch` (a version), `Failing command` (the documented command itself is wrong), `Add` (a missing standard section).
- Numbering runs across the whole list so `all except 3, 7` is unambiguous.
- In quick mode, when the README's last commit changed 5 lines or fewer, the header adds: `Last README change was small; older drift may remain. Say "deep readme sync" to check every claim.`
- Zero drift: print `README matches the code.` with the header, and no prompt.

Example:
```
Commands
  2. Stale  `/favoriteslist` no longer exists; the command is /favoritesplay   cogs/voicedatabase.py:1650
```

---

## 9. Verification and Summary

### 9.1 After the edits

Rerun `readme_facts.py` (same mode) and any documented command the edit changed, then print:
```
README updated.
  Applied : <n> of <m> (left out: <numbers>)
  Facts   : drift <before> → <after>
  Commands: <command> (<result>)
  Diff    : README.md +<added> −<removed>
Changes are unstaged and uncommitted.
```
Only left-out items may remain in the rerun. An approved item that still appears is named under the summary as not fixed; the skill does not retry.

### 9.2 Documented commands

Commands inside README code blocks or backticks run only when they are build, test or lint commands: `dotnet build`, `dotnet test`, `python -m unittest ...`, `python -m pytest ...`, `pytest ...`, `python -m flake8 ...`, `flake8 ...`. Bare `pytest` and `flake8` run in `python -m` form. Install (`pip install`, `dotnet restore` on its own), run (`python bot.py`, `dotnet run`), Docker and deploy commands never run; they are checked against the code instead (the entry point exists, the project path exists).

A documented command is **itself wrong** when it cannot start on this repo: the project, solution, test directory or module path it names does not exist, or it uses an option the tool rejects. It **fails because of the code** when it starts and then reports compile errors or failing tests; that result goes under Not checked, not the drift list.

---

## 10. Edge Cases

| Situation | Behavior |
|---|---|
| No `README.md` | Skip the change window and claims steps; the drift list becomes `Create README.md with: <standard sections for the stack>`, built from facts, entry points and workflows, with the same approval prompt |
| `README.md` has uncommitted changes | `README.md has uncommitted changes; the sync edits will mix with them. Continue? [yes / no]` |
| `README.md` has no commit | No change window; say so and run deep mode, with its size confirmation |
| A documented command fails because the code is broken | Not checked, with the error; not drift |
| A documented command is itself wrong | `Failing command` item with the correct command, taken from the CI workflow when one exists |
| Python, dotnet or NuGet unavailable | Not checked; never install anything |
| Neither stack | `No Python or .NET project found. readme-sync covers those two stacks.` and stop |
| Several projects (an Aspire host and a web app, a bot and its tests) | One root README; facts come from every project |
| `readme_facts.py` cannot parse a file | Listed under Not checked |
| `CLAUDE.md`, `docs/`, `specs/`, nested READMEs | Out of scope, never edited |
| Zero drift | `README matches the code.` with the header |

---

## 11. Permissions

`SKILL.md` frontmatter `allowed-tools`:
- `Bash(git status *)`, `Bash(git log *)`, `Bash(git diff *)`, `Bash(git ls-files *)`, `Bash(git remote get-url *)`
- `Bash(python -m flake8 *)`, `Bash(python -m py_compile *)`, `Bash(python -m pytest *)`, `Bash(python -m unittest *)`
- `Bash(dotnet build *)`, `Bash(dotnet test *)`

The script runs as `python "<skill base directory>/scripts/readme_facts.py" ...`. Permission rules match literal command text and the quoted path contains a space, so no safe wildcard rule matches it; that command asks once per run. Text searches use the Grep tool. File edits keep the user's normal approval.

---

## 12. Testing Plan

1. **Unit tests first** (`scripts/test_readme_facts.py`, `unittest`): a fixture per check ID that must be flagged and look-alikes that must not be (a command referenced with a different prefix, an env var read through `Configuration["..."]`, a README heading with emoji, a `/path` that is a slash command in a Python repo, a key documented under another heading), plus `--since auto` on a temporary git repo with a README commit followed by code commits.
2. **Replay syncs** on scratch clones checked out at the commit before each 2026-09-12 rewrite, run in a fresh session, never touching the user's repos:

   | Replay | Must appear in quick mode | Must appear in deep mode |
   |---|---|---|
   | DiscordVoiceDatabase `bcc255c` | `/favoriteslist` stale; `favoritesplay` and `sync` undocumented; `DiscordVoiceDatabase_WHISPER_MODEL` and `DiscordVoiceDatabase_LOG_LEVEL` undocumented; `your-username` clone URL | Missing slash-command sync step (`setup_hook` never calls `tree.sync()`) |
   | DiscordServerAudit `49541cc` | `bot.token` and `gemini_key` in the README's `config.yaml` example, which `config.yaml` lacks; `DiscordServerAudit_APP_ROOT` and `DiscordServerAudit_DB_PATH` undocumented | "All commands require the admin role" while 12 stats commands have no role check; Manage Server missing from invite permissions although `!listinvites` calls `guild.invites()` |
   | samelhag.dev `829f079` | `MudBlazor 8.0` against 9.6.0; the small-change warning (the README's last commit changed 2 lines) | "Azure Ready" against the IIS workflow; unmeasured CPU and bundle-size numbers |
   | bytecraft.us `e9ac0f9` | Placeholder clone URL `github.com/your-org/bytecraft.us`; SMTP key names `Host`, `Port`, `EnableSsl` against `SmtpHost`, `SmtpPort` | "Only the contact form is interactive" while `PopoverHost.razor` also uses `@rendermode InteractiveServer` |

   Every row was confirmed against its snapshot while the plan was written (the README line and the code that contradicts it). The files behind every deep-mode answer also fall inside that snapshot's change window, so the plan requires them in quick mode as well and runs deep mode once, on DiscordServerAudit, to exercise the size confirmation.
3. **Creation run** on a scratch clone of usvotemap.dev, which has no README: the drift list proposes every standard section for a Blazor site.
4. **Apply run** on one replay, answering `all except <n>`: the diff touches only `README.md`, the left-out item remains in the rerun, the drift count drops by the applied items, and documented commands in the edited README succeed.
5. **Cost:** each replay produces a full drift list and summary with fewer than 1.7M context tokens (half the cheapest 2026-09-12 session), counting each API response once.
6. **User check** in a fresh session: "update the readme" in a real repo.

---

## 13. Out of Scope

- Files other than the root `README.md` (`CLAUDE.md`, `docs/`, `specs/`, nested READMEs, changelogs)
- Languages other than Python and .NET
- Launching the app, installing tools or packages, or fetching URLs over the network
- Spelling, grammar and Markdown formatting that is not drift
- Scores, severities or a per-item fix loop
- Generated marker blocks inside the README
- Committing, staging, or opening pull requests
