# hmd: markdown in herdr

## What herdr 0.9.3 supports
- No built-in markdown/file viewer and no file-opener setting.
- `[[keys.command]]` in config.toml: custom keybindings (`shell`, `pane`, `popup`, `plugin_action`). Not path-aware.
- **Plugins** (`herdr plugin link|install`, manifest `herdr-plugin.toml`): actions, event hooks, panes
  (placement overlay/popup/split/tab) and `[[link_handlers]]`: a regex on a *clicked URL* (Ctrl+click,
  needs `ui.mouse_capture = true`) invokes a plugin action with `HERDR_PLUGIN_CLICKED_URL`.
  Plugin docs: https://herdr.dev/docs/plugins/
- CLI primitives used here: `pane split --current`, `tab create --workspace`, `pane rename`, `pane run`.
  Gotcha: `tab create` without `--workspace` uses the *focused* workspace, not the caller's.

## Design
1. **Renderer: `glow`** (brew, ~single Go binary, good width-aware ANSI output). Alternatives: `mdcat`, `bat -l md`
   (no rendering). `hmd-view` uses glow > mdcat > bat > cat, so it works today (unrendered) with nothing installed.
2. **`hmd <file>`**: splits a pane to the right of the caller (`--down`, `--tab` also available), names it
   `md:<file>`, and runs `hmd-view`. Doesn't steal focus. Outside herdr it renders inline.
3. **Live reload**: `hmd-view` polls mtime every 0.5s and re-renders (glow has no watch mode). Agents
   rewriting a plan file show up within ~0.5s. Press `q` (or Ctrl-C) in the viewer to close it; the pane exits with it. (macOS bash 3.2: integer `read -t` only, so mtime is polled every ~1s.)
4. **Click a path**: herdr only routes Ctrl+click on *URLs*. `plugin/` (id `local.hmd`, linked with
   `herdr plugin link plugin`) registers a link handler for `^file://.*\.md$` -> `open.sh` -> `hmd`.
   It also has an `open-selection` action that reads a selected-text field from `HERDR_PLUGIN_CONTEXT_JSON`
   (key name not yet verified; no selection was available in testing, it fails cleanly). Binding it to a key
   needs a `[[keys.command]]` with `type = "plugin_action"`, `command = "local.hmd.open-selection"` in config.toml (not done).
   Agents must print `file:///...md` URLs for the click path to fire.

## Tested (this workspace, herdr 0.9.3)
- `hmd <real plan .md>` split right: opens, content shown (with cat fallback, since glow is not installed).
- Live reload: appended a line to a file, pane updated within 1.5s.
- `hmd --tab`: new tab in the caller's workspace (after the `--workspace` fix). Test panes/tabs closed.

- glow renders (installed via brew). Plugin linked; `open.sh` with a `file:///tmp/clicktest.md` URL opened a rendered pane.
  A real Ctrl+click and the selection action were not exercised.

## Install (done on this machine)
`brew install glow`; symlink `bin/hmd`, `bin/hmd-view` into ~/.local/bin; `herdr plugin link plugin`.

## Keybinding (added)
`prefix+m` -> `local.hmd.open-selection` appended to ~/.config/herdr/config.toml (backup: config.toml.bak-hmd).
Select a .md path with the mouse, press prefix+m. Not yet verified with a real selection.

## Cmd+click (option A: iTerm Semantic History)
herdr can't see Cmd+click (only Ctrl+click on URLs, and only with mouse_capture on). With `ui.mouse_capture = false`
iTerm handles Cmd+click itself; its Semantic History runs `/Users/gurveerlali/.local/bin/hmd-open \1 \2 \5` (iTerm placeholders: \1 file, \2 line, \5 cwd; `\(path)`/`\(matched)` do NOT work), which finds
the focused herdr pane, resolves relative paths against that pane's cwd, and calls `hmd`. Non-.md files go to `open`.
Tested via `HMD_TARGET_PANE` override: absolute and relative (`README.md:3`) paths both opened. Real Cmd+click confirmed working by Gurveer.
Cost of capture off: no herdr mouse UI (sidebar/tab clicks, drag-select, right-click menu).

REVERTED: `mouse_capture = false` killed all herdr mouse use, which is not acceptable. Capture is back on (default).
Candidate: iTerm bypasses mouse reporting while Option is held, so Cmd+Option+click may reach Semantic History with capture on (untested).

hmd-open on a directory opens that directory's newest .md (non-recursive); notifies if none.
