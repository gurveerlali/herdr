import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "plugin"))

import wtsearch  # noqa: E402
from wtsearch import (  # noqa: E402
    common_dir,
    dedupe_repos,
    list_all,
    read_cache,
    scan_repos,
    workspace_paths,
    worktree_lines,
    write_cache,
)


def git(*args, cwd):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


def make_repo(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    git("init", "-q", "-b", "main", cwd=path)
    git("-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "--allow-empty", "-m", "i", cwd=path)
    return path


def wt_result(name, worktrees, root=None):
    src = {"repo_name": name, "source_checkout_path": root or f"/{name}"}
    return {"result": {"source": src, "worktrees": worktrees}}


def wt(path, branch=None, ws=None, detached=False, prunable=False):
    d = {"path": path, "is_detached": detached, "is_prunable": prunable}
    if branch is not None:
        d["branch"] = branch
    if ws is not None:
        d["open_workspace_id"] = ws
    return d


class ScanTests(unittest.TestCase):
    def test_scan_finds_repos_and_prunes(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            for d in ["a", "b/c", ".hidden/r", "Library/r", "node_modules/r", ".Trash/r", "d/e/f/g"]:
                (root / d / ".git").mkdir(parents=True)
            # a nested repo inside a found repo must not be returned separately
            (root / "a" / "sub" / ".git").mkdir(parents=True)
            (root / "wt").mkdir()
            (root / "wt" / ".git").write_text("gitdir: /elsewhere\n")
            self.assertEqual(sorted(scan_repos(root)), [root / "a", root / "b" / "c"])


class DedupeTests(unittest.TestCase):
    def test_dedupe_by_common_dir(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t).resolve()
            r = make_repo(root / "R")
            w = root / "W"
            git("worktree", "add", "-q", "-b", "feat", str(w), cwd=r)
            s = make_repo(root / "S")
            n = root / "N"
            n.mkdir()
            self.assertEqual(dedupe_repos([r, w, s, n], common_dir), [r, s])

    def test_common_dir_none_for_non_repo(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertIsNone(common_dir(Path(t)))


class ParseTests(unittest.TestCase):
    def test_workspace_paths(self):
        j = {"result": {"panes": [{"cwd": "/x"}, {"cwd": "/y"}]}}
        self.assertEqual(workspace_paths(j), [Path("/x"), Path("/y")])

    def test_worktree_lines(self):
        r = wt_result("myapp", root="/m", worktrees=[
            wt("/m", "main", ws="w21"),
            wt("/d", detached=True),
            wt("/p", "x", prunable=True),
        ])
        self.assertEqual(worktree_lines(r), [
            "●\tmyapp\tmain\t/m\tw21\t/m",
            " \tmyapp\t(detached)\t/d\t\t/m",
        ])

    def test_line_path_with_space(self):
        [line] = worktree_lines(wt_result("r", [wt("/a b/c", "f")]))
        self.assertEqual(line.split("\t")[3], "/a b/c")


class ListAllTests(unittest.TestCase):
    def test_list_all_skips_failing_repo(self):
        a, b, c = Path("/A"), Path("/B"), Path("/C")

        def fetch(repo):
            if repo == b:
                raise RuntimeError("boom")
            return wt_result(repo.name, [wt(str(repo), "main")])

        err = io.StringIO()
        with redirect_stderr(err):
            lines = list_all([a, b, c], fetch)
        self.assertEqual(lines, [" \tA\tmain\t/A\t\t/A", " \tC\tmain\t/C\t\t/C"])
        self.assertIn("wtsearch: skip /B: boom", err.getvalue())


class CacheTests(unittest.TestCase):
    def test_read_cache_missing_returns_none(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertIsNone(read_cache(Path(t) / "nope.json"))

    def test_write_cache_is_atomic(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "sub" / "repos.json"
            write_cache(p, [Path("/one"), Path("/two")])
            self.assertEqual(read_cache(p), [Path("/one"), Path("/two")])
            with mock.patch("wtsearch.os.replace", side_effect=OSError("interrupted")):
                with self.assertRaises(OSError):
                    write_cache(p, [Path("/three")])
            self.assertEqual(read_cache(p), [Path("/one"), Path("/two")])
            self.assertEqual([f.name for f in p.parent.iterdir()], ["repos.json"])


class MainTests(unittest.TestCase):
    def test_list_discovers_when_no_cache(self):
        with tempfile.TemporaryDirectory() as t:
            cache = Path(t) / "repos.json"
            calls = []

            def fake_discover():
                calls.append(1)
                write_cache(cache, [Path("/A")])

            def fake_herdr(args):
                self.assertEqual(args, ["worktree", "list", "--cwd", "/A"])
                return wt_result("A", [wt("/A", "main")])

            out = io.StringIO()
            with mock.patch.object(wtsearch, "cache_path", return_value=cache), \
                 mock.patch.object(wtsearch, "discover", side_effect=fake_discover), \
                 mock.patch.object(wtsearch, "herdr_json", side_effect=fake_herdr), \
                 redirect_stdout(out):
                rc = wtsearch.main(["list"])
            self.assertEqual(rc, 0)
            self.assertEqual(calls, [1])
            self.assertEqual(out.getvalue(), " \tA\tmain\t/A\t\t/A\n")


if __name__ == "__main__":
    unittest.main()
