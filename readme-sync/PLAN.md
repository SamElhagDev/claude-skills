# README Sync Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (inline, recommended for this user) or superpowers:subagent-driven-development (only if the user asks for subagents) to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `readme-sync` skill: one drift list and one approval that bring a Python or .NET repository's `README.md` back in line with its code.

**Architecture:** `SKILL.md` orchestrates; `scripts/readme_facts.py` extracts facts from the code with the standard library and compares them with the README, covered by `scripts/test_readme_facts.py`; eight `sections/*.md` guides say which facts belong to each README section, which prose claims to verify and how to fill a missing section. Correctness is proven by unit tests, by replaying the script on scratch clones at the commits before the 2026-09-12 README rewrites, and by full syncs in a fresh session.

**Tech Stack:** Markdown skill files; Python 3.10 standard library (`ast`, `json`, `re`, `subprocess`, `unittest`); flake8 7.3; git; .NET SDK 10 for documented build and test commands.

**Spec:** `C:\Users\Sam Elhag.EREF\.claude\skills\readme-sync\DESIGN.md`

## Global Constraints

- Never stage, commit or push. Every task ends with changes left uncommitted for the user.
- Never modify the user's repos under `C:\Users\Sam Elhag.EREF\source\repos`; only read them. Replays use `git clone --no-hardlinks` into the session scratchpad, and status checks on the user's repos use `git --no-optional-locks`.
- No subagents unless the user asks.
- `readme_facts.py` uses the Python standard library only and must run on Python 3.10.11.
- Skipped paths: `.venv/`, `venv/`, `node_modules/`, `bin/`, `obj/`, `.specify/`, `.claude/`, `__pycache__/`, `wwwroot/lib/`.
- Script output line: `<section>\t<CHECK-ID>\t<location>\t<detail>`; last line `summary\tfacts=<n> drift=<m> not_checked=<k>`; `SINCE`, `CHANGED` and `NOT-CHECKED` lines do not count toward `drift=`; exit 0 when it ran, 1 when it failed.
- Section order: features, setup, configuration, commands, routes, deployment, development, license, meta.
- Approval prompt: `Apply these README changes? [yes / no / all except <numbers>]`.
- Documented commands run only as `dotnet build`, `dotnet test`, `python -m unittest ...`, `python -m pytest ...` or `python -m flake8 ...`; install, run, Docker and deploy commands never run.
- `SKILL.md` under about 800 words; each section guide under 400 words with `## Facts`, `## Claims` and `## Filling`.
- Skill text uses plain punctuation (no em-dashes). Harness code tests for the em-dash with `chr(0x2014)`, never with a backslash-u escape, because escapes typed into tool calls can arrive as the real character.

## Variables used in commands

- `SKILL="/c/Users/Sam Elhag.EREF/.claude/skills/readme-sync"`
- `REPOS="/c/Users/Sam Elhag.EREF/source/repos"`
- `SCRATCH=<the executing session's scratchpad directory, forward slashes>`

## File Map

| File | Responsibility | Task |
|---|---|---|
| `scripts/readme_facts.py` | Fact extraction, README comparison, change window, CLI | 1 to 6 |
| `scripts/test_readme_facts.py` | Unit tests for every check ID and the CLI | 1 to 6 |
| `sections/features.md`, `setup.md`, `configuration.md`, `commands.md` | Section guides | 8 |
| `sections/routes.md`, `deployment.md`, `development.md`, `license.md` | Section guides | 9 |
| `SKILL.md` | Orchestration, drift list, approval, editing rules, verification | 10 |
| (scratchpad only) `guide_lint.py`, `skill_lint.py`, `usage_now.py`, replay clones | Test harness, never in the repo | 7, 8, 10, 11, 12 |

## Tasks

1. readme_facts foundation
2. Commands checks
3. Configuration checks
4. Routes, versions and paths checks
5. Deployment, license, repository URL and section checks
6. Change window
7. Script replay on pre-rewrite snapshots
8. Section guides: features, setup, configuration, commands
9. Section guides: routes, deployment, development, license
10. SKILL.md orchestrator
11. Full replay syncs and cost measurement
12. Apply run, creation run and automatic checks
13. Wrap-up and handoff

Tasks 1 to 10 run in one session that stops and reports. Tasks 11 to 13 run in a new session opened in `C:\Users\Sam Elhag.EREF\.claude\skills`, starting at Task 11 Step 0.

Every code block below was assembled in a scratchpad and run before this plan was written: each task's tests fail with the stated errors before its implementation and pass after it, flake8 is clean at every stage, and the Task 7 outputs are the real outputs on the snapshots.

---

### Task 1: readme_facts foundation

**Files:**
- Create: `scripts/readme_facts.py`
- Test: `scripts/test_readme_facts.py`

**Interfaces:**
- Produces: `Item(section, check, location, detail)` with `.format() -> str`; `git(root, *args) -> str`; `list_files(root) -> list[str]`; `heading_key(text) -> str | None`; `parse_readme(lines) -> (code_flags, sections, top_headings)`; `Repo` with `files`, `readme`, `readme_text`, `has_readme`, `since`, `code_lines`, `sections`, `top_headings`, `facts`, `not_checked`, `text(rel)`, `matching(*exts)`, `python`, `dotnet`, `trees()`, `corpus(exts)`, `tokens()` and `where(index)`; `line_of(text, offset) -> int`; `_dotted(expr)`; `CHECKS: list` of `(repo) -> list[Item]`; `load_repo(root, since=None) -> Repo`; `run(root, since=None) -> tuple[list[Item], int]`; `main(argv) -> int`. Test helpers `make_repo(files)`, `write(root, files)`, `commit(root, message)`, `checks(check, files)` and the `BOT` fixture.

- [ ] **Step 1: Write the failing tests**

Create `scripts/test_readme_facts.py`:

````python
import io
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from contextlib import redirect_stdout

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import readme_facts as rf  # noqa: E402


def make_repo(files):
    tmp = tempfile.TemporaryDirectory()
    write(tmp.name, files)
    subprocess.run(["git", "init", "-q", tmp.name], check=True)
    subprocess.run(["git", "-C", tmp.name, "add", "-A"], check=True)
    return tmp


