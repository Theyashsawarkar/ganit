"""ganit (गणित, "mathematics"): the calculator and converter for Vyom.

Two tabs. Calculate answers as you type, through qalc (libqalculate):
arithmetic, functions, percentages ("18% of 3897", "3897 + 18%"), units
("5 ft 11 in to cm"), currency ("100 USD to INR"), dates, bases. Each
answer says how qalc read the input, and the preview pane holds its other
forms (plain, exact, hex, binary). Convert takes an amount once ("100 usd",
"€50", "2500", "5 ft", "30 c") and shows it in every pinned currency, or
in the related units. Exchange rates come from qalc; their age is always
shown, and they refresh once a day (Ctrl+R: now).
"""
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from gi.repository import GLib

from vyom import Hint, Row, Section, ui, util
from vyom import Plugin as Base

# keybind: Vyom/calculator | Enter | Copy the answer (on a history line or an example: put it in the box)
# keybind: Vyom/calculator | Shift+Enter | Copy the answer and keep the panel open
# keybind: Vyom/calculator | Ctrl+Enter | Copy the answer with its expression
# keybind: Vyom/calculator | Alt+1..4 | Copy one of the answer's other forms (plain, exact, hex, binary)
# keybind: Vyom/calculator | Ctrl+R | Update the exchange rates now
# keybind: Vyom/calculator | Ctrl+P | Toggle the selected currency's pin (Convert tab)
# keybind: Vyom/calculator | Ctrl+B | Set the selected currency as the base (Convert tab)
# keybind: Vyom/calculator | Ctrl+Backspace | Clear the history (with an empty box)

STATE = "ganit-history"
ICON, ICON_HIST, ICON_TRY, ICON_UNIT, ICON_CASH, ICON_WARN = (
    "\U000f0a9a", "\U000f02da", "\U000f0335", "\U000f046d", "\U000f0114", "\U000f0026")
STALE = 2 * 86400          # rates older than this get a warning
POOL = ThreadPoolExecutor(max_workers=4)

PLACEHOLDER = {
    "calc": "Math, units, currency…   e.g. 18% of 3897 · 100 USD to INR · 5 ft to cm",
    "convert": "An amount and a currency or unit…   e.g. 100 usd · €50 · 2500 · 5 ft · 30 c",
}

EXAMPLES = [
    ("18% of 3897", "percent of a number"),
    ("3897 + 18%", "add a percentage"),
    ("100 USD to INR", "currency"),
    ("5 ft 11 in to cm", "units"),
    ("today + 30 days", "dates"),
    ("0xff to bin", "number bases"),
    ("sqrt(2) * pi", "functions"),
]

# code: (name, symbol). The symbol also serves as the row's icon when it's short.
CURRENCIES = {
    "INR": ("Indian rupee", "₹"), "USD": ("US dollar", "$"), "EUR": ("Euro", "€"),
    "GBP": ("British pound", "£"), "JPY": ("Japanese yen", "¥"), "AED": ("UAE dirham", ""),
    "SGD": ("Singapore dollar", "S$"), "CAD": ("Canadian dollar", "C$"), "AUD": ("Australian dollar", "A$"),
    "NZD": ("New Zealand dollar", "NZ$"), "CHF": ("Swiss franc", ""), "CNY": ("Chinese yuan", "¥"),
    "HKD": ("Hong Kong dollar", "HK$"), "SAR": ("Saudi riyal", ""), "QAR": ("Qatari riyal", ""),
    "KWD": ("Kuwaiti dinar", ""), "KRW": ("South Korean won", "₩"), "THB": ("Thai baht", "฿"),
    "MYR": ("Malaysian ringgit", "RM"), "IDR": ("Indonesian rupiah", "Rp"), "PHP": ("Philippine peso", "₱"),
    "LKR": ("Sri Lankan rupee", ""), "NPR": ("Nepalese rupee", ""), "BDT": ("Bangladeshi taka", "৳"),
    "PKR": ("Pakistani rupee", ""), "ZAR": ("South African rand", "R"), "BRL": ("Brazilian real", "R$"),
    "MXN": ("Mexican peso", "MX$"), "RUB": ("Russian ruble", "₽"), "TRY": ("Turkish lira", "₺"),
    "SEK": ("Swedish krona", "kr"), "NOK": ("Norwegian krone", "kr"), "DKK": ("Danish krone", "kr"),
    "PLN": ("Polish złoty", "zł"), "BTC": ("Bitcoin", "₿"),
}
NO_DECIMALS = {"JPY", "KRW", "IDR"}
CURRENCY_WORDS = {
    "$": "USD", "€": "EUR", "£": "GBP", "¥": "JPY", "₹": "INR", "₩": "KRW", "₿": "BTC",
    "dollar": "USD", "dollars": "USD", "rupee": "INR", "rupees": "INR", "rs": "INR",
    "euro": "EUR", "euros": "EUR", "pound": "GBP", "pounds": "GBP", "yen": "JPY",
    "dirham": "AED", "dirhams": "AED", "yuan": "CNY", "bitcoin": "BTC",
}
PINNED = ["INR", "USD", "EUR", "GBP", "AED", "JPY", "SGD"]

