# Changelog

Newest first. Releases are tags (`vX.Y.Z`).

## v0.2.0 -- 2026-10-24

A redesign of the calculator, and a converter.

- **Wrong answers fixed.** `18% of 3897` (the README's own example) gave
  `rem(18, 1 B)`: qalc reads "of" as a unit, so "X% of Y" is now rewritten
  to "X% * Y" (701.46). Half-typed input (`2 +`) no longer shows qalc's
  guess as the answer: the last answer stays, dimmed, "waiting for more…".
  Money was `₹9492.5546`: digits are grouped and money rounded to 2
  decimals (₹9,494.51). Exchange rates said nothing about their age and the
  daily refresh saved its timestamp even when the download failed (they
  were 3 days old): now their age is shown, a failed update is retried
  after an hour instead of a day, the footer says how it went, `Ctrl+R`
  updates them now, and rates older than two days get a warning.
- **Calculate**: one big answer with how qalc read the input ("read as
  (18 × percent) × 3897 → INR"), the other forms in a side pane (plain,
  exact, hex, binary, scientific; `Alt+1..4` copies one) instead of three
  rows under every whole number, history answers on the right, and recent
  calculations plus examples when it opens. `Shift+Enter` copies and keeps
  the panel open.
- **Convert** (a tab: `vyom ganit convert`, or `Ctrl+L` from Calculate): an
  amount once (`100 usd`, `€50`, `2500` in your home currency) in every
  pinned currency with its rate, a rate board when the box is empty, `Ctrl+P`
  to pin, `Ctrl+B` to make the selected currency the base, and units
  (`5 ft`, `30 c`, `10 gb`, `100 kmh`). Rates are precise to more than
  qalc's 4 displayed decimals.
- Options: `home`, `currencies`, `grouping` (`intl`, `indian`, `none`).
- Tabs switch like every Vyom tool's (`Ctrl+H` / `Ctrl+L`, `Ctrl+1` / `Ctrl+2`). Needs Vyom 0.3.0.

## v0.1.4 -- 2026-10-21

- A website (GitHub Pages, https://theyashsawarkar.github.io/ganit/): the README as a home page, the
  changelog, and architecture decision records (`docs/adr/`), built from these files by
  `scripts/build-site.py`; CI checks the site is up to date.

## v0.1.3 -- 2026-10-21

- Documentation for open source: a logo and banner, a full README (features,
  install, usage, configuration, troubleshooting, the whole Vyom family),
  CONTRIBUTING, SECURITY and CODE_OF_CONDUCT, issue and pull request
  templates, and CI (compiles, checks plugin.toml and that every key is
  documented).

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
