#!/usr/bin/env bash
# Plugin action: open the worktree-search popup.
exec "${HERDR_BIN_PATH:-herdr}" plugin pane open --plugin local.wtsearch --entrypoint picker