# Convert tab units: per dimension, the targets shown (qalc name, label), and
# the words that mean each unit. Any one of them as the input shows the rest.
UNITS = {
    "length": [("mm", "millimetres"), ("cm", "centimetres"), ("m", "metres"), ("km", "kilometres"),
               ("in", "inches"), ("ft", "feet"), ("yd", "yards"), ("mi", "miles")],
    "mass": [("g", "grams"), ("kg", "kilograms"), ("lb", "pounds"), ("oz", "ounces")],
    "temperature": [("°C", "Celsius"), ("°F", "Fahrenheit"), ("K", "kelvin")],
    "volume": [("mL", "millilitres"), ("L", "litres"), ("cup", "US cups"), ("gal", "US gallons")],
    "data": [("kB", "kilobytes"), ("MB", "megabytes"), ("GB", "gigabytes"), ("TB", "terabytes"),
             ("KiB", "kibibytes"), ("MiB", "mebibytes"), ("GiB", "gibibytes")],
    "speed": [("km/h", "km per hour"), ("m/s", "metres per second"), ("mph", "miles per hour"),
              ("knot", "knots")],
    "area": [("m^2", "square metres"), ("ft^2", "square feet"), ("acre", "acres"), ("ha", "hectares")],
    "time": [("s", "seconds"), ("min", "minutes"), ("h", "hours"), ("d", "days"), ("week", "weeks")],
}
UNIT_WORDS = {
    "mm": "mm", "millimeter": "mm", "millimeters": "mm", "millimetre": "mm", "millimetres": "mm",
    "cm": "cm", "centimeter": "cm", "centimeters": "cm", "centimetre": "cm", "centimetres": "cm",
    "m": "m", "meter": "m", "meters": "m", "metre": "m", "metres": "m",
    "km": "km", "kilometer": "km", "kilometers": "km", "kilometre": "km", "kilometres": "km",
    "in": "in", "inch": "in", "inches": "in", '"': "in", "ft": "ft", "foot": "ft", "feet": "ft", "'": "ft",
    "yd": "yd", "yard": "yd", "yards": "yd", "mi": "mi", "mile": "mi", "miles": "mi",
    "g": "g", "gram": "g", "grams": "g", "kg": "kg", "kilo": "kg", "kilos": "kg", "kilogram": "kg",
    "kilograms": "kg", "lb": "lb", "lbs": "lb", "oz": "oz", "ounce": "oz", "ounces": "oz",
    "c": "°C", "°c": "°C", "degc": "°C", "celsius": "°C", "f": "°F", "°f": "°F", "degf": "°F",
    "fahrenheit": "°F", "k": "K", "kelvin": "K",
    "ml": "mL", "l": "L", "liter": "L", "liters": "L", "litre": "L", "litres": "L",
    "cup": "cup", "cups": "cup", "gal": "gal", "gallon": "gal", "gallons": "gal",
    "kb": "kB", "mb": "MB", "gb": "GB", "tb": "TB", "kib": "KiB", "mib": "MiB", "gib": "GiB",
    "km/h": "km/h", "kmh": "km/h", "kph": "km/h", "m/s": "m/s", "mph": "mph",
    "knot": "knot", "knots": "knot", "kn": "knot",
    "m2": "m^2", "m^2": "m^2", "sqm": "m^2", "ft2": "ft^2", "ft^2": "ft^2", "sqft": "ft^2",
    "acre": "acre", "acres": "acre", "ha": "ha", "hectare": "ha", "hectares": "ha",
    "s": "s", "sec": "s", "secs": "s", "second": "s", "seconds": "s", "min": "min", "mins": "min",
    "minute": "min", "minutes": "min", "h": "h", "hr": "h", "hrs": "h", "hour": "h", "hours": "h",
    "d": "d", "day": "d", "days": "d", "week": "week", "weeks": "week",
}
UNIT_DIM = {u: dim for dim, units in UNITS.items() for u, _ in units}


