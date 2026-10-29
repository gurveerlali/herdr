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
   rewriting a plan file show up within ~0.5s. Ctrl-C closes the viewer; the pane exits with it.
4. **Click a path in agent output**: herdr only routes clicks on *URLs*, and agents print bare paths.
   Reasonable options: (a) if the agent/terminal emits `file:///...md` links, a plugin `link_handler`
   with pattern `^file://.*\.md$` calling `hmd` would work (untested; needs the plugin, not yet built);
   (b) otherwise a keybinding/plugin action that opens the selected text
   (`HERDR_PLUGIN_CONTEXT_JSON` includes selected text) as a path. Both need a plugin; not built yet.

## Tested (this workspace, herdr 0.9.3)
- `hmd <real plan .md>` split right: opens, content shown (with cat fallback, since glow is not installed).
- Live reload: appended a line to a file, pane updated within 1.5s.
- `hmd --tab`: new tab in the caller's workspace (after the `--workspace` fix). Test panes/tabs closed.

## Install
`bin/` onto PATH (symlink `bin/hmd` and `bin/hmd-view` into ~/.local/bin; `hmd` resolves symlinks) and `brew install glow`.
