"""Standard-library Python checks for the code-health-audit skill.

Usage: python py_checks.py <repo-root> [path ...]
"""
import ast
import os
import re
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


FILE_CHECKS = [check_attr_outside_init, check_import_side_effect, check_mutable_default,
               check_except_swallow, check_except_no_traceback, check_task_unstored,
               check_import_in_function, check_db_in_loop, check_grows_only]
REPO_CHECKS = [check_blocking_in_async, check_dup_config_default, check_unused_optional_param,
               check_unreferenced_func, check_unpinned_dep, check_undeclared_dep]


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
