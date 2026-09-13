# Code Health Audit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (inline, recommended for this user) or superpowers:subagent-driven-development (only if the user asks for subagents) to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `code-health-audit` skill: a scored, network-audit-style code audit for the user's Python and .NET repos with a per-finding fix loop.

**Architecture:** `SKILL.md` orchestrates; eight `modules/*.md` define detection and risk indicators; eight `remediation/*-fixes.md` define fix recipes; `scripts/py_checks.py` provides standard-library AST checks, covered by `scripts/test_py_checks.py`. Correctness is proven by unit tests for the script and by replaying past audits on scratch clones checked out at pre-audit commits.

**Tech Stack:** Markdown skill files; Python 3.10 standard library (`ast`, `re`, `subprocess`, `unittest`); flake8 7.3; .NET SDK 10 (`dotnet build`, `dotnet list package`); git.

**Spec:** `C:\Users\Sam Elhag.EREF\.claude\skills\code-health-audit\DESIGN.md`

## Global Constraints

- Never stage, commit or push. Every task ends with changes left uncommitted for the user.
- Never modify the user's repos under `C:\Users\Sam Elhag.EREF\source\repos`. Replays use `git clone --no-hardlinks` into the session scratchpad.
- No subagents unless the user asks.
- `py_checks.py` uses the Python standard library only and must run on Python 3.10.11.
- Excluded from findings: `tests/`, `.specify/`, `wwwroot/lib/`, `node_modules/`, `Migrations/`, `.venv/`, `venv/`, generated or minified files.
- py_checks output line: `<module>\t<CHECK-ID>\t<path>:<line>\t<detail>`; last line `summary\tchecked=<n> hits=<m> not_checked=<k>`; exit 0 when it ran, 1 when it failed.
- Module order: bugs, error-handling, concurrency, performance, duplication, dead-code, dependencies, comments.
- Score = `10 × Impact × (0.5 + 0.5 × Likelihood) × (0.6 + 0.4 × Reach)`, rounded half-up to one decimal. Impact: outage/data 1.0, breaks 0.7, degrades 0.4, maintainability 0.1. Likelihood: normal use 1.0, conditions 0.6, rare 0.3, future change 0.1. Reach: whole app 1.0, one feature 0.7, one user 0.4.
- Bands: 9.0 to 10.0 Critical, 7.0 to 8.9 High, 4.0 to 6.9 Medium, 0.1 to 3.9 Low. Vulnerable packages: Critical 9.5, High 8.0, Moderate 5.5, Low 2.0.
- Fix loop prompt: `Apply this fix? [yes / no / skip-severity / stop]`; behavior changes add `⚠ <what changes>. Confirm? [yes / no]`.
- Regression test only when Impact is 0.7 or 1.0 and the baseline test command ran at least one test.
- `SKILL.md` under about 800 words; module and remediation files stay focused on their own module.
- Skill text uses plain punctuation (no em-dashes) and no box-drawing banners outside the report template.

## Variables used in commands

- `SKILL="/c/Users/Sam Elhag.EREF/.claude/skills/code-health-audit"`
- `REPOS="/c/Users/Sam Elhag.EREF/source/repos"`
- `SCRATCH=<the executing session's scratchpad directory, forward slashes>`

## Score lookup (every vector, half-up)

| Impact | normal/app | normal/feature | normal/user | cond/app | cond/feature | cond/user | rare/app | rare/feature | rare/user | future/app | future/feature | future/user |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| outage/data | 10.0 | 8.8 | 7.6 | 8.0 | 7.0 | 6.1 | 6.5 | 5.7 | 4.9 | 5.5 | 4.8 | 4.2 |
| breaks | 7.0 | 6.2 | 5.3 | 5.6 | 4.9 | 4.3 | 4.6 | 4.0 | 3.5 | 3.9 | 3.4 | 2.9 |
| degrades | 4.0 | 3.5 | 3.0 | 3.2 | 2.8 | 2.4 | 2.6 | 2.3 | 2.0 | 2.2 | 1.9 | 1.7 |
| maintainability | 1.0 | 0.9 | 0.8 | 0.8 | 0.7 | 0.6 | 0.7 | 0.6 | 0.5 | 0.6 | 0.5 | 0.4 |

## File Map

| File | Responsibility | Task |
|---|---|---|
| `scripts/py_checks.py` | Standard-library AST checks, output format, file listing | 1 to 4 |
| `scripts/test_py_checks.py` | Unit tests for every check ID and the CLI | 1 to 4 |
| `modules/bugs.md`, `remediation/bugs-fixes.md` | Latent bugs | 6 |
| `modules/error-handling.md`, `remediation/error-handling-fixes.md` | Silent failures | 7 |
| `modules/concurrency.md`, `remediation/concurrency-fixes.md` | Event loop and shared state | 7 |
| `modules/performance.md`, `remediation/performance-fixes.md` | Hot paths and growth | 8 |
| `modules/duplication.md`, `remediation/duplication-fixes.md` | Copied logic and defaults | 8 |
| `modules/dead-code.md`, `remediation/dead-code-fixes.md` | Unused code | 8 |
| `modules/dependencies.md`, `remediation/dependencies-fixes.md` | Pins and vulnerable packages | 9 |
| `modules/comments.md`, `remediation/comments-fixes.md` | trim-comments rules copy | 9 |
| `SKILL.md` | Orchestration, scoring, report, loop, verification, edge cases | 10 |
| (scratchpad only) `score_check.py`, replay clones | Test harness, never in the repo | 5, 11, 12 |

## Tasks

1. py_checks foundation (listing, parsing, CLI, helpers)
2. Bugs and error-handling checks
3. Concurrency and performance checks
4. Duplication, dead-code and dependency checks
5. Script replay on pre-audit snapshots
6. Bugs module and remediation
7. Error-handling and concurrency modules and remediation
8. Performance, duplication and dead-code modules and remediation
9. Dependencies and comments modules and remediation
10. SKILL.md orchestrator
11. Full replay audits and cost measurement
12. Fix loop run and automatic checks
13. Wrap-up and handoff

---

### Task 1: py_checks foundation

**Files:**
- Create: `scripts/py_checks.py`
- Test: `scripts/test_py_checks.py`

**Interfaces:**
- Produces: `Hit(module: str, check: str, path: str, line: int, detail: str)` with `.format() -> str`; `is_excluded(rel: str) -> bool`; `list_python_files(root: str, paths: list[str]) -> list[str]`; `parse_files(root: str, rels: list[str]) -> tuple[dict[str, ast.Module], list[Hit]]`; `run(root: str, paths: list[str]) -> tuple[list[Hit], int]`; `main(argv: list[str]) -> int`; helpers `_dotted(expr) -> str | None`, `_call_name(call: ast.Call) -> str`, `_attr_chain(expr) -> list[str]`, `_functions(tree) -> list`; registries `FILE_CHECKS: list` of `(rel, tree) -> list[Hit]` and `REPO_CHECKS: list` of `(root, trees) -> list[Hit]`.

- [ ] **Step 1: Write the failing tests**

Create `scripts/test_py_checks.py`:

```python
import ast
import io
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from contextlib import redirect_stdout

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import py_checks  # noqa: E402


def tree(src):
    return ast.parse(textwrap.dedent(src))


def make_repo(files):
    tmp = tempfile.TemporaryDirectory()
    for rel, src in files.items():
        path = os.path.join(tmp.name, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(textwrap.dedent(src))
    subprocess.run(["git", "init", "-q", tmp.name], check=True)
    subprocess.run(["git", "-C", tmp.name, "add", "-A"], check=True)
    return tmp


class FoundationTests(unittest.TestCase):
    def test_exclusions(self):
        self.assertTrue(py_checks.is_excluded("tests/test_x.py"))
        self.assertTrue(py_checks.is_excluded(".specify/scripts/a.py"))
        self.assertTrue(py_checks.is_excluded("wwwroot/lib/x.py"))
        self.assertTrue(py_checks.is_excluded("app/node_modules/pkg/a.py"))
        self.assertFalse(py_checks.is_excluded("cogs/polls.py"))
        self.assertFalse(py_checks.is_excluded("tests.py"))

    def test_lists_tracked_python_files_only(self):
        with make_repo({"bot.py": "x = 1\n", "cogs/a.py": "y = 2\n",
                        "tests/test_a.py": "z = 3\n", "notes.txt": "hi\n"}) as root:
            self.assertEqual(py_checks.list_python_files(root, []), ["bot.py", "cogs/a.py"])

    def test_unparseable_file_reported_not_checked(self):
        with make_repo({"good.py": "x = 1\n", "bad.py": "def (:\n"}) as root:
            trees, hits = py_checks.parse_files(root, ["bad.py", "good.py"])
        self.assertEqual(list(trees), ["good.py"])
        self.assertEqual([(h.check, h.path) for h in hits], [("NOT-CHECKED", "bad.py")])

    def test_main_output_and_summary(self):
        with make_repo({"good.py": "x = 1\n", "bad.py": "def (:\n"}) as root:
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = py_checks.main([root])
        lines = buf.getvalue().splitlines()
        self.assertEqual(code, 0)
        self.assertTrue(lines[0].startswith("meta\tNOT-CHECKED\tbad.py:"))
        self.assertEqual(lines[-1], "summary\tchecked=1 hits=0 not_checked=1")

    def test_main_returns_1_without_args(self):
        self.assertEqual(py_checks.main([]), 1)

    def test_helpers(self):
        call = tree("a.b.c(1)").body[0].value
        self.assertEqual(py_checks._dotted(call.func), "a.b.c")
        self.assertEqual(py_checks._call_name(call), "c")
        self.assertEqual(py_checks._attr_chain(call.func), ["a", "b", "c"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests and confirm they fail**

Run: `python -m unittest discover -s "$SKILL/scripts" -p "test_py_checks.py" -v`
Expected: `ModuleNotFoundError: No module named 'py_checks'`

- [ ] **Step 3: Write the implementation**

Create `scripts/py_checks.py`:

```python
"""Standard-library Python checks for the code-health-audit skill.

Usage: python py_checks.py <repo-root> [path ...]
"""
import ast
import os
import subprocess
import sys
from dataclasses import dataclass

MODULE_ORDER = ["bugs", "error-handling", "concurrency", "performance",
                "duplication", "dead-code", "dependencies", "meta"]
EXCLUDED_DIRS = {"tests", ".specify", "node_modules", "Migrations", ".venv", "venv", "__pycache__"}


@dataclass(frozen=True)
class Hit:
    module: str
    check: str
    path: str
    line: int
    detail: str

    def format(self) -> str:
        return f"{self.module}\t{self.check}\t{self.path}:{self.line}\t{self.detail}"


def is_excluded(rel: str) -> bool:
    parts = rel.split("/")
    return any(p in EXCLUDED_DIRS for p in parts[:-1]) or "wwwroot/lib/" in rel


def list_python_files(root: str, paths: list[str]) -> list[str]:
    out = subprocess.run(["git", "-C", root, "ls-files", "--", *(paths or ["."])],
                         capture_output=True, text=True, check=True).stdout
    return sorted(p for p in out.splitlines() if p.endswith(".py") and not is_excluded(p))


def parse_files(root: str, rels: list[str]) -> tuple[dict[str, ast.Module], list[Hit]]:
    trees, hits = {}, []
    for rel in rels:
        try:
            with open(os.path.join(root, rel), encoding="utf-8") as fh:
                trees[rel] = ast.parse(fh.read(), filename=rel)
        except (SyntaxError, UnicodeDecodeError, ValueError) as exc:
            hits.append(Hit("meta", "NOT-CHECKED", rel, getattr(exc, "lineno", None) or 1,
                            f"could not parse: {exc.__class__.__name__}"))
    return trees, hits


def _dotted(expr):
    if isinstance(expr, ast.Name):
        return expr.id
    if isinstance(expr, ast.Attribute):
        base = _dotted(expr.value)
        return f"{base}.{expr.attr}" if base else None
    return None


def _call_name(call: ast.Call) -> str:
    if isinstance(call.func, ast.Attribute):
        return call.func.attr
    if isinstance(call.func, ast.Name):
        return call.func.id
    return ""


def _attr_chain(expr) -> list[str]:
    names = []
    while isinstance(expr, ast.Attribute):
        names.append(expr.attr)
        expr = expr.value
    if isinstance(expr, ast.Name):
        names.append(expr.id)
    return list(reversed(names))


def _functions(tree) -> list:
    return [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]


FILE_CHECKS = []
REPO_CHECKS = []


def run(root: str, paths: list[str]) -> tuple[list[Hit], int]:
    rels = list_python_files(root, paths)
    trees, hits = parse_files(root, rels)
    for rel, tree in trees.items():
        for check in FILE_CHECKS:
            hits.extend(check(rel, tree))
    for check in REPO_CHECKS:
        hits.extend(check(root, trees))
    hits.sort(key=lambda h: (MODULE_ORDER.index(h.module), h.path, h.line, h.check))
    return hits, len(rels)


