# wtsearch: worktree search for herdr

**Cmd+Shift+J** (in iTerm) opens a herdr popup listing every git worktree of every repo.
- Type to fuzzy-filter by repo, branch or path.
- **Enter** jumps to the worktree's workspace if one is open (marked `●`). Otherwise it opens the worktree as a new linked workspace and focuses it.
- **Alt-R** rescans for repos. **Esc** closes.

## How it finds repos
- **Disk scan:** dirs up to 3 levels below `~` whose `.git` is a directory. Hidden dirs, `Library`, `node_modules` and `.Trash` are skipped.
- **Open workspaces:** repos behind any open herdr pane, even outside `~`.
- **Cache:** the disk-scan results are stored in the plugin state dir. The scan reruns on first use, when the cache is older than 24h, or on Alt-R (about 1–2s, with a "scanning repos…" message). Repos behind open herdr panes are merged in on every open, so they always appear.

## Install
Requires `fzf` (`brew install fzf`) and `python3`.

```bash
herdr plugin link worktree-search/plugin   # from a clone of this repo
cp ~/.config/herdr/config.toml ~/.config/herdr/config.toml.bak-wtsearch
cat >> ~/.config/herdr/config.toml <<'EOF'

[[keys.command]]
key = "ctrl+alt+f"
type = "plugin_action"
command = "local.wtsearch.open"
description = "search worktrees"
EOF
herdr server reload-config
```

Ctrl+Alt+F now opens the popup from any herdr pane, with no prefix needed.

### Cmd+Shift+J (iTerm)
iTerm keeps Cmd keys for itself, so map the shortcut to Ctrl+Alt+F:

1. Open iTerm → Settings → Keys → Key Bindings → **+**.
2. Set Keyboard Shortcut to **Cmd+Shift+J**.
3. Set Action to **Send Hex Codes**, with the value `0x1b 0x06`.

Cmd+Shift+F was avoided because it's iTerm's "Find Globally".

## Files
- `plugin/herdr-plugin.toml`: action `open` and popup pane `picker` (80% × 80%).
- `plugin/open.sh`: opens the popup.
- `plugin/picker.sh`: runs fzf and focuses or opens the chosen worktree.
- `plugin/list.sh`: formats the worktree list for fzf.
- `plugin/wtsearch.py`: repo discovery and worktree listing. `python3 wtsearch.py discover|list`.

## Tests
`python3 -m unittest discover -s tests`
