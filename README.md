# ganit

**ganit** (गणित, "mathematics") — The calculator and converter. A tool for [Vyom](https://github.com/Theyashsawarkar/vyom), the keyboard-driven panels of [Vayu](https://github.com/Theyashsawarkar/vayu); in Vayu it replaces wofi-calc.sh (a prompt, then a second wofi for the result).

> Calculator and converter: answers as you type (math, units, currency, percentages) through qalc, with a history.

## Features

- **Answers as you type**, through qalc (libqalculate): arithmetic, functions, percentages (`18% of 3897`, `3897 + 18%`), units (`5 ft 11 in to cm`), **currency** (`100 USD to INR`, rates refreshed once a day), dates, bases.
- Integer answers also show with separators, in hex and in binary.
- `Enter` copies the answer; `Ctrl+Enter` copies `expression = answer`.
- A history of the last 50 calculations; Enter on one puts it back in the box to build on.

## Keys

| Key | Action |
|---|---|
| `Enter` | Copy the answer (on a history line: use it again) |
| `Ctrl+Enter` | Copy the expression with its answer |
| `Ctrl+Backspace` | Clear the history |
| `Esc` | close |

Every Vyom panel also has: `Up`/`Down` (or `Ctrl+K`/`Ctrl+J`) to move, `Page Up`/`Page Down`, `Tab` to switch to the next tool.

## Requirements

- [Vyom](https://github.com/Theyashsawarkar/vyom) 0.2 or newer (Python 3.11+, GTK 4, gtk4-layer-shell, a layer-shell compositor)
- `qalc`

## Install

```sh
git clone https://github.com/Theyashsawarkar/ganit ~/.local/share/vyom/plugins/ganit
vyom reload        # or log out and in
vyom ganit         # open it (again: close it)
```

Bind it to a key, e.g. in sway:

```
bindsym $mod+<key> exec vyom ganit
```

Update: `git -C ~/.local/share/vyom/plugins/ganit pull && vyom reload`. `vyom list` shows every installed tool and why one would be skipped.

## License

MIT.
