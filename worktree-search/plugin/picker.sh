#!/usr/bin/env bash
# Popup UI: fuzzy-pick a worktree with fzf, then focus or open its herdr workspace.
set -u
cd "$(dirname "$0")"
HERDR="${HERDR_BIN_PATH:-herdr}"
STATE="${HERDR_PLUGIN_STATE_DIR:-$HOME/.local/state/wtsearch}"

if ! command -v fzf >/dev/null; then
  echo "wtsearch: fzf not found (brew install fzf)"; read -rn1 -p "press a key"; exit 1
fi

# Refresh the repo cache in the background for next time (first run: list discovers inline).
if [ -f "$STATE/repos.json" ]; then
  python3 wtsearch.py discover >/dev/null 2>&1 &
fi

sel=$(bash list.sh | fzf --delimiter=$'\t' --with-nth=1 --layout=reverse \
  --prompt='worktree> ' --header='enter: open   alt-r: rescan   esc: close   ● = open' \
  --bind 'alt-r:reload(bash list.sh --rescan)')
[ -n "$sel" ] || exit 0

# cut, not read: IFS tabs collapse, which would shift fields when ws is empty
path=$(cut -f2 <<<"$sel"); ws=$(cut -f3 <<<"$sel"); root=$(cut -f4 <<<"$sel")
if [ -n "$ws" ]; then
  out=$("$HERDR" workspace focus "$ws" 2>&1); rc=$?
else
  out=$("$HERDR" worktree open --cwd "${root:-$path}" --path "$path" --focus 2>&1); rc=$?
fi
if [ $rc -ne 0 ] || grep -q '"error"' <<<"$out"; then
  printf 'wtsearch: failed to open %s\n%s\n' "$path" "$out"
  read -rn1 -p "press a key"
  exit 1
fi
