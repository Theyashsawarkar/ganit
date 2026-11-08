"""ganit's vim keys: INSERT types, NORMAL runs every key, Space is the leader.

The keymaps are data, so the keys, the which-key strip shown after a prefix
(Space, g, y, d, c) and the help (?) all come from one table. Sequences are
strings of tokens: one character each, or <CR> <Esc> <BS>; " " is Space.
"""

LEADER = " "

# Gdk key names that stand for one character (shift is part of the name: "G").
NAMES = {
    "space": " ", "Return": "<CR>", "KP_Enter": "<CR>", "Escape": "<Esc>", "BackSpace": "<BS>",
    "slash": "/", "question": "?", "equal": "=", "dollar": "$", "asciicircum": "^",
    "bracketleft": "[", "bracketright": "]", "asterisk": "*", "plus": "+", "minus": "-",
    "period": ".", "comma": ",", "semicolon": ";", "colon": ":", "underscore": "_",
}


def token(name, mods):
    """One key as a token, or None (Ctrl/Alt chords aren't vim keys here)."""
    if mods - {"shift"}:
        return None
    if name in NAMES:
        return NAMES[name]
    if len(name) == 1:
        return name
    if name.startswith("KP_") and len(name) == 4 and name[3].isdigit():
        return name[3]
    return None


def spell(seq):
    """A sequence as the keys you press: " tc" -> "Space t c"."""
    out, i = [], 0
    while i < len(seq):
        if seq[i] == "<":
            j = seq.index(">", i)
            out.append({"<CR>": "Enter", "<Esc>": "Esc", "<BS>": "Backspace"}[seq[i:j + 1]])
            i = j + 1
            continue
        out.append("Space" if seq[i] == " " else seq[i])
        i += 1
    return " ".join(out)


def tokens(seq):
    out, i = [], 0
    while i < len(seq):
        j = seq.index(">", i) + 1 if seq[i] == "<" else i + 1
        out.append(seq[i:j])
        i = j
    return out


# (sequence, action, what it does). An action is a method v_<action> on the
# plugin, called with the count (5j) and the sequence's argument after ":".
COMMON = [
    ("i", "insert", "Enter insert mode to type (Esc goes back to normal)"),
    ("a", "insert", "Enter insert mode at the end of the box"),
    ("gt", "tab:+1", "Switch to the next tab (Calculate, Convert)"),
    ("gT", "tab:-1", "Switch to the previous tab"),
    ("q", "close", "Close the calculator"),
    ("?", "help", "Show every key of this tab"),
    (" tc", "tab:calc", "Switch to Calculate"),
    (" tv", "tab:convert", "Switch to Convert"),
    (" r", "rates", "Update the exchange rates now"),
    (" f", "fullscreen", "Toggle fullscreen"),
    (" q", "close", "Close the calculator"),
    (" ?", "help", "Show every key of this tab"),
]

CALC = [
    ("j", "tape:+1", "Move down the tape (a count moves further: 5j; past the end, back to the box)"),
    ("k", "tape:-1", "Move up the tape (a count moves further: 5k)"),
    ("gg", "tape:first", "Jump to the first tape line"),
    ("G", "tape:last", "Jump to the last tape line"),
    ("<CR>", "run", "Run the sum and keep it on the tape (a picked line: put its sum in the box)"),
    ("=", "run", "Run the sum and keep it on the tape"),
    ("yy", "copy", "Copy the answer (the picked line's, else the live one)"),
    ("Y", "copy:expr", "Copy the sum with its answer (12 + 5 = 17)"),
    ("p", "put", "Paste the answer at the end of the box"),
    ("P", "put:expr", "Paste the picked line's sum into the box, replacing what's there"),
    ("x", "backspace", "Delete the last character in the box"),
    ("D", "clearbox", "Clear the box"),
    ("cc", "change", "Clear the box and enter insert mode"),
    ("S", "change", "Clear the box and enter insert mode"),
    ("dd", "deleteline", "Delete the picked tape line, else the last (u brings it back)"),
    ("u", "undo", "Undo the last deleted tape line"),
    ("m", "store", "Save the answer to memory (mem in a sum uses it)"),
    (" yy", "copy", "Copy the answer"),
    (" ye", "copy:expr", "Copy the sum with its answer"),
    (" yp", "form:plain", "Copy the answer as a plain number"),
    (" yx", "form:exact", "Copy the exact answer (fractions, roots)"),
    (" yh", "form:hex", "Copy the answer in hex"),
    (" yb", "form:binary", "Copy the answer in binary"),
    (" ms", "store", "Save the answer to memory"),
    (" mp", "putmem", "Paste mem into the box"),
    (" mc", "clearmem", "Clear the memory"),
    (" ct", "cleartape", "Clear the whole tape (y confirms)"),
    (" cb", "clearbox", "Clear the box"),
]

