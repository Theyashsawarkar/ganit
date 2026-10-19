"""ganit (गणित, "mathematics"): the calculator for Vyom.

Answers as you type, through qalc (libqalculate): arithmetic, functions,
percentages ("18% of 3897", "3897 + 18%"), units ("5 ft 11 in to cm"),
currency ("100 USD to INR", rates updated once a day), dates, bases.
Enter copies the answer; the history keeps the last 50.
"""
import re
import time

from vyom import Hint, Row, Section, util
from vyom import Plugin as Base

# keybind: Vyom/calculator | Enter | Copy the answer (on a history line: use it again)
# keybind: Vyom/calculator | Ctrl+Enter | Copy the expression with its answer
# keybind: Vyom/calculator | Ctrl+Backspace | Clear the history

STATE = "ganit-history"


def qalc(expr):
    code, out = util.run(["qalc", "-t", expr], timeout=5)
    out = out.splitlines()[0].strip() if out else ""
    return out if code == 0 and out else None


class Plugin(Base):
    name, title, icon, color = "ganit", "Calculator", "\U000f0a9a", "peach"
    placeholder = "Math, units, currency…   e.g. 100 USD to INR · 18% of 3897 · 5 ft to cm"
    debounce = 120
    width = 680
    height = 430
    hints = [Hint("Enter", "copy answer"), Hint("Ctrl+Enter", "copy with expression")]
    empty_text = "Type something to calculate"

    def opened(self, args):
        super().opened(args)
        # Currency rates: qalc fetches them itself; refresh once a day.
        last = util.load_state("ganit-rates", {}).get("t", 0)
        if time.time() - last > 86400:
            util.save_state("ganit-rates", {"t": time.time()})
            util.spawn(["qalc", "-e", "1"])

    def search(self, q):
        rows = []
        hist = util.load_state(STATE, {"items": []})["items"]
        q = q.strip()
        if q:
            ans = qalc(q)
            if ans and ans != q:
                rows.append(Row(f"<span size='xx-large' weight='bold'>{util_escape(ans)}</span>",
                                util_escape(q), icon="\U000f0a9a", color="peach", markup=True,
                                meta="Enter copy", data=("answer", q, ans)))
                n = re.fullmatch(r"-?\d+", ans.replace(" ", ""))
                if n:
                    v = int(ans.replace(" ", ""))
                    rows.append(Row(f"{v:,}", "with separators", icon="\U000f0ff0", color="gray", data=("copy", f"{v:,}")))
                    rows.append(Row(hex(v), "hexadecimal", icon="\U000f0ff0", color="gray", data=("copy", hex(v))))
                    rows.append(Row(bin(v), "binary", icon="\U000f0ff0", color="gray", data=("copy", bin(v))))
            else:
                rows.append(Row("…", "not something qalc understands yet", icon="\U000f0a9a", color="gray", dim=True,
                                data=None))
        if hist:
            rows.append(Section("History"))
            for h in hist[:20]:
                if not q or util.fuzzy(q, h["expr"]) is not None or q in h["ans"]:
                    rows.append(Row(h["expr"], f"= {h['ans']}", icon="\U000f02da", color="gray",
                                    data=("history", h["expr"], h["ans"])))
        return rows

    def remember(self, expr, ans):
        hist = util.load_state(STATE, {"items": []})
        items = [h for h in hist["items"] if h["expr"] != expr]
        items.insert(0, {"expr": expr, "ans": ans})
        util.save_state(STATE, {"items": items[:50]})

    def activate(self, row, mods):
        if not row.data:
            return False
        kind = row.data[0]
        if kind == "history":
            if self.panel:   # put it back in the box to build on it
                self.panel.entry.set_text(row.data[1])
                self.panel.entry.set_position(-1)
            return False
        if kind == "copy":
            util.copy(row.data[1])
            return True
        _, expr, ans = row.data
        util.copy(f"{expr} = {ans}" if "ctrl" in mods else ans)
        self.remember(expr, ans)
        return True

    def key(self, name, row, mods):
        if name == "BackSpace" and "ctrl" in mods and self.panel and not self.panel.query():
            util.save_state(STATE, {"items": []})
            self.refresh()
            return True
        return False


def util_escape(s):
    from gi.repository import GLib
    return GLib.markup_escape_text(s)
