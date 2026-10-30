# Worktree Search Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A herdr plugin popup, opened with Cmd+Shift+J (iTerm) → Ctrl+Alt+F (herdr), that fuzzy-searches every worktree of every repo and jumps to the chosen one.

**Architecture:**
- `wtsearch.py` (Python 3 stdlib) discovers repos and prints one tab-separated line per worktree.
- `picker.sh` pipes those lines into fzf and acts on the selection through the herdr CLI.
- A herdr plugin manifest exposes the picker as a popup pane and an `open` action, which `config.toml` binds to `ctrl+alt+f`.

**Tech Stack:** Python 3 stdlib (`unittest`, `subprocess`, `json`, `concurrent.futures`), bash, fzf, herdr 0.9.3 CLI.

**Spec:** `docs/superpowers/specs/2026-10-30-worktree-search-design.md`

## Global Constraints

- Plugin id `local.wtsearch`, `min_herdr_version = "0.7.0"`, `platforms = ["macos", "linux"]`.
- Call herdr as `${HERDR_BIN_PATH:-herdr}`. Never pass `--trust-repository`.
- herdr CLI errors come back as JSON `{"error": {...}}`, sometimes with exit status 0. Treat a top-level `error` key as failure.
- Disk scan: root `~`, maxdepth 3. Prune hidden dirs (names starting with `.`), `Library`, `node_modules` and `.Trash`. A repo is a dir whose `.git` is a **directory**.
- Cache: `$HERDR_PLUGIN_STATE_DIR/repos.json`, falling back to `~/.local/state/wtsearch/repos.json` when the var is unset (CLI/tests).
- Line format: `marker\trepo\tbranch\tpath\topen_workspace_id`.
  - `marker` is `●` when the worktree is open, otherwise one space.
  - Detached worktrees show `(detached)` as the branch.
  - Prunable worktrees are skipped.
- Popup is 80% × 80%. Key is `ctrl+alt+f`. iTerm sends hex `0x1b 0x06` on Cmd+Shift+J.
- Back up `~/.config/herdr/config.toml` to `config.toml.bak-wtsearch` before editing it.

## Review Focus

1. **Paths containing spaces:** Enter must still open and focus the right worktree, so fields are split on tabs only and quoted in shell. Test `test_line_path_with_space` (Task 1); live check in Task 2.
2. **A cached repo deleted from disk, or herdr reporting an error such as trust required:** that repo is skipped with a stderr warning and the rest still list. Test `test_list_all_skips_failing_repo` (Task 1).
3. **Background discover writing the cache while `list` reads it:** the reader never sees a half-written file, because writes go to a temp file and are moved into place with `os.replace`. Test `test_write_cache_is_atomic` (Task 1).
4. **Esc, or Enter with no match:** the popup closes silently with no herdr call. Live check in Task 2.
5. **First run with no cache:** `list` runs discover synchronously instead of showing an empty list. Test `test_list_discovers_when_no_cache` (Task 1).

---

### Task 1: `wtsearch.py`, repo discovery and worktree listing

**Files:**
- Create: `plugin/wtsearch.py`
- Test: `tests/test_wtsearch.py`

