"""ganit's vim keys, as data: INSERT types, NORMAL runs every key, Space is
the leader. The modes, counts, sequences, which-key strip, help (?) and
palette (Space Space) are Vyom's (vyom/keys.py, vyom/modal.py; Vyom ADR
0008); this file is only what ganit adds. Space groups follow Vayu's shared
letters: t tabs, u toggles, y copy, d delete, a add, e edit, g go to,
m mark, r refresh; v (memory) is ganit's own.

An action "verb:arg" runs Plugin.v_<verb>(count, arg) in ganit/__init__.py,
or Vyom's own (tab, insert, moved, nop...).
"""
from vyom.keys import Bind

B = Bind


def moved(seq, to, tab=None):
    """An old key that moved in v0.5 (for one release): says where to."""
    return B(seq, f"moved:{to}", "", hidden=True, when=tab)


INSERT = [
    B("<CR>", "run", "Run the sum and keep it on the tape; stays in insert mode", mode="insert", when="calc"),
    B("<CR>", "save", "Save the conversion to the list; stays in insert mode", mode="insert", when="convert"),
    # NORMAL mode's: j / k, Space u f
    B("<Up>", "nop", "", mode="insert", hidden=True), B("<Down>", "nop", "", mode="insert", hidden=True),
    B("<PgUp>", "nop", "", mode="insert", hidden=True), B("<PgDn>", "nop", "", mode="insert", hidden=True),
]

COMMON = [
    B("i", "insert", "Enter insert mode to type (Esc goes back to normal)"),
    B("a", "insert", "Enter insert mode at the end of the box"),
    B("gt", "tab:+1", "", hidden=True), B("gT", "tab:-1", "", hidden=True),   # vim's, kept
    B(" tc", "tab:calc", "Switch to Calculate"),
    B(" tv", "tab:convert", "Switch to Convert"),
    B(" r", "rates", "Update the exchange rates now"),
    moved(" f", "Space u f"),
    # Arrows and Page keys aren't NORMAL mode's moves here (j / k are).
    B("<Up>", "nop", "", hidden=True), B("<Down>", "nop", "", hidden=True),
    B("<Left>", "nop", "", hidden=True), B("<Right>", "nop", "", hidden=True),
    B("<PgUp>", "nop", "", hidden=True), B("<PgDn>", "nop", "", hidden=True),
]

CALC = [
    B("j", "tape:+1", "Move down the tape (a count moves further: 5j; past the end, back to the box)"),
    B("k", "tape:-1", "Move up the tape (a count moves further: 5k)"),
    B("gg", "tape:first", "Jump to the first tape line"),
    B("G", "tape:last", "Jump to the last tape line"),
    B("<CR>", "run", "Run the sum and keep it on the tape (a picked line: put its sum in the box)"),
    B("=", "run", "Run the sum and keep it on the tape"),
    B("yy", "copy", "Copy the answer (the picked line's, else the live one)"),
    B("Y", "copy:expr", "Copy the sum with its answer (12 + 5 = 17)"),
    B("p", "put", "Paste the answer at the end of the box"),
    B("P", "put:expr", "Paste the picked line's sum into the box, replacing what's there"),
    B("x", "backspace", "Delete the last character in the box"),
    B("D", "clearbox", "Clear the box"),
    B("cc", "change", "Clear the box and enter insert mode"),
    B("S", "change", "Clear the box and enter insert mode"),
    B("dd", "deleteline", "Delete the picked tape line, else the last (u brings it back)"),
    B("u", "undo", "Undo the last deleted tape line"),
    B("m", "store", "Save the answer to memory (mem in a sum uses it)"),
    B(" yy", "copy", "Copy the answer"),
    B(" ye", "copy:expr", "Copy the sum with its answer"),
    B(" yp", "form:plain", "Copy the answer as a plain number"),
    B(" yx", "form:exact", "Copy the exact answer (fractions, roots)"),
    B(" yh", "form:hex", "Copy the answer in hex"),
    B(" yb", "form:binary", "Copy the answer in binary"),
    B(" vs", "store", "Save the answer to memory"),
    B(" vp", "putmem", "Paste mem into the box"),
    B(" vc", "clearmem", "Clear the memory"),
    B(" dt", "cleartape", "Clear the whole tape (y confirms)"),
    B(" db", "clearbox", "Clear the box"),
    moved(" ms", "Space v s"), moved(" mp", "Space v p"), moved(" mc", "Space v c"),
    moved(" ct", "Space d t"), moved(" cb", "Space d b"),
]

KIND_KEYS = {"currency": "c", "length": "l", "mass": "m", "temperature": "t", "volume": "v",
             "data": "d", "speed": "s", "area": "a", "time": "i"}

CONVERT = [
    B("j", "side:to", "Move to the To amount"),
    B("k", "side:from", "Move to the From amount"),
    B("h", "unit:-1", "Switch this side's unit to the previous one (a count: 3h)"),
    B("l", "unit:+1", "Switch this side's unit to the next one (a count: 3l)"),
    B("[", "kind:-1", "Switch to the previous kind (currency, length, mass…)"),
    B("]", "kind:+1", "Switch to the next kind"),
    B("s", "swap", "Swap From and To"),
    B("<CR>", "save", "Save the conversion to the list"),
    B("=", "save", "Save the conversion to the list"),
    B("yy", "copy:to", "Copy the converted amount"),
    B("Y", "copy:line", "Copy the whole conversion (100 USD = 9,392.25 INR)"),
    B("x", "backspace", "Delete the amount's last character"),
    B("D", "clearbox", "Clear the amount"),
    B("cc", "change", "Clear the amount and enter insert mode"),
    B("S", "change", "Clear the amount and enter insert mode"),
    B("dd", "deletesaved", "Delete the newest saved conversion (u brings it back)"),
    B("u", "undo", "Undo the last deleted conversion"),
    B(" ef", "pickunit:from", "Pick the From unit (type to filter, Enter picks)"),
    B(" et", "pickunit:to", "Pick the To unit (type to filter, Enter picks)"),
    B(" yy", "copy:to", "Copy the converted amount"),
    B(" yf", "copy:from", "Copy the From amount"),
    B(" yl", "copy:line", "Copy the whole conversion"),
    B(" yr", "copy:rate", "Copy the rate (1 USD = 93.92 INR)"),
    B(" mp", "pin", "Toggle the pin on the To currency (pinned ones show below)"),
    B(" aa", "save", "Save the conversion to the list"),
    B(" dd", "deletesaved", "Delete the newest saved conversion"),
    B(" da", "clearsaved", "Clear every saved conversion (y confirms)"),
    moved(" ut", "Space e t"), moved(" p", "Space m p"),
    moved(" ss", "Space a a"), moved(" sd", "Space d d"), moved(" sc", "Space d a"),
] + [B(f" g{key}", f"kind:{kind}", f"Switch to {kind}") for kind, key in KIND_KEYS.items()] \
  + [moved(f" k{key}", f"Space g {key}") for key in KIND_KEYS.values()]

GROUPS = {" v": "memory", " e": "unit", " g": "kind"}

TABS = {"calc": COMMON + CALC, "convert": COMMON + CONVERT}


def keys(tab):
    """ganit's binds on this tab (both modes)."""
    return [b for b in INSERT if b.when in (None, tab)] + TABS.get(tab, COMMON)
