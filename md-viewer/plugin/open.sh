#!/usr/bin/env bash
# Resolve a path from clicked URL or selected text and hand it to hmd.
set -uo pipefail
raw="${HERDR_PLUGIN_CLICKED_URL:-}"
if [ -z "$raw" ]; then
  raw=$(printf '%s' "${HERDR_PLUGIN_CONTEXT_JSON:-{\}}" | python3 -c '
import sys,json
d=json.load(sys.stdin)
def find(o):
    if isinstance(o,dict):
        for k,v in o.items():
            if "select" in k and isinstance(v,str) and v.strip(): return v
            r=find(v)
            if r: return r
    elif isinstance(o,list):
        for v in o:
            r=find(v)
            if r: return r
print(find(d) or "")')
fi
path=$(python3 -c 'import sys,urllib.parse as u;s=sys.argv[1].strip().strip("`\"\x27");s=u.unquote(u.urlparse(s).path) if s.startswith("file://") else s;print(s.split(":")[0] if not s.startswith("file") else s)' "$raw")
case "$path" in "~"*) path="$HOME${path#\~}";; esac
[ -f "$path" ] || { echo "hmd plugin: not a file: '$raw'" >&2; exit 1; }
exec "${HMD_BIN:-$HOME/.local/bin/hmd}" "$path"
