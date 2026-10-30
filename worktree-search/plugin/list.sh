#!/usr/bin/env bash
# Print worktrees for fzf: "<aligned display>\t<path>\t<workspace id>\t<repo root>".
# --rescan refreshes the repo cache first.
cd "$(dirname "$0")"
[ "${1:-}" = "--rescan" ] && python3 wtsearch.py discover >/dev/null 2>&1
python3 wtsearch.py list 2>/dev/null | awk -F'\t' -v home="$HOME" '
  { m[NR]=$1; r[NR]=$2; b[NR]=$3; p[NR]=$4; w[NR]=$5; s[NR]=$6
    if (length($2) > rw) rw = length($2)
    if (length($3) > bw) bw = length($3) }
  END {
    for (i = 1; i <= NR; i++) {
      d = p[i]
      if (index(d, home) == 1) d = "~" substr(d, length(home) + 1)
      printf "%s %-*s  %-*s  %s\t%s\t%s\t%s\n", m[i], rw, r[i], bw, b[i], d, p[i], w[i], s[i]
    }
  }'