def main(argv: list[str]) -> int:
    if not argv:
        print("usage: py_checks.py <repo-root> [path ...]", file=sys.stderr)
        return 1
    try:
        hits, listed = run(argv[0], argv[1:])
    except Exception as exc:  # a crash must never read as a clean repo
        print(f"py_checks failed: {exc!r}", file=sys.stderr)
        return 1
    for hit in hits:
        print(hit.format())
    not_checked = sum(1 for h in hits if h.check == "NOT-CHECKED")
    print(f"summary\tchecked={listed - not_checked} hits={len(hits) - not_checked} not_checked={not_checked}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
```

- [ ] **Step 4: Run the tests and confirm they pass**

Run: `python -m unittest discover -s "$SKILL/scripts" -p "test_py_checks.py" -v`
Expected: `Ran 6 tests` and `OK`

- [ ] **Step 5: Lint and leave uncommitted**

Run: `python -m flake8 --max-line-length=127 "$SKILL/scripts"`
Expected: no output. Do not stage or commit.

### Task 2: Bugs and error-handling checks

**Files:**
- Modify: `scripts/py_checks.py` (insert functions above `FILE_CHECKS = []`, then register them)
- Test: `scripts/test_py_checks.py` (add `BugsAndErrorHandlingTests` above the unindented `if __name__ == "__main__":` line at the end of the file)

**Interfaces:**
- Consumes: `Hit`, `_dotted`, `_call_name`, `_functions`, `FILE_CHECKS` from Task 1.
- Produces: `check_attr_outside_init`, `check_import_side_effect`, `check_mutable_default`, `check_except_swallow`, `check_except_no_traceback`, `check_task_unstored`, each `(rel: str, tree: ast.Module) -> list[Hit]`; helpers `_is_main_guard(test) -> bool`, `_is_broad(handler) -> bool`.

- [ ] **Step 1: Write the failing tests**

Add to `scripts/test_py_checks.py`:

```python
class BugsAndErrorHandlingTests(unittest.TestCase):
    def ids(self, check, src):
        return sorted((h.check, h.line) for h in check("m.py", tree(src)))

    def test_attr_outside_init_flags_start_only_attribute(self):
        src = """
        class Recorder:
            def __init__(self):
                self.streams = {}
            def start(self):
                self.voice_client = object()
            def stop(self):
                self.voice_client.stop()
        """
        self.assertEqual(self.ids(py_checks.check_attr_outside_init, src), [("ATTR-OUTSIDE-INIT", 6)])

    def test_attr_declared_in_init_class_body_or_dataclass_not_flagged(self):
        src = """
        from dataclasses import dataclass
        class A:
            limit = 3
            def start(self):
                self.client = object()
                self.limit = 4
            def stop(self):
                print(self.client, self.limit)
            def __init__(self):
                self.client = None
        @dataclass
        class B:
            def start(self):
                self.x = 1
            def stop(self):
                print(self.x)
        """
        self.assertEqual(self.ids(py_checks.check_attr_outside_init, src), [])

    def test_import_side_effect_top_level_and_inside_if(self):
        src = """
        import logging
        log = logging.getLogger(__name__)
        log.info("Version: %s", 1)
        if True:
            log.info("inside if")
        def f():
            log.info("fine")
        """
        self.assertEqual(self.ids(py_checks.check_import_side_effect, src),
                         [("IMPORT-SIDE-EFFECT", 4), ("IMPORT-SIDE-EFFECT", 6)])

    def test_entry_module_skips_import_side_effects(self):
        src = """
        print("setup")
        if __name__ == "__main__":
            print("run")
        """
        self.assertEqual(self.ids(py_checks.check_import_side_effect, src), [])

    def test_entry_filenames_skip_import_side_effects(self):
        hits = py_checks.check_import_side_effect("bot.py", tree("load_dotenv()\nbot.run(token)\n"))
        self.assertEqual(hits, [])

    def test_mutable_default(self):
        src = """
        def a(x=[]): pass
        def b(*, y=dict()): pass
        def c(z=None, w=()): pass
        """
        self.assertEqual(self.ids(py_checks.check_mutable_default, src),
                         [("MUTABLE-DEFAULT", 2), ("MUTABLE-DEFAULT", 3)])

    def test_except_swallow_broad_only(self):
        src = """
        try:
            pass
        except Exception:
            pass
        try:
            pass
        except:
            handled = 1
        try:
            pass
        except discord.HTTPException:
            pass
        for i in []:
            try:
                pass
            except BaseException:
                continue
        """
        self.assertEqual(self.ids(py_checks.check_except_swallow, src),
                         [("EXCEPT-SWALLOW", 4), ("EXCEPT-SWALLOW", 17)])

    def test_except_no_traceback(self):
        src = """
        try:
            pass
        except Exception as e:
            log.error(f"cleanup failed: {e}")
        try:
            pass
        except Exception as e:
            log.error("cleanup failed", exc_info=True)
        try:
            pass
        except Exception as e:
            log.exception("cleanup failed")
        try:
            pass
        except Exception as e:
            log.warning("retrying: %s", e)
            raise
        """
        self.assertEqual(self.ids(py_checks.check_except_no_traceback, src), [("EXCEPT-NO-TRACEBACK", 5)])

    def test_task_unstored(self):
        src = """
        async def main():
            asyncio.create_task(work())
            task = asyncio.create_task(work())
            bot.loop.create_task(work())
        """
        self.assertEqual(self.ids(py_checks.check_task_unstored, src),
                         [("TASK-UNSTORED", 3), ("TASK-UNSTORED", 5)])
```

- [ ] **Step 2: Run the tests and confirm they fail**

Run: `python -m unittest discover -s "$SKILL/scripts" -p "test_py_checks.py" -v`
Expected: 9 errors with `AttributeError: module 'py_checks' has no attribute 'check_...'`

- [ ] **Step 3: Write the implementation**

Insert above `FILE_CHECKS = []` in `scripts/py_checks.py`:

```python
BROAD_EXCEPTIONS = {"Exception", "BaseException"}
ENTRY_FILENAMES = {"bot.py", "main.py", "app.py", "__main__.py"}
LOG_METHODS = {"debug", "info", "warning", "warn", "error", "critical", "log", "print"}


def _is_main_guard(test) -> bool:
    return isinstance(test, ast.Compare) and isinstance(test.left, ast.Name) and test.left.id == "__name__"


def _module_level_statements(stmts):
    for stmt in stmts:
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        if isinstance(stmt, ast.If) and _is_main_guard(stmt.test):
            continue
        yield stmt
        for field in ("body", "orelse", "finalbody", "handlers"):
            yield from _module_level_statements(getattr(stmt, field, None) or [])


def check_attr_outside_init(rel, tree):
    hits = []
    for cls in (n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)):
        decorators = [_dotted(d.func if isinstance(d, ast.Call) else d) for d in cls.decorator_list]
        if "dataclass" in decorators or "dataclasses.dataclass" in decorators:
            continue
        declared = set()
        for stmt in cls.body:
            if isinstance(stmt, ast.Assign):
                declared.update(t.id for t in stmt.targets if isinstance(t, ast.Name))
            elif isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                declared.add(stmt.target.id)
        first_set, readers = {}, {}
        for method in (m for m in cls.body if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef))):
            for node in ast.walk(method):
                if not (isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == "self"):
                    continue
                if isinstance(node.ctx, ast.Store) and method.name == "__init__":
                    declared.add(node.attr)
                elif isinstance(node.ctx, ast.Store):
                    first_set.setdefault(node.attr, (method.name, node.lineno))
                else:
                    readers.setdefault(node.attr, set()).add(method.name)
        for attr, (method, line) in sorted(first_set.items(), key=lambda item: item[1][1]):
            if attr not in declared and readers.get(attr, set()) - {method}:
                hits.append(Hit("bugs", "ATTR-OUTSIDE-INIT", rel, line,
                                f"self.{attr} is first set in {cls.name}.{method}() but read in other methods"))
    return hits


def check_import_side_effect(rel, tree):
    if rel.split("/")[-1] in ENTRY_FILENAMES or any(isinstance(s, ast.If) and _is_main_guard(s.test) for s in tree.body):
        return []
    return [Hit("bugs", "IMPORT-SIDE-EFFECT", rel, stmt.lineno, f"{_dotted(stmt.value.func) or 'call'}() runs at import time")
            for stmt in _module_level_statements(tree.body)
            if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call)]


def _is_mutable_literal(node) -> bool:
    if isinstance(node, (ast.List, ast.Dict, ast.Set)):
        return True
    return (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
            and node.func.id in ("list", "dict", "set") and not node.args and not node.keywords)


def check_mutable_default(rel, tree):
    hits = []
    for fn in _functions(tree):
        defaults = list(fn.args.defaults) + [d for d in fn.args.kw_defaults if d is not None]
        hits.extend(Hit("bugs", "MUTABLE-DEFAULT", rel, d.lineno, f"{fn.name}() has a mutable default argument")
                    for d in defaults if _is_mutable_literal(d))
    return hits


def _is_broad(handler) -> bool:
    if handler.type is None:
        return True
    types = handler.type.elts if isinstance(handler.type, ast.Tuple) else [handler.type]
    return any(_dotted(t) in BROAD_EXCEPTIONS for t in types)


def _is_none(value) -> bool:
    return value is None or (isinstance(value, ast.Constant) and value.value is None)


def _only_swallows(body) -> bool:
    for stmt in body:
        if isinstance(stmt, (ast.Pass, ast.Continue)):
            continue
        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant) and stmt.value.value is Ellipsis:
            continue
        if isinstance(stmt, ast.Return) and _is_none(stmt.value):
            continue
        return False
    return True


def check_except_swallow(rel, tree):
    return [Hit("error-handling", "EXCEPT-SWALLOW", rel, h.lineno, "broad except hides the error")
            for h in ast.walk(tree)
            if isinstance(h, ast.ExceptHandler) and _is_broad(h) and _only_swallows(h.body)]


def _keeps_traceback(handler) -> bool:
    for node in ast.walk(handler):
        if isinstance(node, ast.Raise):
            return True
        if isinstance(node, ast.Call):
            if _call_name(node) == "exception":
                return True
            for kw in node.keywords:
                if kw.arg == "exc_info" and not (isinstance(kw.value, ast.Constant) and kw.value.value is False):
                    return True
    return False


def check_except_no_traceback(rel, tree):
    hits = []
    for h in ast.walk(tree):
        if not (isinstance(h, ast.ExceptHandler) and h.name and _is_broad(h)) or _keeps_traceback(h):
            continue
        for node in ast.walk(h):
            if not (isinstance(node, ast.Call) and _call_name(node) in LOG_METHODS):
                continue
            if any(isinstance(n, ast.Name) and n.id == h.name for n in ast.walk(node)):
                hits.append(Hit("error-handling", "EXCEPT-NO-TRACEBACK", rel, node.lineno,
                                f"logs '{h.name}' without a traceback"))
                break
    return hits


def check_task_unstored(rel, tree):
    return [Hit("error-handling", "TASK-UNSTORED", rel, n.lineno, f"{_call_name(n.value)}() result is discarded")
            for n in ast.walk(tree)
            if isinstance(n, ast.Expr) and isinstance(n.value, ast.Call)
            and _call_name(n.value) in ("create_task", "ensure_future")]
```

Then replace `FILE_CHECKS = []` with:

```python
FILE_CHECKS = [check_attr_outside_init, check_import_side_effect, check_mutable_default,
               check_except_swallow, check_except_no_traceback, check_task_unstored]