# ------------------------------------------------------------------- qalc
def qalc_lines(args, input=None, timeout=5):
    code, out = util.run(["qalc", "-s", "color 0", *args], timeout=timeout, input=input)
    return code, [line.rstrip() for line in out.splitlines()]


def evaluate(expr):
    """qalc's answer and how it read the input, from two runs side by side:
    -t for the answer (robust), plain for the parse ("(18 × percent) × 3897
    = 701 + 23/50 = 701.46"). None when there's no answer."""
    terse = POOL.submit(qalc_lines, ["-t", expr])
    full = POOL.submit(qalc_lines, [expr])
    code, lines = terse.result()
    _, flines = full.result()
    warnings = [l for l in lines + flines if l.startswith(("warning:", "error:"))]
    lines = [l.strip() for l in lines if l.strip() and not l.startswith(("warning:", "error:"))]
    if code != 0 or not lines:
        return None
    ans, read, middle, approx = lines[-1], None, [], False
    eq = [l for l in flines if " = " in l or " ≈ " in l]
    if eq and "=" not in expr:          # an equation's parse is the equation itself
        line = re.sub(r"^Percentage interpretation:\s*", "", eq[-1].strip())
        parts = re.split(r"\s(=|≈)\s", line)
        read, middle = parts[0], parts[2:-1:2]
        approx = "≈" in parts[1::2]
        target = re.search(r"\s(?:to|->|→)\s+(.+)$", expr)
        if target and target.group(1) not in read:
            read += f" → {target.group(1)}"
    return {"ans": ans, "read": read, "middle": middle, "approx": approx, "warnings": warnings}


def batch(exprs):
    """Several expressions through one qalc (one per line on stdin): the
    answers in the same order, None where qalc failed."""
    if not exprs:
        return []
    _, lines = qalc_lines(["-t"], input="\n".join(exprs) + "\n", timeout=8)
    out, cur = [], None
    for line in lines:
        if line.startswith("> "):
            if cur is not None:
                out.append(None)
            cur = line
        elif line.strip() and cur is not None:
            s = line.strip()
            out.append(None if s.startswith(("warning:", "error:")) else s)
            cur = None
    if cur is not None:
        out.append(None)
    return (out + [None] * len(exprs))[:len(exprs)]


