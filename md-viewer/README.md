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
3. **Viewer (`bin/hmd-view`, Python 3, stdlib only)**: renders with glow (`-s dark`, override with `HMD_STYLE`),
   draws a header with a red **[x]** close button, and handles its own scrolling because it turns on mouse
   reporting: wheel, j/k, arrows, space/b, PgUp/PgDn, g/G. `q`, Ctrl-C or clicking [x] closes the pane.
   It re-renders on file change (0.4s poll) or resize and keeps the scroll position.
   Trade-off: no drag-select inside the viewer while it owns the mouse.
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

## Viewer tests (via `herdr pane send-text`)
j x5 + SGR wheel-down scrolled 8 lines; appending to the file re-rendered in place; click on a body row
did nothing; click on the [x] column in row 1 closed the pane; `q` closed a pane opened via the plugin path.

## Cmd+click on relative .md paths (fixed 2026-11-03)
Symptom: Cmd+click on `docs/plan.md` opened Chrome. iTerm Semantic History only runs its command if the path
exists relative to iTerm's cwd (the herdr client's, usually ~). Repo-relative paths fail that check, so iTerm
treats them as URLs (`.md` is a TLD) and opens the browser. Absolute paths worked.
Fix: `bin/hmd-iterm-rule` adds a Smart Selection rule (precision very_high, action Run Command
`hmd-open \0`) to the Default profile; Cmd+click runs a matching rule's first action with no existence check.
It waits for iTerm to quit before writing prefs (backup: ~/Library/Preferences/com.googlecode.iterm2.plist.bak-hmd-*).
`hmd-open` then picks the pane in the focused tab that shows the clicked text and where the path exists, since
the clicked pane is often not the focused one. Confirmed with a real Cmd+click.
Still open: OSC 8 `file://` links (pi's read/write headers) open in the macOS default .md app (VS Code), and
`prefix+m` gets no selected text.

## Default .md app: hmd.app (2026-11-03)
OSC 8 `file://` links (pi's read/write headers) and Finder double-clicks go to the macOS default .md app, not
Semantic History. `bin/hmd-install-opener` builds `~/Applications/hmd.app` (AppleScript droplet, bundle id
`local.hmd.opener`) and makes it the default for `net.daringfireball.markdown`. It runs `bin/hmd-default-open`:
herdr client attached to a tty -> `hmd-open` + bring iTerm forward; otherwise, or on failure, VS Code
(`HMD_FALLBACK_APP`). The previous default is saved in the plugin config dir; `--uninstall` restores it.
Gotcha: `LSSetDefaultRoleHandlerForContentType` returns 0 but does nothing on current macOS; use
`NSWorkspace.setDefaultApplication`. Switching back to VS Code returned userCanceledErr once (likely a
confirmation dialog); if `--uninstall` fails, use Finder > Get Info > Open with > Change All.
Tested: `open file.md` -> hmd.app -> viewer split beside the focused pane.
