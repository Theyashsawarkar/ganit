# Changelog

Newest first. Releases are tags (`vX.Y.Z`).

## v0.1.2 -- 2026-10-19

- Opens at Vyom's shared panel size (Vyom 0.2.5) like every other tool:
  its own width/height are gone.

## v0.1.1 -- 2026-10-19

- Keys are spelled out (Ctrl+Enter, Shift+Enter, Backspace) instead of symbols
  (⌃↵, ⇧↵, ⌫) in the footer and on rows and buttons.

## v0.1.0 -- 2026-10-19

- First release, as its own repository: the calculator and converter. Replaces wofi-calc.sh (a prompt, then a second wofi for the result) in Vayu.
- **Answers as you type**, through qalc (libqalculate): arithmetic, functions, percentages (`18% of 3897`, `3897 + 18%`), units (`5 ft 11 in to cm`), **currency** (`100 USD to INR`, rates refreshed once a day), dates, bases.
- Integer answers also show with separators, in hex and in binary.
- `Enter` copies the answer; `Ctrl+Enter` copies `expression = answer`.
- A history of the last 50 calculations; Enter on one puts it back in the box to build on.