def write(root, files):
    for rel, src in files.items():
        path = os.path.join(root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(textwrap.dedent(src))


def commit(root, message):
    subprocess.run(["git", "-C", root, "add", "-A"], check=True)
    subprocess.run(["git", "-C", root, "-c", "user.name=test", "-c", "user.email=test@example.com",
                    "commit", "-qm", message], check=True)


def checks(check, files):
    with make_repo(files) as root:
        return [(i.check, i.location, i.detail) for i in check(rf.load_repo(root))]


BOT = """
from discord.ext import commands

class Polls(commands.Cog):
    @commands.hybrid_group(name="poll")
    async def poll_group(self, ctx):
        pass

    @poll_group.command(name="create")
    async def poll_create(self, ctx):
        pass

    @commands.command()
    async def sync(self, ctx):
        pass

    @commands.hybrid_command(name="favoritesplay")
    async def favorites_play(self, ctx):
        pass
"""


class FoundationTests(unittest.TestCase):
    def test_skips_vendor_and_tooling_dirs(self):
        with make_repo({"bot.py": "x = 1\n", ".venv/lib/a.py": "", "obj/Debug/b.cs": "", ".specify/c.yml": "",
                        ".claude/settings.json": "{}", "wwwroot/lib/d.js": "", "cogs/e.py": ""}) as root:
            self.assertEqual(rf.list_files(root), ["bot.py", "cogs/e.py"])

    def test_readme_sections_use_top_level_headings(self):
        lines = textwrap.dedent("""\
            # 🗳️ Vote Bot
            intro
            ## 🚀 Getting started
            ### 3. Configure the environment
            ```bash
            # not a heading
            ```
            ## Pages
            ## 📝 License
            """).splitlines()
        code, sections, tops = rf.parse_readme(lines)
        self.assertEqual(sections, ["features", "features", "setup", "setup", "setup", "setup", "setup", "routes", "license"])
        self.assertEqual(code[4:7], [True, True, True])
        self.assertEqual([t[1] for t in tops], ["setup", "routes", "license"])

    def test_main_prints_summary_and_returns_0(self):
        with make_repo({"README.md": "# X\n", "a.py": "x = 1\n"}) as root:
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = rf.main([root])
        self.assertEqual(code, 0)
        self.assertRegex(buf.getvalue().splitlines()[-1], r"^summary\tfacts=\d+ drift=\d+ not_checked=0$")

    def test_main_returns_1_without_args(self):
        self.assertEqual(rf.main([]), 1)

    def test_unparseable_python_is_not_checked(self):
        with make_repo({"good.py": "x = 1\n", "bad.py": "def (:\n"}) as root:
            repo = rf.load_repo(root)
            self.assertEqual(sorted(repo.trees()), ["good.py"])
        self.assertEqual([(i.check, i.location) for i in repo.not_checked], [("NOT-CHECKED", "bad.py")])


if __name__ == "__main__":
    unittest.main()
````

- [ ] **Step 2: Run the tests and confirm they fail**

Run: `python -m unittest discover -s "$SKILL/scripts" -p "test_readme_facts.py" -v`
Expected: `ModuleNotFoundError: No module named 'readme_facts'`

- [ ] **Step 3: Write the implementation**

Create `scripts/readme_facts.py`:

````python
"""Standard-library README drift checks for the readme-sync skill.

Usage: python readme_facts.py <repo-root> [--since auto]
"""
import ast
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field

SECTION_ORDER = ["features", "setup", "configuration", "commands", "routes",
                 "deployment", "development", "license", "meta"]
SECTION_KEYWORDS = {
    "features": ["features", "overview"],
    "setup": ["setup", "getting started", "installation", "quick start", "requirements", "prerequisites"],
    "configuration": ["configuration", "config", "environment", "settings"],
    "commands": ["commands", "usage"],
    "routes": ["routes", "pages"],
    "deployment": ["deploy", "deployment", "hosting"],
    "development": ["development", "contributing", "contributors", "testing", "structure", "layout"],
    "license": ["license"],
}
SKIP_PARTS = {".venv", "venv", "node_modules", "bin", "obj", ".specify", ".claude", "__pycache__"}
CODE_EXTS = (".py", ".cs", ".razor", ".cshtml", ".js", ".ts", ".css", ".sql")
TEXT_EXTS = CODE_EXTS + (".json", ".yml", ".yaml", ".toml", ".ini", ".cfg", ".txt", ".csproj", ".props",
                         ".targets", ".ps1", ".sh", ".example", ".sample", ".xml", ".config")
HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
BACKTICK = re.compile(r"`([^`\n]+)`")


@dataclass(frozen=True)
class Item:
    section: str
    check: str
    location: str
    detail: str

    def format(self) -> str:
        return f"{self.section}\t{self.check}\t{self.location}\t{self.detail}"


def git(root: str, *args: str) -> str:
    return subprocess.run(["git", "-C", root, *args], capture_output=True, text=True, encoding="utf-8").stdout


def list_files(root: str) -> list[str]:
    out = subprocess.run(["git", "-C", root, "ls-files"], capture_output=True, text=True,
                         encoding="utf-8", check=True).stdout
    return sorted(p for p in out.splitlines()
                  if not any(part in SKIP_PARTS for part in p.split("/")[:-1]) and "wwwroot/lib/" not in p)


def heading_key(text: str):
    words = " ".join(re.sub(r"[^a-z0-9]+", " ", text.lower()).split())
    for section, keywords in SECTION_KEYWORDS.items():
        if any(re.search(rf"\b{re.escape(k)}\b", words) for k in keywords):
            return section
    return None


def parse_readme(lines: list[str]):
    """Return (code line flags, standard section per line, top-level headings as (index, section, text))."""
    in_code, code, headings = False, [], []
    for index, line in enumerate(lines):
        fence = line.lstrip().startswith("```")
        code.append(in_code or fence)
        if fence:
            in_code = not in_code
            continue
        match = None if in_code else HEADING.match(line)
        if match:
            headings.append((index, len(match.group(1)), match.group(2)))
    top = min((level for _, level, _ in headings[1:]), default=2)
    marks = {index: (level, text) for index, level, text in headings}
    sections, tops, current = [], [], "features"
    for index in range(len(lines)):
        if index in marks:
            level, text = marks[index]
            if level < top:
                current = "features"
            elif level == top:
                current = heading_key(text) or "features"
                tops.append((index, heading_key(text), text))
        sections.append(current)
    return code, sections, tops


@dataclass(eq=False)
class Repo:
    root: str
    files: list[str]
    readme: list[str]
    has_readme: bool
    since: str | None = None
    facts: dict = field(default_factory=dict)
    not_checked: list = field(default_factory=list)
    _texts: dict = field(default_factory=dict)
    _trees: dict | None = None

    def __post_init__(self):
        self.code_lines, self.sections, self.top_headings = parse_readme(self.readme)
        self.readme_text = "\n".join(self.readme)

    def text(self, rel: str):
        if rel not in self._texts:
            try:
                with open(os.path.join(self.root, rel), encoding="utf-8-sig") as fh:
                    self._texts[rel] = fh.read()
            except (OSError, UnicodeDecodeError):
                self._texts[rel] = None
        return self._texts[rel]

    def matching(self, *exts: str) -> list[str]:
        return [f for f in self.files if f.lower().endswith(exts)]

    @property
    def python(self) -> bool:
        return any(f.endswith(".py") or f.split("/")[-1].startswith("requirements") for f in self.files)

    @property
    def dotnet(self) -> bool:
        return bool(self.matching(".csproj", ".sln", ".slnx"))

    def trees(self) -> dict:
        if self._trees is None:
            self._trees = {}
            for rel in self.matching(".py"):
                source = self.text(rel)
                try:
                    self._trees[rel] = ast.parse(source if source is not None else "\0", filename=rel)
                except (SyntaxError, ValueError):
                    self.not_checked.append(Item("meta", "NOT-CHECKED", rel, "could not parse"))
        return self._trees

    def corpus(self, exts=TEXT_EXTS) -> str:
        key = ("corpus", exts)
        if key not in self._texts:
            special = ("dockerfile", "docker-compose", ".env")
            parts = [self.text(f) or "" for f in self.files
                     if f.lower().endswith(exts) or f.split("/")[-1].lower().startswith(special)]
            self._texts[key] = "\n".join(parts)
        return self._texts[key]

    def tokens(self):
        """Backticked spans outside code blocks, and whole code-block lines, as (index, text, in_code)."""
        for index, line in enumerate(self.readme):
            if self.code_lines[index]:
                if not line.lstrip().startswith("```") and line.strip():
                    yield index, line.strip(), True
            else:
                for match in BACKTICK.finditer(line):
                    yield index, match.group(1).strip(), False

    def where(self, index: int) -> str:
        return f"README.md:{index + 1}"


def line_of(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def _dotted(expr):
    if isinstance(expr, ast.Name):
        return expr.id
    if isinstance(expr, ast.Attribute):
        base = _dotted(expr.value)
        return f"{base}.{expr.attr}" if base else None
    return None


CHECKS = []


def load_repo(root: str, since=None) -> Repo:
    path = os.path.join(root, "README.md")
    readme = []
    if os.path.exists(path):
        with open(path, encoding="utf-8-sig") as fh:
            readme = fh.read().splitlines()
    return Repo(root=root, files=list_files(root), readme=readme, has_readme=os.path.exists(path), since=since)


def _sort_key(item: Item):
    path, _, line = item.location.rpartition(":")
    number = int(line) if line.isdigit() else 0
    return SECTION_ORDER.index(item.section), item.check, path or item.location, number


def run(root: str, since=None) -> tuple[list[Item], int]:
    repo = load_repo(root, since)
    items = []
    for check in CHECKS:
        items.extend(check(repo))
    items.extend(repo.not_checked)
    items.sort(key=_sort_key)
    return items, sum(len(v) for v in repo.facts.values())


def main(argv: list[str]) -> int:
    args = [a for a in argv if a not in ("--since", "auto")]
    since = "auto" if "--since" in argv else None
    if len(args) != 1:
        print("usage: readme_facts.py <repo-root> [--since auto]", file=sys.stderr)
        return 1
    try:
        items, facts = run(args[0], since)
    except Exception as exc:  # a crash must never read as a clean README
        print(f"readme_facts failed: {exc!r}", file=sys.stderr)
        return 1
    context = {"SINCE", "CHANGED", "NOT-CHECKED"}
    for item in items:
        print(item.format())
    drift = sum(1 for i in items if i.check not in context)
    not_checked = sum(1 for i in items if i.check == "NOT-CHECKED")
    print(f"summary\tfacts={facts} drift={drift} not_checked={not_checked}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
````

- [ ] **Step 4: Run the tests and confirm they pass**

Run: `python -m unittest discover -s "$SKILL/scripts" -p "test_readme_facts.py" -v`
Expected: `Ran 5 tests` and `OK`

- [ ] **Step 5: Lint and leave uncommitted**

Run: `python -m flake8 --max-line-length=127 "$SKILL/scripts"`
Expected: no output. Do not stage or commit.

### Task 2: Commands checks

**Files:**
- Modify: `scripts/readme_facts.py` (insert the block above the unindented `if __name__ == "__main__":` line at the end of the file)
- Test: `scripts/test_readme_facts.py` (add `CommandTests` above the unindented `if __name__ == "__main__":` line at the end of the file)

**Interfaces:**
- Consumes: `Item`, `Repo`, `CHECKS`, `_dotted` from Task 1; the `BOT`, `make_repo` and `checks` test helpers.
- Produces: `code_commands(repo) -> dict[str, str]` (full command name to `path:line`, plus `help` unless the code sets `help_command=None`); `readme_commands(repo)` yielding `(index, prefix, first, second)`; `check_commands(repo) -> list[Item]`; constants `COMMAND_TOKEN` and `PLACEHOLDER_COMMANDS`.

- [ ] **Step 1: Write the failing tests**

Add to `scripts/test_readme_facts.py`:

````python
class CommandTests(unittest.TestCase):
    def test_code_commands_include_groups_and_builtin_help(self):
        with make_repo({"cogs/polls.py": BOT}) as root:
            found = rf.code_commands(rf.load_repo(root))
        self.assertEqual(sorted(found), ["favoritesplay", "help", "poll", "poll create", "sync"])

    def test_help_is_absent_when_disabled(self):
        with make_repo({"bot.py": BOT + "\nbot = commands.Bot(command_prefix='!', help_command=None)\n"}) as root:
            self.assertNotIn("help", rf.code_commands(rf.load_repo(root)))

    def test_stale_and_undocumented_commands(self):
        readme = """\
            # Bot
            ## Commands
            - `>poll create` starts a poll
            - `/favoriteslist` plays favorites
            - `!help`, and commands work as `/command`
            ```text
            !sync guild
            ```
            """
        found = checks(rf.check_commands, {"cogs/polls.py": BOT, "README.md": readme})
        self.assertEqual(found, [
            ("CMD-STALE", "README.md:4", "/favoriteslist matches no command in code"),
            ("CMD-UNDOCUMENTED", "cogs/polls.py:18", "command 'favoritesplay' is not in the README"),
        ])
````

- [ ] **Step 2: Run the tests and confirm they fail**

Run: `python -m unittest discover -s "$SKILL/scripts" -p "test_readme_facts.py" -v`
Expected: `Ran 8 tests`, `FAILED (errors=3)`, with `AttributeError: module 'readme_facts' has no attribute 'code_commands'` twice and `... 'check_commands'` once

- [ ] **Step 3: Write the implementation**

Insert above `if __name__ == "__main__":` in `scripts/readme_facts.py`:

````python
COMMAND_ATTRS = {"command", "hybrid_command", "group", "hybrid_group"}
GROUP_ATTRS = {"group", "hybrid_group"}
PLACEHOLDER_COMMANDS = {"command", "cmd", "name", "commandname", "subcommand"}
COMMAND_TOKEN = re.compile(r"^([!>/])([a-z][a-z0-9_-]*)(?=$|\s)(?:\s+([a-z][a-z0-9_-]*)(?=$|\s))?")


def _command_decorator(dec):
    call = dec if isinstance(dec, ast.Call) else None
    func = dec.func if call else dec
    if not isinstance(func, ast.Attribute) or func.attr not in COMMAND_ATTRS:
        return None
    name = None
    for kw in (call.keywords if call else []):
        if kw.arg == "name" and isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
            name = kw.value.value
    owner = func.value.id if isinstance(func.value, ast.Name) else None
    return func.attr, owner, name


def code_commands(repo: Repo) -> dict:
    if "commands" in repo.facts:
        return repo.facts["commands"]
    found = {}
    for rel, tree in repo.trees().items():
        groups = {}
        functions = sorted((n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))),
                           key=lambda n: n.lineno)
        for fn in functions:
            for dec in fn.decorator_list:
                spec = _command_decorator(dec)
                if not spec:
                    continue
                kind, owner, name = spec
                full = (name or fn.name).lower()
                if owner in groups:
                    full = f"{groups[owner]} {full}"
                if kind in GROUP_ATTRS:
                    groups[fn.name] = full
                found.setdefault(full, f"{rel}:{fn.lineno}")
    if found and "help" not in found and "help_command=None" not in repo.corpus((".py",)).replace(" ", ""):
        found["help"] = "discord.py built-in help"
    repo.facts["commands"] = found
    return found


def readme_commands(repo: Repo):
    for index, text, _ in repo.tokens():
        match = COMMAND_TOKEN.match(text)
        if match:
            yield index, match.group(1), match.group(2), match.group(3)


def check_commands(repo: Repo) -> list[Item]:
    if not repo.python:
        return []
    commands = code_commands(repo)
    if not commands:
        return []
    items, mentioned = [], set()
    for index, prefix, first, second in readme_commands(repo):
        if first in PLACEHOLDER_COMMANDS:
            continue
        pair = f"{first} {second}" if second else None
        if first in commands or pair in commands:
            mentioned.update(name for name in (first, pair) if name in commands)
            continue
        if prefix == "/" and repo.dotnet:
            continue  # check_routes reports it when it matches no route either
        items.append(Item(repo.sections[index], "CMD-STALE", repo.where(index),
                          f"{prefix}{first} matches no command in code"))
    for name, location in sorted(commands.items()):
        if name not in mentioned and name != "help":
            items.append(Item("commands", "CMD-UNDOCUMENTED", location, f"command '{name}' is not in the README"))
    return items
````

- [ ] **Step 4: Run the tests and confirm they pass**

Run: `python -m unittest discover -s "$SKILL/scripts" -p "test_readme_facts.py" -v`
Expected: `Ran 8 tests` and `OK`

- [ ] **Step 5: Lint and leave uncommitted**

Run: `python -m flake8 --max-line-length=127 "$SKILL/scripts"`
Expected: no output. Do not stage or commit.

### Task 3: Configuration checks

**Files:**
- Modify: `scripts/readme_facts.py` (add `import json` on the line after `import ast`; insert the block above the `if __name__ == "__main__":` line)
- Test: `scripts/test_readme_facts.py` (add `ConfigurationTests` above the `if __name__ == "__main__":` line)

**Interfaces:**
- Consumes: `Item`, `Repo` (`corpus`, `tokens`, `trees`, `code_lines`, `sections`), `CHECKS`, `CODE_EXTS`, `BACKTICK`, `line_of`, `_dotted` from Task 1.
- Produces: `env_reads(repo) -> dict[str, str]`; `yaml_keys(text) -> list[tuple[str, int]]`; `config_keys(repo) -> dict[str, dict[str, int]]`; `check_configuration(repo) -> list[Item]`; constants `ENV_TOKEN` and `FILE_EXTS` (used by Tasks 4 and 5).

- [ ] **Step 1: Write the failing tests**

Add to `scripts/test_readme_facts.py`:

````python
class ConfigurationTests(unittest.TestCase):
    def test_env_reads_from_python_and_dotnet(self):
        files = {
            "config.py": 'import os\nA = os.getenv("Bot_TOKEN")\nB = os.environ.get("Bot_LOG_LEVEL", "INFO")\n'
                         'C = os.environ["Bot_DB_PATH"]\n',
            "Extensions.cs": 'var a = Environment.GetEnvironmentVariable("KALSHI_API_KEY_ID");\n'
                             'var b = builder.Configuration["OTEL_EXPORTER_OTLP_ENDPOINT"];\n',
            "site.csproj": "<Project />\n",
        }
        with make_repo(files) as root:
            found = rf.env_reads(rf.load_repo(root))
        self.assertEqual(sorted(found), ["Bot_DB_PATH", "Bot_LOG_LEVEL", "Bot_TOKEN", "KALSHI_API_KEY_ID",
                                         "OTEL_EXPORTER_OTLP_ENDPOINT"])

    def test_env_undocumented_and_stale(self):
        files = {
            "config.py": 'import os\nMAX_OPTIONS = 25\nA = os.getenv("Bot_TOKEN")\nB = os.getenv("Bot_LOG_LEVEL")\n',
            "README.md": "# Bot\n## Configuration\n- `Bot_TOKEN` token\n- `Bot_OLD_NAME` removed\n"
                         "- token: YOUR_BOT_TOKEN_HERE\n- `MAX_OPTIONS` is 25\n",
        }
        found = checks(rf.check_configuration, files)
        self.assertEqual(found, [
            ("ENV-UNDOCUMENTED", "config.py:4", "env var Bot_LOG_LEVEL is not in the README"),
            ("ENV-STALE", "README.md:4", "Bot_OLD_NAME is not used anywhere in the code, workflows or config"),
        ])

    def test_yaml_keys_nested_with_comments_and_lists(self):
        text = "bot:\n  prefix: '!'   # comment\n  roles:\n    - admin\n# top comment\nintervals:\n  audit: 6\n"
        expected = [("bot", 1), ("bot.prefix", 2), ("bot.roles", 3), ("intervals", 6), ("intervals.audit", 7)]
        self.assertEqual(rf.yaml_keys(text), expected)

    def test_config_keys_stale_on_config_lines_and_grouped_undocumented(self):
        files = {
            "site.csproj": "<Project />\n",
            "EmailService.cs": "public class EmailService {}\n",
            "appsettings.json": '{"Logging": {"LogLevel": {"Default": "Information"}},\n'
                                ' "bytecraftSMTP": {"SmtpHost": "smtp", "SmtpPort": 587, "ToAddress": ""}}\n',
            "README.md": "# Site\n## Contact form\nSet `bytecraftSMTP:ToAddress` with user secrets.\n"
                         "The rest (`Host`, `Port`) lives in `appsettings.json` and `EmailService` reads it.\n",
        }
        found = [f for f in checks(rf.check_configuration, files) if f[0].startswith("CONFIG")]
        self.assertEqual(found, [
            ("CONFIG-KEY-UNDOCUMENTED", "appsettings.json:2",
             "2 of 3 config keys are not in the README: bytecraftSMTP:SmtpHost, bytecraftSMTP:SmtpPort"),
            ("CONFIG-KEY-STALE", "README.md:4", "Host is not a key in appsettings.json"),
            ("CONFIG-KEY-STALE", "README.md:4", "Port is not a key in appsettings.json"),
        ])

    def test_config_key_stale_in_readme_yaml_block(self):
        files = {
            "config.yaml": "bot:\n  prefix: '!'\nadmin_role: Bot Admin\n",
            "README.md": "# Bot\n## Setup\n```yaml\nbot:\n  prefix: \"!\"\n  token: \"YOUR_BOT_TOKEN_HERE\"\n"
                         "admin_role: Admin\n```\n",
        }
        found = [f for f in checks(rf.check_configuration, files) if f[0] == "CONFIG-KEY-STALE"]
        self.assertEqual(found, [("CONFIG-KEY-STALE", "README.md:6",
                                  "bot.token is shown in a README yaml block but config.yaml has no such key")])
````

- [ ] **Step 2: Run the tests and confirm they fail**

Run: `python -m unittest discover -s "$SKILL/scripts" -p "test_readme_facts.py" -v`
Expected: `Ran 13 tests`, `FAILED (errors=5)`, with `AttributeError` for `env_reads`, `yaml_keys` and `check_configuration`

- [ ] **Step 3: Write the implementation**

Add `import json` on the line after `import ast`. Insert above `if __name__ == "__main__":`:

````python
ENV_TOKEN = re.compile(r"(?<![\w$])([A-Za-z][A-Za-z0-9]*_[A-Z0-9][A-Z0-9_]*)(?![\w])")
PLACEHOLDER_ENV = re.compile(r"^(YOUR|MY|EXAMPLE|XXX)_|_HERE$|PLACEHOLDER")
NET_ENV = re.compile(r'Environment\.GetEnvironmentVariable\(\s*"([^"]+)"')
NET_CONFIG_ENV = re.compile(r'Configuration\[\s*"([A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+)"\s*\]')
YAML_KEY = re.compile(r"^(\s*)([A-Za-z0-9_.-]+)\s*:(?:\s|$)")
FRAMEWORK_KEYS = {"Logging", "AllowedHosts", "DetailedErrors"}
FILE_EXTS = {"py", "yaml", "yml", "json", "md", "txt", "cs", "razor", "csproj", "sln", "slnx", "db", "log", "ps1",
             "sh", "toml", "cfg", "ini", "wav", "png", "jpg", "svg", "ico", "css", "js", "html", "xml", "sql", "props"}


def env_reads(repo: Repo) -> dict:
    if "env" in repo.facts:
        return repo.facts["env"]
    found = {}
    for rel, tree in repo.trees().items():
        for node in ast.walk(tree):
            name = None
            if isinstance(node, ast.Call) and node.args and _dotted(node.func) in (
                    "os.getenv", "getenv", "os.environ.get", "environ.get"):
                name = node.args[0]
            elif isinstance(node, ast.Subscript) and _dotted(node.value) in ("os.environ", "environ"):
                name = node.slice
            if isinstance(name, ast.Constant) and isinstance(name.value, str):
                found.setdefault(name.value, f"{rel}:{node.lineno}")
    for rel in repo.matching(".cs", ".razor"):
        text = repo.text(rel) or ""
        for pattern in (NET_ENV, NET_CONFIG_ENV):
            for match in pattern.finditer(text):
                found.setdefault(match.group(1), f"{rel}:{line_of(text, match.start())}")
    repo.facts["env"] = found
    return found


def yaml_keys(text: str) -> list[tuple[str, int]]:
    keys, stack = [], []
    for number, raw in enumerate(text.splitlines(), 1):
        stripped = raw.strip()
        if not stripped or stripped.startswith(("#", "- ")):
            continue
        match = YAML_KEY.match(raw)
        if not match:
            continue
        indent = len(match.group(1))
        while stack and stack[-1][0] >= indent:
            stack.pop()
        stack.append((indent, match.group(2)))
        keys.append((".".join(k for _, k in stack), number))
    return keys


def _json_keys(data, prefix=""):
    if isinstance(data, dict):
        for key, value in data.items():
            path = f"{prefix}:{key}" if prefix else key
            yield path
            yield from _json_keys(value, path)


def config_keys(repo: Repo) -> dict:
    """{file: {key path: line}} for config*.yaml and appsettings*.json files."""
    if "config_files" in repo.facts:
        return repo.facts["config_files"]
    result = {}
    for rel in repo.files:
        name = rel.split("/")[-1].lower()
        text = repo.text(rel)
        if text is None:
            continue
        if re.match(r"^config(\.[\w-]+)?\.ya?ml$", name):
            result[rel] = dict(yaml_keys(text))
        elif re.match(r"^appsettings(\.[\w-]+)?\.json$", name):
            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                repo.not_checked.append(Item("meta", "NOT-CHECKED", rel, "invalid JSON"))
                continue
            result[rel] = {path: _json_line(text, path) for path in _json_keys(data)
                           if path.split(":")[0] not in FRAMEWORK_KEYS}
    repo.facts["config_files"] = result
    return result


def _json_line(text: str, path: str) -> int:
    match = re.search(r'"' + re.escape(path.split(":")[-1]) + r'"\s*:', text)
    return line_of(text, match.start()) if match else 1


def _leaves(keys: dict, sep: str) -> list[str]:
    return [k for k in keys if not any(other.startswith(k + sep) for other in keys)]


def check_configuration(repo: Repo) -> list[Item]:
    items = []
    reads = env_reads(repo)
    corpus = repo.corpus()
    for name, location in sorted(reads.items()):
        if name not in repo.readme_text:
            items.append(Item("configuration", "ENV-UNDOCUMENTED", location, f"env var {name} is not in the README"))
    seen = set()
    for index, line in enumerate(repo.readme):
        for match in ENV_TOKEN.finditer(line):
            token = match.group(1)
            if token in seen or token in corpus or token.startswith("__") or PLACEHOLDER_ENV.search(token):
                continue
            seen.add(token)
            items.append(Item(repo.sections[index], "ENV-STALE", repo.where(index),
                              f"{token} is not used anywhere in the code, workflows or config"))
    items.extend(_config_key_items(repo))
    return items


def _config_key_items(repo: Repo) -> list[Item]:
    files = config_keys(repo)
    if not files:
        return []
    items = []
    sep_of = {rel: ("." if rel.lower().endswith((".yaml", ".yml")) else ":") for rel in files}
    all_keys = {k: rel for rel, keys in files.items() for k in keys}
    documented_any = any(k in repo.readme_text for k in all_keys if (":" in k or "." in k))
    names_in_readme = {t for _, t, _ in repo.tokens()}
    if documented_any:
        for rel, keys in files.items():
            leaves = _leaves(keys, sep_of[rel])
            missing = [k for k in leaves if k not in repo.readme_text and k.split(sep_of[rel])[-1] not in names_in_readme]
            if missing:
                items.append(Item("configuration", "CONFIG-KEY-UNDOCUMENTED", f"{rel}:{keys[missing[0]]}",
                                  f"{len(missing)} of {len(leaves)} config keys are not in the README: {', '.join(missing)}"))
    items.extend(_code_block_keys(repo, files, sep_of))
    tops = {k.split(sep_of[rel])[0]: rel for rel, keys in files.items() for k in keys}
    segments = {rel: {s for k in keys for s in re.split(r"[.:]", k)} for rel, keys in files.items()}
    code_words = set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", repo.corpus(CODE_EXTS)))
    basenames = {rel.split("/")[-1]: rel for rel in files}
    for index, text, in_code in repo.tokens():
        token = text.strip('"')
        dotted = re.fullmatch(r"[A-Za-z_][\w-]*(?:\.[A-Za-z_][\w-]*)+", token)
        colon = re.fullmatch(r"[A-Za-z_][\w-]*(?::[A-Za-z_][\w-]*)+", token)
        if dotted and token.rsplit(".", 1)[-1].lower() not in FILE_EXTS and token.split(".")[0] in tops:
            if token not in all_keys:
                items.append(Item(repo.sections[index], "CONFIG-KEY-STALE", repo.where(index),
                                  f"{token} is not a key in {tops[token.split('.')[0]]}"))
        elif colon and token.split(":")[0] in tops and token not in all_keys:
            items.append(Item(repo.sections[index], "CONFIG-KEY-STALE", repo.where(index),
                              f"{token} is not a key in {tops[token.split(':')[0]]}"))
    for index, line in enumerate(repo.readme):
        if repo.code_lines[index]:
            continue
        ticked = {m.group(1) for m in BACKTICK.finditer(line)}
        named = [rel for base, rel in basenames.items() if base in line]
        named += [rel for top, rel in tops.items() if top in ticked and rel not in named]
        if not named:
            continue
        for match in BACKTICK.finditer(line):
            token = match.group(1)
            if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", token) or token in code_words:
                continue
            if not any(token in segments[rel] or token in tops for rel in named):
                items.append(Item(repo.sections[index], "CONFIG-KEY-STALE", repo.where(index),
                                  f"{token} is not a key in {', '.join(sorted(set(named)))}"))
    return items


def _code_block_keys(repo: Repo, files: dict, sep_of: dict) -> list[Item]:
    """Keys shown in README ```yaml or ```json blocks that the matching config file does not have."""
    items, index = [], 0
    while index < len(repo.readme):
        fence = re.match(r"^\s*```\s*(yaml|yml|json|jsonc)\s*$", repo.readme[index], re.I)
        if not fence:
            index += 1
            continue
        start, index = index + 1, index + 1
        while index < len(repo.readme) and not repo.readme[index].lstrip().startswith("```"):
            index += 1
        block = "\n".join(repo.readme[start:index])
        kind = "yaml" if fence.group(1).lower().startswith("y") else "json"
        targets = [rel for rel in files if (sep_of[rel] == ".") == (kind == "yaml")]
        if not targets:
            continue
        known = {k for rel in targets for k in files[rel]}
        if kind == "yaml":
            shown = yaml_keys(block)
        else:
            try:
                data = json.loads(block)
            except json.JSONDecodeError:
                continue
            shown = [(k, _json_line(block, k)) for k in _json_keys(data) if k.split(":")[0] not in FRAMEWORK_KEYS]
        for key, line in shown:
            if key not in known:
                items.append(Item(repo.sections[start], "CONFIG-KEY-STALE", repo.where(start + line - 1),
                                  f"{key} is shown in a README {kind} block but {', '.join(targets)} has no such key"))
    return items


CHECKS.append(check_configuration)
````

- [ ] **Step 4: Run the tests and confirm they pass**

Run: `python -m unittest discover -s "$SKILL/scripts" -p "test_readme_facts.py" -v`
Expected: `Ran 13 tests` and `OK`

- [ ] **Step 5: Lint and leave uncommitted**

Run: `python -m flake8 --max-line-length=127 "$SKILL/scripts"`
Expected: no output. Do not stage or commit.

### Task 4: Routes, versions and paths checks

**Files:**
- Modify: `scripts/readme_facts.py` (insert the block above the `if __name__ == "__main__":` line)
- Test: `scripts/test_readme_facts.py` (add `RoutesVersionsPathsTests` above the `if __name__ == "__main__":` line)

**Interfaces:**
- Consumes: Task 1 foundation; `code_commands` from Task 2; `FILE_EXTS` from Task 3.
- Produces: `code_routes(repo) -> dict[str, str]`; `route_matches(route, token) -> bool`; `check_routes(repo)`; `code_versions(repo) -> dict[str, list[tuple[str, str]]]`; `versions_match(readme, code, minimum) -> bool`; `check_versions(repo)`; `_tracked(repo, path) -> bool`; `check_paths(repo)`; constant `FRAMEWORK_ROUTES` (used by Task 5).

- [ ] **Step 1: Write the failing tests**

Add to `scripts/test_readme_facts.py`:

````python
class RoutesVersionsPathsTests(unittest.TestCase):
    def test_routes_stale_undocumented_and_framework_pages(self):
        files = {
            "site.csproj": "<Project />\n",
            "Pages/About.razor": '@page "/about"\n',
            "Pages/Error.razor": '@page "/Error"\n',
            "Pages/Showcase.razor": '@page "/projects/{slug}"\n',
            "Pages/Interests.razor": '@page "/interests"\n',
            "README.md": "# Site\n## Routes\n| `/about` | About |\n| `/services` | Services |\n"
                         "| `/projects/heat-transfer` | Showcase |\n",
        }
        self.assertEqual(checks(rf.check_routes, files), [
            ("ROUTE-STALE", "README.md:4", "/services matches no route"),
            ("ROUTE-UNDOCUMENTED", "Pages/Interests.razor:1", "route /interests is not in the README"),
        ])

    def test_version_mismatch_precision_and_minimum(self):
        files = {
            "site.csproj": '<Project><PropertyGroup><TargetFramework>net10.0</TargetFramework></PropertyGroup>\n'
                           '<ItemGroup><PackageReference Include="MudBlazor" Version="9.6.0" /></ItemGroup></Project>\n',
            "requirements.txt": "discord.py[voice]==2.7.1\n",
            ".python-version": "3.12\n",
            "README.md": "# Site\n## Stack\n- .NET 10 with MudBlazor 9.6\n- MudBlazor 8.0 components\n"
                         "- Python 3.10+ and discord.py 2.7\n- Python 3.11 on the server\n",
        }
        self.assertEqual([(c, loc) for c, loc, _ in checks(rf.check_versions, files)],
                         [("VERSION-MISMATCH", "README.md:4"), ("VERSION-MISMATCH", "README.md:6")])

    def test_path_stale_ignores_basenames_packages_runtime_and_ignored_files(self):
        files = {
            ".gitignore": "logs/\n",
            "requirements.txt": "discord.py==2.7.1\n",
            "cogs/polls.py": "x = 1\n",
            "Components/App.razor": "<Routes />\n",
            "appsettings.json": "{}\n",
            "README.md": "# Bot\n## Development\n- `cogs/polls.py`, `App.razor`, `discord.py`\n"
                         "- `logs/`, `bot.log`, `appsettings.Production.json`\n"
                         "- `docs/old.md` and [guide](docs/guide.md)\n",
        }
        self.assertEqual(checks(rf.check_paths, files), [
            ("PATH-STALE", "README.md:5", "docs/old.md is not in the repository"),
            ("PATH-STALE", "README.md:5", "docs/guide.md is not in the repository"),
        ])
````

- [ ] **Step 2: Run the tests and confirm they fail**

Run: `python -m unittest discover -s "$SKILL/scripts" -p "test_readme_facts.py" -v`
Expected: `Ran 16 tests`, `FAILED (errors=3)`, with `AttributeError` for `check_routes`, `check_versions` and `check_paths`

- [ ] **Step 3: Write the implementation**

Insert above `if __name__ == "__main__":`:

````python
PAGE_ROUTE = re.compile(r'@page\s+"([^"]+)"')
FRAMEWORK_ROUTES = {"/", "/error", "/not-found", "/notfound"}
MAP_ROUTE = re.compile(r'\.Map(?:Get|Post|Put|Patch|Delete|Methods)?\(\s*"(/[^"]*)"')
ROUTE_TOKEN = re.compile(r"^/[A-Za-z0-9{][\w{}:./-]*$")
LINK_TARGET = re.compile(r"\]\(([^)\s]+)\)")


def code_routes(repo: Repo) -> dict:
    if "routes" in repo.facts:
        return repo.facts["routes"]
    found = {}
    for rel in repo.matching(".razor", ".cs", ".cshtml"):
        text = repo.text(rel) or ""
        pattern = PAGE_ROUTE if rel.endswith((".razor", ".cshtml")) else MAP_ROUTE
        for match in pattern.finditer(text):
            found.setdefault(match.group(1), f"{rel}:{line_of(text, match.start())}")
    repo.facts["routes"] = found
    return found


def route_matches(route: str, token: str) -> bool:
    a = [s for s in route.lower().strip("/").split("/")]
    b = [s for s in token.lower().split("#")[0].split("?")[0].strip("/").split("/")]
    return len(a) == len(b) and all(x == y or (x.startswith("{") and x.endswith("}")) for x, y in zip(a, b))


def check_routes(repo: Repo) -> list[Item]:
    if not repo.dotnet:
        return []
    routes = code_routes(repo)
    if not routes:
        return []
    commands = code_commands(repo) if repo.python else {}
    items, candidates = [], []
    for index, text, in_code in repo.tokens():
        if not in_code and ROUTE_TOKEN.match(text):
            candidates.append((index, text))
    for index, line in enumerate(repo.readme):
        for match in LINK_TARGET.finditer(line):
            if match.group(1).startswith("/"):
                candidates.append((index, match.group(1)))
    for index, token in candidates:
        if any(route_matches(r, token) for r in routes) or token.strip("/").split("/")[0].lower() in commands:
            continue
        if _tracked(repo, token.strip("/")):
            continue
        items.append(Item(repo.sections[index], "ROUTE-STALE", repo.where(index), f"{token} matches no route"))
    plain = re.findall(r"(?<![\w/.:-])(/[A-Za-z0-9{][\w{}:./-]*)", repo.readme_text)
    for route, location in sorted(routes.items()):
        if route.lower() in FRAMEWORK_ROUTES:
            continue
        if not any(route_matches(route, token) for token in plain):
            items.append(Item("routes", "ROUTE-UNDOCUMENTED", location, f"route {route} is not in the README"))
    return items


VERSION_SOURCES = [
    (re.compile(r"<TargetFrameworks?>([^<]+)</TargetFrameworks?>"), ".csproj", "tfm"),
    (re.compile(r'<(?:PackageReference|PackageVersion)\s+Include="([^"]+)"\s+Version="([^"]+)"'),
     (".csproj", ".props"), "pkg"),
    (re.compile(r'Sdk="([^"/]+)/([\d.]+)"'), ".csproj", "pkg"),
    (re.compile(r'<Sdk\s+Name="([^"]+)"\s+Version="([^"]+)"'), ".csproj", "pkg"),
]


def code_versions(repo: Repo) -> dict:
    if "versions" in repo.facts:
        return repo.facts["versions"]
    found = {}

    def add(name, version, location):
        found.setdefault(name.lower(), []).append((version, location))
        if name.lower().startswith("aspire."):
            found.setdefault("aspire", []).append((version, location))

    for pattern, exts, kind in VERSION_SOURCES:
        for rel in repo.matching(*((exts,) if isinstance(exts, str) else exts)):
            text = repo.text(rel) or ""
            for match in pattern.finditer(text):
                where = f"{rel}:{line_of(text, match.start())}"
                if kind == "tfm":
                    for tfm in match.group(1).split(";"):
                        number = re.match(r"net(\d+(?:\.\d+)?)", tfm.strip())
                        if number:
                            add(".NET", number.group(1), where)
                else:
                    add(match.group(1), match.group(2), where)
    for rel in repo.files:
        name = rel.split("/")[-1].lower()
        text = repo.text(rel) if (name.startswith("requirements") or name == ".python-version"
                                  or name.startswith("dockerfile") or rel.startswith(".github/workflows/")) else None
        if not text:
            continue
        if name.startswith("requirements"):
            for number, line in enumerate(text.splitlines(), 1):
                pin = re.match(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)(?:\[[^\]]*\])?\s*==\s*([\w.]+)", line)
                if pin:
                    add(pin.group(1), pin.group(2), f"{rel}:{number}")
        elif name == ".python-version":
            add("Python", text.strip().splitlines()[0], f"{rel}:1")
        else:
            for match in re.finditer(r"python-version:\s*[\"']?([\d.]+)|FROM\s+python:([\d.]+)", text):
                add("Python", match.group(1) or match.group(2), f"{rel}:{line_of(text, match.start())}")
            for match in re.finditer(r"dotnet-version:\s*[\"']?([\d.]+)|mcr\.microsoft\.com/dotnet/\w+:([\d.]+)", text):
                add(".NET", match.group(1) or match.group(2), f"{rel}:{line_of(text, match.start())}")
    repo.facts["versions"] = found
    return found


