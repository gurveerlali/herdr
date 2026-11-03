# herdr add-ons

Plugins and config for [herdr](https://herdr.dev), the terminal workspace manager for coding agents.
Built and tested on macOS with iTerm2 and herdr 0.9.3.

| Folder | What it does |
|---|---|
| [`md-viewer/`](md-viewer/README.md) | `hmd`: open `.md` files in a live-rendered herdr pane. Cmd+click a path in iTerm, click a link, or open a file from Finder. |
| [`worktree-search/`](worktree-search/README.md) | `wtsearch`: a popup to fuzzy-search every git worktree of every repo and jump to it. |
| [`config/`](config/config.toml) | My `~/.config/herdr/config.toml`: keybindings for both plugins and sidebar rules. |

## Install

```bash
git clone https://github.com/gurveerlali/herdr ~/herdr && cd ~/herdr

# md-viewer
brew install glow                          # renderer (optional; falls back to mdcat, bat, cat)
mkdir -p ~/.local/bin
ln -sf "$PWD"/md-viewer/bin/{hmd,hmd-view,hmd-open} ~/.local/bin/
herdr plugin link md-viewer/plugin
md-viewer/bin/hmd-iterm-rule               # Cmd+click on .md paths -> hmd; quit iTerm (Cmd+Q) when it waits
md-viewer/bin/hmd-install-opener           # optional: make hmd the default .md app (--uninstall to undo)

# worktree-search
herdr plugin link worktree-search/plugin

# keybindings: merge config/config.toml into ~/.config/herdr/config.toml
```

The plugins are also installable straight from GitHub, e.g.
`herdr plugin install gurveerlali/herdr/worktree-search/plugin`. The md-viewer plugin also needs the
`bin/` scripts above.

## License

[MIT](LICENSE)
