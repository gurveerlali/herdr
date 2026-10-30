#!/usr/bin/env bash
# Popup UI: fuzzy-pick a worktree with fzf, then focus or open its herdr workspace.
set -u
cd "$(dirname "$0")"
HERDR="${HERDR_BIN_PATH:-herdr}"

if ! command -v fzf >/dev/null; then
  echo "wtsearch: fzf not found (brew install fzf)"; read -rn1 -p "press a key"; exit 1
fi

# Disk scan only when the cache is missing or >24h old (alt-r forces one).
# Repos behind live herdr panes are merged in by `list` on every open.
# No background job: it would be killed with the popup (or outlive it).
if python3 wtsearch.py stale; then
  echo "scanning repos…"
  python3 wtsearch.py discover 2>/dev/null
fi

HEADER='enter: open   alt-r: rescan   esc: close   ● = open'
sel=$(bash list.sh | fzf --delimiter=$'\t' --with-nth=1 --layout=reverse \
  --prompt='worktree> ' --header="$HEADER" \
  --bind "alt-r:change-header(scanning repos…)+reload(bash list.sh --rescan)" \
  --bind "load:change-header($HEADER)")
[ -n "$sel" ] || exit 0

# cut, not read: IFS tabs collapse, which would shift fields when ws is empty
path=$(cut -f2 <<<"$sel"); ws=$(cut -f3 <<<"$sel"); root=$(cut -f4 <<<"$sel")
if [ -n "$ws" ]; then
  out=$("$HERDR" workspace focus "$ws" 2>&1); rc=$?
else
  out=$("$HERDR" worktree open --cwd "${root:-$path}" --path "$path" --focus 2>&1); rc=$?
fi
if [ $rc -ne 0 ] || python3 wtsearch.py is-error <<<"$out"; then
  printf 'wtsearch: failed to open %s\n%s\n' "$path" "$out"
  read -rn1 -p "press a key"
  exit 1
fi