def _version_parts(version: str) -> list[int]:
    return [int(p) for p in re.findall(r"\d+", version)]


def versions_match(readme: str, code: str, minimum: bool) -> bool:
    r, c = _version_parts(readme), _version_parts(code)
    n = min(len(r), len(c))
    return c[:len(r)] >= r if minimum else r[:n] == c[:n]


def check_versions(repo: Repo) -> list[Item]:
    versions = code_versions(repo)
    if not versions:
        return []
    names = sorted(set(versions), key=len, reverse=True)
    pattern = re.compile(r"(?<![\w.])(" + "|".join(re.escape(n) for n in names) + r")\s*(?:v|version\s*)?(\d+(?:\.\d+)*)(\+)?",
                         re.IGNORECASE)
    items = []
    for index, line in enumerate(repo.readme):
        for match in pattern.finditer(line):
            name, version, plus = match.group(1).lower(), match.group(2), bool(match.group(3))
            known = versions.get(name, [])
            if known and not any(versions_match(version, v, plus) for v, _ in known):
                have = ", ".join(sorted({v for v, _ in known}))
                items.append(Item(repo.sections[index], "VERSION-MISMATCH", repo.where(index),
                                  f"README says {match.group(1)} {version}; code has {have} ({known[0][1]})"))
    return items


