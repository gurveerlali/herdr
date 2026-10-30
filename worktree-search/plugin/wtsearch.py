#!/usr/bin/env python3
"""Discover git repos and list their worktrees for the herdr worktree-search popup.

Usage:
  wtsearch.py discover   scan for repos and refresh the cache
  wtsearch.py list       print one tab-separated line per worktree:
                         marker  repo  branch  path  open_workspace_id  repo_root
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

PRUNE = {"Library", "node_modules", ".Trash"}
OPEN_MARKER = "●"


def herdr_bin() -> str:
    return os.environ.get("HERDR_BIN_PATH") or "herdr"


def cache_path() -> Path:
    state = os.environ.get("HERDR_PLUGIN_STATE_DIR")
    base = Path(state) if state else Path.home() / ".local" / "state" / "wtsearch"
    return base / "repos.json"


def scan_repos(root: Path, max_depth: int = 3) -> list[Path]:
    """Return dirs (at most max_depth below root) whose .git is a directory."""
    root = Path(root)
    found: list[Path] = []
    base_depth = len(root.parts)
    for dirpath, dirnames, _ in os.walk(root):
        here = Path(dirpath)
        if os.path.isdir(here / ".git") and here != root:
            found.append(here)
            dirnames[:] = []  # don't descend into a repo
            continue
        if len(here.parts) - base_depth >= max_depth:
            dirnames[:] = []
            continue
        dirnames[:] = [d for d in dirnames if not d.startswith(".") and d not in PRUNE]
    return found


def common_dir(path: Path) -> Path | None:
    try:
        out = subprocess.run(
            ["git", "-C", str(path), "rev-parse", "--path-format=absolute", "--git-common-dir"],
            capture_output=True, text=True, timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0 or not out.stdout.strip():
        return None
    return Path(out.stdout.strip()).resolve()


def workspace_paths(herdr_json: dict) -> list[Path]:
    panes = herdr_json.get("result", {}).get("panes", [])
    return [Path(p["cwd"]) for p in panes if p.get("cwd")]


def dedupe_repos(paths: list[Path], common_dir_fn) -> list[Path]:
    seen: set[Path] = set()
    out: list[Path] = []
    for p in paths:
        cd = common_dir_fn(p)
        if cd is None or cd in seen:
            continue
        seen.add(cd)
        out.append(p)
    return out


def worktree_lines(result: dict) -> list[str]:
    res = result.get("result", {})
    src = res.get("source", {})
    repo = src.get("repo_name", "?")
    root = src.get("source_checkout_path") or src.get("repo_root") or ""
    lines = []
    for w in res.get("worktrees", []):
        if w.get("is_prunable"):
            continue
        ws = w.get("open_workspace_id") or ""
        marker = OPEN_MARKER if ws else " "
        branch = "(detached)" if w.get("is_detached") or not w.get("branch") else w["branch"]
        lines.append("\t".join([marker, repo, branch, w["path"], ws, root]))
    return lines


def list_all(repos: list[Path], fetch) -> list[str]:
    def one(repo):
        try:
            return worktree_lines(fetch(repo))
        except Exception as e:  # noqa: BLE001 - any failure skips just this repo
            print(f"wtsearch: skip {repo}: {e}", file=sys.stderr)
            return []

    if not repos:
        return []
    with ThreadPoolExecutor(max_workers=min(8, len(repos))) as ex:
        results = list(ex.map(one, repos))
    return [line for lines in results for line in lines]


def read_cache(path: Path) -> list[Path] | None:
    try:
        data = json.loads(Path(path).read_text())
    except (OSError, ValueError):
        return None
    return [Path(p) for p in data.get("repos", [])]


def write_cache(path: Path, repos: list[Path]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".repos-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump({"repos": [str(r) for r in repos]}, f)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def herdr_json(args: list[str]) -> dict:
    proc = subprocess.run([herdr_bin(), *args], capture_output=True, text=True, timeout=30)
    try:
        data = json.loads(proc.stdout)
    except ValueError:
        raise RuntimeError((proc.stderr or proc.stdout).strip() or f"exit {proc.returncode}")
    if "error" in data:
        err = data["error"]
        raise RuntimeError(err.get("message", str(err)) if isinstance(err, dict) else str(err))
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or f"exit {proc.returncode}")
    return data


def discover() -> None:
    paths = scan_repos(Path.home())
    try:
        paths += workspace_paths(herdr_json(["pane", "list"]))
    except Exception as e:  # noqa: BLE001 - herdr unavailable: disk scan only
        print(f"wtsearch: pane list failed: {e}", file=sys.stderr)
    write_cache(cache_path(), dedupe_repos(paths, common_dir))


def main(argv: list[str]) -> int:
    cmd = argv[0] if argv else ""
    if cmd == "discover":
        discover()
        return 0
    if cmd == "list":
        repos = read_cache(cache_path())
        if repos is None:
            discover()
            repos = read_cache(cache_path()) or []
        for line in list_all(repos, lambda r: herdr_json(["worktree", "list", "--cwd", str(r)])):
            print(line)
        return 0
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
