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


if __name__ == "__main__":
    unittest.main()