def _tracked(repo: Repo, path: str) -> bool:
    path = path.strip("/")
    if path.startswith("./"):
        path = path[2:]
    if "/" not in path and any(f.split("/")[-1] == path for f in repo.files):
        return True
    return path in repo.files or any(f.startswith(path + "/") or f.endswith("/" + path) for f in repo.files)


def check_paths(repo: Repo) -> list[Item]:
    packages = {n for n in code_versions(repo)} | {n.split("[")[0].lower() for n in _requirement_names(repo)}
    candidates = []
    for index, text, in_code in repo.tokens():
        if in_code:
            continue
        token = text[2:] if text.startswith("./") else text
        if (not re.fullmatch(r"[\w.-]+(?:/[\w.-]+)*/?", token) or token.startswith((".env", "."))
                and "/" not in token):
            continue
        ext = token.rsplit(".", 1)[-1].lower() if "." in token.split("/")[-1] else ""
        has_ext = ext in FILE_EXTS and ext not in ("db", "log")
        server_only = re.fullmatch(r"appsettings\.\w+\.json", token.split("/")[-1]) and "appsettings.json" in {
            f.split("/")[-1] for f in repo.files}
        if ("/" in token or has_ext) and token.lower() not in packages and not server_only:
            candidates.append((index, token))
    for index, line in enumerate(repo.readme):
        for match in LINK_TARGET.finditer(line):
            target = match.group(1).split("#")[0]
            if target and not re.match(r"^(\w+:|/|#|<)", target):
                candidates.append((index, target))
    items = []
    for index, token in candidates:
        if _tracked(repo, token):
            continue
        if subprocess.run(["git", "-C", repo.root, "check-ignore", "-q", "--no-index", token.lstrip("/")]).returncode == 0:
            continue
        items.append(Item(repo.sections[index], "PATH-STALE", repo.where(index), f"{token} is not in the repository"))
    return items


def _requirement_names(repo: Repo) -> list[str]:
    names = []
    for rel in repo.files:
        if rel.split("/")[-1].lower().startswith("requirements") and rel.endswith(".txt"):
            names += re.findall(r"(?m)^\s*([A-Za-z0-9][A-Za-z0-9._\[\]-]*)", repo.text(rel) or "")
    return names


CHECKS.extend([check_commands, check_routes, check_versions, check_paths])
````

- [ ] **Step 4: Run the tests and confirm they pass**

Run: `python -m unittest discover -s "$SKILL/scripts" -p "test_readme_facts.py" -v`
Expected: `Ran 16 tests` and `OK`

- [ ] **Step 5: Lint and leave uncommitted**

Run: `python -m flake8 --max-line-length=127 "$SKILL/scripts"`
Expected: no output. Do not stage or commit.

### Task 5: Deployment, license, repository URL and section checks

**Files:**
- Modify: `scripts/readme_facts.py` (insert the block above the `if __name__ == "__main__":` line)
- Test: `scripts/test_readme_facts.py` (add `DeploymentLicenseSectionsTests` above the `if __name__ == "__main__":` line)

**Interfaces:**
- Consumes: Task 1 foundation (`HEADING`, `SECTION_KEYWORDS`); `code_commands` from Task 2; `ENV_TOKEN` from Task 3; `code_routes` and `FRAMEWORK_ROUTES` from Task 4.
- Produces: `workflow_secrets(repo) -> dict[str, str]`; `check_secrets(repo)`; `check_license(repo)`; `check_repo_url(repo)`; `check_sections(repo)`.

- [ ] **Step 1: Write the failing tests**

Add to `scripts/test_readme_facts.py`:

````python
class DeploymentLicenseSectionsTests(unittest.TestCase):
    def test_secrets_undocumented_and_stale(self):
        files = {
            ".github/workflows/deploy.yml": "env:\n  A: ${{ secrets.BOT_TOKEN }}\n  B: ${{ secrets.DEPLOY_KEY }}\n",
            "config.py": 'import os\nL = os.getenv("Bot_LOG_FILE")\n',
            "README.md": "# Bot\n## Deployment\n### Required secrets\n| `BOT_TOKEN` | token |\n| `Bot_LOG_FILE` | log |\n",
        }
        self.assertEqual(checks(rf.check_secrets, files), [
            ("SECRET-UNDOCUMENTED", ".github/workflows/deploy.yml:3", "secret DEPLOY_KEY is not in the README"),
            ("SECRET-STALE", "README.md:5", "Bot_LOG_FILE is not a workflow secret"),
        ])

    def test_license_mismatch(self):
        files = {"LICENSE": "Apache License\nVersion 2.0, January 2004\n", "README.md": "# Bot\n## License\nMIT\n"}
        self.assertEqual(checks(rf.check_license, files),
                         [("LICENSE-MISMATCH", "README.md:3", "README names MIT; LICENSE is Apache")])

    def test_repo_url_mismatch_and_placeholder(self):
        readme = ("# Bot\n## Setup\ngit clone https://github.com/your-org/Bot.git\n"
                  "[CI](https://github.com/Sam/Bot/actions) uses [discord.py](https://github.com/Rapptz/discord.py)\n")
        with make_repo({"README.md": readme}) as root:
            subprocess.run(["git", "-C", root, "remote", "add", "origin", "https://github.com/Sam/Bot.git"], check=True)
            found = [(i.check, i.location, i.detail) for i in rf.check_repo_url(rf.load_repo(root))]
        self.assertEqual(found, [("REPO-URL-MISMATCH", "README.md:3",
                                  "github.com/your-org/Bot should be github.com/Sam/Bot")])

    def test_sections_missing_for_a_python_bot(self):
        files = {"cogs/polls.py": BOT, "README.md": "# Bot\n## Features\n## Setup\n## Commands\n"}
        with make_repo(files) as root:
            sections = [i.section for i in rf.check_sections(rf.load_repo(root))]
        self.assertEqual(sections, ["configuration", "deployment", "development", "license"])
````

- [ ] **Step 2: Run the tests and confirm they fail**

Run: `python -m unittest discover -s "$SKILL/scripts" -p "test_readme_facts.py" -v`
Expected: `Ran 20 tests`, `FAILED (errors=4)`, with `AttributeError` for `check_secrets`, `check_license`, `check_repo_url` and `check_sections`

- [ ] **Step 3: Write the implementation**

Insert above `if __name__ == "__main__":`:

````python
SECRET_REF = re.compile(r"secrets\.([A-Za-z_][A-Za-z0-9_]*)")
LICENSE_FAMILIES = [("Apache", r"\bapache\b"), ("LGPL", r"\blgpl\b|lesser general public"),
                    ("GPL", r"\bgpl\b|general public license"), ("MIT", r"\bmit\b"),
                    ("MPL", r"\bmpl\b|mozilla public"), ("BSD", r"\bbsd\b"), ("Unlicense", r"\bunlicense\b")]