# ------------------------------------------------------------ rates
def rates_dir():
    return os.path.join(os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share"), "qalculate")


def rates_time():
    """When qalc last downloaded exchange rates (0: never)."""
    times = []
    for f in ("eurofxref-daily.xml", "rates.json"):
        try:
            times.append(os.path.getmtime(os.path.join(rates_dir(), f)))
        except OSError:
            pass
    return max(times, default=0)


def rates_age_text(t=None):
    t = rates_time() if t is None else t
    if not t:
        return "never downloaded"
    age, when = time.time() - t, time.localtime(t)
    if age < 3600:
        return "updated just now" if age < 120 else f"updated {int(age // 60)} min ago"
    if time.strftime("%F") == time.strftime("%F", when):
        return time.strftime("today, %H:%M", when)
    if age < 2 * 86400:
        return time.strftime("yesterday, %H:%M", when)
    return f"{int(age // 86400)} days old ({time.strftime('%-d %b', when)})"


# ------------------------------------------------------------- numbers
NUM = re.compile(r"(?<![\w.])[−-]?\d+(?:\.\d+)?(?![\w.])")
MONEY = re.compile(r"^[−-]?\s*(?:(?P<sym>[^\d\s−-]{1,3}|[A-Z]{3})\s?)?[−-]?\d+(?:\.\d+)?(?:\s?(?P<code>[A-Z]{3}))?$")


def group(int_digits, style):
    if style == "none" or len(int_digits) < 4:
        return int_digits
    if style == "indian":
        head, tail = int_digits[:-3], int_digits[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        return ",".join(([head] if head else []) + parts + [tail])
    return f"{int(int_digits):,}"


def fmt_num(s, style, decimals=None, max_decimals=None):
    """A plain number string grouped (and rounded) for display."""
    s = s.replace("−", "-")
    try:
        d = Decimal(s)
    except InvalidOperation:
        return s
    if decimals is not None:
        d = d.quantize(Decimal(1).scaleb(-decimals), rounding=ROUND_HALF_UP)
    elif max_decimals is not None:
        if abs(d) >= 1 or d == 0:
            d = d.quantize(Decimal(1).scaleb(-max_decimals), rounding=ROUND_HALF_UP).normalize()
        else:  # small: keep 4 significant digits instead of rounding to 0
            d = Decimal(f"{d:.4g}").normalize()
    text = f"{d:f}"
    neg = text.startswith("-")
    whole, _, frac = text.lstrip("-").partition(".")
    out = group(whole, style) + (f".{frac}" if frac else "")
    return ("−" if neg else "") + out


def money_code(ans):
    """The currency of a qalc answer like "₹9492.5546" or "AED 3.67", else None."""
    m = MONEY.match(ans.strip())
    if not m or not (m.group("sym") or m.group("code")):
        return None
    tok = m.group("code") or m.group("sym")
    return currency(tok) or (tok if re.fullmatch(r"[A-Z]{3}", tok) else None)


def pretty(ans, style):
    """qalc's answer for display: digits grouped, money to 2 decimals.
    Dates, bases, binary and scientific notation are left alone."""
    if re.fullmatch(r'"[^"]*"', ans):
        return ans.strip('"')
    if '"' in ans or re.fullmatch(r"[01 ]+", ans) or re.search(r"\d[Ee][−+-]?\d|0[xob]", ans):
        return ans
    code = money_code(ans)
    if code:
        dec = 0 if code in NO_DECIMALS else 6 if code == "BTC" else 2
        return NUM.sub(lambda m: fmt_num(m.group(), style, decimals=dec), ans, count=1)
    return NUM.sub(lambda m: fmt_num(m.group(), style), ans)


def plain(text):
    """A displayed number without its group separators, for pasting."""
    return re.sub(r"(?<=\d),(?=\d)", "", text).replace("−", "-")


def currency(tok):
    if not tok:
        return None
    t = tok.strip().lower()
    if t in CURRENCY_WORDS:
        return CURRENCY_WORDS[t]
    return t.upper() if t.upper() in CURRENCIES else None


def money(value_text, code, style):
    """An amount qalc gave for `code` ("₹9492.5546", "AED 3.67"), as display text."""
    m = re.search(r"[−-]?\d+(?:\.\d+)?(?:E[−+-]?\d+)?", value_text or "")
    if not m:
        return value_text or "?"
    dec = 0 if code in NO_DECIMALS else 6 if code == "BTC" else 2
    num = fmt_num(str(Decimal(m.group().replace("−", "-"))), style, decimals=dec)
    sym = CURRENCIES.get(code, ("", ""))[1]
    return f"{sym}{num}" if sym and len(sym) <= 3 and code not in ("SEK", "NOK", "DKK", "PLN") else f"{num} {code}"


RATE_SCALE = 1000000   # qalc shows money to 4 decimals: "1 INR to USD" is $0.0105


def rate_text(value_text, scale=1):
    """A rate for display; `scale`: value_text is for that many units."""
    m = re.search(r"[−-]?\d+(?:\.\d+)?(?:E[−+-]?\d+)?", value_text or "")
    if not m:
        return "?"
    d = Decimal(m.group().replace("−", "-")) / scale
    return fmt_num(str(d), "intl", max_decimals=4) if d else "0"


def number_of(text):
    m = re.search(r"[−-]?\d+(?:\.\d+)?(?:E[−+-]?\d+)?", plain(text or ""))
    return Decimal(m.group().replace("−", "-")) if m else None


def incomplete(q, res):
    """Half-typed input ("2 +", "100 usd to"): qalc would guess an answer
    that jumps around with every key."""
    if re.search(r"([-+*/^×÷·,(=]|\b(to|in|of|as|mod|and|or))\s*$", q, re.I):
        return True
    return bool(res and any("Misplaced operator" in w for w in res["warnings"]))


def rewrite(q):
    """What qalc can't read as people write it: "18% of 3897" (qalc reads
    "of" as a unit and answers rem(18, 1 B))."""
    return re.sub(r"(\d+(?:\.\d+)?)\s*(?:%|percent)\s+of\s+", r"\1% * ", q, flags=re.I)


def esc(s):
    return GLib.markup_escape_text(str(s))


def big(text, unit_split=True):
    """A hero answer: the number large, a unit after it smaller."""
    m = re.fullmatch(r"(.*?\d)\s+([^\d\s].*)", text) if unit_split else None
    if m and not money_code(text):
        return (f"<span size='xx-large' weight='bold'>{esc(m.group(1))}</span>"
                f"<span size='large' alpha='75%'>  {esc(m.group(2))}</span>")
    return f"<span size='xx-large' weight='bold'>{esc(text)}</span>"


def section_label(text):
    return ui.label(text.upper(), "section", xalign=0)


# --------------------------------------------------------------- plugin
class Plugin(Base):
    name, title, icon, color = "ganit", "Calculator", ICON, "peach"
    placeholder = PLACEHOLDER["calc"]
    debounce = 120
    preview = True
    preview_width = 300
    hints = [Hint("Enter", "copy"), Hint("Shift+Enter", "copy, keep open"),
             Hint("Ctrl+Enter", "with expression")]
    empty_text = "Type something to calculate"
    tabs = [("calc", "Calculate"), ("convert", "Convert")]

    def __init__(self, vyom, conf):
        super().__init__(vyom, conf)
        self.tab = "calc"
        self.last_good = None
        self.updating = False
        self.style = self.conf.get("grouping", "intl")
        self.home = str(self.conf.get("home", "INR")).upper()

    # ---- tabs (Vyom draws them: Ctrl+H/L, Ctrl+1/2)
    def tab_changed(self, key):
        if self.panel:
            self.panel.entry.set_placeholder_text(PLACEHOLDER[key])
        self.refresh()

    def opened(self, args):
        super().opened(args)
        self.last_good = None
        self.select_tab("convert" if args and args[0] in ("convert", "conv") else "calc")
        if self.panel:
            self.panel.entry.set_placeholder_text(PLACEHOLDER[self.tab])
        # Rates: once a day, and not again within an hour of a failed try
        # (offline), so opening the panel never hammers the network.
        tried = util.load_state("ganit-rates", {}).get("tried", 0)
        if time.time() - rates_time() > 86400 and time.time() - tried > 3600:
            GLib.idle_add(lambda: (self.update_rates(), False)[1])

    def update_rates(self):
        if self.updating:
            return
        self.updating = True
        self.set_status("Updating exchange rates…")
        before = rates_time()
        util.save_state("ganit-rates", {"tried": time.time()})

        def done(_r):
            self.updating = False
            ok = rates_time() > before
            self.set_status("Exchange rates updated" if ok else "Couldn't update exchange rates (offline?)")
            self.refresh()
        self.background(lambda: util.run(["qalc", "-e", "-s", "color 0", "1"], timeout=30), done)

    # ---- state
    def pinned(self):
        p = util.load_state("ganit-pinned", {}).get("codes")
        return p if isinstance(p, list) else list(self.conf.get("currencies", PINNED))

    def history(self):
        return util.load_state(STATE, {"items": []})["items"]

    def remember(self, expr, ans):
        items = [h for h in self.history() if h["expr"] != expr]
        items.insert(0, {"expr": expr, "ans": ans, "t": time.time()})
        util.save_state(STATE, {"items": items[:50]})

    # ---- search
    def search(self, q):
        return self.search_convert(q) if self.tab == "convert" else self.search_calc(q)

    def history_rows(self, q="", limit=6):
        rows = []
        for h in self.history():
            if q and util.fuzzy(q, h["expr"]) is None and q not in h["ans"]:
                continue
            rows.append(Row(esc(h["expr"]), "", icon=ICON_HIST, color="gray", markup=True,
                            meta=f"<span size='large' weight='bold'>{esc(h['ans'])}</span>",
                            data=("history", h["expr"], h["ans"], h.get("t"))))
            if len(rows) == limit:
                break
        return rows

    def example_rows(self, n=None):
        return [Row(e, what, icon=ICON_TRY, color="gray", data=("example", e, what))
                for e, what in EXAMPLES[:n]]

    def search_calc(self, q):
        q = q.strip()
        if not q:
            self.last_good = None
            recent = self.history_rows(limit=5)
            tries = [Section("Try")] + self.example_rows()
            return ([Section("Recent")] + recent + tries) if recent else tries
        expr = rewrite(q)
        res = None if incomplete(q, None) else evaluate(expr)
        rows = []
        if res is None or incomplete(q, res):
            if res is None and not incomplete(q, None):
                rows.append(Row("Not something qalc understands", f"“{q}”, try one of these:", icon=ICON_WARN,
                                color="red", dim=True, data=None))
                rows += self.example_rows(4)
                return rows
            last = self.last_good
            rows.append(Row(big(last) if last else "…", "waiting for more…", icon=ICON, color="gray",
                            markup=True, dim=True, data=None))
        else:
            display = pretty(res["ans"], self.style)
            self.last_good = display
            read = res["read"] or q
            sub = f"read as  {read}" + ("   ·   rounded" if res["approx"] else "")
            rows.append(Row(big(display), esc(sub), icon=ICON, color="peach", markup=True,
                            data=("answer", q, display, self.forms(res, display), self.rate_info(q, res))))
        hist = self.history_rows(q, limit=8)
        if hist:
            rows += [Section("History")] + hist
        return rows

    def forms(self, res, display):
        """The answer's other forms, for Alt+1..4."""
        out = []

        def add(label, value):
            if value and value.strip('"') != display and value not in [v for _, v in out]:
                out.append((label, value))
        add("plain", plain(display))
        add("exact", res["ans"])
        for m in res["middle"]:
            add("exact", m)
        n = number_of(res["ans"]) if re.fullmatch(r"[−-]?\d+", res["ans"]) else None
        if n is not None:
            v = int(n)
            add("hex", hex(v))
            add("binary", bin(v))
            if abs(v) >= 10 ** 7:
                add("scientific", f"{v:.4e}")
        return out[:4]

    def rate_info(self, q, res):
        """For "100 USD to INR": the rate both ways, for the preview."""
        m = re.fullmatch(r"\s*([$€£¥₹₩₿])?\s*[\d.,]+\s*([A-Za-z$€£¥₹₩₿]+)?\s+(?:to|in|->|→)\s+([A-Za-z$€£¥₹₩₿]+)\s*", q)
        if not m or not money_code(res["ans"]):
            return None
        a, b = currency(m.group(1) or m.group(2)), currency(m.group(3))
        if not a or not b or a == b:
            return None
        fwd, back = batch([f"{RATE_SCALE} {a} to {b}", f"{RATE_SCALE} {b} to {a}"])
        return {"from": a, "to": b, "rate": rate_text(fwd, RATE_SCALE), "inverse": rate_text(back, RATE_SCALE)}

    # ---- convert tab
    def parse_amount(self, q):
        m = re.fullmatch(r"(?P<pre>[$€£¥₹₩₿])?\s*(?P<num>\d[\d,]*(?:\.\d+)?|\.\d+)\s*(?P<rest>.*)", q.strip())
        if not m:
            return None
        num = m.group("num").replace(",", "")
        words = m.group("rest").split()
        if m.group("pre"):
            unit = m.group("pre")
        elif words:
            unit = words.pop(0)
        else:
            unit = None
        if words and words[0].lower() in ("to", "in", "->", "→"):
            words.pop(0)
        return num, unit, " ".join(words).lower()

    def search_convert(self, q):
        q = q.strip()
        if not q:
            return self.rate_board()
        p = self.parse_amount(q)
        if p is None:
            return [Row("An amount, then a currency or a unit", f"“{q}” isn't one yet: try 100 usd · €50 · 2500 · 5 ft · 30 c",
                        icon=ICON_WARN, color="gray", dim=True, data=None)]
        num, unit, filt = p
        base = self.home if unit is None else currency(unit)
        if base:
            return self.convert_currency(num, base, filt)
        u = UNIT_WORDS.get(unit.lower()) or UNIT_WORDS.get(unit)
        if u:
            return self.convert_unit(num, u)
        return [Row(f"No currency or unit called “{unit}”", "currencies: usd, eur, inr, $, € …   units: ft, kg, c, gb, km/h …",
                    icon=ICON_WARN, color="gray", dim=True, data=None)]

    def currency_row(self, amount, base, code, value, rate, pinned):
        name, sym = CURRENCIES.get(code, (code, ""))
        display = money(value, code, self.style)
        return Row(big(display, unit_split=False), name, icon=sym if sym and len(sym) == 1 else ICON_CASH,
                   color="peach" if pinned else "gray", markup=True, badge=code,
                   badge_color="yellow" if pinned else "gray",
                   meta=f"<span alpha='70%'>1 {base} = {esc(rate)} {code}</span>",
                   data=("conv", amount, base, code, display, rate))

    def rate_board(self):
        """Empty Convert tab: what one of each pinned currency is worth at home."""
        home, codes = self.home, [c for c in self.pinned() if c != self.home]
        vals = batch([f"{RATE_SCALE} {c} to {home}" for c in codes])
        rows = [Section(f"1 of each in {home}")]
        for c, v in zip(codes, vals):
            if v is None:
                continue
            n = number_of(v) / RATE_SCALE if number_of(v) else None
            display = money(str(n), home, self.style) if n else "?"
            name, sym = CURRENCIES.get(c, (c, ""))
            back = rate_text(str(1 / n)) if n else "?"
            rows.append(Row(big(display, unit_split=False), f"1 {c} · {name}", icon=sym if sym and len(sym) == 1 else ICON_CASH,
                            color="peach", markup=True, badge=c, badge_color="yellow",
                            meta=f"<span alpha='70%'>1 {home} = {esc(back)} {c}</span>",
                            data=("conv", "1", c, home, display, rate_text(v, RATE_SCALE))))
        return rows

    def convert_currency(self, num, base, filt):
        pinned = self.pinned()
        if filt:
            f = currency(filt)
            targets = [c for c, (name, _) in CURRENCIES.items() if c != base and (
                c == f or c.lower().startswith(filt) or filt in name.lower())]
        else:
            targets = [c for c in pinned if c != base]
        name = CURRENCIES.get(base, (base, ""))[0]
        head = Section(f"{fmt_num(num, self.style)} {base} · {name}")
        if not targets:
            return [head, Row(f"No currency matches “{filt}”", "type a code (cad) or a name (franc)",
                              icon=ICON_WARN, color="gray", dim=True, data=None)]
        exprs = []
        for t in targets:
            exprs += [f"{num} {base} to {t}", f"{RATE_SCALE} {base} to {t}"]
        out = batch(exprs)
        rows = [head]
        for i, t in enumerate(targets):
            value, rate = out[2 * i], out[2 * i + 1]
            if value is None:
                continue
            rows.append(self.currency_row(num, base, t, value, rate_text(rate, RATE_SCALE), t in pinned))
        if len(rows) == 1:
            rows.append(Row("qalc has no rate for these", "Ctrl+R updates the exchange rates", icon=ICON_WARN,
                            color="gray", dim=True, data=None))
        return rows

    def convert_unit(self, num, unit):
        dim = UNIT_DIM[unit]
        targets = [(u, label) for u, label in UNITS[dim] if u != unit]
        out = batch([f"{num} {unit} to {u}" for u, _ in targets])
        mixed = [i for i, v in enumerate(out) if v and " + " in v]
        for i, v in zip(mixed, batch([f"({num} {unit}) / (1 {targets[i][0]})" for i in mixed])):
            out[i] = f"{v} {targets[i][0]}" if v else out[i]
        rows = [Section(f"{fmt_num(num, self.style)} {unit.replace('^2', '²')} · {dim}")]
        for (u, label), value in zip(targets, out):
            if value is None:
                continue
            m = re.match(r"\s*([−-]?\d+(?:\.\d+)?)(.*)", value)
            display = (fmt_num(m.group(1), self.style, max_decimals=4) + m.group(2)) if m else value
            rows.append(Row(big(display), label, icon=ICON_UNIT, color="teal", markup=True,
                            data=("unit", f"{num} {unit}", display, dim)))
        return rows

    # ---- preview
    def build_preview(self, row):
        d = row.data
        if not d:
            return None
        kind = d[0]
        if kind == "answer":
            _, q, display, forms, info = d
            parts = [ui.meta(q), ui.label(display, "big-number", xalign=0, wrap=True)]
            if forms:
                parts.append(section_label("Other forms"))
                parts.append(ui.kv([(f"Alt+{i} {label}", value) for i, (label, value) in enumerate(forms, 1)]))
            if info:
                parts.append(section_label("Rate"))
                parts.append(ui.kv([("Rate", f"1 {info['from']} = {info['rate']} {info['to']}"),
                                    ("Inverse", f"1 {info['to']} = {info['inverse']} {info['from']}"),
                                    ("Rates", rates_age_text())]))
                parts.append(self.stale_chip())
            parts += [ui.spacer(), self.keys_body([("Enter", "copy"), ("Shift+Enter", "copy, keep open"),
                                                   ("Ctrl+Enter", "copy with expression")])]
            return ui.vbox(*parts)
        if kind == "history":
            _, expr, ans, t = d
            when = time.strftime("%-d %b, %H:%M", time.localtime(t)) if t else None
            return ui.vbox(ui.meta(expr), ui.label(ans, "big-number", xalign=0, wrap=True),
                           ui.kv([("When", when)]) if when else None, ui.spacer(),
                           self.keys_body([("Enter", "put it back in the box"), ("Shift+Enter", "copy the answer")]))
        if kind == "example":
            return ui.vbox(ui.title(d[1]), ui.meta(d[2]), ui.spacer(), self.keys_body([("Enter", "put it in the box")]))
        if kind == "conv":
            _, amount, base, code, display, rate = d
            try:
                inverse = rate_text(str(1 / Decimal(rate)))
            except (InvalidOperation, ZeroDivisionError):
                inverse = "?"
            pinned = code in self.pinned()
            return ui.vbox(
                ui.meta(f"{fmt_num(amount, self.style)} {base} ="), ui.label(display, "big-number", xalign=0, wrap=True),
                section_label("Rate"),
                ui.kv([("Rate", f"1 {base} = {rate} {code}"), ("Inverse", f"1 {code} = {inverse} {base}"),
                       ("Pinned", "yes" if pinned else "no"), ("Rates", rates_age_text())]),
                self.stale_chip(), ui.spacer(),
                self.keys_body([("Enter", "copy"), ("Ctrl+Enter", "copy with amount"),
                                ("Ctrl+P", "unpin" if pinned else "pin"), ("Ctrl+B", f"make {code} the base"),
                                ("Ctrl+R", "update rates")]))
        if kind == "unit":
            _, src, display, dim = d
            return ui.vbox(ui.meta(f"{src} ="), ui.label(display, "big-number", xalign=0, wrap=True),
                           ui.kv([("Dimension", dim)]), ui.spacer(),
                           self.keys_body([("Enter", "copy"), ("Ctrl+Enter", "copy with amount")]))
        return None

    def stale_chip(self):
        t = rates_time()
        if t and time.time() - t < STALE:
            return None
        return ui.chip(f"{ICON_WARN}  Rates {rates_age_text(t)} · Ctrl+R", "yellow")

    def keys_body(self, pairs):
        return ui.body("\n".join(f"{ui.keycap_markup(k)}  {esc(what)}" for k, what in pairs), markup=True)

    # ---- actions
    def copied(self, text, keep):
        util.copy(text)
        if keep:
            self.set_status(f"Copied {text}")
        return not keep

    def activate(self, row, mods):
        d = row.data
        if not d:
            return False
        kind, keep = d[0], "shift" in mods
        if kind in ("history", "example"):
            if kind == "history" and keep:
                return self.copied(d[2], True)
            if self.panel:   # put it back in the box to build on it
                if self.tab != "calc":
                    self.select_tab("calc")
                self.panel.entry.set_text(d[1])
                self.panel.entry.set_position(-1)
            return False
        if kind == "answer":
            _, q, display, _, _ = d
            self.remember(q, display)
            return self.copied(f"{q} = {display}" if "ctrl" in mods else display, keep)
        if kind == "conv":
            _, amount, base, code, display, _ = d
            self.remember(f"{amount} {base} to {code}", display)
            return self.copied(f"{fmt_num(amount, self.style)} {base} = {display}" if "ctrl" in mods else display, keep)
        if kind == "unit":
            _, src, display, _ = d
            self.remember(f"{src} to {display.split()[-1]}", display)
            return self.copied(f"{src} = {display}" if "ctrl" in mods else display, keep)
        return False

    def key(self, name, row, mods):
        d = row.data if row else None
        if name in ("r", "R") and mods == {"ctrl"}:
            self.update_rates()
            return True
        if "alt" in mods and name in "1234" and len(name) == 1 and d and d[0] == "answer":
            forms = d[3]
            i = int(name) - 1
            if i < len(forms):
                util.copy(forms[i][1])
                self.close()
            return True
        if d and d[0] == "conv" and mods == {"ctrl"}:
            code = d[3]
            if name == "p":
                pins = self.pinned()
                pins = [c for c in pins if c != code] if code in pins else pins + [code]
                util.save_state("ganit-pinned", {"codes": pins})
                self.set_status(f"{'Pinned' if code in pins else 'Unpinned'} {code}")
                self.refresh()
                return True
            if name == "b" and self.panel:   # 100 USD → ₹9,492.55: now convert 9492.55 INR
                n = number_of(d[4])
                self.panel.entry.set_text(f"{n:f} {code}" if n is not None else f"1 {code}")
                self.panel.entry.set_position(-1)
                return True
        if name == "BackSpace" and "ctrl" in mods and self.panel and not self.panel.query() and self.tab == "calc":
            util.save_state(STATE, {"items": []})
            self.refresh()
            return True
        return False
