# 6. Vyom owns the vim keys; ganit keeps only its own, in Vayu's shared letters

**Status:** Accepted  
**Date:** 2026-11-08

## Context

[ADR 5](0005-vim-modes-and-a-space-leader.md) gave ganit vim modes and a Space leader, with the engine (modes, counts, sequences, which-key strip, help, confirm, footer) inside ganit. Vayu then decided every tool gets vim keys with the same Space letters (Vyom [ADR 8](https://github.com/Theyashsawarkar/vyom/blob/main/docs/adr/0008-vim-keys-in-the-panel.md)), and Vyom 0.7 took ganit's engine into the panel. Several of ganit's leader letters meant something else there: `Space f` was fullscreen (find, elsewhere), `Space u` picked units (toggles), `Space s` saved conversions (sort), `Space m` was memory (mark), `Space k` a kind (ask AI), and `H`/`L` changed the kind where every other tool switches tabs.

## Decision

ganit sets `modal = True` and keeps only data: its binds in `ganit/vim.py`, its `v_<verb>` actions, and the unit picker (Vyom shows it in the which-key slot; ganit's `key()` takes every key while it's open). The keys move to Vayu's letters:

- Tabs: `H`/`L` (vim's `gt`/`gT` kept), `Space t c` / `Space t v`.
- Kinds: `[` / `]`, and `Space g <letter>` jumps to one.
- `Space u f` fullscreen, `Space v` memory (s, p, c), `Space d` clears (`d t` tape, `d b` box, `d d` newest saved, `d a` every saved), `Space a a` saves a conversion, `Space e f` / `e t` pick a unit, `Space m p` pins a currency.
- Calculate opens in INSERT (a sum at once); Convert opens in NORMAL, a form that a stray key doesn't change. `start_mode` in the config sets both.
- An old key that moved says where it went, for one release.

## Consequences

- ganit loses about 250 lines (footer, which-key, help, confirm, mode code) and needs Vyom 0.7.
- Its keys are the same as every other Vyom tool's; `scripts/keybinds.py` still writes the annotations and README tables, now with the mode after the scope, and finds Vyom's `keys.py` (CI clones Vyom).
- Muscle memory for `Space f`, `Space u`, `Space s`, `Space m`, `Space k` and `H`/`L` changes; the moved-key hints cover the first.