GITHUB_URL = re.compile(r"github\.com[/:]([\w.<>-]+)/([\w.-]+?)(?:\.git)?(?=[/)\s\"'#?`>\]]|$)")
PLACEHOLDER_OWNERS = {"your-org", "your-username", "yourusername", "username", "user", "owner", "your-name", "yourname", "org"}


def workflow_secrets(repo: Repo) -> dict:
    if "secrets" in repo.facts:
        return repo.facts["secrets"]
    found = {}
    for rel in repo.files:
        if rel.startswith(".github/workflows/") and rel.endswith((".yml", ".yaml")):
            text = repo.text(rel) or ""
            for match in SECRET_REF.finditer(text):
                if match.group(1) != "GITHUB_TOKEN":
                    found.setdefault(match.group(1), f"{rel}:{line_of(text, match.start())}")
    repo.facts["secrets"] = found
    return found


def check_secrets(repo: Repo) -> list[Item]:
    secrets = workflow_secrets(repo)
    if not any(section == "deployment" for _, section, _ in repo.top_headings):
        return []
    items = []
    for name, location in sorted(secrets.items()):
        if name not in repo.readme_text:
            items.append(Item("deployment", "SECRET-UNDOCUMENTED", location, f"secret {name} is not in the README"))
    corpus = repo.corpus()
    nearest = ""
    for index, line in enumerate(repo.readme):
        heading = HEADING.match(line) if not repo.code_lines[index] else None
        if heading:
            nearest = heading.group(2)
        if repo.sections[index] != "deployment" or not ("secret" in nearest.lower() or "secret" in line.lower()):
            continue
        for match in ENV_TOKEN.finditer(line):
            token = match.group(1)
            if token not in secrets and token in corpus:
                items.append(Item("deployment", "SECRET-STALE", repo.where(index), f"{token} is not a workflow secret"))
    return items


def _license_family(text: str):
    lowered = text.lower()
    for family, pattern in LICENSE_FAMILIES:
        if re.search(pattern, lowered):
            return family
    return None


def check_license(repo: Repo) -> list[Item]:
    files = [f for f in repo.files if "/" not in f and f.lower().startswith("license")]
    if not files:
        return []
    head = "\n".join((repo.text(files[0]) or "").strip().splitlines()[:3])
    family = _license_family(head)
    if family:
        repo.facts["license"] = [family]
    in_section = [i for i, s in enumerate(repo.sections) if s == "license"]
    lines = in_section or [i for i, line in enumerate(repo.readme) if "license" in line.lower()]
    for index in lines:
        named = _license_family(repo.readme[index])
        if family and named and named != family:
            return [Item(repo.sections[index], "LICENSE-MISMATCH", repo.where(index),
                         f"README names {named}; {files[0]} is {family}")]
    return []


def check_repo_url(repo: Repo) -> list[Item]:
    url = git(repo.root, "remote", "get-url", "origin").strip()
    origin = re.search(r"github\.com[/:]([\w.-]+)/([\w.-]+?)(?:\.git)?/?$", url)
    if not origin:
        return []
    owner, name = origin.group(1).lower(), origin.group(2).lower()
    repo.facts["origin"] = [f"{owner}/{name}"]
    items = []
    for index, line in enumerate(repo.readme):
        for match in GITHUB_URL.finditer(line):
            found_owner, found_name = match.group(1).lower(), match.group(2).lower()
            placeholder = found_owner in PLACEHOLDER_OWNERS or "<" in found_owner
            if (found_name == name or placeholder) and (found_owner, found_name) != (owner, name):
                expected = f"github.com/{origin.group(1)}/{origin.group(2)}"
                items.append(Item(repo.sections[index], "REPO-URL-MISMATCH", repo.where(index),
                                  f"github.com/{match.group(1)}/{match.group(2)} should be {expected}"))
    return items


def check_sections(repo: Repo) -> list[Item]:
    wanted = ["features", "setup", "configuration"]
    if repo.python and code_commands(repo):
        wanted.append("commands")
    if repo.dotnet and any(r.lower() not in FRAMEWORK_ROUTES for r in code_routes(repo)):
        wanted.append("routes")
    wanted += ["deployment", "development", "license"]
    present = {section for _, section, _ in repo.top_headings if section}
    return [Item(section, "SECTION-MISSING", "README.md:1",
                 f"no {section} section (a top-level heading containing: {', '.join(SECTION_KEYWORDS[section])})")
            for section in wanted if section not in present]


CHECKS.extend([check_secrets, check_license, check_repo_url, check_sections])
````

- [ ] **Step 4: Run the tests and confirm they pass**

Run: `python -m unittest discover -s "$SKILL/scripts" -p "test_readme_facts.py" -v`
Expected: `Ran 20 tests` and `OK`

- [ ] **Step 5: Lint and leave uncommitted**

Run: `python -m flake8 --max-line-length=127 "$SKILL/scripts"`
Expected: no output. Do not stage or commit.

### Task 6: Change window

**Files:**
- Modify: `scripts/readme_facts.py` (insert the block above the `if __name__ == "__main__":` line)
- Test: `scripts/test_readme_facts.py` (add `ChangeWindowTests` above the `if __name__ == "__main__":` line)

**Interfaces:**
- Consumes: `git`, `SKIP_PARTS`, `CODE_EXTS` from Task 1; `code_commands` (Task 2), `env_reads` (Task 3) and `code_routes` (Task 4); the `commit` and `write` test helpers.
- Produces: `sections_for(repo, path) -> list[tuple[str, str]]`; `check_change_window(repo) -> list[Item]` printing `SINCE` always and `CHANGED` lines when `repo.since` is set.

- [ ] **Step 1: Write the failing tests**

Add to `scripts/test_readme_facts.py`:

````python
class ChangeWindowTests(unittest.TestCase):
    def test_since_without_readme_or_commit(self):
        with make_repo({"a.py": "x = 1\n"}) as root:
            self.assertEqual([i.detail for i in rf.check_change_window(rf.load_repo(root))], ["README.md does not exist"])
            write(root, {"README.md": "# X\n"})
            self.assertEqual([i.detail for i in rf.check_change_window(rf.load_repo(root))], ["README.md has no commit"])

    def test_since_auto_lists_changed_files_by_section(self):
        with make_repo({"README.md": "# Bot\nline\n", "bot.py": "x = 1\n"}) as root:
            commit(root, "readme")
            write(root, {"cogs/polls.py": BOT, ".github/workflows/deploy.yml": "on: push\n"})
            commit(root, "code")
            items = rf.check_change_window(rf.load_repo(root, since="auto"))
        self.assertRegex(items[0].detail, r"^\d{4}-\d{2}-\d{2} \+2 -0 README lines, 2 files changed since$")
        self.assertEqual([(i.section, i.check, i.location) for i in items[1:]], [
            ("deployment", "CHANGED", ".github/workflows/deploy.yml"),
            ("commands", "CHANGED", "cogs/polls.py"),
        ])
````

- [ ] **Step 2: Run the tests and confirm they fail**

Run: `python -m unittest discover -s "$SKILL/scripts" -p "test_readme_facts.py" -v`
Expected: `Ran 22 tests`, `FAILED (errors=2)`, with `AttributeError: module 'readme_facts' has no attribute 'check_change_window'`

- [ ] **Step 3: Write the implementation**

Insert above `if __name__ == "__main__":`:

````python
def sections_for(repo: Repo, path: str) -> list[tuple[str, str]]:
    name = path.split("/")[-1].lower()
    out = []
    if any(loc.split(":")[0] == path for loc in code_commands(repo).values()):
        out.append(("commands", "defines commands"))
    if (any(loc.split(":")[0] == path for loc in env_reads(repo).values())
            or re.match(r"^(config(\.[\w-]+)?\.ya?ml|appsettings(\.[\w-]+)?\.json|\.env\.example)$", name)):
        out.append(("configuration", "reads env vars or config"))
    if any(loc.split(":")[0] == path for loc in code_routes(repo).values()):
        out.append(("routes", "defines routes"))
    if path.startswith(".github/workflows/") or name.startswith(("dockerfile", "docker-compose")):
        out.append(("deployment", "deployment file"))
    if re.match(r"^(requirements.*\.txt|pyproject\.toml|.*\.csproj|\.python-version|(bot|main|app)\.py|program\.cs)$", name):
        out.append(("setup", "dependencies or entry point"))
    if "test" in path.lower() and name.endswith((".py", ".cs", ".csproj")):
        out.append(("development", "tests"))
    if name.startswith("license"):
        out.append(("license", "license file"))
    if not out and name.endswith(CODE_EXTS):
        out.append(("features", "code"))
    return out


def check_change_window(repo: Repo) -> list[Item]:
    log = git(repo.root, "log", "-1", "--format=%H %h %ad", "--date=short", "--", "README.md").split()
    if not log:
        state = "README.md has no commit" if repo.has_readme else "README.md does not exist"
        return [Item("meta", "SINCE", "none", state)]
    full, short, date = log
    stat = git(repo.root, "show", "--numstat", "--format=", full, "--", "README.md").split()
    added, removed = (stat[0], stat[1]) if len(stat) >= 2 else ("0", "0")
    changed = [p for p in git(repo.root, "diff", "--name-only", full).splitlines()
               if p != "README.md" and not any(part in SKIP_PARTS for part in p.split("/")[:-1])]
    items = [Item("meta", "SINCE", short, f"{date} +{added} -{removed} README lines, {len(changed)} files changed since")]
    if repo.since:
        for path in changed:
            for section, why in sections_for(repo, path):
                items.append(Item(section, "CHANGED", path, why))
    return items


CHECKS.append(check_change_window)
````

- [ ] **Step 4: Run the tests and confirm they pass**

Run: `python -m unittest discover -s "$SKILL/scripts" -p "test_readme_facts.py" -v`
Expected: `Ran 22 tests` and `OK`

- [ ] **Step 5: Lint and leave uncommitted**

Run: `python -m flake8 --max-line-length=127 "$SKILL/scripts"`
Expected: no output. Do not stage or commit.

### Task 7: Script replay on pre-rewrite snapshots

**Files:**
- None in the skill. Scratch only: `$SCRATCH/replay/{dvd,dsa,bytecraft,samelhag,usvotemap}` and `$SCRATCH/replay/*.facts.txt`

**Interfaces:**
- Consumes: the finished `scripts/readme_facts.py` from Task 6.
- Produces: the five replay clones reused by Tasks 11 and 12, and the recorded fact lists.

Snapshots (verified 2026-09-14):

| Clone | Repo | Commit | Why this commit |
|---|---|---|---|
| `dvd` | DiscordVoiceDatabase | `bcc255c` | Parent of `2403ab4`, the 2026-09-12 README rewrite |
| `dsa` | DiscordServerAudit | `49541cc` | Parent of `5fe06cb`, the 2026-09-12 README rewrite |
| `bytecraft` | bytecraft.us | `e9ac0f9` | Parent of `1f098e6`, the 2026-09-12 README rewrite |
| `samelhag` | samelhag.dev | `829f079` | Parent of `56f40c7`, the 2026-09-12 README rewrite |
| `usvotemap` | usvotemap.dev | `8e42372` | Current head when planned; the repo has no README |