```

- [ ] **Step 4: Run the tests and confirm they pass**

Run: `python -m unittest discover -s "$SKILL/scripts" -p "test_py_checks.py" -v`
Expected: `Ran 15 tests` and `OK`

- [ ] **Step 5: Lint and leave uncommitted**

Run: `python -m flake8 --max-line-length=127 "$SKILL/scripts"`
Expected: no output. Do not stage or commit.

### Task 3: Concurrency and performance checks

**Files:**
- Modify: `scripts/py_checks.py` (insert functions above `FILE_CHECKS = [`, then extend the registries)
- Test: `scripts/test_py_checks.py` (add `ConcurrencyPerformanceTests` above the unindented `if __name__ == "__main__":` line at the end of the file)

**Interfaces:**
- Consumes: `Hit`, `_dotted`, `_call_name`, `_attr_chain`, `_functions`, `FILE_CHECKS`, `REPO_CHECKS` from Task 1.
- Produces: `check_blocking_in_async(root: str, trees: dict[str, ast.Module]) -> list[Hit]`; `check_import_in_function`, `check_db_in_loop`, `check_grows_only`, each `(rel, tree) -> list[Hit]`; helper `_walk_body(node)` (yields descendants without entering nested functions, classes or lambdas).

- [ ] **Step 1: Write the failing tests**

Add to `scripts/test_py_checks.py`:

```python
class ConcurrencyPerformanceTests(unittest.TestCase):
    def test_blocking_in_async_direct_and_one_level(self):
        trees = {"rec.py": tree("""
        import time
        class UserStream:
            def flush_to_disk(self):
                with open(self.path, "wb") as f:
                    f.write(b"")
        async def rotate(stream):
            time.sleep(1)
            path = stream.flush_to_disk()
            await asyncio.to_thread(stream.flush_to_disk)
            await asyncio.sleep(1)
        """)}
        hits = py_checks.check_blocking_in_async(".", trees)
        self.assertEqual(sorted((h.check, h.line) for h in hits),
                         [("BLOCKING-IN-ASYNC", 8), ("BLOCKING-IN-ASYNC", 9)])
        self.assertIn("flush_to_disk() calls open()", [h.detail for h in hits if h.line == 9][0])

    def test_blocking_ignores_nested_sync_helpers_and_generic_names(self):
        trees = {"a.py": tree("""
        def write(data):
            open("x", "w").write(data)
        async def handler(stream):
            stream.write(b"")
            def later():
                open("y")
        """)}
        self.assertEqual(py_checks.check_blocking_in_async(".", trees), [])

    def test_import_in_function_skips_guarded_imports(self):
        src = """
        def write(packet):
            from discord.ext.voice_recv.rtp import SilencePacket
            return SilencePacket
        def optional():
            try:
                import numpy
            except ImportError:
                numpy = None
        def typed():
            if TYPE_CHECKING:
                import discord
        """
        self.assertEqual([(h.check, h.line) for h in py_checks.check_import_in_function("m.py", tree(src))],
                         [("IMPORT-IN-FUNCTION", 3)])

    def test_db_in_loop(self):
        src = """
        async def restore(bot):
            for poll in polls:
                votes = await db.get_votes(poll["id"])
                cursor.execute("SELECT 1")
            for x in items:
                total = await compute(x)
        """
        self.assertEqual(sorted((h.check, h.line) for h in py_checks.check_db_in_loop("m.py", tree(src))),
                         [("DB-IN-LOOP", 4), ("DB-IN-LOOP", 5)])

    def test_grows_only(self):
        src = """
        SEEN = set()
        CACHE = {}
        def remember(key):
            SEEN.add(key)
            CACHE[key] = 1
        def forget(key):
            CACHE.pop(key, None)
        class Index:
            def __init__(self):
                self.vectors = []
                self.names = []
            def add(self, v):
                self.vectors.append(v)
                self.names.append(v)
            def reset(self):
                self.names = []
        """
        self.assertEqual(sorted((h.detail, h.line) for h in py_checks.check_grows_only("m.py", tree(src))),
                         [("SEEN only ever grows", 2), ("self.vectors only ever grows", 11)])
```

- [ ] **Step 2: Run the tests and confirm they fail**

Run: `python -m unittest discover -s "$SKILL/scripts" -p "test_py_checks.py" -v`
Expected: 5 errors with `AttributeError: module 'py_checks' has no attribute 'check_...'`

- [ ] **Step 3: Write the implementation**

Insert above `FILE_CHECKS = [` in `scripts/py_checks.py`:

```python
BLOCKING_CALLS = {
    "open", "time.sleep", "sqlite3.connect", "urllib.request.urlopen",
    "requests.get", "requests.post", "requests.put", "requests.patch", "requests.delete",
    "requests.head", "requests.request",
    "subprocess.run", "subprocess.call", "subprocess.check_call", "subprocess.check_output", "subprocess.Popen",
    "os.remove", "os.unlink", "os.rmdir", "os.mkdir", "os.makedirs", "os.listdir", "os.scandir",
    "os.walk", "os.rename", "os.replace",
}
BLOCKING_PATH_METHODS = {"read_text", "write_text", "read_bytes", "write_bytes", "unlink", "mkdir", "rmdir", "iterdir"}
GENERIC_NAMES = {"write", "read", "close", "get", "set", "run", "open", "send", "start", "stop"}
DB_METHODS = {"execute", "executemany", "fetchone", "fetchall", "fetchmany", "commit"}
DB_RECEIVERS = {"db", "database", "conn", "connection", "cursor", "session"}
GROW_METHODS = {"append", "add", "update", "setdefault", "extend", "insert"}
SHRINK_METHODS = {"pop", "popitem", "remove", "discard", "clear"}
CONTAINER_FACTORIES = {"list", "dict", "set", "defaultdict", "OrderedDict", "deque",
                       "collections.defaultdict", "collections.OrderedDict", "collections.deque"}


def _walk_body(node):
    stack = list(ast.iter_child_nodes(node))
    while stack:
        child = stack.pop()
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
            continue
        yield child
        stack.extend(ast.iter_child_nodes(child))


def _blocking_name(call):
    dotted = _dotted(call.func) or ""
    if dotted in BLOCKING_CALLS or dotted.startswith("shutil."):
        return dotted
    if isinstance(call.func, ast.Attribute) and call.func.attr in BLOCKING_PATH_METHODS:
        return f".{call.func.attr}"
    return None


def check_blocking_in_async(root, trees):
    blocking_funcs = {}
    for tree in trees.values():
        for fn in _functions(tree):
            if not isinstance(fn, ast.FunctionDef) or fn.name in GENERIC_NAMES:
                continue
            for node in _walk_body(fn):
                name = _blocking_name(node) if isinstance(node, ast.Call) else None
                if name:
                    blocking_funcs.setdefault(fn.name, name)
                    break
    hits = []
    for rel, tree in trees.items():
        for fn in _functions(tree):
            if not isinstance(fn, ast.AsyncFunctionDef):
                continue
            for node in _walk_body(fn):
                if not isinstance(node, ast.Call):
                    continue
                direct = _blocking_name(node)
                called = _call_name(node)
                if direct:
                    hits.append(Hit("concurrency", "BLOCKING-IN-ASYNC", rel, node.lineno,
                                    f"{direct}() blocks the event loop inside async {fn.name}()"))
                elif called in blocking_funcs:
                    hits.append(Hit("concurrency", "BLOCKING-IN-ASYNC", rel, node.lineno,
                                    f"{called}() calls {blocking_funcs[called]}() inside async {fn.name}()"))
    return hits


def _catches_import_error(handler) -> bool:
    types = handler.type.elts if isinstance(handler.type, ast.Tuple) else [handler.type]
    return any(_dotted(t) in ("ImportError", "ModuleNotFoundError") for t in types if t is not None)


def _imports_in(stmts, guarded=False):
    for stmt in stmts:
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        if isinstance(stmt, (ast.Import, ast.ImportFrom)):
            if not guarded:
                yield stmt
            continue
        if isinstance(stmt, ast.If) and _dotted(stmt.test) in ("TYPE_CHECKING", "typing.TYPE_CHECKING"):
            yield from _imports_in(stmt.orelse, guarded)
            continue
        if isinstance(stmt, ast.Try):
            catches = any(_catches_import_error(h) for h in stmt.handlers)
            yield from _imports_in(stmt.body, guarded or catches)
            for handler in stmt.handlers:
                yield from _imports_in(handler.body, guarded)
            yield from _imports_in(stmt.orelse + stmt.finalbody, guarded)
            continue
        if isinstance(stmt, ast.Match):
            for case in stmt.cases:
                yield from _imports_in(case.body, guarded)
            continue
        for field in ("body", "orelse", "finalbody"):
            yield from _imports_in(getattr(stmt, field, None) or [], guarded)


def check_import_in_function(rel, tree):
    return [Hit("performance", "IMPORT-IN-FUNCTION", rel, stmt.lineno, f"import inside {fn.name}()")
            for fn in _functions(tree) for stmt in _imports_in(fn.body)]


def check_db_in_loop(rel, tree):
    hits, seen = [], set()
    for loop in ast.walk(tree):
        if not isinstance(loop, (ast.For, ast.AsyncFor, ast.While)):
            continue
        for stmt in loop.body:
            for node in ast.walk(stmt):
                call = None
                if isinstance(node, ast.Call) and _call_name(node) in DB_METHODS:
                    call = node
                elif (isinstance(node, ast.Await) and isinstance(node.value, ast.Call)
                      and DB_RECEIVERS.intersection(_attr_chain(node.value.func)[:-1])):
                    call = node.value
                if call is not None and call.lineno not in seen:
                    seen.add(call.lineno)
                    hits.append(Hit("performance", "DB-IN-LOOP", rel, call.lineno,
                                    f"{_dotted(call.func) or _call_name(call)}() runs once per loop iteration"))
    return hits


def _container_key(expr):
    if isinstance(expr, ast.Name):
        return expr.id
    if isinstance(expr, ast.Attribute) and isinstance(expr.value, ast.Name) and expr.value.id == "self":
        return f"self.{expr.attr}"
    return None


def _is_container(value) -> bool:
    if isinstance(value, (ast.List, ast.Dict, ast.Set)):
        return True
    return isinstance(value, ast.Call) and _dotted(value.func) in CONTAINER_FACTORIES


def check_grows_only(rel, tree):
    containers = {}
    for stmt in tree.body:
        if isinstance(stmt, ast.Assign) and _is_container(stmt.value):
            for target in stmt.targets:
                if isinstance(target, ast.Name):
                    containers[target.id] = stmt.lineno
    for fn in _functions(tree):
        if fn.name != "__init__":
            continue
        for node in ast.walk(fn):
            if isinstance(node, ast.Assign) and _is_container(node.value):
                for target in node.targets:
                    key = _container_key(target)
                    if key and key.startswith("self."):
                        containers[key] = node.lineno
    grows, shrinks = set(), set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            key = _container_key(node.func.value)
            if key in containers and node.func.attr in GROW_METHODS:
                grows.add(key)
            elif key in containers and node.func.attr in SHRINK_METHODS:
                shrinks.add(key)
        elif isinstance(node, (ast.Assign, ast.AugAssign, ast.Delete)):
            targets = [node.target] if isinstance(node, ast.AugAssign) else node.targets
            for target in targets:
                if isinstance(target, ast.Subscript) and _container_key(target.value) in containers:
                    if isinstance(node, ast.Delete):
                        shrinks.add(_container_key(target.value))
                    else:
                        grows.add(_container_key(target.value))
                elif _container_key(target) in containers:
                    key = _container_key(target)
                    if isinstance(node, ast.AugAssign):
                        grows.add(key)
                    elif node.lineno != containers[key]:
                        shrinks.add(key)
    return [Hit("performance", "GROWS-ONLY", rel, containers[key], f"{key} only ever grows")
            for key in sorted(grows - shrinks)]
```

Then update the registries:

```python
FILE_CHECKS = [check_attr_outside_init, check_import_side_effect, check_mutable_default,
               check_except_swallow, check_except_no_traceback, check_task_unstored,
               check_import_in_function, check_db_in_loop, check_grows_only]
REPO_CHECKS = [check_blocking_in_async]
```

- [ ] **Step 4: Run the tests and confirm they pass**

Run: `python -m unittest discover -s "$SKILL/scripts" -p "test_py_checks.py" -v`
Expected: `Ran 20 tests` and `OK`

- [ ] **Step 5: Lint and leave uncommitted**

Run: `python -m flake8 --max-line-length=127 "$SKILL/scripts"`
Expected: no output. Do not stage or commit.

### Task 4: Duplication, dead-code and dependency checks

**Files:**
- Modify: `scripts/py_checks.py` (add `import re` after `import os`; insert functions above `FILE_CHECKS = [`; extend `REPO_CHECKS`)
- Test: `scripts/test_py_checks.py` (add `DuplicationDeadCodeDependencyTests` above the unindented `if __name__ == "__main__":` line at the end of the file)

**Interfaces:**
- Consumes: `Hit`, `_dotted`, `_call_name`, `parse_files`, `main`, `REPO_CHECKS` from Tasks 1 to 3.
- Produces: `check_dup_config_default`, `check_unused_optional_param`, `check_unreferenced_func`, `check_unpinned_dep`, `check_undeclared_dep`, each `(root: str, trees: dict[str, ast.Module]) -> list[Hit]`; `read_requirements(root: str) -> dict[str, list[tuple[int, str, bool]]]` mapping file name to `(line, name, pinned)`.

- [ ] **Step 1: Write the failing tests**

Add to `scripts/test_py_checks.py`:

```python
class DuplicationDeadCodeDependencyTests(unittest.TestCase):
    def test_dup_config_default(self):
        trees = {
            "cogs/fact_check.py": tree('model = config.get("factcheck.semantic.model", "gemini-embedding-001")\n'),
            "utils/embeddings.py": tree('m = config.get("factcheck.semantic.model", "gemini-embedding-001")\n'
                                        'title = data.get("title", "")\n'
                                        'token = os.getenv("BOT_TOKEN", "")\n'),
        }
        hits = py_checks.check_dup_config_default(".", trees)
        self.assertEqual([(h.check, h.path) for h in hits], [("DUP-CONFIG-DEFAULT", "cogs/fact_check.py")])
        self.assertIn("2 places", hits[0].detail)

    def test_unused_optional_param(self):
        trees = {"index.py": tree("""
        class VectorIndex:
            def search(self, query, k=10, allowed_ids=None):
                return []
        def run(index):
            index.search("q")
            index.search("q", 5)
        """)}
        hits = py_checks.check_unused_optional_param(".", trees)
        self.assertEqual([h.detail for h in hits], ["search() parameter 'allowed_ids' is never passed by any caller"])

    def test_unreferenced_func_skips_framework_and_decorated(self):
        trees = {"cog.py": tree("""
        class Polls(commands.Cog):
            @commands.command()
            async def poll(self, ctx):
                return helper()
            async def on_ready(self):
                pass
            def cog_check(self, ctx):
                return True
            def _cb(self):
                pass
            def wire(self):
                self.select.callback = self._cb
        def helper():
            return 1
        def orphan():
            return 2
        async def setup(bot):
            await bot.add_cog(Polls(bot))
        """)}
        hits = py_checks.check_unreferenced_func(".", trees)
        self.assertEqual(sorted(h.detail for h in hits), ["orphan() is never referenced", "wire() is never referenced"])

    def test_unpinned_and_undeclared_deps(self):
        with make_repo({
            "requirements.txt": "discord.py[voice]>=2.7.1\npython-dotenv==1.0.1\n# comment\naiosqlite\n",
            "bot.py": "import discord\nimport numpy\nimport os\nimport cogs.polls\nfrom dotenv import load_dotenv\n",
            "cogs/polls.py": "x = 1\n",
        }) as root:
            trees, _ = py_checks.parse_files(root, ["bot.py", "cogs/polls.py"])
            unpinned = py_checks.check_unpinned_dep(root, trees)
            undeclared = py_checks.check_undeclared_dep(root, trees)
        self.assertEqual([(h.path, h.line) for h in unpinned], [("requirements.txt", 1)])
        self.assertIn("2 of 3 requirements are unpinned: discord.py, aiosqlite", unpinned[0].detail)
        self.assertEqual([h.detail for h in undeclared], ["imports 'numpy' but no requirement provides it"])

    def test_main_runs_every_registered_check_in_module_order(self):
        with make_repo({
            "requirements.txt": "aiosqlite\n",
            "cogs/rec.py": "import time\nasync def rotate():\n    time.sleep(1)\ndef f(x=[]):\n    return x\n",
        }) as root:
            buf = io.StringIO()
            with redirect_stdout(buf):
                py_checks.main([root])
        modules = [line.split("\t")[0] for line in buf.getvalue().splitlines()]
        self.assertEqual(modules, ["bugs", "concurrency", "dead-code", "dead-code", "dependencies", "summary"])
```

- [ ] **Step 2: Run the tests and confirm they fail**

Run: `python -m unittest discover -s "$SKILL/scripts" -p "test_py_checks.py" -v`
Expected: 4 errors (`AttributeError: ... has no attribute 'check_...'`) and 1 failure in `test_main_runs_every_registered_check_in_module_order` (lists differ: no dead-code or dependencies rows)

- [ ] **Step 3: Write the implementation**

Add `import re` after `import os`. Insert above `FILE_CHECKS = [`:

```python
ENV_STYLE = re.compile(r"^[A-Z][A-Z0-9_]*$")
REQUIREMENT_NAME = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)")
FRAMEWORK_HOOKS = {"setup", "setup_hook", "interaction_check", "callback", "setUp", "tearDown", "main"}
IMPORT_TO_PACKAGE = {"discord": "discord.py", "dotenv": "python-dotenv", "yaml": "PyYAML", "PIL": "Pillow",
                     "nacl": "PyNaCl", "whisper": "openai-whisper", "cv2": "opencv-python",
                     "sklearn": "scikit-learn", "bs4": "beautifulsoup4", "dateutil": "python-dateutil"}


def check_dup_config_default(root, trees):
    sites = {}
    for rel, tree in trees.items():
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Call) and len(node.args) >= 2 and isinstance(node.args[0], ast.Constant)
                    and isinstance(node.args[0].value, str)):
                continue
            key = node.args[0].value
            is_lookup = _call_name(node) == "get" or _dotted(node.func) == "os.getenv"
            if is_lookup and ("." in key or ENV_STYLE.match(key)):
                sites.setdefault(key, []).append((rel, node.lineno))
    hits = []
    for key, locations in sorted(sites.items()):
        if len(locations) >= 2:
            rel, line = locations[0]
            where = ", ".join(f"{r}:{n}" for r, n in locations)
            hits.append(Hit("duplication", "DUP-CONFIG-DEFAULT", rel, line,
                            f"'{key}' is read with a default in {len(locations)} places: {where}"))
    return hits


def _definitions(trees):
    for rel, tree in trees.items():
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        yield rel, item, True
        for item in tree.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                yield rel, item, False


def check_unused_optional_param(root, trees):
    sites = {}
    for tree in trees.values():
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and _call_name(node):
                sites.setdefault(_call_name(node), []).append(node)
    hits = []
    for rel, fn, is_method in _definitions(trees):
        if fn.decorator_list or fn.name.startswith(("__", "test")) or fn.name not in sites:
            continue
        calls = sites[fn.name]
        if any(isinstance(a, ast.Starred) for c in calls for a in c.args):
            continue
        if any(k.arg is None for c in calls for k in c.keywords):
            continue
        positional = fn.args.posonlyargs + fn.args.args
        offset = 1 if is_method and positional and positional[0].arg in ("self", "cls") else 0
        first_default = len(positional) - len(fn.args.defaults)
        optional = [(p.arg, i - offset) for i, p in enumerate(positional) if i >= first_default]
        optional += [(p.arg, None) for p, d in zip(fn.args.kwonlyargs, fn.args.kw_defaults) if d is not None]
        for name, index in optional:
            passed = any(any(k.arg == name for k in c.keywords) or (index is not None and len(c.args) > index)
                         for c in calls)
            if not passed:
                hits.append(Hit("dead-code", "UNUSED-OPTIONAL-PARAM", rel, fn.lineno,
                                f"{fn.name}() parameter '{name}' is never passed by any caller"))
    return hits


def check_unreferenced_func(root, trees):
    references = {}
    for tree in trees.values():
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                name = node.id
            elif isinstance(node, ast.Attribute) and isinstance(node.ctx, ast.Load):
                name = node.attr
            elif isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value.isidentifier():
                name = node.value
            else:
                continue
            references[name] = references.get(name, 0) + 1
    hits = []
    for rel, fn, _ in _definitions(trees):
        skip = fn.decorator_list or fn.name.startswith(("__", "on_", "cog_", "test")) or fn.name in FRAMEWORK_HOOKS
        if skip or references.get(fn.name, 0) > 0:
            continue
        hits.append(Hit("dead-code", "UNREFERENCED-FUNC", rel, fn.lineno, f"{fn.name}() is never referenced"))
    return hits


def _normalize(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def read_requirements(root):
    result = {}
    for fname in sorted(os.listdir(root)):
        if not (fname.startswith("requirements") and fname.endswith(".txt")):
            continue
        entries = []
        with open(os.path.join(root, fname), encoding="utf-8") as fh:
            for number, raw in enumerate(fh, 1):
                line = raw.split("#", 1)[0].strip()
                if not line or line.startswith("-") or "://" in line:
                    continue
                match = REQUIREMENT_NAME.match(line)
                if match:
                    entries.append((number, match.group(1), "==" in line))
        result[fname] = entries
    return result


def check_unpinned_dep(root, trees):
    hits = []
    for fname, entries in read_requirements(root).items():
        unpinned = [(number, name) for number, name, pinned in entries if not pinned]
        if unpinned:
            names = ", ".join(name for _, name in unpinned)
            hits.append(Hit("dependencies", "UNPINNED-DEP", fname, unpinned[0][0],
                            f"{len(unpinned)} of {len(entries)} requirements are unpinned: {names}"))
    return hits


def check_undeclared_dep(root, trees):
    requirements = read_requirements(root)
    if not requirements:
        return []
    declared = {_normalize(name) for entries in requirements.values() for _, name, _ in entries}
    local = {rel.split("/")[0].removesuffix(".py") for rel in trees}
    first_seen = {}
    for rel, tree in sorted(trees.items()):
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                names = [node.module]
            else:
                continue
            for full in names:
                top = full.split(".")[0]
                if top in sys.stdlib_module_names or top in local or top == "__future__":
                    continue
                first_seen.setdefault(top, (rel, node.lineno, full))
    hits = []
    for top, (rel, line, full) in sorted(first_seen.items()):
        package = _normalize(IMPORT_TO_PACKAGE.get(top, top))
        if package in declared or (top == "google" and any(d.startswith("google-") for d in declared)):
            continue
        hits.append(Hit("dependencies", "UNDECLARED-DEP", rel, line, f"imports '{full}' but no requirement provides it"))
    return hits
```

Then update `REPO_CHECKS`:

```python
REPO_CHECKS = [check_blocking_in_async, check_dup_config_default, check_unused_optional_param,
               check_unreferenced_func, check_unpinned_dep, check_undeclared_dep]
```

- [ ] **Step 4: Run the tests and confirm they pass**

Run: `python -m unittest discover -s "$SKILL/scripts" -p "test_py_checks.py" -v`
Expected: `Ran 25 tests` and `OK`

- [ ] **Step 5: Lint and leave uncommitted**

Run: `python -m flake8 --max-line-length=127 "$SKILL/scripts"`
Expected: no output. Do not stage or commit.

### Task 5: Script replay on pre-audit snapshots

**Files:**
- None in the skill. Scratch only: `$SCRATCH/replay/dsv`, `$SCRATCH/replay/dvd`, `$SCRATCH/replay/bytecraft`, `$SCRATCH/replay/*.hits.txt`

**Interfaces:**
- Consumes: `scripts/py_checks.py` from Task 4.
- Produces: the three replay clones reused by Tasks 6 to 12, and the recorded hit lists.

Known pre-audit commits (verified 2026-09-13):

| Clone | Repo | Commit | Why this commit |
|---|---|---|---|
| `dsv` | DiscordServerVote | `d426eed` | Parent of `31db0dc`, which carries the 2026-08-07 audit fixes |
| `dvd` | DiscordVoiceDatabase | `9fbaa3e` | Parent of `429a643`, the 2026-09-11 audit fixes |
| `bytecraft` | bytecraft.us | `edcf2a8` | Parent of `42085a6`, which added MimeKit 4.15.1 over MailKit 4.15.0's vulnerable transitive MimeKit |

- [ ] **Step 1: Clone the snapshots (the user's repos are only read)**

```bash
mkdir -p "$SCRATCH/replay" && cd "$SCRATCH/replay"
git clone -q --no-hardlinks --no-checkout "$REPOS/DiscordServerVote" dsv && git -C dsv checkout -q d426eed
git clone -q --no-hardlinks --no-checkout "$REPOS/DiscordVoiceDatabase" dvd && git -C dvd checkout -q 9fbaa3e
git clone -q --no-hardlinks --no-checkout "$REPOS/bytecraft.us" bytecraft && git -C bytecraft checkout -q edcf2a8
git -C "$REPOS/DiscordServerVote" status --short; git -C "$REPOS/DiscordVoiceDatabase" status --short; git -C "$REPOS/bytecraft.us" status --short
```

Expected: the three `status --short` commands print nothing.

- [ ] **Step 2: Run py_checks on the Python snapshots**

```bash
cd "$SCRATCH/replay"
python "$SKILL/scripts/py_checks.py" dsv > dsv.hits.txt; echo "exit=$?"; tail -1 dsv.hits.txt
python "$SKILL/scripts/py_checks.py" dvd > dvd.hits.txt; echo "exit=$?"; tail -1 dvd.hits.txt
```

Expected:
```
exit=0
summary	checked=9 hits=9 not_checked=0
exit=0
summary	checked=13 hits=39 not_checked=0
```

- [ ] **Step 3: Confirm the known answers are present**

```bash
grep -P "IMPORT-SIDE-EFFECT\tconfig.py:27" dsv.hits.txt
grep -P "BLOCKING-IN-ASYNC\trecording/recorder.py:580" dvd.hits.txt
grep -P "UNPINNED-DEP" dvd.hits.txt
python -m flake8 --select=F401 dsv
```

Expected:
```
bugs	IMPORT-SIDE-EFFECT	config.py:27	log.info() runs at import time
concurrency	BLOCKING-IN-ASYNC	recording/recorder.py:580	flush_to_disk() calls open() inside async _rotate_user()
dependencies	UNPINNED-DEP	requirements.txt:1	10 of 10 requirements are unpinned: aiohttp, aiosqlite, discord.py, discord-ext-voice-recv, davey, python-dotenv, PyNaCl, faster-whisper, numpy, tzdata
dsv\bot.py:17:1: F401 'config' imported but unused
dsv\utils\embeds.py:7:1: F401 'utils.rcv.RCVRound' imported but unused
```

If any expected line is missing, stop and use superpowers:systematic-debugging on the check before continuing.

- [ ] **Step 4: Confirm the .NET vulnerability check on bytecraft**

```bash
cd "$SCRATCH/replay/bytecraft" && dotnet list package --vulnerable --include-transitive
```

Expected: a transitive `MimeKit` 4.15.0 row with a severity, under the `bytecraft.us` project. If restore or the vulnerability feed cannot be reached, record the exact error; Task 11 then verifies the "Not checked" path instead.

- [ ] **Step 5: Record precision for later tuning**

```bash
cd "$SCRATCH/replay" && for r in dsv dvd; do echo "== $r"; cut -f2 $r.hits.txt | sort | uniq -c | sort -rn; done
```

Expected for `dvd`: 14 BLOCKING-IN-ASYNC, 11 EXCEPT-NO-TRACEBACK, 7 DB-IN-LOOP, 3 EXCEPT-SWALLOW, 2 UNREFERENCED-FUNC, 1 UNUSED-OPTIONAL-PARAM, 1 UNPINNED-DEP. Keep these counts; Task 11 compares them with the findings the audit actually reports. Nothing in the skill folder changes in this task.

### Task 6: Bugs module and remediation

**Files:**
- Create: `modules/bugs.md`, `remediation/bugs-fixes.md`
- Scratch harness (never in the skill): `$SCRATCH/harness/score_check.py`, `$SCRATCH/harness/module_lint.py`

**Interfaces:**
- Consumes: py_checks check IDs from Tasks 2 to 4; replay clones from Task 5.
- Produces: `score_check.score_for(vector: str) -> float`, `score_check.band(score: float) -> str`, `score_check.check_report(text: str) -> list[str]`; `module_lint.lint(skill_dir: str, module: str) -> list[str]`. Every module file uses the headings `## Data Collection (run all in parallel)`, `## Risk Indicators`, `## Analysis Notes`, a Risk Indicators table with columns `| Finding | Condition | Vector | Score |`, vectors written as `<impact> / <likelihood> / <reach>` with the exact words `outage`, `data loss`, `data exposure`, `breaks`, `degrades`, `maintainability`, `normal use`, `conditions`, `rare`, `future change`, `whole app`, `one feature`, `one user` (or `advisory: <Critical|High|Moderate|Low>`), and scores written as `<score> <band>`. Every remediation file has one `### <Finding>` entry per indicator (a trailing parenthetical in the indicator name may be dropped), each with `**Verify:**`, a `**Test:**` line when Impact is 0.7 or 1.0 or the vector is an advisory, and `**⚠ BEHAVIOR CHANGE**` when users or callers get different results for inputs that already worked.

- [ ] **Step 1: Write the harness and watch the lint fail**

Create `$SCRATCH/harness/score_check.py`:

```python
"""Scratch harness: score vectors and check audit reports. Not part of the skill."""
import math
import re
import sys

IMPACT = {"outage": 1.0, "data loss": 1.0, "data exposure": 1.0, "breaks": 0.7, "degrades": 0.4,
          "maintainability": 0.1}
LIKELIHOOD = {"normal use": 1.0, "conditions": 0.6, "rare": 0.3, "future change": 0.1}
REACH = {"whole app": 1.0, "one feature": 0.7, "one user": 0.4}
ADVISORY = {"Critical": 9.5, "High": 8.0, "Moderate": 5.5, "Low": 2.0}
HEADER = re.compile(r"^\[(\d+\.\d)\]\s+(.+?)\s+\(([\w-]+)\)\s*$")
VECTOR = re.compile(r"^\s+Vector:\s+(.+?)\s*$")
COUNTS = re.compile(r"Critical\s*:\s*(\d+)\s+High\s*:\s*(\d+)\s+Medium\s*:\s*(\d+)\s+Low\s*:\s*(\d+)")
TOTAL = re.compile(r"Total risk score:\s*(\d+(?:\.\d)?)")


def score_for(vector: str) -> float:
    vector = vector.strip()
    if vector.startswith("advisory:"):
        return ADVISORY[vector.split(":", 1)[1].strip()]
    impact, likelihood, reach = (part.strip() for part in vector.split("/"))
    raw = 10 * IMPACT[impact] * (0.5 + 0.5 * LIKELIHOOD[likelihood]) * (0.6 + 0.4 * REACH[reach])
    return math.floor(raw * 10 + 0.5 + 1e-9) / 10


def band(score: float) -> str:
    return "Critical" if score >= 9.0 else "High" if score >= 7.0 else "Medium" if score >= 4.0 else "Low"


def check_report(text: str) -> list[str]:
    problems, scores, pending = [], [], None
    for line in text.splitlines():
        header = HEADER.match(line)
        if header:
            pending = (float(header.group(1)), header.group(2))
            continue
        vector = VECTOR.match(line)
        if vector and pending:
            expected = score_for(vector.group(1))
            if expected != pending[0]:
                problems.append(f"{pending[1]}: shows {pending[0]}, vector gives {expected}")
            scores.append(pending[0])
            pending = None
    counts = COUNTS.search(text)
    if counts:
        shown = dict(zip(["Critical", "High", "Medium", "Low"], map(int, counts.groups())))
        actual = {name: sum(1 for s in scores if band(s) == name) for name in shown}
        if shown != actual:
            problems.append(f"summary counts {shown} but findings give {actual}")
    total = TOTAL.search(text)
    if total and abs(float(total.group(1)) - round(sum(scores), 1)) > 0.05:
        problems.append(f"total {total.group(1)} but findings sum to {round(sum(scores), 1)}")
    if not scores and "Findings: 0" not in text:
        problems.append("no scored findings found")
    return problems


if __name__ == "__main__":
    if sys.argv[1:] == ["--self-test"]:
        assert score_for("outage / normal use / whole app") == 10.0
        assert score_for("breaks / conditions / one user") == 4.3
        assert score_for("maintainability / normal use / one user") == 0.8
        assert score_for("advisory: Moderate") == 5.5
        sample = ("Critical : 1   High : 0   Medium : 1   Low : 0\nTotal risk score: 14.3\n"
                  "[10.0] Blocking flush     (concurrency)\n  x.py:1  d\n  Vector: outage / normal use / whole app\n"
                  "[4.3] Field overflow     (bugs)\n  y.py:2  d\n  Vector: breaks / conditions / one user\n")
        assert check_report(sample) == [], check_report(sample)
        assert check_report(sample.replace("[4.3]", "[4.4]"))
        print("score_check self-test OK")
    else:
        issues = check_report(open(sys.argv[1], encoding="utf-8").read())
        print("\n".join(issues) if issues else "report scores OK")
        sys.exit(1 if issues else 0)
```

Create `$SCRATCH/harness/module_lint.py`:

```python
"""Scratch harness: lint module and remediation files. Not part of the skill."""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from score_check import band, score_for  # noqa: E402

PY_CHECK_IDS = {"ATTR-OUTSIDE-INIT", "IMPORT-SIDE-EFFECT", "MUTABLE-DEFAULT", "EXCEPT-SWALLOW",
                "EXCEPT-NO-TRACEBACK", "TASK-UNSTORED", "BLOCKING-IN-ASYNC", "IMPORT-IN-FUNCTION",
                "DB-IN-LOOP", "GROWS-ONLY", "DUP-CONFIG-DEFAULT", "UNUSED-OPTIONAL-PARAM",
                "UNREFERENCED-FUNC", "UNPINNED-DEP", "UNDECLARED-DEP", "NOT-CHECKED"}
ROW = re.compile(r"^\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*(\d+\.\d)\s+(Critical|High|Medium|Low)\s*\|\s*$")
HIGH_IMPACT = ("outage", "data loss", "data exposure", "breaks")


def base_name(title: str) -> str:
    return re.sub(r"\s*\([^)]*\)\s*$", "", title).strip()


def lint(skill_dir: str, module: str) -> list[str]:
    mod_path = os.path.join(skill_dir, "modules", f"{module}.md")
    fix_path = os.path.join(skill_dir, "remediation", f"{module}-fixes.md")
    missing = [p for p in (mod_path, fix_path) if not os.path.exists(p)]
    if missing:
        return [f"missing {os.path.relpath(p, skill_dir)}" for p in missing]
    mod = open(mod_path, encoding="utf-8").read()
    fixes = open(fix_path, encoding="utf-8").read()
    problems = [f"{module}.md lacks '{h}'" for h in
                ("## Data Collection (run all in parallel)", "## Risk Indicators", "## Analysis Notes") if h not in mod]
    problems += [f"{name} contains an em-dash" for name, text in ((f"{module}.md", mod), (f"{module}-fixes.md", fixes))
                 if "\u2014" in text]
    problems += [f"{module}.md names unknown check id {ident}"
                 for ident in sorted(set(re.findall(r"\b[A-Z]+(?:-[A-Z]+)+\b", mod)) - PY_CHECK_IDS)]
    sections = {m.group(1).strip(): m.group(2)
                for m in re.finditer(r"^### (.+?)\n(.*?)(?=^### |\Z)", fixes, re.M | re.S)}
    rows = [r for r in (ROW.match(line) for line in mod.splitlines()) if r and r.group(1) != "Finding"]
    if not rows:
        problems.append(f"{module}.md has no risk indicator rows")
    for row in rows:
        title, vector, shown, shown_band = row.group(1), row.group(3), float(row.group(4)), row.group(5)
        try:
            expected = score_for(vector)
        except (KeyError, ValueError):
            problems.append(f"{title}: bad vector '{vector}'")
            continue
        if expected != shown or band(shown) != shown_band:
            problems.append(f"{title}: shows {shown} {shown_band}, vector gives {expected} {band(expected)}")
        section = sections.get(title) or sections.get(base_name(title))
        if section is None:
            problems.append(f"{title}: no '### {base_name(title)}' entry in {module}-fixes.md")
            continue
        if "**Verify:**" not in section:
            problems.append(f"{title}: fix entry lacks **Verify:**")
        needs_test = vector.startswith("advisory") or vector.split("/")[0].strip() in HIGH_IMPACT
        if needs_test and "**Test:**" not in section:
            problems.append(f"{title}: impact 0.7+ fix entry lacks **Test:**")
    return problems


if __name__ == "__main__":
    skill_dir, modules = sys.argv[1], sys.argv[2:]
    issues = [p for m in modules for p in lint(skill_dir, m)]
    print("\n".join(issues) if issues else f"module lint OK: {', '.join(modules)}")
    sys.exit(1 if issues else 0)
```

Run:
```bash
python "$SCRATCH/harness/score_check.py" --self-test
python "$SCRATCH/harness/module_lint.py" "$SKILL" bugs
```
Expected: `score_check self-test OK`, then `missing modules\bugs.md` and `missing remediation\bugs-fixes.md` with exit code 1.

- [ ] **Step 2: Confirm the Discord limits against the documentation**

Fetch `https://discord.com/developers/docs/resources/message` (section "Embed Limits") and `https://discord.com/developers/docs/components/reference` with WebFetch. Compare with the limits table in Step 3. If the documentation differs, use the documented values in Step 3. If neither page loads, keep the table and record that in the Task 13 report.

- [ ] **Step 3: Create `modules/bugs.md`**

Create `modules/bugs.md`:

````markdown
# Bugs Module

## Data Collection (run all in parallel)

### Python
- `py_checks.py` lines for module `bugs`: `ATTR-OUTSIDE-INIT`, `IMPORT-SIDE-EFFECT`, `MUTABLE-DEFAULT`
- Grep (glob `*.py`, content with line numbers): `add_field\(|Embed\(|set_footer\(|\.send\(|\.edit\(|SelectOption\(`
- Grep (glob `*.py`): `datetime\.(now|utcnow)\(\s*\)`

### .NET
- `dotnet build -nologo -clp:NoSummary`: keep lines containing `warning CS86`
- Grep (globs `*.razor`, `*.cs`): `OnInitialized(Async)?\s*\(`, then read each method for `JS.Invoke`, `JSRuntime.Invoke` or `IJSRuntime`
- Grep (globs `*.razor`, `*.razor.cs`): `\+=\s*[A-Za-z_]`; in those files Grep `IDisposable|IAsyncDisposable`
- Grep (glob `*.cs`): `new HttpClient\(`

## Risk Indicators

| Finding | Condition | Vector | Score |
|---|---|---|---|
| Attribute used before it exists | `ATTR-OUTSIDE-INIT`, and a method that reads the attribute can run before the method that sets it | breaks / conditions / one feature | 4.9 Medium |
| Import-time side effect | `IMPORT-SIDE-EFFECT` whose effect is lost or wrong because of import order | degrades / normal use / whole app | 4.0 Medium |
| Mutable default argument | `MUTABLE-DEFAULT` on a function that changes the argument | breaks / conditions / one feature | 4.9 Medium |
| Discord text over its limit | Text built at runtime can pass a Discord limit with realistic data, with no length check | breaks / conditions / one user | 4.3 Medium |
| Naive datetime | `now()` or `utcnow()` without a timezone in code that shows or compares times | breaks / normal use / one feature | 6.2 Medium |
| Nullable dereference | A CS86xx warning on a value that can be null at runtime | breaks / conditions / one feature | 4.9 Medium |
| JS interop during prerendering | `IJSRuntime` called from `OnInitialized` or `OnInitializedAsync` of a prerendered component | breaks / normal use / one feature | 6.2 Medium |
| Event subscription never removed | `+=` on a longer-lived object's event in a component with no `Dispose` that removes it | degrades / normal use / one feature | 3.5 Low |
| HttpClient created per call | `new HttpClient(` inside a method that runs per request or per call | degrades / conditions / whole app | 3.2 Low |

## Analysis Notes

**Attributes:** attributes set in discord.py `setup_hook`, `cog_load` or `on_ready` and only read afterwards are normal. Report only when a real call order reads first, such as `stop()` before `start()`.

**Import-time effects:** `load_dotenv()` and logger setup are normal. Report when the effect is lost or wrong: `log.info` before handlers exist (the messages vanish), network or file work during import, or work a test triggers just by importing.

**Discord limits:** estimate the largest realistic value from the code, items times characters per item. `>history mystats` built 15 lines of about 105 characters: 1579 characters for a 1024-character field. Prefer a helper the repo already has (`add_chunked_field`, `clip`).

| Object | Limit |
|---|---|
| Message content | 2000 characters |
| Embed title | 256 |
| Embed description | 4096 |
| Fields per embed | 25 |
| Field name / field value | 256 / 1024 |
| Footer text | 2048 |
| All text in one embed | 6000 |
| Embeds per message | 10 |
| Select menu options | 25; label, value and description up to 100 each |
| Button label | 80 |

**Datetimes:** the user's bots show US Eastern time. A naive `now()` is only correct when the server's clock happens to use that timezone.

**Nullable warnings:** report only when the value can really be null, for example after `FirstOrDefault`, not when the compiler cannot see an assignment that always happens.

**Prerendering:** interactive render modes prerender by default, and JS interop is not available while prerendering. It belongs in `OnAfterRenderAsync(firstRender)`.

**Subscriptions:** a component that subscribes to an event on a singleton or scoped service stays in memory after navigation until it unsubscribes.

**HttpClient:** a new client per call exhausts sockets under load. `IHttpClientFactory` or an injected client reuses connections.
````

- [ ] **Step 4: Create `remediation/bugs-fixes.md`**

Create `remediation/bugs-fixes.md`:

````markdown
# Bugs Remediation

Tag a fix **⚠ BEHAVIOR CHANGE** when users or callers get different results for inputs that already worked. A fix that only stops a crash or an error is not tagged. **Test:** lines apply only when the baseline test command ran at least one test, and tests use the repo's existing framework and naming.

---

### Attribute used before it exists

Set the attribute in `__init__`, usually to `None`, and return early where it can be read first.

```python
def __init__(self):
    self.voice_client = None

def stop(self):
    if self.voice_client is None:
        return
    self.voice_client.stop()
```

**Test:** create the object without calling the method that sets the attribute, call the reading method, and assert it does not raise.
**Verify:** `python -m py_compile <file>`, then the new test.

---

### Import-time side effect

Move the effect into a function and call it from the entry point after setup. For logging, call it after handlers are attached.

```python
# config.py
def log_summary():
    log.info("Version: %s", VERSION)

# bot.py, after logging is configured
config.log_summary()
```

**Verify:** `python -m py_compile <files>`, then the baseline test command.

---

### Mutable default argument

**⚠ BEHAVIOR CHANGE**: callers that relied on the shared default now get a fresh object each call.

```python
def collect(vote, seen=None):
    seen = [] if seen is None else seen
```

**Test:** call the function twice without the argument and assert the second call does not see data from the first.
**Verify:** `python -m py_compile <file>`, then the new test.

---

### Discord text over its limit

Send the text through a helper the repo already has; otherwise split it across fields or clip it at the limit.

```python
embeds.add_chunked_field(embed, "Recent Votes", lines, sep="\n")
```

**Test:** run the command with mocked data at the largest realistic size (for `mystats`: 15 entries with 30-character titles and 60-character choices) and assert every field value is at most 1024 characters.
**Verify:** `python -m py_compile <file>`, then the new test.

---

### Naive datetime

**⚠ BEHAVIOR CHANGE**: displayed times move to the chosen timezone.

```python
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

EASTERN = ZoneInfo("America/New_York")
stored = datetime.now(timezone.utc)
shown = stored.astimezone(EASTERN)
```

**Test:** assert the datetime the function returns or formats has `tzinfo` set.
**Verify:** `python -m py_compile <file>`, then the new test.

---

### Nullable dereference

Handle the null case where the value is produced: return early, use `?.` or `??`, or throw with a clear message.

```csharp
var contest = await _db.Contests.FirstOrDefaultAsync(c => c.Id == id, ct);
if (contest is null)
    return null;
```

**Test:** an xUnit test that passes the input producing null and asserts the guarded result.
**Verify:** `dotnet build`, then `dotnet test --filter <new test name>`.

---

### JS interop during prerendering

Move the call to `OnAfterRenderAsync` and run it once.

```csharp
protected override async Task OnAfterRenderAsync(bool firstRender)
{
    if (firstRender)
        await JS.InvokeVoidAsync("siteInterop.init");
}
```

**Test:** a Playwright test that loads the page and asserts the Blazor error UI stays hidden, when the repo has an E2E project; otherwise none practical.
**Verify:** `dotnet build`, then `dotnet test` for the E2E project when one exists.

---

### Event subscription never removed

Implement `IDisposable` and unsubscribe in `Dispose`.

```razor
@implements IDisposable

@code {
    protected override void OnInitialized() => State.Changed += OnStateChanged;
    public void Dispose() => State.Changed -= OnStateChanged;
}
```

**Verify:** `dotnet build`.

---

### HttpClient created per call

Register the factory once and create clients from it.

```csharp
builder.Services.AddHttpClient();

public sealed class FeedService(IHttpClientFactory http)
{
    public Task<string> GetAsync(string url) => http.CreateClient().GetStringAsync(url);
}
```

**Verify:** `dotnet build`, then `dotnet test`.
````

- [ ] **Step 5: Run the lint and confirm it passes**

Run: `python "$SCRATCH/harness/module_lint.py" "$SKILL" bugs`
Expected: `module lint OK: bugs`

- [ ] **Step 6: Spot-check detection on the DiscordServerVote snapshot**

Run the module's Discord Grep on `$SCRATCH/replay/dsv` (glob `*.py`, pattern `add_field\(|Embed\(|set_footer\(|\.send\(|\.edit\(|SelectOption\(`) and `grep -P "^bugs\t" "$SCRATCH/replay/dsv.hits.txt"`.
Expected: the Grep output includes `cogs/history.py:85` (`embed.add_field(name="Recent Votes", value="\n".join(lines), inline=False)`), and the bugs lines include `config.py:27`. Leave everything uncommitted.

### Task 7: Error-handling and concurrency modules and remediation

**Files:**
- Create: `modules/error-handling.md`, `remediation/error-handling-fixes.md`, `modules/concurrency.md`, `remediation/concurrency-fixes.md`

**Interfaces:**
- Consumes: `$SCRATCH/harness/module_lint.py` and the file format defined in Task 6; `$SCRATCH/replay/dvd.hits.txt` from Task 5.
- Produces: two lint-clean modules with their remediation files.

- [ ] **Step 1: Watch the lint fail**

Run: `python "$SCRATCH/harness/module_lint.py" "$SKILL" error-handling concurrency`
Expected: four `missing ...` lines and exit code 1.

- [ ] **Step 2: Create `modules/error-handling.md`**

Create `modules/error-handling.md`:

````markdown
# Error Handling Module

## Data Collection (run all in parallel)

### Python
- `py_checks.py` lines for module `error-handling`: `EXCEPT-SWALLOW`, `EXCEPT-NO-TRACEBACK`, `TASK-UNSTORED`
- `python -m flake8 --select=E722 .`

### .NET
- Grep (globs `*.cs`, `*.razor`, multiline): `catch\s*(\([^)]*\))?\s*\{\s*\}`
- Grep (globs `*.cs`, `*.razor`): `catch\s*\(\s*Exception`, then read each block for a log call or `throw`
- Grep (globs `*.cs`, `*.razor`): `async\s+void\s+\w+\s*\(`

## Risk Indicators

| Finding | Condition | Vector | Score |
|---|---|---|---|
| Swallowed error that leaves state broken | `EXCEPT-SWALLOW` where later code relies on what the try block was supposed to do | breaks / conditions / one feature | 4.9 Medium |
| Swallowed error with a deliberate fallback | `EXCEPT-SWALLOW` where skipping is intended but the exception type is broad | maintainability / conditions / one feature | 0.7 Low |
| Error logged without a traceback | `EXCEPT-NO-TRACEBACK` in code that runs unattended: loops, tasks, workers | degrades / conditions / one feature | 2.8 Low |
| Bare except | flake8 E722 | degrades / conditions / one feature | 2.8 Low |
| Discarded task | `TASK-UNSTORED` for a task that does real work | breaks / rare / one feature | 4.0 Medium |
| Empty catch block | An empty `catch`, or a catch-all that neither logs nor rethrows | degrades / conditions / one feature | 2.8 Low |
| async void method | `async void` that is not an event handler | breaks / conditions / one user | 4.3 Medium |

## Analysis Notes

**Narrow handlers are intentional.** `except discord.HTTPException: pass` around a best-effort delete is fine; `py_checks.py` only reports broad handlers.

**Broken state:** a swallowed error leaves state broken when code after the try uses its result, such as a startup migration, a file that is written and then read, or a message that is edited and then referenced. DiscordVoiceDatabase's migration loop in `bot.py` was `except Exception: pass`.

**Unattended code:** `tasks.loop` bodies, queue workers and cleanup jobs run with nobody watching. A traceback in the log is often the only evidence a failure leaves.

**Discarded tasks:** the event loop keeps only a weak reference to a task, so a task nothing references can be garbage-collected before it finishes, and its exception is never seen.

**async void in C#:** callers cannot catch its exceptions, and in Blazor Server an unhandled exception ends that user's circuit. Real event handlers (`object sender, EventArgs e`) stay `async void` with a try/catch inside.
````

- [ ] **Step 3: Create `remediation/error-handling-fixes.md`**

Create `remediation/error-handling-fixes.md`:

````markdown
# Error Handling Remediation

Tag a fix **⚠ BEHAVIOR CHANGE** when users or callers get different results for inputs that already worked. **Test:** lines apply only when the baseline test command ran at least one test, and tests use the repo's existing framework and naming.

---

### Swallowed error that leaves state broken

**⚠ BEHAVIOR CHANGE**: code after the failure stops instead of continuing with broken state.

```python
try:
    await db.execute(MIGRATION_SQL)
except Exception:
    log.exception("Migration failed")
    raise
```

**Test:** patch the wrapped call to raise and assert the error is logged and re-raised.
**Verify:** `python -m py_compile <file>`, then the new test.

---

### Swallowed error with a deliberate fallback

**⚠ BEHAVIOR CHANGE**: exception types the fallback was not meant for now propagate.

Catch only the exception type the fallback exists for.

```python
try:
    await message.delete()
except discord.HTTPException:
    pass
```

**Verify:** `python -m py_compile <file>`, then the baseline test command.

---

### Error logged without a traceback

```python
except Exception:
    log.error("Cleanup failed for %s", path, exc_info=True)
```

**Verify:** `python -m py_compile <file>`.

---

### Bare except

```python
except Exception:
```

**Verify:** `python -m flake8 --select=E722 <file>` prints nothing, then the baseline test command.

---

### Discarded task

Keep a reference until the task finishes.

```python
self._tasks = set()  # in __init__

task = asyncio.create_task(self.process(item))
self._tasks.add(task)
task.add_done_callback(self._tasks.discard)
```

Module-level code uses a module-level set the same way.

**Test:** none practical, because garbage collection timing is not deterministic.
**Verify:** `python -m py_compile <file>`, then the baseline test command.

---

### Empty catch block

Log with the injected logger. Add `throw;` when the caller must know; that addition is a **⚠ BEHAVIOR CHANGE** because callers now see the exception.

```csharp
catch (Exception ex)
{
    _logger.LogError(ex, "Refresh failed for {Source}", source);
    throw;
}
```

**Verify:** `dotnet build`, then `dotnet test`.

---

### async void method

**⚠ BEHAVIOR CHANGE**: callers now await the method, so the code after the call runs later.

```csharp
private async Task SaveAsync()
{
    await Store.SaveAsync(Model);
}
```

Event handlers stay `async void` with the whole body inside a try/catch that logs.

**Test:** an xUnit test that awaits the method with a failing dependency and asserts the exception reaches the caller.
**Verify:** `dotnet build`, then `dotnet test --filter <new test name>`.
````

- [ ] **Step 4: Create `modules/concurrency.md`**

Create `modules/concurrency.md`:

````markdown
# Concurrency Module

## Data Collection (run all in parallel)

### Python
- `py_checks.py` lines for module `concurrency`: `BLOCKING-IN-ASYNC`
- While reading flagged regions and entry points: module-level or `self.` state that more than one handler or task changes, with an `await` between reading and writing it

### .NET
- Grep (globs `*.cs`, `*.razor`): `\.Result\b|\.Wait\(\)|GetAwaiter\(\)\.GetResult\(\)`
- `dotnet build -nologo -clp:NoSummary`: keep lines containing `warning CS4014`
- Grep (glob `*.cs`): `\bstatic\b`, then read the matching field declarations that have neither `readonly` nor `const`

## Risk Indicators

| Finding | Condition | Vector | Score |
|---|---|---|---|
| Blocking call on a hot path | `BLOCKING-IN-ASYNC` in code that runs during normal operation (per message, audio frame or rotation) and can take more than a few milliseconds | outage / normal use / whole app | 10.0 Critical |
| Occasional blocking call | `BLOCKING-IN-ASYNC` that runs rarely or on small data, such as startup or deleting a few files | degrades / rare / whole app | 2.6 Low |
| Unsynchronized shared state | State changed by several handlers or tasks with an `await` between read and write, and no lock | breaks / conditions / one feature | 4.9 Medium |
| Sync-over-async | `.Result`, `.Wait()` or `GetAwaiter().GetResult()` on a request or Blazor Server path | outage / conditions / whole app | 8.0 High |
| Unawaited task | CS4014 where the ignored task can fail or must finish before the next step | breaks / conditions / one feature | 4.9 Medium |
| Writable static state | A static field without `readonly` or `const` holding per-user or per-request data in a Blazor Server or ASP.NET app | data exposure / conditions / whole app | 8.0 High |

## Analysis Notes

**Hot path:** judge by call frequency and data size. DiscordVoiceDatabase's `_rotate_user()` called `stream.flush_to_disk()`, which wrote about 11.5 MB per speaking user per rotation on the event loop. The gateway heartbeat stalled and the bot went grey: Critical. `open()` inside `_init_schema()` at startup is an Occasional blocking call.

**How far py_checks looks:** it follows one level into repo functions. Deeper chains show up while reading the flagged function.

**Shared state:** discord.py handlers and `tasks.loop` bodies interleave at every `await`, so a read-modify-write across an `await` can lose updates, for example two playback requests for the same guild.

**Sync-over-async:** each blocked call holds a thread-pool thread; under load the app stops responding.

**Static state:** a static field is shared by every user and circuit. A deliberate process-wide guard such as usvotemap's `static readonly SemaphoreSlim _gate` is not a finding.
````

- [ ] **Step 5: Create `remediation/concurrency-fixes.md`**

Create `remediation/concurrency-fixes.md`:

````markdown
# Concurrency Remediation

Tag a fix **⚠ BEHAVIOR CHANGE** when users or callers get different results for inputs that already worked. **Test:** lines apply only when the baseline test command ran at least one test, and tests use the repo's existing framework and naming.

---

### Blocking call on a hot path

**⚠ BEHAVIOR CHANGE**: other coroutines can run while the work happens on a thread.

```python
pcm_path = await asyncio.to_thread(stream.flush_to_disk)
```

When other threads also touch the data the function reads, guard it with a `threading.Lock`.

**Test:** patch the blocking function to record `threading.get_ident()`, run the coroutine, and assert the function ran on a different thread from the event loop.
**Verify:** `python -m py_compile <file>`, then the new test.

---

### Occasional blocking call

**⚠ BEHAVIOR CHANGE**: other coroutines can run while the work happens on a thread.

```python
schema = await asyncio.to_thread(Path(SCHEMA_PATH).read_text)
```

**Verify:** `python -m py_compile <file>`, then the baseline test command.

---

### Unsynchronized shared state

Hold one `asyncio.Lock` per resource across the whole read-modify-write. Create `self._locks = {}` in `__init__`.

```python
def _playback_lock(self, guild_id):
    return self._locks.setdefault(guild_id, asyncio.Lock())

async def play(self, guild, clip):
    async with self._playback_lock(guild.id):
        await self._play_locked(guild, clip)
```

**Test:** start two calls for the same resource with `asyncio.gather` and assert the invariant holds, for example that only one playback is active at a time.
**Verify:** `python -m py_compile <file>`, then the new test.

---

### Sync-over-async

**⚠ BEHAVIOR CHANGE**: the method and its callers become async.

```csharp
var results = await _service.LoadAsync(ct);
```

Change each caller in the chain to `async Task` and await it.

**Test:** none practical, because thread-pool starvation does not reproduce reliably in a unit test.
**Verify:** `dotnet build`, then `dotnet test`.

---

### Unawaited task

**⚠ BEHAVIOR CHANGE** when the fix adds `await`: the next step now waits for the task.

```csharp
await _cache.RefreshAsync(ct);
```

For fire-and-forget that is intended, make sure failures are logged:

```csharp
_ = RefreshInBackgroundAsync();

private async Task RefreshInBackgroundAsync()
{
    try { await _cache.RefreshAsync(CancellationToken.None); }
    catch (Exception ex) { _logger.LogError(ex, "Background refresh failed"); }
}
```

**Test:** an xUnit test that makes the task fail and asserts the caller sees the failure when awaited, or that the error is logged for fire-and-forget.
**Verify:** `dotnet build`, then `dotnet test --filter <new test name>`.

---

### Writable static state

**⚠ BEHAVIOR CHANGE**: data every user shared becomes per user or per request.

```csharp
builder.Services.AddScoped<SelectionState>();

public sealed class SelectionState
{
    public string? SourceKey { get; set; }
}
```

**Test:** an xUnit test that resolves the service from two scopes and asserts a value set in one scope is not visible in the other.
**Verify:** `dotnet build`, then `dotnet test --filter <new test name>`.
````

- [ ] **Step 6: Run the lint and confirm it passes**

Run: `python "$SCRATCH/harness/module_lint.py" "$SKILL" error-handling concurrency`
Expected: `module lint OK: error-handling, concurrency`

- [ ] **Step 7: Spot-check detection on the DiscordVoiceDatabase snapshot**

Run: `grep -cP "^error-handling\t" "$SCRATCH/replay/dvd.hits.txt"; grep -P "^concurrency\tBLOCKING-IN-ASYNC\trecording/recorder.py:580" "$SCRATCH/replay/dvd.hits.txt"`
Expected: `14`, then the `flush_to_disk() calls open() inside async _rotate_user()` line. Leave everything uncommitted.

### Task 8: Performance, duplication and dead-code modules and remediation

**Files:**
- Create: `modules/performance.md`, `remediation/performance-fixes.md`, `modules/duplication.md`, `remediation/duplication-fixes.md`, `modules/dead-code.md`, `remediation/dead-code-fixes.md`

**Interfaces:**
- Consumes: `$SCRATCH/harness/module_lint.py` and the file format defined in Task 6; `$SCRATCH/replay/*.hits.txt` from Task 5.
- Produces: three lint-clean modules with their remediation files.

- [ ] **Step 1: Watch the lint fail**

Run: `python "$SCRATCH/harness/module_lint.py" "$SKILL" performance duplication dead-code`
Expected: six `missing ...` lines and exit code 1.

- [ ] **Step 2: Create `modules/performance.md`**

Create `modules/performance.md`:

````markdown
# Performance Module

## Data Collection (run all in parallel)

### Python
- `py_checks.py` lines for module `performance`: `IMPORT-IN-FUNCTION`, `DB-IN-LOOP`, `GROWS-ONLY`
- Grep (glob `*.py`, 2 lines of context): `argsort\(|sorted\(`, then read for a slice that keeps only the first few items

### .NET
- Grep (globs `*.cs`, `*.razor`): `foreach\s*\(|for\s*\(`, then read loop bodies for EF queries such as `await _db.`
- Grep (globs `*.cs`, `*.razor`, multiline): `\.ToList(Async)?\(\)\s*\.\s*Where\(`

## Risk Indicators

| Finding | Condition | Vector | Score |
|---|---|---|---|
| Per-call work on a hot path | `IMPORT-IN-FUNCTION` or other setup repeated inside code that runs per message, frame or request | degrades / normal use / whole app | 4.0 Medium |
| Import in a rarely called function | `IMPORT-IN-FUNCTION` in a command, startup or error path | maintainability / rare / one feature | 0.6 Low |
| Query per loop iteration | `DB-IN-LOOP` or an EF query in a loop over a collection that grows with users or data | degrades / conditions / one feature | 2.8 Low |
| Stale entries never removed | `GROWS-ONLY` where entries for deleted source data stay behind and are still used | breaks / normal use / one feature | 6.2 Medium |
| Unbounded growth | `GROWS-ONLY` keyed by users, messages or events in a long-running process | degrades / normal use / whole app | 4.0 Medium |
| Full sort for the top few | Sorting a collection that can be large, then keeping only the first few items | degrades / normal use / one feature | 3.5 Low |
| Filtering after loading everything | `.ToList()` before `.Where(` on an EF query | degrades / normal use / one feature | 3.5 Low |

## Analysis Notes

**Hot path:** DiscordVoiceDatabase's `_PerUserPCMSink.write()` imported from `discord.ext.voice_recv.rtp` on every Opus frame, about 50 times a second per speaking user.

**Imports inside functions** are fine in commands and startup code, and are sometimes there to break a circular import. Check before hoisting.

**Stale entries:** DiscordServerAudit's in-memory vector index kept vectors after their message rows were pruned, so searches could return deleted context while memory kept growing.

**Unbounded growth:** the bots run for weeks without restarting, so a dict keyed by user or message needs eviction or cleanup on a lifecycle event.

**Top few:** `np.argsort` over every vector to keep 10 results is O(N log N); `np.argpartition` or `heapq.nlargest` is O(N).

**EF queries:** `.ToList()` pulls every row into memory before the filter runs.
````

- [ ] **Step 3: Create `remediation/performance-fixes.md`**

Create `remediation/performance-fixes.md`:

````markdown
# Performance Remediation

Tag a fix **⚠ BEHAVIOR CHANGE** when users or callers get different results for inputs that already worked. **Test:** lines apply only when the baseline test command ran at least one test, and tests use the repo's existing framework and naming.

---

### Per-call work on a hot path

Move the import or setup to module scope or `__init__`.

```python
from discord.ext.voice_recv.rtp import FakePacket, SilencePacket


class _PerUserPCMSink:
    def write(self, user, data):
        if isinstance(data.packet, (SilencePacket, FakePacket)):
            return
```

**Verify:** `python -m py_compile <file>`; import the module (for example `python -c "import recording.recorder"`) to confirm no circular import; then the baseline test command.

---

### Import in a rarely called function

Hoist the import only when that creates no circular import; otherwise report the finding with `Fix available: no`.

**Verify:** import the module with `python -c "import <module>"`, then the baseline test command.

---

### Query per loop iteration

Load everything the loop needs with one query, then group in memory.

```python
placeholders = ",".join("?" * len(poll_ids))
cursor = await conn.execute(f"SELECT * FROM votes WHERE poll_id IN ({placeholders})", poll_ids)
votes_by_poll = {}
for row in await cursor.fetchall():
    votes_by_poll.setdefault(row["poll_id"], []).append(row)
```

**Verify:** `python -m py_compile <file>`, then the baseline test command.

---

### Stale entries never removed

**⚠ BEHAVIOR CHANGE**: results no longer include entries for deleted data.

Remove entries in the same place the source data is deleted.

```python
deleted_ids = await db.prune_context(cutoff)
self.index.remove(deleted_ids)
```

**Test:** add entries, delete their source rows through the normal path, and assert a search no longer returns them.
**Verify:** `python -m py_compile <file>`, then the new test.

---

### Unbounded growth

**⚠ BEHAVIOR CHANGE**: the oldest entries are evicted.

```python
from collections import OrderedDict


class RecentCache:
    def __init__(self, limit=1000):
        self._items = OrderedDict()
        self._limit = limit

    def remember(self, key, value):
        self._items[key] = value
        self._items.move_to_end(key)
        if len(self._items) > self._limit:
            self._items.popitem(last=False)
```

Deleting entries on the matching lifecycle event (a user leaves, a poll closes) also works.

**Verify:** `python -m py_compile <file>`, then the baseline test command.

---

### Full sort for the top few

```python
k = min(k, len(scores))
top = np.argpartition(-scores, k - 1)[:k]
top = top[np.argsort(-scores[top])]
```

When scores can tie, the order of tied items can differ from the full sort.

**Verify:** `python -m py_compile <file>`; compare old and new results on at least 1000 random inputs, including ties; then the baseline test command.

---

### Filtering after loading everything

Filter before the query runs.

```csharp
var rows = await _db.Datasets.Where(d => d.IsPublished).ToListAsync(ct);
```

When the filter compares strings, check case sensitivity: the database collation can differ from C# string comparison.

**Verify:** `dotnet build`, then `dotnet test`.
````

- [ ] **Step 4: Create `modules/duplication.md`**

Create `modules/duplication.md`:

````markdown
# Duplication Module

## Data Collection (run all in parallel)

### Python
- `py_checks.py` lines for module `duplication`: `DUP-CONFIG-DEFAULT`
- While reading (flagged regions, entry points and config in quick mode; every file in deep mode): three or more near-identical blocks, and code that repeats what a helper in the repo already does

### .NET
- While reading: three or more near-identical blocks, and repeated code a helper already covers

## Risk Indicators

| Finding | Condition | Vector | Score |
|---|---|---|---|
| Default copied into several call sites | `DUP-CONFIG-DEFAULT` where a drifted default would silently change behavior | breaks / future change / one feature | 3.4 Low |
| Cosmetic default copied | `DUP-CONFIG-DEFAULT` where drift would only change a display value | maintainability / future change / one feature | 0.5 Low |
| Copies that have drifted apart | Three or more copies of the same logic where at least one already differs, such as a guard only some copies have | breaks / conditions / one feature | 4.9 Medium |
| Identical copies | Three or more identical copies of the same logic | maintainability / future change / one feature | 0.5 Low |
| Existing helper not used | Code repeats what a helper in the repo already does | maintainability / future change / one feature | 0.5 Low |

## Analysis Notes

**Drifting defaults:** DiscordServerAudit read `factcheck.context.semantic.model` with the default `gemini-embedding-001` in three places. Vectors only load on an exact model and dimension match, so a drifted default would silently load zero vectors.

**Copies:** DiscordServerVote open-coded `dict(row)` plus `json.loads` in five database functions, next to an existing `_row_to_poll` that showed the pattern to follow. Two of three copies of a medal-line loop lacked the bounds check the third had: that is drift.

**Coverage:** quick mode only sees duplication inside the files it reads; "deep audit" finds more.
````

- [ ] **Step 5: Create `remediation/duplication-fixes.md`**

Create `remediation/duplication-fixes.md`:

````markdown
# Duplication Remediation

Tag a fix **⚠ BEHAVIOR CHANGE** when users or callers get different results for inputs that already worked. **Test:** lines apply only when the baseline test command ran at least one test, and tests use the repo's existing framework and naming.

---

### Default copied into several call sites

Put one accessor in the module that owns the setting and route every call site through it. When the copies currently disagree, this is a **⚠ BEHAVIOR CHANGE**: the accessor's value wins everywhere.

```python
def model_name() -> str:
    return config.get("factcheck.context.semantic.model", "gemini-embedding-001")
```

**Test:** patch `model_name` to return a sentinel and assert every consumer receives the sentinel.
**Verify:** `python -m py_compile <files>`, then the new test.

---

### Cosmetic default copied

Move the default into one constant or accessor and use it at every call site.

**Verify:** `python -m py_compile <files>`.

---

### Copies that have drifted apart

**⚠ BEHAVIOR CHANGE**: copies that lacked a fix now behave like the most correct copy.

Extract one helper from the most correct copy and call it from each site.

```python
def _ranked_lines(rows, limit):
    lines = []
    for i, row in enumerate(rows[:limit]):
        medal = MEDALS[i] if i < len(MEDALS) else f"{i + 1}."
        lines.append(f"{medal} {row['name']}: {row['votes']}")
    return lines
```

**Test:** send the input the drifted copy handled wrong (for the medal loop, more rows than medals) through each call site.
**Verify:** `python -m py_compile <files>`, then the new test.

---

### Identical copies

Extract one helper and call it from each site.

```python
def _row_to_vote(row):
    vote = dict(row)
    vote["choices"] = json.loads(vote["choices"])
    return vote
```

**Verify:** `python -m py_compile <files>`, then the baseline test command.

---

### Existing helper not used

Replace the repeated code with a call to the helper. When the helper behaves differently from the repeated code, this is a **⚠ BEHAVIOR CHANGE**.

```python
return [_row_to_vote(row) for row in rows]
```

**Verify:** `python -m py_compile <files>`, then the baseline test command.
````

- [ ] **Step 6: Create `modules/dead-code.md`**

Create `modules/dead-code.md`:

````markdown
# Dead Code Module

## Data Collection (run all in parallel)

### Python
- `python -m flake8 --select=F401,F811,F841 .`
- `py_checks.py` lines for module `dead-code`: `UNUSED-OPTIONAL-PARAM`, `UNREFERENCED-FUNC`

### .NET
- `dotnet build -nologo -clp:NoSummary`: keep lines containing `warning CS0168`, `warning CS0219` or `warning CS0162`
- Grep (glob `*.cs`): `private\s+(static\s+)?(async\s+)?[\w<>\[\],?.]+\s+(\w+)\s*\(`; Grep the repo for each method name and keep names found only at their declaration

## Risk Indicators

| Finding | Condition | Vector | Score |
|---|---|---|---|
| Unused imports or variables | F401, F841, F811 on an import, CS0168 or CS0219, grouped one finding per file | maintainability / normal use / one user | 0.8 Low |
| Name redefined before use | F811 on a function or method | breaks / normal use / one feature | 6.2 Medium |
| Optional parameter never passed | `UNUSED-OPTIONAL-PARAM` confirmed by reading | maintainability / future change / one feature | 0.5 Low |
| Function never referenced | `UNREFERENCED-FUNC` confirmed by reading | maintainability / future change / one feature | 0.5 Low |
| Unreachable code | CS0162, grouped one finding per file | maintainability / normal use / one user | 0.8 Low |
| Private member never referenced | A private method found only at its declaration | maintainability / future change / one feature | 0.5 Low |

## Analysis Notes

**Imports kept for side effects** (a module imported so its import-time code runs, or re-exported from `__init__.py`) are not unused.

**Not dead:** discord.py commands, listeners and views registered through decorators or `add_view`; functions named in strings for `getattr`; public functions another repo imports.

**F811 on a function:** the later definition silently replaces the earlier one, so decide which behavior is intended before deleting either.

**Optional parameters:** DiscordServerAudit's `VectorIndex.search()` kept an `allowed_ids` parameter no caller passed, and its filter branch blocked a faster top-k rewrite.
````

- [ ] **Step 7: Create `remediation/dead-code-fixes.md`**

Create `remediation/dead-code-fixes.md`:

````markdown
# Dead Code Remediation

Tag a fix **⚠ BEHAVIOR CHANGE** when users or callers get different results for inputs that already worked. **Test:** lines apply only when the baseline test command ran at least one test, and tests use the repo's existing framework and naming.

---

### Unused imports or variables

Delete the import. For F841, keep the call when it has side effects and drop only the assignment.

```python
await channel.send(embed=embed)
```

**Verify:** `python -m flake8 --select=F401,F841 <file>` prints nothing, `python -m py_compile <file>`, then the baseline test command.

---

### Name redefined before use

**⚠ BEHAVIOR CHANGE**: the definition that was silently replaced either comes back or goes away.

Keep the intended definition and rename or delete the other one.

**Test:** call the name and assert the intended behavior.
**Verify:** `python -m flake8 --select=F811 <file>` prints nothing, then the new test.

---

### Optional parameter never passed

Remove the parameter and the code that only ran when it was passed.

```python
def search(self, query_vec, k=10):
```

**Verify:** `python -m py_compile <file>`, then the baseline test command.

---

### Function never referenced

Delete the function.

**Verify:** Grep the repo for the name and find no matches, `python -m py_compile <file>`, then the baseline test command.

---

### Unreachable code

Delete the unreachable statements.

**Verify:** `dotnet build` shows no CS0162 for the file, then `dotnet test`.

---

### Private member never referenced

Delete the member.

**Verify:** `dotnet build`, then `dotnet test`.
````

- [ ] **Step 8: Run the lint and confirm it passes**

Run: `python "$SCRATCH/harness/module_lint.py" "$SKILL" performance duplication dead-code`
Expected: `module lint OK: performance, duplication, dead-code`

- [ ] **Step 9: Spot-check detection on the snapshots**

Run: `grep -cP "^performance\t" "$SCRATCH/replay/dvd.hits.txt"; grep -P "^dead-code\t" "$SCRATCH/replay/dsv.hits.txt"`
Expected: `7` (the DB-IN-LOOP lines), then `dead-code	UNUSED-OPTIONAL-PARAM	utils/embeds.py:45	_bar() parameter 'width' is never passed by any caller`. Leave everything uncommitted.

### Task 9: Dependencies and comments modules and remediation

**Files:**
- Create: `modules/dependencies.md`, `remediation/dependencies-fixes.md`, `modules/comments.md`, `remediation/comments-fixes.md`

**Interfaces:**
- Consumes: `$SCRATCH/harness/module_lint.py` and the file format defined in Task 6; `$SCRATCH/replay/*.hits.txt` from Task 5; the bytecraft result from Task 5 Step 4.
- Produces: the last two lint-clean modules. The comments remediation table is a copy of the trim-comments rules, so the two skills stay independent.

- [ ] **Step 1: Watch the lint fail**

Run: `python "$SCRATCH/harness/module_lint.py" "$SKILL" dependencies comments`
Expected: four `missing ...` lines and exit code 1.

- [ ] **Step 2: Create `modules/dependencies.md`**

Create `modules/dependencies.md`:

````markdown
# Dependencies Module

## Data Collection (run all in parallel)

### Python
- `py_checks.py` lines for module `dependencies`: `UNPINNED-DEP`, `UNDECLARED-DEP`
- `python -m pip freeze`, for the installed versions to pin to

### .NET
- `dotnet list package --vulnerable --include-transitive` from the repo root; keep rows that show a severity
- When the command fails because restore or the vulnerability feed is unreachable, list "NuGet vulnerability check" under Not checked

## Risk Indicators

| Finding | Condition | Vector | Score |
|---|---|---|---|
| Unpinned requirements | `UNPINNED-DEP` | outage / rare / whole app | 6.5 Medium |
| Undeclared dependency | `UNDECLARED-DEP` confirmed as a real third-party package | outage / conditions / whole app | 8.0 High |
| Vulnerable package (Critical) | Advisory severity Critical | advisory: Critical | 9.5 Critical |
| Vulnerable package (High) | Advisory severity High | advisory: High | 8.0 High |
| Vulnerable package (Moderate) | Advisory severity Moderate | advisory: Moderate | 5.5 Medium |
| Vulnerable package (Low) | Advisory severity Low | advisory: Low | 2.0 Low |

## Analysis Notes

**Pins:** an unpinned requirement lets a new release break the next deploy. DiscordVoiceDatabase pinned all ten of its requirements during its 2026-09-11 audit. Pin to the versions the tests ran against, keeping extras such as `discord.py[voice]`; the deploy server installs from `requirements.txt`, so the pins become the production versions.

**Undeclared imports:** check the import-to-package mapping first. Namespace extensions come from their own package, for example `discord.ext.voice_recv` from `discord-ext-voice-recv`.

**Transitive vulnerabilities:** bytecraft.us got a vulnerable MimeKit through MailKit 4.15.0 and fixed it by adding an explicit MimeKit 4.15.1 reference.
````

- [ ] **Step 3: Create `remediation/dependencies-fixes.md`**

Create `remediation/dependencies-fixes.md`:

````markdown
# Dependencies Remediation

Tag a fix **⚠ BEHAVIOR CHANGE** when users or callers get different results for inputs that already worked. **Test:** lines apply only when the baseline test command ran at least one test, and tests use the repo's existing framework and naming.

---

### Unpinned requirements

**⚠ BEHAVIOR CHANGE**: deploys install these exact versions and stop picking up new releases.

Pin every line to the version `python -m pip freeze` reports. For example:

```text
discord.py[voice]==2.7.1
aiosqlite==0.21.0
```

**Test:** none practical; the check below proves the pins.
**Verify:** rerun `py_checks.py` for the repo and confirm there is no `UNPINNED-DEP` line.

---

### Undeclared dependency

Add the package with the installed version, for example `numpy==2.2.6`.

**Test:** none practical; the check below proves the declaration.
**Verify:** rerun `py_checks.py` and confirm the `UNDECLARED-DEP` line for that import is gone.

---

### Vulnerable package

**⚠ BEHAVIOR CHANGE**: a library version changes.

Upgrade the direct package to a fixed version, or reference the vulnerable transitive package explicitly at a fixed version.

```xml
<PackageReference Include="MimeKit" Version="4.15.1" />
```

**Test:** none practical; the vulnerability report below proves the upgrade.
**Verify:** `dotnet list package --vulnerable --include-transitive` no longer lists the package, then `dotnet build` and `dotnet test`.
````

- [ ] **Step 4: Create `modules/comments.md`**

Create `modules/comments.md`:

````markdown
# Comments Module

## Data Collection (run all in parallel)

### Python and .NET (globs `*.py`, `*.cs`, `*.razor`)
- Grep: `(#|//|/\*|@\*).*(\x{2500}{2,}|\x{2550}{2,}|={4,})` for banners
- Grep: `(#|//|/\*|@\*).*\x{2014}` for em-dashes in comments
- Grep: `\b(T\d{3}|US\d+|FR-\d{3}|SC-\d{3})\b|Principle [IVX]+\b` for Spec Kit IDs, keeping only matches inside comments or docstrings
- Grep (glob `*.py`): `^\s*"""\s*$` for docstrings that open on their own line
- Grep (globs `*.cs`, `*.razor`): `^\s*///`, then read for blocks longer than one line
- While reading: comments that restate the code, tell its history, or are wrong

## Risk Indicators

| Finding | Condition | Vector | Score |
|---|---|---|---|
| Heavy comments in a file | Banners, em-dashes, Spec Kit IDs, multi-line docstrings or `///` blocks, or comments that restate code, grouped one finding per file | maintainability / normal use / one user | 0.8 Low |
| Wrong comment | A comment that describes behavior the code does not have | degrades / normal use / one feature | 3.5 Low |

## Analysis Notes

**Not findings:** `# noqa`, `# type: ignore`, `#region`, `// <auto-generated>`, `/// <inheritdoc />`, shebang and encoding lines, license headers. Commented-out code is listed in the summary and never changed.

**Wrong comments:** DiscordVoiceDatabase had `# Wait until db is ready (setup_hook sets self.bot.database)` above a line that did no waiting.

**New code:** comments written by any fix in this audit follow `remediation/comments-fixes.md` too.
````

- [ ] **Step 5: Create `remediation/comments-fixes.md`**

Create `remediation/comments-fixes.md`:

````markdown
# Comments Remediation

Only comment and docstring text changes. **Test:** lines do not apply; these findings never reach Impact 0.7.

---

### Heavy comments in a file

| Comment | Becomes |
|---|---|
| Restates what the code shows, or tells its history ("previously", "now uses", "before this existed") | Removed |
| Explains why: a reason, constraint, pitfall, or workaround | Kept at 1 or 2 lines, on the line it explains |
| Docstring or `///` block | One line: `"""..."""` or `/// <summary>...</summary>`. Its why moves to a comment on the line it explains, or above the first body line when it covers the whole function. Removed when the line would only repeat the name, unless that leaves the body empty; then the one line stays |
| Banner like `# ── Setup ──` or `/* ===== FONTS ===== */` | Plain label: `# Setup`, `/* Fonts */` |
| Em-dash | `;`, `:`, `.` or `,` |
| Spec Kit IDs (`T032`, `US3`, `FR-008`, `SC-007`, `Principle I`) | ID removed, sentence kept; the whole comment goes when it only tracks a task |
| Functional: `# noqa`, `# type: ignore`, `#region`, `// <auto-generated>`, `/// <inheritdoc />`, shebang, encoding line, license header | Unchanged |
| Commented-out code | Unchanged |

**Verify:** `python -m py_compile <file>` or `dotnet build`; the diff for the file changes only comment text, docstrings and blank lines.

---

### Wrong comment

Correct the comment to match the code, or remove it when the corrected comment would only restate the code.

**Verify:** the diff for the file changes only comment text.
````

- [ ] **Step 6: Run the lint for all eight modules**

Run: `python "$SCRATCH/harness/module_lint.py" "$SKILL" bugs error-handling concurrency performance duplication dead-code dependencies comments`
Expected: `module lint OK: bugs, error-handling, concurrency, performance, duplication, dead-code, dependencies, comments`

- [ ] **Step 7: Spot-check detection on the snapshots**

Run: `grep -P "^dependencies\t" "$SCRATCH/replay/dsv.hits.txt" "$SCRATCH/replay/dvd.hits.txt"` and the banner Grep from `modules/comments.md` on `$SCRATCH/replay/dsv/cogs/polls.py`.
Expected: one `UNPINNED-DEP` line per snapshot (`2 of 2 requirements are unpinned: discord.py, aiosqlite` and `10 of 10 ...`), and banner matches in `cogs/polls.py`. Leave everything uncommitted.

### Task 10: SKILL.md orchestrator

**Files:**
- Create: `SKILL.md`
- Scratch harness: `$SCRATCH/harness/skill_lint.py`

**Interfaces:**
- Consumes: every module and remediation file from Tasks 6 to 9; `scripts/py_checks.py`.
- Produces: the loadable skill. Report lines follow `[<score>] <title>  (<module>)` and `  Vector: <vector>` so `score_check.py` can parse them.

- [ ] **Step 1: Write the skill lint and watch it fail**

Create `$SCRATCH/harness/skill_lint.py`:

```python
"""Scratch harness: lint code-health-audit/SKILL.md against the spec. Not part of the skill."""
import os
import re
import sys

DESCRIPTION = ("Use when asked to run a code audit, code health check, code cleanup review, "
               "or a scan for improvements on the current repository")
TOOLS = {"Bash(git status *)", "Bash(git diff *)", "Bash(git ls-files *)", "Bash(python -m flake8 *)",
         "Bash(python -m py_compile *)", "Bash(python -m pytest *)", "Bash(python -m unittest *)",
         "Bash(dotnet build *)", "Bash(dotnet test *)", "Bash(dotnet list package *)"}
OPTIONAL_TOOLS = {"Bash(python *py_checks.py *)"}
REQUIRED_TEXT = [
    "Apply this fix? [yes / no / skip-severity / stop]", "Confirm? [yes / no]",
    "No Python or .NET code found. This audit covers those two stacks.", "Deep audit reads",
    "You have uncommitted changes in", "Remediation complete.", "Changes are unstaged and uncommitted.",
    "Undo those fixes? [yes / no]", "Total risk score", "Fix available:", "Not checked",
    "10 × Impact × (0.5 + 0.5 × Likelihood) × (0.6 + 0.4 × Reach)", "scripts/py_checks.py",
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
    if "name: code-health-audit" not in front:
        problems.append("frontmatter name is not code-health-audit")
    if f"description: {DESCRIPTION}" not in front:
        problems.append("frontmatter description differs from the spec")
    tools = set(re.findall(r"^\s+-\s+(Bash\(.+\))\s*$", front, re.M))
    extra = tools - TOOLS - OPTIONAL_TOOLS
    if not TOOLS <= tools or extra:
        problems.append(f"allowed-tools mismatch: missing {sorted(TOOLS - tools)}, extra {sorted(extra)}")
    problems += [f"missing text: {t}" for t in REQUIRED_TEXT if t not in text]
    for ref in sorted(set(re.findall(r"(?:modules|remediation|scripts)/[\w.-]+\.(?:md|py)", text))):
        if not os.path.exists(os.path.join(skill_dir, ref)):
            problems.append(f"references missing file {ref}")
    if "\u2014" in text:
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
```

Run: `python "$SCRATCH/harness/skill_lint.py" "$SKILL"`
Expected: `missing SKILL.md` and exit code 1.

- [ ] **Step 2: Decide the py_checks permission rule**

Fetch the Claude Code permissions documentation with WebFetch (`https://code.claude.com/docs/en/iam`, falling back to `https://docs.claude.com/en/docs/claude-code/iam`) and look for how `*` wildcards match inside Bash rules. If a wildcard before a word is documented (so `Bash(python *py_checks.py *)` matches `python "C:/.../scripts/py_checks.py" .`), add that line to the frontmatter in Step 3. Otherwise leave it out; that command then asks once per audit. Record the decision for the Task 13 report.

- [ ] **Step 3: Create `SKILL.md`**

Create `SKILL.md`:

````markdown
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
````

If Step 2 found the wildcard rule valid, add `  - Bash(python *py_checks.py *)` as the last `allowed-tools` line.

- [ ] **Step 4: Run the skill lint and confirm it passes**

Run: `python "$SCRATCH/harness/skill_lint.py" "$SKILL"` and `wc -w "$SKILL/SKILL.md"`
Expected: `skill lint OK`, and a word count of at most 850.

- [ ] **Step 5: Confirm the skill registers**

Expected: a system notice listing `code-health-audit` with the spec description appears after the file is created. If it does not appear, start a new session in `C:\Users\Sam Elhag.EREF\.claude\skills` and confirm `/code-health-audit` is listed. Leave everything uncommitted.

### Task 11: Full replay audits and cost measurement

**Files:**
- None in the skill unless a known answer is missed (Step 8). Scratch: `$SCRATCH/harness/usage_now.py`, `$SCRATCH/replay/<clone>.<mode>.report.txt`, `$SCRATCH/replay/costs.md`

**Interfaces:**
- Consumes: the finished skill (Tasks 1 to 10), replay clones (Task 5), `score_check.py` (Task 6).
- Produces: saved reports and measured costs used by Tasks 12 and 13.

Run Tasks 11 to 13 in a new session opened in `C:\Users\Sam Elhag.EREF\.claude\skills`, so token counts are comparable with the past audits and the skill loads from the finished files. For every audit, treat the clone as the repository: run commands with the clone as the working directory, pass the clone as the Grep path, and pass it as `py_checks.py`'s root.

Known answers by mode:

| Clone | Must appear in quick mode | Must appear in deep mode | Recorded only |
|---|---|---|---|
| `dsv` | Import-time side effect in `config.py`; Discord text over its limit at `cogs/history.py:85`; unused imports in `bot.py` and `utils/embeds.py` | Everything from quick, plus identical or drifted copies of the vote-row conversion in `models/database.py` | |
| `dvd` | `[10.0]` blocking call at `recording/recorder.py:580`; `[6.5] Unpinned requirements` | | Unsynchronized shared state around playback or Whisper |
| `bytecraft` | A `Vulnerable package` finding for MimeKit with `Vector: advisory: <severity>`, or `Not checked` naming the NuGet vulnerability check | | |

- [ ] **Step 0: Prepare this session's scratch folder**

A new session has its own scratchpad, so recreate what earlier tasks left in the old one:
1. Run the commands in Task 5 Step 1 (clone the three snapshots) and Task 5 Step 2 (write `dsv.hits.txt` and `dvd.hits.txt`); expect the same outputs listed there.
2. Create `$SCRATCH/harness/score_check.py` and `$SCRATCH/harness/module_lint.py` with the exact contents shown in Task 6 Step 1, and `$SCRATCH/harness/skill_lint.py` with the exact contents shown in Task 10 Step 1.
3. Run `python "$SCRATCH/harness/score_check.py" --self-test` and `python "$SCRATCH/harness/skill_lint.py" "$SKILL"`; expect `score_check self-test OK` and `skill lint OK`.

- [ ] **Step 1: Create the usage counter**

Create `$SCRATCH/harness/usage_now.py`:

```python
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
            context = sum(usage.get(k, 0) or 0 for k in ("input_tokens", "cache_read_input_tokens",
                                                          "cache_creation_input_tokens"))
            responses[message.get("id") or f"line{number}"] = (usage.get("output_tokens", 0) or 0, context)
output = sum(v[0] for v in responses.values())
context = sum(v[1] for v in responses.values())
print(f"{os.path.basename(latest)} responses={len(responses)} output={output} context={context}")
```

Run: `python "$SCRATCH/harness/usage_now.py"`
Expected: one line such as `<session-id>.jsonl responses=3 output=1200 context=90000`. Record it as the starting point.

- [ ] **Step 2: Quick audit on `dsv`**

Invoke `/code-health-audit` for `$SCRATCH/replay/dsv`. Answer `stop` at the first `Apply this fix?` prompt. Save the report text, from the first `═══` line through the last finding, to `$SCRATCH/replay/dsv.quick.report.txt`. Run `usage_now.py` again and record the difference.

Run: `python "$SCRATCH/harness/score_check.py" "$SCRATCH/replay/dsv.quick.report.txt"`
Expected: `report scores OK`, and the report contains every quick-mode known answer for `dsv`.

- [ ] **Step 3: Deep audit on `dsv`**

Ask for a deep audit of `$SCRATCH/replay/dsv`. Expected first reply: `Deep audit reads <n> files (~<lines> lines). Continue? [yes / no]`. Answer `yes`, then `stop` at the first fix prompt. Save `$SCRATCH/replay/dsv.deep.report.txt`, run `score_check.py` on it, and record the usage difference.
Expected: `report scores OK` and every deep-mode known answer for `dsv`.

- [ ] **Step 4: Quick audit on `dvd`**

Run the quick audit on `$SCRATCH/replay/dvd`, answer `stop` at the first prompt, save `$SCRATCH/replay/dvd.quick.report.txt`, run `score_check.py`, record usage.
Expected: `report scores OK`; the BASELINE line shows no test suite; the `[10.0]` finding and `[6.5] Unpinned requirements` appear. Note whether a shared-state finding for playback or Whisper appears.

- [ ] **Step 5: Quick audit on `bytecraft`**

Run the quick audit on `$SCRATCH/replay/bytecraft`, answer `stop` at the first prompt (or let it finish when nothing is fixable), save `$SCRATCH/replay/bytecraft.quick.report.txt`, run `score_check.py`, record usage.
Expected: `report scores OK` and the bytecraft known answer.

- [ ] **Step 6: Confirm the user's repos were only read**

Run: `for r in DiscordServerVote DiscordVoiceDatabase bytecraft.us; do git -C "$REPOS/$r" status --short; done`
Expected: no output.

- [ ] **Step 7: Write the cost comparison**

Create `$SCRATCH/replay/costs.md` with one row per audit (responses, output tokens, context tokens) and this reference row, measured the same way: the two 2026-09-11 scans used 17k to 24k output and about 1.7M context tokens each before producing any report. A quick audit passes this check when it produces a full report with fewer context tokens than 1.7M.

- [ ] **Step 8: Fix any missed known answer**

For each known answer missing from its required mode:
- If `$SCRATCH/replay/<clone>.hits.txt` has the py_checks line but the report lacks the finding, make the matching Risk Indicator condition or Analysis Note in `modules/` more precise, rerun `module_lint.py`, and rerun that audit in a new session (a skill edited mid-session keeps its first-loaded text).
- If the py_checks line is missing, add a failing test to `scripts/test_py_checks.py` first, fix `scripts/py_checks.py`, run the unit tests until they pass, then rerun the audit.

Record every change for the Task 13 report. Leave everything uncommitted.

### Task 12: Fix loop run and automatic checks

**Files:**
- None in the skill. Scratch: the `dsv` clone, `$SCRATCH/replay/dsv_check` (a second clone), `$SCRATCH/replay/dsv.loop.report.txt`

**Interfaces:**
- Consumes: the finished skill, `score_check.py`, the `dsv` clone.
- Produces: evidence that every loop path works: `yes` with a test, `yes` on a ⚠ fix, `no`, `skip-severity`, a failed check with undo, and `stop`.

- [ ] **Step 1: Start from a clean clone**

```bash
cd "$SCRATCH/replay/dsv" && git status --short
```

Expected: no output. If anything is listed, run `git checkout -- . && git clean -fd` inside this scratch clone only, then check again.

- [ ] **Step 2: Run the audit and answer the loop by these rules**

Invoke `/code-health-audit` for `$SCRATCH/replay/dsv` in quick mode and save the report to `$SCRATCH/replay/dsv.loop.report.txt`. Then answer:

1. The first prompt tagged ⚠ (expected `[6.5] Unpinned requirements`): `yes`, then `yes` at `⚠ ... Confirm? [yes / no]`. Expected: no Test line, pins written from `python -m pip freeze`, and a py_checks rerun without `UNPINNED-DEP`.
2. The first prompt with a `Test:` line (expected `[4.3] Discord text over its limit` at `cogs/history.py:85`): `yes`. Expected: the skill reports the new test failing before the change and passing after it.
3. The next prompt (expected `[4.0] Import-time side effect` in `config.py`): `no`.
4. The next prompt if it is still Medium: `skip-severity`. If the Medium band has already ended, answer `skip-severity` at the Low prompt that follows rule 5 instead of `stop`, and answer `stop` at the Low prompt after that.
5. The first Low prompt whose fix touches exactly one Python file (expected unused imports in `bot.py` or `utils/embeds.py`): before answering, in that file's folder remove the `__pycache__` directory and create an empty file named `__pycache__`, so `python -m py_compile` fails. Answer `yes`. Expected: the check fails, the skill undoes that fix's edits, reports the error and continues. Then delete the `__pycache__` file.
6. The next prompt: `stop`.

- [ ] **Step 3: Check scores and changed files**

```bash
python "$SCRATCH/harness/score_check.py" "$SCRATCH/replay/dsv.loop.report.txt"
cd "$SCRATCH/replay/dsv" && git status --short && git diff --quiet -- config.py && echo "config.py unchanged"
```

Expected: `report scores OK`; `git status --short` lists `requirements.txt`, `cogs/history.py` and the new untracked test file, and nothing else; `config.py unchanged`. The file from rule 5 must not appear.

- [ ] **Step 4: Prove the new test fails on the original code**

```bash
cd "$SCRATCH/replay" && rm -rf dsv_check && git clone -q --no-hardlinks dsv dsv_check && git -C dsv_check checkout -q d426eed
NEW_TEST=$(git -C dsv status --short | awk '/^\?\? tests\//{print $2}')
cp "dsv/$NEW_TEST" "dsv_check/$NEW_TEST"
cd dsv_check && python -m unittest discover -s tests -t .
cd ../dsv && python -m unittest discover -s tests -t .
```

Expected: `FAILED` in `dsv_check` (the original `history.py`), then `Ran 31 tests` and `OK` in `dsv`.

- [ ] **Step 5: Check the summary against what happened**

Expected in the printed summary: `Fixed   : 2`, `Failed  : 1`, `Tests   : 1 added · 31 passed (baseline 30)`, `risk reduced by` equal to the two fixed scores added together (10.8 when they are 6.5 and 4.3), `Skipped` equal to the number of findings answered `no` or covered by `skip-severity` and `stop`, and the closing line `Changes are unstaged and uncommitted.`

If any expectation fails, fix the matching section of `SKILL.md` (or the remediation file involved), rerun `skill_lint.py` and `module_lint.py`, and repeat Tasks 12 Steps 1 to 5 in a new session. Leave everything uncommitted.

### Task 13: Wrap-up and handoff

**Files:**
- Modify: `C:\Users\Sam Elhag.EREF\.claude\projects\C--Users-Sam-Elhag-EREF--claude-skills\memory\skills-roadmap.md` (status line for item 3)

**Interfaces:**
- Consumes: results from Tasks 1 to 12.
- Produces: the final report to the user and the commands they run themselves.

- [ ] **Step 1: Run every check one last time**

```bash
python -m unittest discover -s "$SKILL/scripts" -p "test_py_checks.py"
python -m flake8 --max-line-length=127 "$SKILL/scripts"
python "$SCRATCH/harness/module_lint.py" "$SKILL" bugs error-handling concurrency performance duplication dead-code dependencies comments
python "$SCRATCH/harness/skill_lint.py" "$SKILL"
python -c "import pathlib, sys; hits = [str(p) for p in pathlib.Path(sys.argv[1]).rglob('*.md') if chr(0x2014) in p.read_text(encoding='utf-8')]; print(chr(10).join(hits) or 'no em-dashes')" "$SKILL"
git -C "/c/Users/Sam Elhag.EREF/.claude/skills" status --short
```

Expected: `Ran 25 tests` and `OK` (more if Task 11 added tests); no flake8 output; `module lint OK: ...`; `skill lint OK`; `no em-dashes`; `git status` shows `code-health-audit/` plus any skills the user has not committed yet, and nothing staged.

- [ ] **Step 2: Update the roadmap memory**

In `skills-roadmap.md`, replace the item 3 text with `` `code-health-audit` `` followed by "(built and tested", today's date, and ", left uncommitted for the user)". Add any new testing lesson to `skill-testing-notes.md`, one line each.

- [ ] **Step 3: Report to the user**

Report, in plain language:
- Unit test count, lint results, and the known answers caught per replay and mode, including anything recorded only (playback or Whisper shared state)
- Token costs from `costs.md` next to the 2026-09-11 reference
- Decisions made during the build: Discord limit values (Task 6 Step 2), the py_checks permission rule (Task 10 Step 2), and any module or py_checks change from Task 11 Step 8
- The check only the user can do: in a new session in a real repo, say "code health audit", confirm this skill runs, and note any permission prompts

Then give the commit commands, one per `bash` block, without running them:

```bash
git add -A
```

```bash
git commit -m "Adding code-health-audit skill"
```

```bash
git push
```
