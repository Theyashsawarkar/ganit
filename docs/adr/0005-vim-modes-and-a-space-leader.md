# 5. Vim modes and a Space leader

**Status:** Accepted  
**Date:** 2026-11-08

## Context

ganit's keys were Ctrl and Alt chords (Ctrl+M, Alt+1..4, Ctrl+S…) on top of Vyom's own (Tab, Ctrl+1..9). They were hard to remember, and they clashed with Vyom's tab keys. The user works in vim and asked for the same system here: modes, a Space leader, layers under it, and every key in normal mode only.

## Decision

- **Two modes.** INSERT types: only `Enter` (run the sum, or save the conversion; it stays in INSERT) and `Esc` (to NORMAL) do anything else. NORMAL runs every other key and takes no typing. It opens in INSERT (`start_mode` changes that), and clicking a box enters INSERT.
- **Vim's keys where vim has one:** `j`/`k`, `gg`/`G`, counts (`5k`), `yy`/`Y`, `p`/`P`, `x`, `D`, `cc`/`S`, `dd`/`u`, `gt`/`gT`, `q`. The converter adds `h`/`l` (unit), `H`/`L` (kind) and `s` (swap).
- **Space is the leader**, with layers: `t` tabs, `y` copy, `m` memory, `c` clear, `k` kind, `u` unit, `s` saved, plus `r` rates, `f` fullscreen, `q` close, `?` help. After a prefix, a strip shows what comes next (which-key), and `?` lists every key of the tab.
- **The keymaps are data** (`ganit/vim.py`). `scripts/keybinds.py` writes the `# keybind:` lines and the README's key tables from them, and CI checks they're up to date, so the keys, the strip, the help and the docs can't drift apart.
- **Vyom's tab keys (Tab, Ctrl+1..9, Ctrl+H/L) don't apply in ganit**: `gt`/`gT` and `Space t` replace them.
- **Clearing everything asks first** (`Space c t`, `Space s c`: `y` confirms). One deletion (`dd`) is undone with `u`.
- **Units are picked in ganit's own strip** (`Space u f` / `t`: type to filter, Enter picks). GTK's dropdown list can't take keys while the box keeps the focus.

## Consequences

- Every key is one or two letters, and the strip teaches them as you go.
- ganit's keys differ from the other Vyom tools' (their Tab and Ctrl+1..9 stay). Other tools can follow with the same table-driven approach.
- A key is changed in `vim.py`, then `scripts/keybinds.py` is run.