- [ ] **Step 1: Clone the snapshots (the user's repos are only read)**

````bash
mkdir -p "$SCRATCH/replay" && cd "$SCRATCH/replay"
for spec in "DiscordVoiceDatabase dvd bcc255c" "DiscordServerAudit dsa 49541cc" "bytecraft.us bytecraft e9ac0f9" "samelhag.dev samelhag 829f079" "usvotemap.dev usvotemap 8e42372"; do
  set -- $spec
  git clone -q --no-hardlinks --no-checkout "$REPOS/$1" "$2" && git -C "$2" checkout -q "$3"
  git -C "$2" remote set-url origin "$(git --no-optional-locks -C "$REPOS/$1" remote get-url origin)"
done
for r in DiscordVoiceDatabase DiscordServerAudit bytecraft.us samelhag.dev usvotemap.dev; do git --no-optional-locks -C "$REPOS/$r" status --short; done
````

Expected: the final status loop prints nothing. The origin URLs are copied so `REPO-URL-MISMATCH` compares against GitHub, not the local path the clone came from.

- [ ] **Step 2: Run readme_facts on every snapshot**

````bash
cd "$SCRATCH/replay"
for c in dvd dsa bytecraft samelhag usvotemap; do python "$SKILL/scripts/readme_facts.py" $c --since auto > $c.facts.txt; echo "$c exit=$?"; grep -P "\tSINCE\t|^summary" $c.facts.txt; done
````

Expected:
````
dvd exit=0
meta	SINCE	a647574	2026-06-12 +109 -60 README lines, 30 files changed since
summary	facts=57 drift=14 not_checked=0
dsa exit=0
meta	SINCE	a7a4519	2026-07-05 +1 -1 README lines, 44 files changed since
summary	facts=107 drift=9 not_checked=0
bytecraft exit=0
meta	SINCE	7caf170	2026-09-11 +42 -11 README lines, 4 files changed since
summary	facts=14 drift=12 not_checked=0
samelhag exit=0
meta	SINCE	93defcf	2026-09-11 +0 -2 README lines, 90 files changed since
summary	facts=30 drift=13 not_checked=0
usvotemap exit=0
meta	SINCE	none	README.md does not exist
summary	facts=22 drift=9 not_checked=0
````

- [ ] **Step 3: Confirm the mechanical known answers**

````bash
cd "$SCRATCH/replay"
grep -hE "favoriteslist|WHISPER_MODEL|LOG_LEVEL|'sync'|your-username" dvd.facts.txt
grep -hE "bot\.token|gemini_key|APP_ROOT|DB_PATH" dsa.facts.txt
grep -hP "your-org|\tHost is|\tPort is|EnableSsl" bytecraft.facts.txt
grep -hE "MudBlazor 8\.0" samelhag.facts.txt
grep -c SECTION-MISSING usvotemap.facts.txt
````

Expected:
````
features	CMD-STALE	README.md:15	/favoriteslist matches no command in code
setup	REPO-URL-MISMATCH	README.md:36	github.com/your-username/DiscordVoiceDatabase should be github.com/SamElhagDev/DiscordVoiceDatabase
configuration	ENV-UNDOCUMENTED	config.py:59	env var DiscordVoiceDatabase_WHISPER_MODEL is not in the README
configuration	ENV-UNDOCUMENTED	config.py:65	env var DiscordVoiceDatabase_LOG_LEVEL is not in the README
commands	CMD-STALE	README.md:138	/favoriteslist matches no command in code
commands	CMD-UNDOCUMENTED	cogs/owner.py:60	command 'sync' is not in the README
setup	CONFIG-KEY-STALE	README.md:40	bot.token is shown in a README yaml block but config.yaml has no such key
setup	CONFIG-KEY-STALE	README.md:47	gemini_key is shown in a README yaml block but config.yaml has no such key
configuration	ENV-UNDOCUMENTED	bot.py:24	env var DiscordServerAudit_APP_ROOT is not in the README
configuration	ENV-UNDOCUMENTED	database/connection.py:15	env var DiscordServerAudit_DB_PATH is not in the README
setup	CONFIG-KEY-STALE	README.md:79	Host is not a key in appsettings.json
setup	CONFIG-KEY-STALE	README.md:79	Port is not a key in appsettings.json
setup	CONFIG-KEY-STALE	README.md:79	EnableSsl is not a key in appsettings.json
setup	REPO-URL-MISMATCH	README.md:63	github.com/your-org/bytecraft.us should be github.com/SamElhagDev/bytecraft.us
features	VERSION-MISMATCH	README.md:49	README says MudBlazor 8.0; code has 9.6.0 (samelhag.dev/samelhag.dev.csproj:13)
6
````

If any expected line is missing, stop and use superpowers:systematic-debugging on the check before continuing.

- [ ] **Step 4: Record the counts for Task 11**

````bash
cd "$SCRATCH/replay" && for c in dvd dsa bytecraft samelhag usvotemap; do echo "== $c"; grep -vP "\t(CHANGED|SINCE)\t|^summary" $c.facts.txt | cut -f2 | sort | uniq -c; done
````

Expected:
````
== dvd
      2 CMD-STALE
      7 CMD-UNDOCUMENTED
      2 ENV-UNDOCUMENTED
      1 REPO-URL-MISMATCH
      2 SECTION-MISSING
== dsa
      2 CONFIG-KEY-STALE
      1 CONFIG-KEY-UNDOCUMENTED
      2 ENV-UNDOCUMENTED
      1 SECRET-STALE
      3 SECTION-MISSING
== bytecraft
      3 CONFIG-KEY-STALE
      1 CONFIG-KEY-UNDOCUMENTED
      1 REPO-URL-MISMATCH
      3 ROUTE-UNDOCUMENTED
      4 SECTION-MISSING
== samelhag
      2 ENV-UNDOCUMENTED
      6 ROUTE-UNDOCUMENTED
      4 SECTION-MISSING
      1 VERSION-MISMATCH
== usvotemap
      3 ENV-UNDOCUMENTED
      6 SECTION-MISSING
````

Keep these counts; Task 11 compares them with the drift lists the skill reports.

- [ ] **Step 5: Confirm the prose known answers exist in the snapshots**

````bash
cd "$SCRATCH/replay"
git -C dvd grep -n "tree.sync" -- '*.py'
grep -ci "sync" dvd/README.md
grep -n "All commands" dsa/README.md | cut -d: -f1
grep -c "Manage Server" dsa/README.md
git -C dsa grep -n "guild.invites()" -- cogs/info.py
grep -nE "Azure|CPU Usage|Compressed bundle" samelhag/README.md
grep -h "Deploy to IIS" samelhag/.github/workflows/*.yml
grep -n "one interactive island" bytecraft/README.md
git -C bytecraft grep -n "@rendermode InteractiveServer" -- '*.razor'
````

Expected:
````
cogs/owner.py:34:        await context.bot.tree.sync(guild=guild)
2
17
264
0
cogs/info.py:105:        invites = await ctx.guild.invites()
8:![Azure](https://img.shields.io/badge/Azure-Ready-0089D6?style=for-the-badge&logo=microsoftazure&logoColor=white)
53:| **Hosting** | .NET Aspire, Azure Ready |
90:- 💾 CPU Usage (idle): ~10%
91:- 📦 Compressed bundle: <1MB
    - name: Deploy to IIS
12:| Rendering | Static server-side rendering + enhanced navigation; one interactive island (the contact form) |
Components/Pages/ContactForm.razor:1:@rendermode InteractiveServer
Components/Pages/PopoverHost.razor:1:@rendermode InteractiveServer
````

These lines show the README claims Task 11 must report as Wrong: DiscordVoiceDatabase only syncs slash commands from an owner command and its README never mentions the step; DiscordServerAudit says all commands need the admin role (lines 17 and 264) and lists no Manage Server permission although `!listinvites` calls `guild.invites()`; samelhag.dev claims Azure hosting and unmeasured numbers while its workflow deploys to IIS; bytecraft.us names one interactive island while two components use `@rendermode InteractiveServer`. Nothing in the skill folder changes in this task.

### Task 8: Section guides: features, setup, configuration, commands

**Files:**
- Create: `sections/features.md`, `sections/setup.md`, `sections/configuration.md`, `sections/commands.md`
- Scratch harness (never in the skill): `$SCRATCH/harness/guide_lint.py`

**Interfaces:**
- Consumes: the check IDs from Tasks 2 to 6; the evidence from Task 7.
- Produces: `guide_lint.lint(skill_dir, name) -> list[str]`. Every guide has `## Facts`, `## Claims` and `## Filling`; its Facts section names its check IDs and `SECTION-MISSING`; its Filling section covers `Python bot` and `Blazor site` (commands covers only `Python bot`, routes only `Blazor site`); it stays under 400 words and has no em-dash.

- [ ] **Step 1: Write the guide lint and watch it fail**

Create `$SCRATCH/harness/guide_lint.py`:

````python
"""Scratch harness: lint readme-sync section guides. Not part of the skill."""
import os
import re
import sys

KNOWN_IDS = {"CMD-UNDOCUMENTED", "CMD-STALE", "ENV-UNDOCUMENTED", "ENV-STALE", "CONFIG-KEY-UNDOCUMENTED",
             "CONFIG-KEY-STALE", "ROUTE-UNDOCUMENTED", "ROUTE-STALE", "VERSION-MISMATCH", "PATH-STALE",
             "SECRET-UNDOCUMENTED", "SECRET-STALE", "LICENSE-MISMATCH", "REPO-URL-MISMATCH", "SECTION-MISSING",
             "NOT-CHECKED"}
REQUIRED_IDS = {
    "features": set(),
    "setup": {"VERSION-MISMATCH"},
    "configuration": {"ENV-UNDOCUMENTED", "ENV-STALE", "CONFIG-KEY-UNDOCUMENTED", "CONFIG-KEY-STALE"},
    "commands": {"CMD-UNDOCUMENTED", "CMD-STALE"},
    "routes": {"ROUTE-UNDOCUMENTED", "ROUTE-STALE"},
    "deployment": {"SECRET-UNDOCUMENTED", "SECRET-STALE"},
    "development": {"PATH-STALE"},
    "license": {"LICENSE-MISMATCH", "REPO-URL-MISMATCH"},
}
STACK_LABELS = {"commands": ["Python bot"], "routes": ["Blazor site"]}


def lint(skill_dir: str, name: str) -> list[str]:
    path = os.path.join(skill_dir, "sections", f"{name}.md")
    if not os.path.exists(path):
        return [f"missing sections/{name}.md"]
    text = open(path, encoding="utf-8").read()
    problems = [f"{name}.md lacks '{h}'" for h in ("## Facts", "## Claims", "## Filling") if h not in text]
    if chr(0x2014) in text:
        problems.append(f"{name}.md contains an em-dash")
    ids = set(re.findall(r"\b[A-Z]+(?:-[A-Z]+)+\b", text))
    problems += [f"{name}.md names unknown check id {i}" for i in sorted(ids - KNOWN_IDS)]
    facts = text.split("## Facts", 1)[-1].split("## Claims", 1)[0]
    problems += [f"{name}.md Facts lacks {i}" for i in sorted(REQUIRED_IDS[name] | {"SECTION-MISSING"}) if i not in facts]
    filling = text.split("## Filling", 1)[-1]
    problems += [f"{name}.md Filling lacks '{label}'" for label in STACK_LABELS.get(name, ["Python bot", "Blazor site"])
                 if label not in filling]
    words = len(text.split())
    if words > 400:
        problems.append(f"{name}.md has {words} words; keep it under 400")
    return problems


if __name__ == "__main__":
    skill_dir, names = sys.argv[1], sys.argv[2:]
    issues = [p for n in names for p in lint(skill_dir, n)]
    print("\n".join(issues) if issues else f"guide lint OK: {', '.join(names)}")
    sys.exit(1 if issues else 0)
````

Run: `python "$SCRATCH/harness/guide_lint.py" "$SKILL" features setup configuration commands`
Expected: four `missing sections/<name>.md` lines and exit code 1.

- [ ] **Step 2: Create `sections/features.md`**

````markdown
# Features Guide

## Facts

- No check belongs only to this section. README-side items on lines under headings that match no standard section (for example "Architecture", "Stack", "Access control") are reported as `features`: `CMD-STALE`, `ENV-STALE`, `CONFIG-KEY-STALE`, `ROUTE-STALE`, `VERSION-MISMATCH`, `PATH-STALE` and `REPO-URL-MISMATCH`. Handle each with the guide for its kind.
- `SECTION-MISSING` for features.
- `CHANGED` lines for features name code files that belong to no other section.

## Claims

- **Behavior:** read the code a claim describes and compare what it does. DiscordVoiceDatabase said auto-join used `/setchannel`; the code joins the busiest channel with an opted-in member.
- **Numbers:** keep limits, timings, sizes and performance figures only when the code defines them or the repo records the measurement; remove the rest. samelhag.dev listed "CPU Usage (idle): ~10%" and "Compressed bundle: <1MB" that were never measured.
- **Feature lists:** a listed feature the code no longer has is Stale; a user-facing feature the code has and the README never names is Missing. Commands and routes belong to their own guides.
- **Badges and taglines:** "Azure Ready" and similar badges are claims; check them against the deployment workflow.

## Filling

When `SECTION-MISSING` reports features, add the section right after the intro paragraph:

- **Python bot:** a short bullet list of what the bot does, one line per cog, taken from each cog's docstring and commands.
- **Blazor site:** a short bullet list of the main pages and interactive features (forms, simulations, command palettes), taken from the page components.
````

- [ ] **Step 3: Create `sections/setup.md`**

````markdown
# Setup Guide

## Facts

- `VERSION-MISMATCH`: change the version to the one the code pins. For a minimum such as `Python 3.10+`, change it only when the code needs a newer version.
- `SECTION-MISSING` for setup.

## Claims

- **Credentials:** the README names the env var or secret store the code reads. DiscordServerAudit showed the token in a `config.yaml` example while the code only reads `DiscordServerAudit_TOKEN`.
- **Intents:** privileged intents the README tells users to enable match `intents.<name> = True` in the code.
- **Invite permissions:** every permission the code needs is listed. `guild.invites()` needs Manage Server, `add_reaction` needs Add Reactions, and sending embeds needs Embed Links.
- **Run command:** the entry point it names exists and is the one the deploy workflow starts.
- **Slash commands:** when `setup_hook` never calls `tree.sync()`, setup includes the step that runs the bot's own sync command (DiscordVoiceDatabase: `!sync guild`).
- **Prerequisites:** match `TargetFramework`, `.python-version`, the workflow's `python-version` or the Dockerfile base image.

## Filling

When `SECTION-MISSING` reports setup:

- **Python bot:** numbered steps: install (`python -m pip install -r requirements.txt`), create the Discord application (intents and invite permissions from the code), configure (the variables in Configuration), run (the entry point), and sync slash commands when the bot does not sync on its own.
- **Blazor site:** prerequisites (the SDK from `TargetFramework`), configure (user secrets or `appsettings.json` values), and run locally (`dotnet run --project <project>`).
````

- [ ] **Step 4: Create `sections/configuration.md`**

````markdown
# Configuration Guide

## Facts

- `ENV-UNDOCUMENTED`: add the variable with its default and whether it is required, read from the line the item names.
- `ENV-STALE`: remove the name, or rename it when the code reads a renamed variable; `git log -S"<name>" --oneline -1` shows the commit that dropped it.
- `CONFIG-KEY-UNDOCUMENTED`: one item per config file lists every missing key; add them to the README's existing key reference in its format.
- `CONFIG-KEY-STALE`: rename or remove the key. For a key shown in a README code block, make the block match the config file.
- `SECTION-MISSING` for configuration: drop the item when another section already documents the settings, as bytecraft.us does under "Contact form".

## Claims

- **Defaults and required flags:** compare with the config loader and the `os.getenv` defaults.
- **Override claims:** "any setting can be overridden with an env var" must match the variables the loader maps; DiscordServerAudit mapped 11.
- **Examples:** `.env.example` lines and config snippets list only keys the code reads.

## Filling

When `SECTION-MISSING` reports configuration:

- **Python bot:** a table `| Variable | Required | Default | Purpose |` built from the env vars the code reads, then a key reference for `config.yaml` when the repo has one.
- **Blazor site:** the `appsettings.json` sections the app binds with `GetSection("...")`, which values belong in user secrets or environment variables, and any env vars the code reads.
````

- [ ] **Step 5: Create `sections/commands.md`**

````markdown
# Commands Guide

## Facts

- `CMD-UNDOCUMENTED`: add the command to the existing list or table in its format, with the description from `description=` or the docstring, written with the prefix the README already uses (`!`, `>` or `/`).
- `CMD-STALE`: remove it, or rename it when the code has a command with a close name (`/favoriteslist` became `/favoritesplay`).
- `SECTION-MISSING` for commands.

## Claims

- **Access:** "admin only", "owner only", "everyone" and "all commands require the admin role" against `@commands.has_permissions`, `@commands.is_owner`, role-check decorators and `cog_check`. DiscordServerAudit claimed every command needed the admin role while 12 stats commands had no check.
- **Descriptions:** what each command does, for commands in files named by `CHANGED` lines (every command in deep mode).
- **Usage:** parameters such as `<poll_id>` against the function signature.
- **Hybrid:** "works as both `!command` and `/command`" against `hybrid_command` and `hybrid_group`.

## Filling

When `SECTION-MISSING` reports commands:

- **Python bot:** one subsection per cog, each a table `| Command | Description | Access |`, with commands written in the bot's prefix and owner commands last.
````

- [ ] **Step 6: Run the guide lint and confirm it passes**

Run: `python "$SCRATCH/harness/guide_lint.py" "$SKILL" features setup configuration commands`
Expected: `guide lint OK: features, setup, configuration, commands`. Leave everything uncommitted.

### Task 9: Section guides: routes, deployment, development, license

**Files:**
- Create: `sections/routes.md`, `sections/deployment.md`, `sections/development.md`, `sections/license.md`

**Interfaces:**
- Consumes: `$SCRATCH/harness/guide_lint.py` and the guide format from Task 8.
- Produces: the last four guides.

- [ ] **Step 1: Watch the lint fail**

Run: `python "$SCRATCH/harness/guide_lint.py" "$SKILL" routes deployment development license`
Expected: four `missing sections/<name>.md` lines and exit code 1.

- [ ] **Step 2: Create `sections/routes.md`**

````markdown
# Routes Guide

## Facts

- `ROUTE-UNDOCUMENTED`: add the route to the README's routes table or page list with the component that declares it.
- `ROUTE-STALE`: remove it, or correct it to the route the component declares.
- `SECTION-MISSING` for routes: a "Pages" section that lists pages by name counts; add the routes there instead of a new section.

## Claims

- **Purpose:** each route's description against its component. File names often differ from routes: `ProjectShowcase.razor` serves `/projects/heat-transfer`.
- **Render modes:** "static SSR" and "one interactive island" against `@rendermode` in components and the `AddInteractive*` calls in `Program.cs`. bytecraft.us said only the contact form was interactive while `PopoverHost.razor` also used `@rendermode InteractiveServer`.
- **Error pages:** the error and not-found pages need no entry unless the README already lists them.

## Filling

When `SECTION-MISSING` reports routes:

- **Blazor site:** a table `| Route | Page | Purpose |` from the `@page` directives and the minimal API maps in `Program.cs`, home page first.
````

- [ ] **Step 3: Create `sections/deployment.md`**

````markdown
# Deployment Guide

## Facts

- `SECRET-UNDOCUMENTED`: add the secret to the README's secrets list with what the workflow uses it for.
- `SECRET-STALE`: the README lists a name as a GitHub secret that no workflow reads from `secrets.*`. Move it to the env var list when the code reads it; otherwise remove it.
- `SECTION-MISSING` for deployment.

## Claims

- **Hosting:** "Azure Ready", "Docker" and "IIS" claims against the workflows. samelhag.dev showed an Azure badge while its workflow deployed to IIS on a self-hosted runner.
- **Pipeline:** the trigger (push to `main`, manual dispatch), build, test and publish steps, target paths, and whether a Scheduled Task or IIS site is restarted, against each workflow file.
- **Docker:** instructions against `Dockerfile` and `docker-compose.yml`.

## Filling

When `SECTION-MISSING` reports deployment:

- **Python bot:** what triggers the workflow, where it copies the bot, how it registers and restarts the Scheduled Task, and a table of the required secrets.
- **Blazor site:** what triggers the workflow, the build and publish steps, the IIS site it deploys to, and the required secrets.
````

- [ ] **Step 4: Create `sections/development.md`**

````markdown
# Development Guide

## Facts

- `PATH-STALE`: change the path to the file's current location, or remove the reference when the file is gone.
- `SECTION-MISSING` for development.

## Claims

- **Tests:** the framework and command (`unittest` or `pytest` for `tests/`, `dotnet test` for test projects) match the CI workflow's test step.
- **Lint:** lint commands match the workflow, for example `flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics`.
- **Structure:** every directory in a project structure tree exists, and the main code directories appear.

## Filling

When `SECTION-MISSING` reports development:

- **Python bot:** how to run the tests and lint in the workflow's `python -m` form (`python -m unittest discover -s tests -t .`, `python -m flake8 ...`), and a short tree of top-level directories.
- **Blazor site:** `dotnet build`, `dotnet test` for each test project, and a short project layout.
````

- [ ] **Step 5: Create `sections/license.md`**

````markdown
# License Guide

## Facts

- `LICENSE-MISMATCH`: name the license the `LICENSE` file contains.
- `REPO-URL-MISMATCH`: use the owner and name from `git remote get-url origin`, keeping any path after the repository name.
- `SECTION-MISSING` for license.

## Claims

- **Links:** profile, company and contact links against the values the site or bot uses; samelhag.dev's README linked a different LinkedIn profile than the site.
- **Badges:** badges that point at the repository or its workflows match the origin URL and existing workflow files.

## Filling

When `SECTION-MISSING` reports license:

- **Python bot** and **Blazor site:** one sentence naming the license from `LICENSE`, linked to the file.
````

- [ ] **Step 6: Run the lint for all eight guides**

Run: `python "$SCRATCH/harness/guide_lint.py" "$SKILL" features setup configuration commands routes deployment development license`
Expected: `guide lint OK: features, setup, configuration, commands, routes, deployment, development, license`. Leave everything uncommitted.

### Task 10: SKILL.md orchestrator

**Files:**
- Create: `SKILL.md`
- Scratch harness: `$SCRATCH/harness/skill_lint.py`

**Interfaces:**
- Consumes: every guide from Tasks 8 and 9; `scripts/readme_facts.py`.
- Produces: the loadable skill.

- [ ] **Step 1: Write the skill lint and watch it fail**

Create `$SCRATCH/harness/skill_lint.py`:

````python
"""Scratch harness: lint readme-sync/SKILL.md against the spec. Not part of the skill."""
import os
import re
import sys

DESCRIPTION = ("Use when asked to update, sync, refresh, or check a repository's README against its current code, "
               "including requests to scan a project and update its readme")
TOOLS = {"Bash(git status *)", "Bash(git log *)", "Bash(git diff *)", "Bash(git ls-files *)",
         "Bash(git remote get-url *)", "Bash(python -m flake8 *)", "Bash(python -m py_compile *)",
         "Bash(python -m pytest *)", "Bash(python -m unittest *)", "Bash(dotnet build *)", "Bash(dotnet test *)"}
REQUIRED_TEXT = [
    "Apply these README changes? [yes / no / all except <numbers>]",
    "README.md has uncommitted changes; the sync edits will mix with them. Continue? [yes / no]",
    "No Python or .NET project found. readme-sync covers those two stacks.",
    "Deep sync reads <n> files (~<lines> lines). Continue? [yes / no]",
    "Last README change was small; older drift may remain.",
    "README matches the code.", "README updated.", "Changes are unstaged and uncommitted.",
    "scripts/readme_facts.py", "--since auto", "Not checked", "all except",
]


def lint(skill_dir: str) -> list[str]:
    path = os.path.join(skill_dir, "SKILL.md")
    if not os.path.exists(path):
        return ["missing SKILL.md"]
    text = open(path, encoding="utf-8").read()
    match = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not match:
        return ["no frontmatter"]
    front = match.group(1)
    problems = []
    if "name: readme-sync" not in front:
        problems.append("frontmatter name is not readme-sync")
    if f"description: {DESCRIPTION}" not in front:
        problems.append("frontmatter description differs from the spec")
    tools = set(re.findall(r"^\s+-\s+(Bash\(.+\))\s*$", front, re.M))
    if tools != TOOLS:
        problems.append(f"allowed-tools mismatch: missing {sorted(TOOLS - tools)}, extra {sorted(tools - TOOLS)}")
    problems += [f"missing text: {t}" for t in REQUIRED_TEXT if t not in text]
    for ref in sorted(set(re.findall(r"(?:sections|scripts)/[\w.-]+\.(?:md|py)", text))):
        if not os.path.exists(os.path.join(skill_dir, ref)):
            problems.append(f"references missing file {ref}")
    if chr(0x2014) in text:
        problems.append("contains an em-dash")
    if "DESIGN.md" in text or "PLAN.md" in text:
        problems.append("references DESIGN.md or PLAN.md")
    words = len(text.split())
    if words > 850:
        problems.append(f"{words} words; keep it under about 800")
    return problems


if __name__ == "__main__":
    issues = lint(sys.argv[1])
    print("\n".join(issues) if issues else "skill lint OK")
    sys.exit(1 if issues else 0)
````

Run: `python "$SCRATCH/harness/skill_lint.py" "$SKILL"`
Expected: `missing SKILL.md` and exit code 1.

- [ ] **Step 2: Create `SKILL.md`**

````markdown
---
name: readme-sync
description: Use when asked to update, sync, refresh, or check a repository's README against its current code, including requests to scan a project and update its readme
allowed-tools:
  - Bash(git status *)
  - Bash(git log *)
  - Bash(git diff *)
  - Bash(git ls-files *)
  - Bash(git remote get-url *)
  - Bash(python -m flake8 *)
  - Bash(python -m py_compile *)
  - Bash(python -m pytest *)
  - Bash(python -m unittest *)
  - Bash(dotnet build *)
  - Bash(dotnet test *)
---

# README Sync

## Overview

Brings the repository-root `README.md` in line with the code of a Python or .NET project: one drift list, one approval, then edits in the README's own style. Nothing is staged or committed.

## Sequence

1. **Stacks:** Python when `requirements*.txt`, `pyproject.toml` or `.py` files exist; .NET when `*.csproj`, `*.sln` or `*.slnx` exist. Neither: reply `No Python or .NET project found. readme-sync covers those two stacks.` and stop.
2. **Working tree:** if `git status --short -- README.md` lists the file, ask `README.md has uncommitted changes; the sync edits will mix with them. Continue? [yes / no]`
3. **Facts:** run `python "<skill base directory>/scripts/readme_facts.py" <repo root> --since auto`, or without `--since auto` for "deep readme sync". Every line is a candidate; confirm it by reading before it becomes drift.
   - `SINCE none README.md does not exist`: skip step 4 and propose `Create README.md with: <sections>`, built from the facts, entry points and workflows.
   - `SINCE none README.md has no commit`: use deep mode.
4. **Claims:** quick mode reads the README sections named by `CHANGED` lines and the files those lines name. Deep mode first asks `Deep sync reads <n> files (~<lines> lines). Continue? [yes / no]`, then checks every claim. Each section's guide says what to verify and how to fill a missing section.
5. **Commands:** run the build, test and lint commands the README documents (`dotnet build`, `dotnet test`, `python -m unittest ...`, `python -m pytest ...`, `python -m flake8 ...`; bare `pytest` and `flake8` in `python -m` form). Never run install, run, Docker or deploy commands; check those against the code. A command that cannot start (missing project, path or option) is drift. A missing tool, unreachable NuGet, compile error or failing test goes under Not checked.
6. **Drift list**, then **edit**, then **verify**, as below.

| Section | Guide |
|---|---|
| Features | `sections/features.md` |
| Setup | `sections/setup.md` |
| Configuration | `sections/configuration.md` |
| Commands (bots) | `sections/commands.md` |
| Routes (sites) | `sections/routes.md` |
| Deployment | `sections/deployment.md` |
| Development | `sections/development.md` |
| License | `sections/license.md` |

## Drift List

```
README SYNC: <repo>
  Mode: <quick|deep>  |  README last changed <date> (<sha>), <k> files changed since
  Checked: <n> facts · <command> (<ok|failed>)
  Not checked: <tools, files or commands, when any>

<Section>
  <n>. <Missing|Stale|Wrong|Mismatch|Failing command|Add>  <what is wrong, with the fix>   <evidence location>

Apply these README changes? [yes / no / all except <numbers>]
```

- Number items across the whole list so `all except 3, 7` is unambiguous.
- In quick mode, when `SINCE` shows 5 or fewer README lines changed, add under the header: `Last README change was small; older drift may remain. Say "deep readme sync" to check every claim.`
- With no drift, print the header and `README matches the code.` with no prompt.

## Editing Rules

- Change only approved items and leave every other word alone.
- Fix a wrong fact inside its own sentence, table row or list item.
- Fill lists and tables in their existing format and order; descriptions and defaults come from the code.
- Add a missing section at its standard position (Features, Setup, Configuration, Commands or Routes, Deployment, Development, License) with the README's heading level, emoji style and list style.
- Remove claims that cannot be verified instead of inventing values.
- Write env var and secret names, never their values.

## Verification

Rerun `readme_facts.py` in the same mode and any documented command the edit changed, then print:

```
README updated.
  Applied : <n> of <m> (left out: <numbers>)
  Facts   : drift <before> → <after>
  Commands: <command> (<result>)
  Diff    : README.md +<added> −<removed>
Changes are unstaged and uncommitted.
```

Only left-out items may remain in the rerun. Name any approved item that still appears; do not retry.
````

- [ ] **Step 3: Run the skill lint and confirm it passes**

Run: `python "$SCRATCH/harness/skill_lint.py" "$SKILL"` and `wc -w "$SKILL/SKILL.md"`
Expected: `skill lint OK`, and 708 words.

- [ ] **Step 4: Confirm the skill registers**

Expected: a system notice listing `readme-sync` with the spec description appears after the file is created. If it does not appear, start a new session in `C:\Users\Sam Elhag.EREF\.claude\skills` and confirm `/readme-sync` is listed. Stop here and report; Tasks 11 to 13 run in a new session. Leave everything uncommitted.

### Task 11: Full replay syncs and cost measurement

**Files:**
- None in the skill unless a known answer is missed (Step 9). Scratch: `$SCRATCH/harness/usage_now.py`, `$SCRATCH/replay/<clone>.<mode>.drift.txt`, `$SCRATCH/replay/costs.md`

**Interfaces:**
- Consumes: the finished skill (Tasks 1 to 10), the replay clones and counts (Task 7).
- Produces: saved drift lists and measured costs used by Tasks 12 and 13.

Run Tasks 11 to 13 in a new session opened in `C:\Users\Sam Elhag.EREF\.claude\skills`, so token counts are comparable with the 2026-09-12 sessions and the skill loads from the finished files. For every sync, treat the clone as the repository: run commands with the clone as the working directory, pass the clone as the Grep path, and pass it as `readme_facts.py`'s root. At every `Apply these README changes?` prompt in this task, answer `no`.

Known answers. The files behind every prose answer fall inside its snapshot's change window, so quick mode must find them:

| Run | Must appear in the drift list | Recorded only |
|---|---|---|
| `dvd` quick | Stale `/favoriteslist`; Missing `favoritesplay`, `sync` and the other owner commands; Missing `DiscordVoiceDatabase_WHISPER_MODEL` and `DiscordVoiceDatabase_LOG_LEVEL`; the `your-username` clone URL; Add Deployment and Development; Missing slash-command sync step in Setup | How it judges the auto-join description |
| `dsa` quick | The small-change warning; Stale `bot.token` and `gemini_key` in the `config.yaml` example; Missing `DiscordServerAudit_APP_ROOT` and `DiscordServerAudit_DB_PATH`; Missing config keys (one item); Wrong "All commands require the admin role" (12 stats commands have no role check); Missing Manage Server in the invite permissions | What it does with `DiscordServerAudit_LOG_FILE` listed as a secret |
| `dsa` deep | `Deep sync reads <n> files (~<lines> lines). Continue? [yes / no]` first (answer `yes`), then everything from `dsa` quick | Extra drift deep mode finds |
| `samelhag` quick | The small-change warning; Mismatch `MudBlazor 8.0`; Wrong "Azure Ready" (the workflow deploys to IIS); the unmeasured CPU and bundle-size numbers marked for removal; Missing routes | Add items for Configuration, Routes, Deployment, Development; the LinkedIn link |
| `bytecraft` quick | The `your-org` clone URL; Stale `Host`, `Port` and `EnableSsl`; Wrong "one interactive island" (`PopoverHost.razor` also uses `@rendermode InteractiveServer`); Missing `/about`, `/contact` and `/services` | Add items |
| `usvotemap` quick | `Create README.md with:` Features, Setup, Configuration, Deployment, Development and License, with `KALSHI_API_KEY_ID`, `KALSHI_PRIVATE_KEY_PATH` and `DATAVERSE_API_TOKEN` under Configuration | |

- [ ] **Step 0: Prepare this session's scratch folder**

A new session has its own scratchpad, so recreate what earlier tasks left in the old one:
1. Run Task 7 Step 1 and Task 7 Step 2; expect the same outputs listed there.
2. Create `$SCRATCH/harness/guide_lint.py` with the exact contents in Task 8 Step 1 and `$SCRATCH/harness/skill_lint.py` with the exact contents in Task 10 Step 1.
3. Run `python "$SCRATCH/harness/guide_lint.py" "$SKILL" features setup configuration commands routes deployment development license` and `python "$SCRATCH/harness/skill_lint.py" "$SKILL"`; expect both OK lines.

- [ ] **Step 1: Create the usage counter**

Create `$SCRATCH/harness/usage_now.py`:

````python
"""Scratch harness: tokens used so far by the newest session in this project, counting each API response once."""
import glob
import json
import os

folder = os.path.expanduser(r"~/.claude/projects/C--Users-Sam-Elhag-EREF--claude-skills")
latest = max(glob.glob(os.path.join(folder, "*.jsonl")), key=os.path.getmtime)
responses = {}
with open(latest, encoding="utf-8", errors="replace") as fh:
    for number, line in enumerate(fh):
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        message = entry.get("message") or {}
        usage = message.get("usage") if entry.get("type") == "assistant" else None
        if usage:
            keys = ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")
            context = sum(usage.get(k, 0) or 0 for k in keys)
            responses[message.get("id") or f"line{number}"] = (usage.get("output_tokens", 0) or 0, context)
output = sum(v[0] for v in responses.values())
context = sum(v[1] for v in responses.values())
print(f"{os.path.basename(latest)} responses={len(responses)} output={output} context={context}")
````

Run: `python "$SCRATCH/harness/usage_now.py"`
Expected: one line such as `<session-id>.jsonl responses=3 output=1200 context=90000`. Record it as the starting point.

- [ ] **Step 2: Quick sync on `dvd`**

Invoke `/readme-sync` for `$SCRATCH/replay/dvd`. Answer `no` at the approval prompt. Save the drift list, from the `README SYNC:` line through the prompt, to `$SCRATCH/replay/dvd.quick.drift.txt`. Run `usage_now.py` again and record the difference.
Expected: every `dvd` quick answer in the table, items numbered across the whole list, and the prompt text exactly `Apply these README changes? [yes / no / all except <numbers>]`.

- [ ] **Step 3: Quick sync on `dsa`**

Same as Step 2 for `$SCRATCH/replay/dsa`, saving `dsa.quick.drift.txt`.
Expected: every `dsa` quick answer, including `Last README change was small; older drift may remain. Say "deep readme sync" to check every claim.` under the header.

- [ ] **Step 4: Deep sync on `dsa`**

Ask for a deep readme sync of `$SCRATCH/replay/dsa`. Expected first reply: `Deep sync reads <n> files (~<lines> lines). Continue? [yes / no]`. Answer `yes`, then `no` at the approval prompt. Save `dsa.deep.drift.txt` and record the usage difference.
Expected: every `dsa` deep answer, and no small-change warning (it applies to quick mode only).

- [ ] **Step 5: Quick syncs on `samelhag` and `bytecraft`**

Same as Step 2 for each clone, saving `samelhag.quick.drift.txt` and `bytecraft.quick.drift.txt`.
Expected: every quick answer for each; the small-change warning for `samelhag` only.

- [ ] **Step 6: Quick sync on `usvotemap`**

Same as Step 2, saving `usvotemap.quick.drift.txt`.
Expected: the `usvotemap` answer, with no claims step (the README does not exist).

- [ ] **Step 7: Confirm the user's repos were only read**

Run: `for r in DiscordVoiceDatabase DiscordServerAudit bytecraft.us samelhag.dev usvotemap.dev; do git --no-optional-locks -C "$REPOS/$r" status --short; done`
Expected: no output.

- [ ] **Step 8: Write the cost comparison**

Create `$SCRATCH/replay/costs.md` with one row per sync (responses, output tokens, context tokens, drift items) and this reference, measured the same way: the four 2026-09-12 README sessions used 3.4M to 8.4M context tokens and 54k to 114k output tokens each, and two hit a usage limit. A sync passes when it produces a full drift list with fewer than 1.7M context tokens.

- [ ] **Step 9: Fix any missed known answer**

For each answer missing from its drift list:
- If `$SCRATCH/replay/<clone>.facts.txt` has the script line but the drift list lacks the item, make the matching guide's Facts or Claims text more precise, rerun `guide_lint.py`, and rerun that sync in a new session (a skill edited mid-session keeps its first-loaded text).
- If the script line is missing, add a failing test to `scripts/test_readme_facts.py` first, fix `scripts/readme_facts.py`, run the unit tests and flake8 until they pass, then rerun the sync.

Record every change for the Task 13 report. Leave everything uncommitted.

### Task 12: Apply run, creation run and automatic checks

**Files:**
- None in the skill. Scratch: the `dvd` and `usvotemap` clones, `$SCRATCH/replay/dvd.apply.txt`, `$SCRATCH/replay/usvotemap.create.txt`

**Interfaces:**
- Consumes: the finished skill, the replay clones, `$SCRATCH/replay/*.facts.txt` from Task 7.
- Produces: evidence that the approval, editing and verification paths work: `all except <n>`, a created README, the summary numbers.

- [ ] **Step 1: Start from clean clones**

````bash
for c in dvd usvotemap; do git -C "$SCRATCH/replay/$c" status --short; done
````

Expected: no output. If anything is listed, run `git checkout -- . && git clean -fd` inside that scratch clone only, then check again.

- [ ] **Step 2: Apply run on `dvd`**

Invoke `/readme-sync` for `$SCRATCH/replay/dvd` in quick mode. At the approval prompt, answer `all except <n>` where `<n>` is the number of the `your-username` clone URL item. Save everything from the drift list through the summary to `$SCRATCH/replay/dvd.apply.txt`.
Expected: the summary reads `Applied : <m minus 1> of <m> (left out: <n>)`, `Facts   : drift 14 → 1`, and ends with `Changes are unstaged and uncommitted.`

- [ ] **Step 3: Check the apply run**

````bash
cd "$SCRATCH/replay/dvd" && git status --short
python "$SKILL/scripts/readme_facts.py" . --since auto | grep -vP "\t(CHANGED|SINCE)\t"
````

Expected: `git status --short` lists only ` M README.md`; the script prints one drift line, `setup	REPO-URL-MISMATCH	README.md:<line>	github.com/your-username/DiscordVoiceDatabase should be github.com/SamElhagDev/DiscordVoiceDatabase`, then `summary	facts=57 drift=1 not_checked=0`. Every build, test or lint command the new README documents either succeeded in the summary's Commands line or is listed under Not checked with its reason.

- [ ] **Step 4: Creation run on `usvotemap`**

Invoke `/readme-sync` for `$SCRATCH/replay/usvotemap` and answer `yes`. Save the output to `$SCRATCH/replay/usvotemap.create.txt`.

````bash
cd "$SCRATCH/replay/usvotemap" && git status --short
python "$SKILL/scripts/readme_facts.py" . --since auto
````

Expected: `git status --short` lists only `?? README.md`; the script prints `meta	SINCE	none	README.md has no commit` and a summary with `drift=0`; the new README has Features, Setup, Configuration, Deployment, Development and License headings in that order and names the three env vars without values.

- [ ] **Step 5: Check the summaries against what happened**

Expected in `dvd.apply.txt`: `Applied` counts every approved item, `left out` names exactly the clone URL item, the `Facts` line matches the before and after `drift=` values, and the `Diff` line matches `git diff --numstat -- README.md` in the `dvd` clone. Expected in `usvotemap.create.txt`: `Facts   : drift 9 → 0`.

If any expectation fails, fix the matching section of `SKILL.md` or the guide involved, rerun `skill_lint.py` and `guide_lint.py`, and repeat Task 12 Steps 1 to 5 in a new session. Leave everything uncommitted.

### Task 13: Wrap-up and handoff

**Files:**
- Modify: `C:\Users\Sam Elhag.EREF\.claude\projects\C--Users-Sam-Elhag-EREF--claude-skills\memory\skills-roadmap.md` (status line for item 4)

**Interfaces:**
- Consumes: results from Tasks 1 to 12.
- Produces: the final report to the user and the commands they run themselves.

- [ ] **Step 1: Run every check one last time**

````bash
python -m unittest discover -s "$SKILL/scripts" -p "test_readme_facts.py"
python -m flake8 --max-line-length=127 "$SKILL/scripts"
python "$SCRATCH/harness/guide_lint.py" "$SKILL" features setup configuration commands routes deployment development license
python "$SCRATCH/harness/skill_lint.py" "$SKILL"
python -c "import pathlib, sys; hits = [str(p) for p in pathlib.Path(sys.argv[1]).rglob('*.md') if chr(0x2014) in p.read_text(encoding='utf-8')]; print(chr(10).join(hits) or 'no em-dashes')" "$SKILL"
git -C "/c/Users/Sam Elhag.EREF/.claude/skills" status --short --untracked-files=all -- readme-sync
````

Expected: `Ran 22 tests` and `OK` (more if Task 11 added tests); no flake8 output; `guide lint OK: ...`; `skill lint OK`; `no em-dashes`; `git status` lists the `readme-sync/` files and nothing staged. If it lists `readme-sync/scripts/__pycache__/` files, tell the user before giving the commit commands, since `git add -A` would commit them.

- [ ] **Step 2: Update the roadmap memory**

In `skills-roadmap.md`, replace the item 4 text with `` `readme-sync` `` followed by "(built and tested", today's date, and ", left uncommitted for the user)". Add any new testing lesson to `skill-testing-notes.md`, one line each.

- [ ] **Step 3: Report to the user**

Report, in plain language:
- Unit test count, lint results, and the known answers caught per replay, including what was recorded only
- Token costs from `costs.md` next to the 2026-09-12 reference
- The apply and creation runs: what changed, the drift counts before and after, and any documented command results
- Any guide or script change from Task 11 Step 9
- The check only the user can do: in a new session in a real repo, say "update the readme", confirm this skill runs, and note any permission prompts

Then give the commit commands, one per `bash` block, without running them:

```bash
git add -A
```

```bash
git commit -m "Adding readme-sync skill"
```

```bash
git push
```
