# Worktree search for herdr: design

## Goal
Press **Cmd+Shift+J** in iTerm while using herdr to open a popup. Type to fuzzy-filter every git worktree of every repo, then press Enter to jump to it. Success means reaching any worktree in a few keystrokes instead of scanning the herdr sidebar.

## Constraints
- herdr 0.9.3 is a closed binary, so this is built as a **herdr plugin** (`local.wtsearch`), structured like `~/herdr-md-viewer`.
- iTerm keeps Cmd keys for itself. Cmd+Shift+J is free in iTerm (Cmd+Shift+F is iTerm's "Find Globally", so it isn't used).
- No prefix key: the binding is a direct chord.

## Key path
1. **iTerm** (Settings → Keys → Key Bindings): Cmd+Shift+J → "Send Hex Codes" `0x1b 0x06`, the bytes for Ctrl+Alt+F. This is a manual step, documented in the README.
2. **herdr** `~/.config/herdr/config.toml` (backed up before editing):
   ```toml
   [[keys.command]]
   key = "ctrl+alt+f"
   type = "plugin_action"
   command = "local.wtsearch.open"
   description = "search worktrees"
   ```
3. The action `open` runs `$HERDR_BIN_PATH plugin pane open --plugin local.wtsearch --entrypoint picker`. The manifest declares `picker` with `placement = "popup"`, `width = "80%"` and `height = "80%"`.

Ctrl+Alt+F also works directly as a fallback.

## Repo discovery (`wtsearch discover`)
The result is the union of the following, deduped by the repo's real git common dir:
- **Disk scan:** `find ~ -maxdepth 3`, pruning hidden dirs, `Library`, `node_modules` and `.Trash`. It keeps paths where `.git` is a *directory*, i.e. main repos. Linked worktrees, which have a `.git` file, are reached through their repo.
- **Open workspaces:** for each `herdr workspace list` entry, take the cwd of its root pane (`herdr pane list`) and run `git rev-parse --git-common-dir`. Repos outside `~` are included this way.

The repo list is cached in `$HERDR_PLUGIN_STATE_DIR/repos.json`.

## Listing (`wtsearch list`)
- For each cached repo, run `herdr worktree list --cwd <repo>`, in parallel.
- Emit one tab-separated line per worktree: `marker  repo  branch  path  open_workspace_id`.
  - `marker` is `●` when `open_workspace_id` is set and blank otherwise.
  - A detached worktree shows `(detached)` as the branch.
  - Prunable worktrees are skipped.
- A repo whose listing fails is skipped, with a warning written to stderr.

## Picker (`picker.sh`)
- `wtsearch list | fzf --delimiter '\t' --with-nth 1..4 --header 'enter: open  alt-r: rescan  esc: close'`
- Before showing results, start a background `wtsearch discover` that refreshes the cache for next time.
- On first run (no cache), run discover synchronously, which takes about 1s.
- **alt-r** reruns discover and then reloads the list.
- **Enter:**
  - If an `open_workspace_id` exists, run `herdr workspace focus <id>`.
  - Otherwise run `herdr worktree open --path <path> --focus`.
  - If either command fails, show the error in the popup and wait for a keypress.
- **Esc** exits, which closes the popup.

## Files
```
~/herdr-worktree-search/
  README.md
  plugin/herdr-plugin.toml   # id local.wtsearch; action "open"; pane "picker" (popup)
  plugin/open.sh             # opens the popup pane
  plugin/picker.sh           # fzf UI + enter handling
  plugin/wtsearch.py         # discover / list (Python 3 stdlib)
  tests/test_wtsearch.py     # unittest
```

## Dependencies
- `fzf` (`brew install fzf`). **Decision to confirm:** the alternative is a stdlib Python picker with no dependency, at the cost of more code and simpler matching.
- Python 3 (already present).

## Testing
- **Unit tests** (`python3 -m unittest`) for the pure functions, with `herdr`/`git` calls stubbed:
  - scan pruning
  - dedupe by common dir
  - worktree JSON → lines (open marker, detached, prunable skipped)
  - one repo failing doesn't break the list
- **Live checks** in herdr:
  - Ctrl+Alt+F opens the popup and the list contains `myapp`, `linear-cli` and `herdr-md-viewer` worktrees.
  - Filtering "123 money" narrows to one row.
  - Enter on an open worktree focuses its workspace.
  - Enter on an unopened worktree opens a new linked workspace (close it afterwards).
  - Esc closes the popup.
- **Cmd+Shift+J** is confirmed by Gurveer after the iTerm mapping.

## Out of scope
Creating or removing worktrees, searching file contents, and remote machines.