**Interfaces:**
- Produces (all in `plugin/wtsearch.py`):
  - `scan_repos(root: Path, max_depth: int = 3) -> list[Path]`: implement with `os.walk` and in-place pruning of `dirnames`, not `find`. Don't descend into a repo once it's found.
  - `common_dir(path: Path) -> Path | None`: `git -C path rev-parse --path-format=absolute --git-common-dir`, resolved. Returns `None` on failure.
  - `workspace_paths(herdr_json: dict) -> list[Path]`: the `cwd` of each pane in a parsed `herdr pane list` result.
  - `dedupe_repos(paths: list[Path], common_dir_fn) -> list[Path]`: one entry per distinct common dir, keeping the first path seen. Drops paths where `common_dir_fn` returns `None`.
  - `worktree_lines(result: dict) -> list[str]`: takes a parsed `herdr worktree list` response. The repo name comes from `result.source.repo_name`.
  - `list_all(repos: list[Path], fetch) -> list[str]`: `fetch(repo) -> dict` raises on failure. Runs in a ThreadPoolExecutor and keeps the input repo order. A failure prints `wtsearch: skip <repo>: <err>` to stderr.
  - `read_cache(path: Path) -> list[Path] | None` and `write_cache(path: Path, repos: list[Path]) -> None` (atomic).
  - CLI:
    - `python3 wtsearch.py discover`: scan plus workspace paths, dedupe, write the cache.
    - `python3 wtsearch.py list`: read the cache (discovering first if it's missing), print the lines.
    - `herdr_json(args: list[str]) -> dict` runs the herdr CLI. It raises `RuntimeError(message)` on a non-zero exit, invalid JSON or a top-level `error` key.

- [ ] **Step 1: Write the failing tests** in `tests/test_wtsearch.py`. Import via `sys.path.insert(0, <repo>/plugin)`. Use `tempfile.TemporaryDirectory` trees for the scan and real `git init` / `git worktree add` for `common_dir`.

```python
def test_scan_finds_repos_and_prunes(self):
    # tree: a/.git/ (dir), b/c/.git/ (dir), .hidden/r/.git/, Library/r/.git/,
    #       node_modules/r/.git/, d/e/f/g/.git/ (depth 4), wt/.git (FILE)
    self.assertEqual(sorted(scan_repos(root)), [root/"a", root/"b"/"c"])

def test_dedupe_by_common_dir(self):
    # real repo R plus linked worktree W of R, plus unrelated repo S, plus a non-repo dir N
    self.assertEqual(dedupe_repos([R, W, S, N], common_dir), [R, S])

def test_workspace_paths(self):
    j = {"result": {"panes": [{"cwd": "/x"}, {"cwd": "/y"}]}}
    self.assertEqual(workspace_paths(j), [Path("/x"), Path("/y")])

def test_worktree_lines(self):
    r = {"result": {"source": {"repo_name": "myapp"}, "worktrees": [
        {"branch": "main", "path": "/m", "open_workspace_id": "w21", "is_prunable": False, "is_detached": False},
        {"path": "/d", "is_prunable": False, "is_detached": True},
        {"branch": "x", "path": "/p", "is_prunable": True, "is_detached": False}]}}
    self.assertEqual(worktree_lines(r), [
        "●\tmyapp\tmain\t/m\tw21",
        " \tmyapp\t(detached)\t/d\t"])

def test_line_path_with_space(self):
    # worktree path "/a b/c" with branch "f" → line split on "\t" has field[3] == "/a b/c"

def test_list_all_skips_failing_repo(self):
    # fetch raises RuntimeError for repo B; A and C succeed
    # result == lines(A) + lines(C); stderr contains "wtsearch: skip"

def test_write_cache_is_atomic(self):
    # patch os.replace to raise mid-write: an existing cache stays readable and unchanged;
    # normal write then read_cache round-trips the list of Paths

def test_read_cache_missing_returns_none(self):
    self.assertIsNone(read_cache(tmp/"nope.json"))

def test_list_discovers_when_no_cache(self):
    # main(["list"]) with cache path in tmp, discover patched to write [A];
    # herdr_json patched → discover called once, A's lines printed
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd ~/herdr-worktree-search && python3 -m unittest discover -s tests -v`
Expected: FAIL / ERROR with `ModuleNotFoundError: No module named 'wtsearch'`.

- [ ] **Step 3: Implement `plugin/wtsearch.py`** with the interfaces above. `main(argv: list[str]) -> int` is the entry point; `if __name__ == "__main__": sys.exit(main(sys.argv[1:]))`. The cache path comes from `cache_path() -> Path` (see Global Constraints).

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -m unittest discover -s tests -v`
Expected: all 9 pass.

- [ ] **Step 5: Smoke-test against the real herdr**

Run: `python3 plugin/wtsearch.py discover && python3 plugin/wtsearch.py list | cut -f2 | sort | uniq -c`
Expected: counts for `myapp`, `linear-cli` and `herdr-md-viewer`, with no tracebacks.

- [ ] **Step 6: Commit**

```bash
git add plugin/wtsearch.py tests/test_wtsearch.py
git commit -m "feat: wtsearch discovery and worktree listing"
```

### Task 2: Plugin, fzf picker, key binding, README

**Files:**
- Create: `plugin/herdr-plugin.toml`, `plugin/open.sh`, `plugin/picker.sh`, `README.md`
- Modify: `~/.config/herdr/config.toml` (append binding; back up first)

**Interfaces:**
- Consumes: `python3 wtsearch.py list` and `python3 wtsearch.py discover` (Task 1), plus the line format in Global Constraints.
- Produces:
  - action `local.wtsearch.open`, which runs `bash open.sh`
  - pane entrypoint `picker` (`placement = "popup"`, `width = "80%"`, `height = "80%"`), which runs `bash picker.sh`

- [ ] **Step 1: Install fzf**

Run: `brew install fzf && fzf --version`
Expected: a version string.

- [ ] **Step 2: Write `herdr-plugin.toml` and `open.sh`.**
  - `open.sh` runs `exec "${HERDR_BIN_PATH:-herdr}" plugin pane open --plugin local.wtsearch --entrypoint picker`.

- [ ] **Step 3: Write `picker.sh`**
  - **Startup:**
    - Start `python3 wtsearch.py discover >/dev/null 2>&1 &` (skip when no cache exists; `list` discovers synchronously then).
    - Pipe `python3 wtsearch.py list` into fzf with `--delimiter=$'\t' --with-nth=1..4 --header 'enter: open  alt-r: rescan  esc: close'` and `--bind "alt-r:reload(python3 wtsearch.py discover && python3 wtsearch.py list)"`.
  - **Empty selection** (Esc or no match): `exit 0`.
  - **Otherwise:** split the selection on tabs with `IFS=$'\t' read -r _ _ _ path ws`, then:
    - if `ws` is non-empty, run `herdr workspace focus "$ws"`
    - otherwise run `herdr worktree open --cwd "$path" --path "$path" --focus`
  - **Failure:** if the herdr call exits non-zero or prints a top-level `error` key, print the output and `read -n1 -p "press a key"`.

- [ ] **Step 4: Link the plugin and bind the key**

```bash
herdr plugin link ~/herdr-worktree-search/plugin
cp ~/.config/herdr/config.toml ~/.config/herdr/config.toml.bak-wtsearch
cat >> ~/.config/herdr/config.toml <<'EOF'

[[keys.command]]
key = "ctrl+alt+f"
type = "plugin_action"
command = "local.wtsearch.open"
description = "search worktrees"
EOF
herdr server reload-config
herdr plugin action list --plugin local.wtsearch
```

Expected: the action list shows `open`, and reload-config returns no error.

- [ ] **Step 5: Live check: popup and filtering.** Run `herdr plugin action invoke local.wtsearch.open`, then use `herdr pane`/screen reads, or Gurveer's eyes, to confirm:
  - The popup shows rows from all three repos.
  - Typing `123 money` narrows the list to `myapp-eng-123-card-money`.
  - Esc closes it and leaves no stray pane in `herdr pane list`.

- [ ] **Step 6: Live check: Enter**
  - On a ● row (e.g. `myapp-eng-123-card`, workspace `w23`): `herdr workspace list` shows that workspace focused.
  - On an unopened row (e.g. `myapp-eng-456`): a new workspace appears, labelled for that worktree, and is focused.
  - Close only that new workspace afterwards with `herdr workspace close <id>`.

- [ ] **Step 7: Write `README.md`**
  - What it does, the install steps from Step 4, and the dependencies (fzf, python3).
  - The iTerm mapping: Settings → Keys → Key Bindings → + → shortcut Cmd+Shift+J → action "Send Hex Codes" → `0x1b 0x06`.
  - Ctrl+Alt+F as the fallback.
  - That Cmd+Shift+F was avoided because it's iTerm's Find Globally.

- [ ] **Step 8: Gurveer adds the iTerm mapping and confirms that Cmd+Shift+J opens the popup.**

- [ ] **Step 9: Commit**

```bash
git add plugin/herdr-plugin.toml plugin/open.sh plugin/picker.sh README.md
git commit -m "feat: herdr popup picker for worktree search"
```
