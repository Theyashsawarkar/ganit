# Changelog

Newest first. Releases are tags (`vX.Y.Z`).

## v0.5.0 -- 2026-11-09

- **Vyom's vim keys** ([ADR 6](docs/adr/0006-vyom-owns-the-vim-keys.md)). The modes,
  counts, which-key strip, `?` help and the confirm are Vyom's now (Vyom 0.7), so ganit's
  keys work like every other Vyom tool's, and `Space Space` opens a palette of every action.
- **Keys in Vayu's shared letters:**
  - Tabs are `H` / `L` (`gt` / `gT` and `Tab` still work); the converter's kinds moved to
    `[` / `]`, and `Space g <letter>` jumps to one (was `Space k`).
  - `Space u f` fullscreen (was `Space f`), `Space v s` / `v p` / `v c` memory (was
    `Space m`), `Space d t` / `d b` clear the tape / box (was `Space c`), `Space a a` saves a
    conversion, `Space d d` / `d a` delete the newest / every saved one (was `Space s`),
    `Space e f` / `e t` pick a unit (was `Space u`), `Space m p` pins a currency (was `Space p`).
  - A key that moved says where it went, for this release.
- **Convert opens in normal mode**, so a stray key changes nothing; Calculate still opens
  ready to type. `start_mode` sets both.
- The status line is Vyom's footer's (green when it worked, yellow when it didn't).

## v0.4.0 -- 2026-11-08

- **Vim modes.** It opens in INSERT, where keys type: `Enter` runs the sum (or saves the
  conversion) and stays there, and `Esc` goes to NORMAL. Every other key is NORMAL mode's:
  - `j`/`k` (with a count: `5k`), `gg`/`G`, `yy`/`Y`, `p`/`P`, `x`, `D`, `cc`/`S`, `dd`/`u`
    (delete a tape line or a saved conversion, and undo it), `m` (memory), `gt`/`gT` (tabs),
    `q` (close), `?` (every key).
  - The converter adds `h`/`l` (unit), `H`/`L` (kind) and `s` (swap).
- **Space is the leader**, with layers: `Space t` tabs, `Space y` copy (answer, sum, plain,
  exact, hex, binary; From, To, the line, the rate), `Space m` memory, `Space c` clear,
  `Space k` kind (`Space k t` temperature…), `Space u` unit, `Space s` saved, `Space p` pin,
  `Space r` rates, `Space f` fullscreen. After a prefix, a strip shows what comes next.
- **`Space u f` / `Space u t` pick a unit** in a small list: type to filter, Enter picks.
- **Clearing the tape or the saved list asks first** (`y` confirms).
- The old chords (Ctrl+M, Ctrl+L, Ctrl+S, Ctrl+P, Ctrl+R, Alt+1..9, Alt+Up/Down) are gone,
  and Vyom's Tab and Ctrl+1..9 don't switch ganit's tabs (`gt`/`gT`, `Space t`).
- `start_mode = "normal"` in `[plugin.ganit]` opens it in NORMAL instead.
- The keymaps are one table (`ganit/vim.py`); `scripts/keybinds.py` writes the keybinding
  lines and the README's key tables from it, and CI checks them. ADR 0005.

## v0.3.1 -- 2026-11-08

- No numbers on the tape's lines or on the converter's kind buttons (each kind's tooltip
  has its `Alt` key).

## v0.3.0 -- 2026-11-06

A calculator and converter that behave like the real thing.

- **`Enter` no longer closes it.** In Calculate it runs the sum and keeps the
  answer on a paper tape; the box clears for the next one and `Esc` closes.
  A sum that starts with an operator (`+ 100`, `× 2`) carries on from the
  last answer; `ans` and `mem` (`Ctrl+M`) can go anywhere in a sum.
- **A tape kept between sessions**: the last 300 sums, by day. `Up`/`Down`
  walk it, `Ctrl+C` copies a line, `Enter` or a double-click recalls it,
  `Ctrl+L` twice clears it.
- **A new look**: one big peach answer with how it was read, the answer's
  other forms (`Alt+1..4`), a clickable keypad and the memory beside it.
- **Convert is two-sided**: From and To amounts (type in either; `Up`/`Down`
  moves between them, `Alt+Up`/`Alt+Down` changes the unit, `Ctrl+S`
  swaps), nine kinds each with its own colour (`Alt+1..9`), the amount in
  every other unit or pinned currency below, and `Enter` saves the
  conversion to a list (the next amount you type replaces the old one).
  Converted amounts are grouped like the rest (7,044.19). The rates' age
  turns yellow past two days.
- `Tab` switches between Calculate and Convert, and `F11` toggles fullscreen
  (Vyom 0.5.0). Gone: `Shift+Enter`, `Ctrl+B` and `Ctrl+Backspace`.
- Every corner is rounded: the website's callouts.
- A logo and a shloka at the top of the README and the website: every Vayu tool has them now.

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