KIND_KEYS = {"currency": "c", "length": "l", "mass": "m", "temperature": "t", "volume": "v",
             "data": "d", "speed": "s", "area": "a", "time": "i"}

CONVERT = [
    ("j", "side:to", "Move to the To amount"),
    ("k", "side:from", "Move to the From amount"),
    ("h", "unit:-1", "Switch this side's unit to the previous one (a count: 3h)"),
    ("l", "unit:+1", "Switch this side's unit to the next one (a count: 3l)"),
    ("H", "kind:-1", "Switch to the previous kind (currency, length, mass…)"),
    ("L", "kind:+1", "Switch to the next kind"),
    ("s", "swap", "Swap From and To"),
    ("<CR>", "save", "Save the conversion to the list"),
    ("=", "save", "Save the conversion to the list"),
    ("yy", "copy:to", "Copy the converted amount"),
    ("Y", "copy:line", "Copy the whole conversion (100 USD = 9,392.25 INR)"),
    ("x", "backspace", "Delete the amount's last character"),
    ("D", "clearbox", "Clear the amount"),
    ("cc", "change", "Clear the amount and enter insert mode"),
    ("S", "change", "Clear the amount and enter insert mode"),
    ("dd", "deletesaved", "Delete the newest saved conversion (u brings it back)"),
    ("u", "undo", "Undo the last deleted conversion"),
    (" uf", "pickunit:from", "Pick the From unit (type to filter, Enter picks)"),
    (" ut", "pickunit:to", "Pick the To unit (type to filter, Enter picks)"),
    (" yy", "copy:to", "Copy the converted amount"),
    (" yf", "copy:from", "Copy the From amount"),
    (" yl", "copy:line", "Copy the whole conversion"),
    (" yr", "copy:rate", "Copy the rate (1 USD = 93.92 INR)"),
    (" p", "pin", "Toggle the pin on the To currency (pinned ones show below)"),
    (" ss", "save", "Save the conversion to the list"),
    (" sd", "deletesaved", "Delete the newest saved conversion"),
    (" sc", "clearsaved", "Clear every saved conversion (y confirms)"),
] + [(f" k{key}", f"kind:{kind}", f"Switch to {kind}") for kind, key in KIND_KEYS.items()]

# What a prefix opens, for the which-key strip.
LAYERS = {
    " ": "leader", " t": "tabs", " y": "copy", " m": "memory", " c": "clear", " k": "kind",
    " u": "unit", " s": "saved", "g": "go", "y": "copy", "d": "delete", "c": "change",
}


class Keymap:
    def __init__(self, binds):
        self.binds = {}
        for seq, action, desc in binds:
            self.binds.setdefault(seq, (action, desc))

    def lookup(self, pending):
        """(the bind for exactly this, whether a longer one starts with it)."""
        exact = self.binds.get(pending)
        longer = any(s != pending and s.startswith(pending) for s in self.binds)
        return exact, longer

    def next_keys(self, pending):
        """[(token, what)] after `pending`: a bind's description, or a layer's name."""
        out, seen = [], set()
        for seq, (_, desc) in self.binds.items():
            if seq == pending or not seq.startswith(pending):
                continue
            rest = tokens(seq[len(pending):])
            tok = rest[0]
            if tok in seen:
                continue
            seen.add(tok)
            out.append((tok, desc if len(rest) == 1 else LAYERS.get(pending + tok, "more") + "…"))
        return out

    def plain_binds(self):
        """Every bind that doesn't start with the leader, in order."""
        return [(s, d) for s, (_, d) in self.binds.items() if not s.startswith(LEADER)]


MAPS = {"calc": Keymap(COMMON + CALC), "convert": Keymap(COMMON + CONVERT)}
