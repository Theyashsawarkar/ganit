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

from gi.repository import GLib, Gtk, Pango
from vyom import Plugin as Base
from vyom import ui, util

# keybind: Vyom/calculator | Enter | Run the sum and keep its answer on the tape (the panel stays open; Esc closes)
# keybind: Vyom/calculator | Ctrl+Enter | Copy the answer with its expression
# keybind: Vyom/calculator | Up / Down | Move along the tape (Enter with an empty box puts that line back in it)
# keybind: Vyom/calculator | Ctrl+C | Copy the answer (the picked tape line's, else the live one)
# keybind: Vyom/calculator | Ctrl+M | Save the answer to memory (mem in a sum uses it)
# keybind: Vyom/calculator | Ctrl+L | Clear the tape (press it twice)
# keybind: Vyom/calculator | Alt+1..4 | Copy one of the answer's other forms (plain, exact, hex, binary)
# keybind: Vyom/calculator | Ctrl+R | Update the exchange rates now
# keybind: Vyom/converter | Enter | Save the conversion to the list (the panel stays open)
# keybind: Vyom/converter | Up / Down | Move between the From and To amounts
# keybind: Vyom/converter | Alt+Up / Alt+Down | Switch the unit of the side you're typing in
# keybind: Vyom/converter | Alt+1..9 | Switch the kind (currency, length, mass, temperature…)
# keybind: Vyom/converter | Ctrl+S | Swap From and To
# keybind: Vyom/converter | Ctrl+C | Copy the converted amount
# keybind: Vyom/converter | Ctrl+P | Toggle the target currency's pin

STATE = "ganit-history"
ICON, ICON_HIST, ICON_TRY, ICON_UNIT, ICON_CASH, ICON_WARN = (
    "\U000f0a9a", "\U000f02da", "\U000f0335", "\U000f046d", "\U000f0114", "\U000f0026")
STALE = 2 * 86400          # rates older than this get a warning
POOL = ThreadPoolExecutor(max_workers=4)

PLACEHOLDER = {
    "calc": "18% of 3897 · (12 + 8) × 3 · sqrt(2) × pi · 100 usd to inr · 5 ft to cm",
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
    if re.search(r"([-+*/^×÷·,(=]|\b(to|in|of|as|mod|and|or))\s*$", q, re.IGNORECASE):
        return True
    return bool(res and any("Misplaced operator" in w for w in res["warnings"]))


def rewrite(q):
    """What qalc can't read as people write it: "18% of 3897" (qalc reads
    "of" as a unit and answers rem(18, 1 B))."""
    return re.sub(r"(\d+(?:\.\d+)?)\s*(?:%|percent)\s+of\s+", r"\1% * ", q, flags=re.IGNORECASE)


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
# The calculator and the converter are cards: they stay open until Esc.
# Enter calculates (or saves a conversion) and keeps going, like the real thing.

KINDS = ["currency"] + list(UNITS)          # the converter's kinds, Alt+1..9
KIND_COLOR = {"currency": "peach", "length": "teal", "mass": "green", "temperature": "red", "volume": "sky",
              "data": "blue", "speed": "yellow", "area": "lavender", "time": "pink"}
KIND_ICON = {"currency": "\U000f0114", "length": "\U000f046d", "mass": "\U000f05a1", "temperature": "",
             "volume": "\U000f058c", "data": "\U000f02ca", "speed": "\U000f04c5", "area": "\U000f0e5f",
             "time": "\U000f0954"}
OPERATOR_START = re.compile(r"^\s*(?:[+*/×÷^%·]|[-−]\s)")
CONV_STATE = "ganit-conversions"
TAPE_KEEP = 300
PAD = [("C", "clear"), ("(", ""), (")", ""), ("%", "op"), ("÷", "op"),
       ("7", ""), ("8", ""), ("9", ""), ("√", "fn"), ("×", "op"),
       ("4", ""), ("5", ""), ("6", ""), ("x²", "fn"), ("−", "op"),
       ("1", ""), ("2", ""), ("3", ""), ("ans", "fn"), ("+", "op"),
       ("0", ""), (".", ""), ("⌫", "clear"), ("π", "fn"), ("=", "eq")]
PAD_TEXT = {"÷": "/", "×": "*", "−": "-", "√": "sqrt(", "x²": "^2", "π": "pi"}


def day_label(t):
    if not t:
        return "Earlier"
    d = time.strftime("%F", time.localtime(t))
    if d == time.strftime("%F"):
        return "Today"
    if d == time.strftime("%F", time.localtime(time.time() - 86400)):
        return "Yesterday"
    return time.strftime("%A, %-d %B", time.localtime(t))


def lbl(text="", *classes, xalign=0, markup=False, **kw):
    w = Gtk.Label(xalign=xalign, **kw)
    (w.set_markup if markup else w.set_text)(text)
    for c in classes:
        w.add_css_class(c)
    return w


def kv_rows(pairs):
    g = Gtk.Grid(column_spacing=12, row_spacing=3)
    for i, (k, v) in enumerate(pairs):
        g.attach(lbl(k, "g-k"), 0, i, 1, 1)
        val = lbl(v, "g-v", ellipsize=Pango.EllipsizeMode.END, max_width_chars=24)
        val.set_tooltip_text(v)
        g.attach(val, 1, i, 1, 1)
    return g


def hint(keys, what):
    return ui.hint_label(keys, what)


class Plugin(Base):
    name, title, icon, color = "ganit", "Calculator", ICON, "peach"
    layout = "card"
    width, height = 900, 520            # the size of every Vyom panel
    tabs = [("calc", "Calculate"), ("convert", "Convert")]  # noqa: RUF012 (Vyom reads the class attribute)

    def __init__(self, vyom, conf):
        super().__init__(vyom, conf)
        self.tab = "calc"
        self.updating = False
        self.style = self.conf.get("grouping", "intl")
        self.home = str(self.conf.get("home", "INR")).upper()
        # calculator
        self.ans_raw = None          # the last answer as qalc wrote it (chains into the next sum)
        self.mem_raw = None
        self.live = None             # the current input's answer: {"display", "raw", "read", "forms"} or a status
        self.sel = None              # a tape line picked with Up / Down (its index in the history)
        self.gen = 0
        self.timer = None
        self.clear_armed = 0
        # converter
        self.kind = "currency"
        self.units = {"currency": ("USD", self.home if self.home != "USD" else "INR")}
        self.amount = "100"
        self.editing = "from"
        self.result = {}             # unit -> value (number) for the amount in self.amount
        self.cgen = 0
        self.ctimer = None
        self.setting = False

    # ------------------------------------------------------------- opening
    def opened(self, args):
        super().opened(args)
        if args and args[0] in ("convert", "conv"):
            self.tab = "convert"
        elif args:
            self.tab = "calc"
        if self.panel and getattr(self.panel, "tab_buttons", None):
            self.panel.select_tab(self.tab)
        # Rates: once a day, and not again within an hour of a failed try
        # (offline), so opening the panel never hammers the network.
        tried = util.load_state("ganit-rates", {}).get("tried", 0)
        if time.time() - rates_time() > 86400 and time.time() - tried > 3600:
            GLib.idle_add(lambda: (self.update_rates(), False)[1])

    def tab_changed(self, key):
        if self.panel:
            self.panel.rebuild_card()
            self.focus_soon()

    def build_card(self):
        card = self.calc_card() if self.tab == "calc" else self.convert_card()
        if self.panel:   # the panel's height (minus its tab bar): it never grows with what's in it
            card.set_size_request(-1, max(360, self.panel.sizes()[1] - 56))
        self.focus_soon()
        return card

    def focus_soon(self):
        def go():
            w = self.entry if self.tab == "calc" else (self.to_entry if self.editing == "to" else self.from_entry)
            if w is not None and w.get_root() is not None:
                w.grab_focus()
                if self.tab == "convert":
                    w.select_region(0, -1)   # typing replaces the amount
                else:
                    w.set_position(-1)
            return False
        GLib.timeout_add(30, go)

    def update_rates(self):
        if self.updating:
            return
        self.updating = True
        self.say("Updating exchange rates…")
        before = rates_time()
        util.save_state("ganit-rates", {"tried": time.time()})

        def done(_r):
            self.updating = False
            ok = rates_time() > before
            self.say("Exchange rates updated" if ok else "Couldn't update exchange rates (offline?)")
            if self.tab == "convert":
                self.convert_now()
        self.background(lambda: util.run(["qalc", "-e", "-s", "color 0", "1"], timeout=30), done)

    def say(self, text, bad=False):
        st = getattr(self, "status", None)
        if st is not None and st.get_root() is not None:
            st.set_text(text)
            for c in ("g-bad", "g-ok"):
                st.remove_css_class(c)
            st.add_css_class("g-bad" if bad else "g-ok")

    def footer(self, pairs):
        foot = Gtk.Box(spacing=14)
        foot.add_css_class("g-foot")
        mode = lbl("CALC" if self.tab == "calc" else "CONVERT", "g-mode")
        foot.append(mode)
        for k, w in pairs:
            foot.append(hint(k, w))
        self.status = lbl("", "g-status", hexpand=True, xalign=1, ellipsize=Pango.EllipsizeMode.END)
        foot.append(self.status)
        foot.append(hint("F11", "fullscreen"))
        foot.append(hint("Esc", "close"))
        return foot

    # =========================================================== calculator
    def history(self):
        return util.load_state(STATE, {"items": []})["items"]

    def tape_items(self):
        """The history oldest first: the tape reads top to bottom."""
        return list(reversed(self.history()))

    def remember(self, expr, ans, raw):
        items = self.history()
        items.insert(0, {"expr": expr, "ans": ans, "raw": raw, "t": time.time()})
        util.save_state(STATE, {"items": items[:TAPE_KEEP]})

    def calc_card(self):
        self.entry = None
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, vexpand=True)
        root.add_css_class("g-card")
        body = Gtk.Box(vexpand=True)
        left = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8, hexpand=True)
        left.add_css_class("g-left")
        head = Gtk.Box()
        head.append(lbl("TAPE", "g-head", hexpand=True))
        self.tape_count = lbl("", "g-head-note", xalign=1)
        head.append(self.tape_count)
        left.append(head)
        self.tape_scroll = Gtk.ScrolledWindow(vexpand=True)
        self.tape_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.tape_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1, valign=Gtk.Align.END)
        self.tape_scroll.set_child(self.tape_box)
        left.append(self.tape_scroll)

        disp = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        disp.add_css_class("g-display")
        row = Gtk.Box(spacing=10, halign=Gtk.Align.END)
        self.live_eq = lbl("", "g-eq")
        self.live_big = lbl("0", "g-big", selectable=False, ellipsize=Pango.EllipsizeMode.START)
        row.append(self.live_eq)
        row.append(self.live_big)
        disp.append(row)
        self.live_read = lbl("", "g-read", xalign=1, ellipsize=Pango.EllipsizeMode.END)
        disp.append(self.live_read)
        inrow = Gtk.Box(spacing=10)
        inrow.add_css_class("g-inrow")
        self.ans_chip = lbl("ans", "g-ans")
        self.ans_chip.set_visible(False)
        inrow.append(self.ans_chip)
        self.entry = Gtk.Entry(hexpand=True)
        self.entry.add_css_class("g-input")
        self.entry.set_placeholder_text(PLACEHOLDER["calc"])
        self.entry.connect("changed", lambda *_: self.on_input())
        inrow.append(self.entry)
        disp.append(inrow)
        left.append(disp)
        body.append(left)

        right = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        right.add_css_class("g-right")
        self.forms_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        right.append(self.panel_card("THIS ANSWER", self.forms_box, note="Alt+1..4 copies"))
        grid = Gtk.Grid(row_spacing=6, column_spacing=6, column_homogeneous=True)
        for i, (k, kind) in enumerate(PAD):
            b = Gtk.Button(label=k, can_focus=False)
            b.add_css_class("g-pad")
            if kind:
                b.add_css_class(f"g-pad-{kind}")
            b.connect("clicked", lambda _b, k=k: self.pad(k))
            grid.attach(b, i % 5, i // 5, 1, 1)
        right.append(self.panel_card("KEYPAD", grid, note="or just type"))
        self.mem_label = lbl("", "g-v")
        right.append(self.panel_card("MEMORY", self.mem_label, note="Ctrl+M stores"))
        body.append(right)
        root.append(body)
        root.append(self.footer([("Enter", "calculate"), ("↑↓", "tape"), ("Ctrl+C", "copy"),
                                 ("Ctrl+M", "memory"), ("Tab", "convert")]))
        self.draw_tape()
        self.draw_mem()
        self.show_live()
        return root

    def panel_card(self, title, child, note=""):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.add_css_class("g-box")
        head = Gtk.Box()
        head.append(lbl(title, "g-head", hexpand=True))
        if note:
            head.append(lbl(note, "g-head-note", xalign=1))
        box.append(head)
        box.append(child)
        return box

    def draw_tape(self):
        box = self.tape_box
        while (c := box.get_first_child()) is not None:
            box.remove(c)
        items = self.tape_items()
        last_day, n = None, 0
        self.tape_rows = {}
        for i, h in enumerate(items):
            day = day_label(h.get("t"))
            if day != last_day:
                box.append(lbl(day.upper(), "g-day"))
                last_day = day
            n += 1
            line = Gtk.Box(spacing=10)
            line.add_css_class("g-line")
            if i == self.sel:
                line.add_css_class("g-sel")
            line.append(lbl(str(n), "g-n", xalign=1, width_chars=3))
            line.append(lbl(h["expr"], "g-expr", hexpand=True, ellipsize=Pango.EllipsizeMode.END))
            line.append(lbl(h["ans"], "g-ans-v", xalign=1))
            click = Gtk.GestureClick()
            click.connect("pressed", lambda g, presses, x, y, i=i: self.tape_click(i, presses))
            line.add_controller(click)
            self.tape_rows[i] = line
            box.append(line)
        if not items:
            box.append(lbl("Your sums stay here, like a calculator's paper tape.", "g-empty"))
        self.tape_count.set_text(f"{n} line{'s' if n != 1 else ''} · kept" if n else "")
        GLib.idle_add(self.scroll_tape)

    def scroll_tape(self):
        adj = self.tape_scroll.get_vadjustment()
        if self.sel is not None and self.sel in self.tape_rows:
            w = self.tape_rows[self.sel]
            ok, b = w.compute_bounds(self.tape_box)
            if ok:
                y, h = b.get_y(), b.get_height()
                if y < adj.get_value():
                    adj.set_value(y)
                elif y + h > adj.get_value() + adj.get_page_size():
                    adj.set_value(y + h - adj.get_page_size())
            return False
        adj.set_value(adj.get_upper())
        return False

    def tape_click(self, i, presses):
        if presses >= 2:
            self.recall(i)
        else:
            self.select_line(i)

    def select_line(self, i):
        old = self.tape_rows.get(self.sel)
        if old is not None:
            old.remove_css_class("g-sel")
        self.sel = i
        new = self.tape_rows.get(i)
        if new is not None:
            new.add_css_class("g-sel")
        GLib.idle_add(self.scroll_tape)
        self.show_forms()

    def recall(self, i):
        items = self.tape_items()
        if 0 <= i < len(items):
            self.entry.set_text(items[i]["expr"])
            self.entry.set_position(-1)
            self.entry.grab_focus()

    # ---- live answer
    def prepare(self, q):
        """What qalc gets: a sum starting with an operator goes on from the
        last answer; ans and mem are those values; "18% of 3897" is rewritten."""
        if OPERATOR_START.match(q):
            q = "ans " + q.lstrip()
        expr = rewrite(q)
        expr = re.sub(r"\bans\b", f"({self.ans_raw})" if self.ans_raw else "0", expr)
        expr = re.sub(r"\bmem\b", f"({self.mem_raw})" if self.mem_raw else "0", expr)
        return q, expr

    def on_input(self):
        q = self.entry.get_text()
        self.ans_chip.set_visible(bool(OPERATOR_START.match(q)))
        if self.sel is not None:
            self.select_line(None)
        if self.timer:
            GLib.source_remove(self.timer)
        self.timer = GLib.timeout_add(110, self.evaluate_now)

    def evaluate_now(self, then=None):
        self.timer = None
        q = self.entry.get_text().strip() if self.entry else ""
        self.gen += 1
        gen = self.gen
        if not q:
            self.live = None
            self.show_live()
            return False
        shown, expr = self.prepare(q)
        if incomplete(q, None):
            self.live = {"wait": True}
            self.show_live()
            return False

        def work():
            return evaluate(expr)

        def done(res):
            if gen != self.gen:
                return
            if isinstance(res, Exception) or res is None:
                self.live = {"error": "Not something qalc understands"}
            elif incomplete(q, res):
                self.live = {"wait": True}
            else:
                display = pretty(res["ans"], self.style)
                read = (res["read"] or shown).replace(f"({self.ans_raw})", "ans") if self.ans_raw else (res["read"] or shown)
                self.live = {"q": shown, "display": display, "raw": res["ans"], "read": read,
                             "approx": res["approx"], "forms": self.forms(res, display)}
                self.last_display = display
            self.show_live()
            if then:
                then()
        self.background(work, done)
        return False

    def show_live(self):
        if getattr(self, "live_big", None) is None or self.live_big.get_root() is None:
            return
        big, eq, read = self.live_big, self.live_eq, self.live_read
        for c in ("g-dim", "g-err"):
            big.remove_css_class(c)
        lv = self.live
        if lv is None:
            ans = pretty(self.ans_raw, self.style) if self.ans_raw else "0"
            big.set_text(ans)
            big.add_css_class("g-dim")
            eq.set_text("ans =" if self.ans_raw else "")
            read.set_text("Type a sum · Enter calculates and keeps going")
        elif lv.get("error"):
            big.set_text(lv["error"])
            big.add_css_class("g-err")
            eq.set_text("")
            read.set_text("try 18% of 3897 · 100 usd to inr · 5 ft to cm · today + 30 days")
        elif lv.get("wait"):
            big.set_text(getattr(self, "last_display", None) or "…")
            big.add_css_class("g-dim")
            eq.set_text("")
            read.set_text("waiting for more…")
        else:
            big.set_text(lv["display"])
            eq.set_text("=")
            read.set_text("read as  " + lv["read"] + ("   ·   rounded" if lv["approx"] else ""))
        self.show_forms()

    def forms(self, res, display):
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

    def current_forms(self):
        """(what, display, forms) of the picked tape line, or the live answer."""
        if self.sel is not None:
            items = self.tape_items()
            if 0 <= self.sel < len(items):
                h = items[self.sel]
                return f"line {self.sel + 1}", h["ans"], [("plain", plain(h["ans"]))] + (
                    [("exact", h["raw"])] if h.get("raw") and h["raw"] != h["ans"] else [])
        lv = self.live
        if lv and lv.get("display"):
            return "live", lv["display"], lv["forms"]
        if self.ans_raw:
            d = pretty(self.ans_raw, self.style)
            return "ans", d, [("plain", plain(d))]
        return "", "", []

    def show_forms(self):
        box = getattr(self, "forms_box", None)
        if box is None or box.get_root() is None:
            return
        while (c := box.get_first_child()) is not None:
            box.remove(c)
        _, display, forms = self.current_forms()
        if not display:
            box.append(lbl("Other forms: exact, hex, binary…", "g-empty"))
            return
        box.append(lbl(display, "g-mid", xalign=0, ellipsize=Pango.EllipsizeMode.END, max_width_chars=22))
        rows = [(f"Alt+{i}  {k}", v) for i, (k, v) in enumerate(forms, 1)]
        if rows:
            box.append(kv_rows(rows))

    def draw_mem(self):
        if getattr(self, "mem_label", None) is not None:
            self.mem_label.set_text(f"mem = {pretty(self.mem_raw, self.style)}" if self.mem_raw else
                                    "empty · type mem in a sum to use it")

    # ---- actions
    def commit(self):
        q = self.entry.get_text().strip()
        if not q:
            if self.sel is not None:
                self.recall(self.sel)
            return
        if self.timer:   # typed faster than the live answer: get it first
            GLib.source_remove(self.timer)
            self.timer = None
        lv = self.live
        if lv and lv.get("display") and lv.get("q") == (("ans " + q.lstrip()) if OPERATOR_START.match(q) else q):
            self.keep_answer(lv)
        else:
            self.evaluate_now(then=lambda: self.live and self.live.get("display") and self.keep_answer(self.live)
                              or self.say_why())

    def say_why(self):
        lv = self.live or {}
        self.say("Not something qalc understands" if lv.get("error") else "Not finished yet", bad=True)

    def keep_answer(self, lv):
        self.remember(lv["q"], lv["display"], lv["raw"])
        self.ans_raw = lv["raw"]
        self.live = None
        self.sel = None
        self.entry.set_text("")
        self.draw_tape()
        self.show_live()
        self.say(f"= {lv['display']}")
        return True

    def pad(self, k):
        e = self.entry
        if k == "=":
            self.commit()
        elif k == "C":
            e.set_text("")
        elif k == "⌫":
            t = e.get_text()
            e.set_text(t[:-1])
        else:
            e.set_text(e.get_text() + PAD_TEXT.get(k, k))
        e.grab_focus()
        e.set_position(-1)

    def copy_answer(self, with_expr=False):
        _, display, _ = self.current_forms()
        if not display:
            return self.say("Nothing to copy yet", bad=True)
        text = display
        if with_expr:
            if self.sel is not None:
                text = f"{self.tape_items()[self.sel]['expr']} = {display}"
            elif self.live and self.live.get("q"):
                text = f"{self.live['q']} = {display}"
        util.copy(text)
        self.say(f"Copied {text}")

    def calc_key(self, name, mods):
        if name in ("Return", "KP_Enter") and not mods:
            self.commit()
            return True
        if name in ("Return", "KP_Enter") and mods == {"ctrl"}:
            self.copy_answer(with_expr=True)
            return True
        if name in ("Up", "Down") and not mods:
            n = len(self.tape_items())
            if not n:
                return True
            if name == "Up":
                self.select_line(n - 1 if self.sel is None else max(0, self.sel - 1))
            elif self.sel is not None:
                self.select_line(None if self.sel + 1 >= n else self.sel + 1)
            return True
        if mods == {"ctrl"} and name == "c":
            if self.entry.get_selection_bounds():
                return False   # copying selected text in the box
            self.copy_answer()
            return True
        if mods == {"ctrl"} and name == "m":
            if self.sel is not None:
                h = self.tape_items()[self.sel]
                self.mem_raw = h.get("raw") or plain(h["ans"])
            elif self.live and self.live.get("raw"):
                self.mem_raw = self.live["raw"]
            elif self.ans_raw:
                self.mem_raw = self.ans_raw
            else:
                return True
            self.draw_mem()
            self.say(f"Stored {pretty(self.mem_raw, self.style)} in mem")
            return True
        if mods == {"ctrl"} and name == "l":
            if time.time() - self.clear_armed < 3:
                util.save_state(STATE, {"items": []})
                self.sel = None
                self.draw_tape()
                self.say("Tape cleared")
            else:
                self.clear_armed = time.time()
                self.say("Press Ctrl+L again to clear the tape", bad=True)
            return True
        if mods == {"alt"} and name in "1234" and len(name) == 1:
            _, _, forms = self.current_forms()
            i = int(name) - 1
            if i < len(forms):
                util.copy(forms[i][1])
                self.say(f"Copied {forms[i][1]}")
            return True
        return False

    # ============================================================ converter
    def unit_list(self, kind=None):
        kind = kind or self.kind
        if kind == "currency":
            return [(c, f"{c} · {CURRENCIES[c][0]}") for c in CURRENCIES]
        return [(u, f"{u.replace('^2', '²')} · {label}") for u, label in UNITS[kind]]

    def pair(self):
        if self.kind not in self.units:
            us = [u for u, _ in self.unit_list()]
            self.units[self.kind] = (us[min(5, len(us) - 1)] if self.kind != "temperature" else "°C",
                                     us[0] if self.kind != "temperature" else "°F")
        return self.units[self.kind]

    def pinned(self):
        p = util.load_state("ganit-pinned", {}).get("codes")
        return p if isinstance(p, list) else list(self.conf.get("currencies", PINNED))

    def show_value(self, v, unit):
        if v is None:
            return "?"
        if self.kind == "currency":
            return money(str(v), unit, self.style)
        return fmt_num(str(v), self.style, max_decimals=4) + " " + unit.replace("^2", "²")

    def convert_card(self):
        self.from_entry = self.to_entry = None
        a, b = self.pair()
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, vexpand=True)
        root.add_css_class("g-card")
        root.add_css_class(f"g-kind-{KIND_COLOR[self.kind]}")
        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10, vexpand=True)
        inner.add_css_class("g-left")
        kinds = Gtk.FlowBox(selection_mode=Gtk.SelectionMode.NONE, max_children_per_line=9, column_spacing=6,
                            row_spacing=6, homogeneous=False)
        for i, k in enumerate(KINDS, 1):
            b_ = Gtk.Button(can_focus=False)
            box = Gtk.Box(spacing=6)
            box.append(lbl(KIND_ICON[k], "glyph"))
            box.append(lbl(k.capitalize()))
            box.append(lbl(str(i), "g-num"))
            b_.set_child(box)
            b_.add_css_class("g-kind")
            b_.add_css_class(f"c-{KIND_COLOR[k]}")
            if k == self.kind:
                b_.add_css_class("g-on")
            b_.connect("clicked", lambda _b, k=k: self.set_kind(k))
            kinds.append(b_)
        inner.append(kinds)

        sides = Gtk.Box(spacing=12)
        self.from_entry, self.from_drop, from_box = self.side("FROM", a, "from")
        swap = Gtk.Button(label="⇄", can_focus=False, valign=Gtk.Align.CENTER)
        swap.add_css_class("g-swap")
        swap.set_tooltip_text("Swap (Ctrl+S)")
        swap.connect("clicked", lambda *_: self.swap())
        self.to_entry, self.to_drop, to_box = self.side("TO", b, "to")
        sides.append(from_box)
        sides.append(swap)
        sides.append(to_box)
        inner.append(sides)
        self.rate_label = lbl("", "g-rate", ellipsize=Pango.EllipsizeMode.END)
        inner.append(self.rate_label)

        low = Gtk.Box(spacing=12, vexpand=True)
        gridcol = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6, hexpand=True)
        head = Gtk.Box()
        head.append(lbl("IN EVERY " + ("PINNED CURRENCY" if self.kind == "currency" else self.kind.upper()),
                        "g-head", hexpand=True))
        head.append(lbl("click one to convert to it", "g-head-note", xalign=1))
        gridcol.append(head)
        scroll = Gtk.ScrolledWindow(vexpand=True)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.cells = Gtk.FlowBox(selection_mode=Gtk.SelectionMode.NONE, max_children_per_line=3,
                                 min_children_per_line=3, column_spacing=8, row_spacing=8, homogeneous=True,
                                 valign=Gtk.Align.START)
        scroll.set_child(self.cells)
        gridcol.append(scroll)
        low.append(gridcol)
        self.saved_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        sscroll = Gtk.ScrolledWindow(vexpand=True)
        sscroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        sscroll.set_child(self.saved_box)
        sbox = self.panel_card("SAVED", sscroll, note="Enter saves")
        sbox.set_size_request(250, -1)
        low.append(sbox)
        inner.append(low)
        root.append(inner)
        root.append(self.footer([("Enter", "save"), ("↑↓", "from / to"), ("Ctrl+S", "swap"),
                                 ("Alt+1..9", "kind"), ("Ctrl+C", "copy")]
                                + ([("Ctrl+P", "pin")] if self.kind == "currency" else [])))
        self.setting = True
        self.from_entry.set_text(self.amount)
        self.setting = False
        self.draw_saved()
        GLib.timeout_add(40, self.convert_now)   # once the card is on screen
        return root

    def side(self, title, unit, which):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4, hexpand=True)
        box.add_css_class("g-side")
        box.append(lbl(title, "g-head"))
        e = Gtk.Entry()
        e.add_css_class("g-amount")
        e.connect("changed", lambda *_: self.on_amount(which))
        focus = Gtk.EventControllerFocus()
        focus.connect("enter", lambda *_: self.set_editing(which))
        e.add_controller(focus)
        box.append(e)
        units = self.unit_list()
        drop = Gtk.DropDown.new_from_strings([label for _, label in units])
        drop.set_can_focus(False)
        drop.set_selected(max(0, [u for u, _ in units].index(unit)) if unit in [u for u, _ in units] else 0)
        drop.connect("notify::selected", lambda d, _p: self.on_unit(which, units[d.get_selected()][0]))
        box.append(drop)
        setattr(self, f"{which}_box", box)
        return e, drop, box

    def set_editing(self, which):
        self.editing = which
        for w in ("from", "to"):
            b = getattr(self, f"{w}_box", None)
            if b is not None:
                (b.add_css_class if w == which else b.remove_css_class)("g-focus")

    def set_kind(self, k):
        if k == self.kind:
            return
        self.kind = k
        self.amount = "1" if k == "currency" and not self.amount else self.amount
        if self.panel:
            self.panel.rebuild_card()

    def on_unit(self, which, unit):
        if self.setting:
            return
        a, b = self.pair()
        self.units[self.kind] = (unit, b) if which == "from" else (a, unit)
        self.convert_now()

    def on_amount(self, which):
        if self.setting:
            return
        self.editing = which
        if self.ctimer:
            GLib.source_remove(self.ctimer)
        self.ctimer = GLib.timeout_add(110, self.convert_now)

    def amount_of(self, entry):
        t = plain(entry.get_text().strip()).replace(" ", "")
        try:
            return str(Decimal(t)) if t else None
        except InvalidOperation:
            return None

    def convert_now(self):
        self.ctimer = None
        if getattr(self, "from_entry", None) is None or self.from_entry.get_root() is None:
            return False
        a, b = self.pair()
        src_entry, src_unit = (self.from_entry, a) if self.editing == "from" else (self.to_entry, b)
        num = self.amount_of(src_entry)
        self.cgen += 1
        gen, kind = self.cgen, self.kind
        if num is None:
            self.result = {}
            self.draw_cells()
            if src_entry.get_text().strip():
                self.say("Type a number: 100 · 2500.50 · 1,20,000", bad=True)
            return False
        targets = [u for u, _ in self.unit_list(kind)]
        if kind == "currency":
            shown = [c for c in self.pinned() if c in CURRENCIES]
            targets = list(dict.fromkeys([a, b] + shown))
        exprs = []
        for t in targets:
            if kind == "temperature" or kind == "currency":
                exprs.append(f"{num} {src_unit} to {t}")
            else:
                exprs.append(f"({num} {src_unit}) / (1 {t})")

        def work():
            return batch(exprs)

        def done(out):
            if gen != self.cgen or isinstance(out, Exception):
                return
            vals = {}
            for t, v in zip(targets, out):
                n = number_of(v) if v else None
                vals[t] = n
            vals[src_unit] = Decimal(num)
            self.result = vals
            self.after_convert(src_unit)
        self.background(work, done)
        return False

    def after_convert(self, src_unit):
        a, b = self.pair()
        other_entry, other_unit = (self.to_entry, b) if self.editing == "from" else (self.from_entry, a)
        v = self.result.get(other_unit)
        self.setting = True
        if v is not None:
            dec = (0 if other_unit in NO_DECIMALS else 2) if self.kind == "currency" else None
            other_entry.set_text(fmt_num(str(v), self.style, decimals=dec, max_decimals=None if dec is not None else 6))
        else:
            other_entry.set_text("")
        self.setting = False
        self.amount = plain(self.from_entry.get_text()) or self.amount
        self.draw_rate()
        self.draw_cells()
        self.say("")

    def draw_rate(self):
        a, b = self.pair()
        va, vb = self.result.get(a), self.result.get(b)
        if not va or vb is None:
            self.rate_label.set_text("")
            return
        r = vb / va
        txt = f"1 {a} = {rate_text(str(r))} {b}"
        if r:
            txt += f"     1 {b} = {rate_text(str(1 / r))} {a}"
        if self.kind == "currency":
            age = rates_age_text()
            txt += f"     rates {age}"
            self.rate_label.remove_css_class("g-old")
            if time.time() - rates_time() > STALE:
                self.rate_label.add_css_class("g-old")
                txt += " · Ctrl+R updates"
        self.rate_label.set_text(txt)

    def draw_cells(self):
        box = getattr(self, "cells", None)
        if box is None:
            return
        while (c := box.get_first_child()) is not None:
            box.remove(c)
        a, b = self.pair()
        pins = self.pinned()
        for u, label in self.unit_list():
            if u == a or u not in self.result:
                continue
            cell = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
            cell.add_css_class("g-cell")
            if u == b:
                cell.add_css_class("g-cell-to")
            cell.append(lbl(self.show_value(self.result[u], u), "g-cell-v", ellipsize=Pango.EllipsizeMode.END))
            name = label.split(" · ", 1)[1]
            pin = "  " if self.kind == "currency" and u in pins else ""
            cell.append(lbl(f"{pin}{name}{' · ' + u if self.kind == 'currency' else ''}", "g-cell-k",
                            ellipsize=Pango.EllipsizeMode.END))
            click = Gtk.GestureClick()
            click.connect("pressed", lambda *_x, u=u: self.pick_target(u))
            cell.add_controller(click)
            box.append(cell)

    def pick_target(self, u):
        a, _ = self.pair()
        self.units[self.kind] = (a, u)
        units = [x for x, _ in self.unit_list()]
        self.setting = True
        self.to_drop.set_selected(units.index(u))
        self.setting = False
        self.editing = "from"
        self.convert_now()

    def swap(self):
        a, b = self.pair()
        self.units[self.kind] = (b, a)
        to_text = self.to_entry.get_text()
        units = [x for x, _ in self.unit_list()]
        self.setting = True
        self.from_drop.set_selected(units.index(b))
        self.to_drop.set_selected(units.index(a))
        self.from_entry.set_text(to_text)
        self.setting = False
        self.editing = "from"
        self.convert_now()
        self.from_entry.grab_focus()
        self.from_entry.set_position(-1)

    def saved(self):
        return util.load_state(CONV_STATE, {"items": []})["items"]

    def draw_saved(self):
        box = self.saved_box
        while (c := box.get_first_child()) is not None:
            box.remove(c)
        items = self.saved()
        if not items:
            box.append(lbl("Enter keeps a conversion here.", "g-empty"))
        for it in items[:40]:
            row = Gtk.Box(spacing=8)
            row.add_css_class("g-saved")
            row.append(lbl(it["a"], "g-expr", hexpand=True, ellipsize=Pango.EllipsizeMode.END))
            row.append(lbl(it["b"], "g-ans-v", xalign=1))
            box.append(row)

    def save_conversion(self):
        a, b = self.pair()
        va, vb = self.result.get(a), self.result.get(b)
        if va is None or vb is None:
            return self.say("Type an amount first", bad=True)
        left = self.show_value(va, a) if self.kind != "currency" else money(str(va), a, self.style)
        right = self.show_value(vb, b)
        items = [{"a": left, "b": right, "t": time.time()}] + self.saved()
        util.save_state(CONV_STATE, {"items": items[:60]})
        self.remember(f"{plain(left)} to {b}", right, plain(right))
        self.draw_saved()
        self.say(f"Saved {left} = {right}")
        (self.from_entry if self.editing == "from" else self.to_entry).select_region(0, -1)   # the next amount replaces it

    def cycle_unit(self, step):
        which = self.editing
        a, b = self.pair()
        units = [x for x, _ in self.unit_list()]
        cur = a if which == "from" else b
        nxt = units[(units.index(cur) + step) % len(units)]
        (self.from_drop if which == "from" else self.to_drop).set_selected(units.index(nxt))

    def convert_key(self, name, mods):
        if name in ("Return", "KP_Enter") and not mods:
            self.save_conversion()
            return True
        if name in ("Up", "Down") and not mods:
            target = self.from_entry if name == "Up" else self.to_entry
            self.set_editing("from" if name == "Up" else "to")
            target.grab_focus()
            target.select_region(0, -1)
            return True
        if name in ("Up", "Down") and mods == {"alt"}:
            self.cycle_unit(-1 if name == "Up" else 1)
            return True
        if mods == {"alt"} and len(name) == 1 and name.isdigit() and name != "0":
            i = int(name) - 1
            if i < len(KINDS):
                self.set_kind(KINDS[i])
            return True
        if mods == {"ctrl"} and name == "s":
            self.swap()
            return True
        if mods == {"ctrl"} and name == "c":
            focus = self.to_entry if self.editing == "to" else self.from_entry
            if focus.get_selection_bounds():
                return False
            _, b = self.pair()
            v = self.result.get(b)
            if v is None:
                return True
            text = self.show_value(v, b)
            util.copy(text)
            self.say(f"Copied {text}")
            return True
        if mods == {"ctrl"} and name == "p" and self.kind == "currency":
            _, b = self.pair()
            pins = self.pinned()
            pins = [c for c in pins if c != b] if b in pins else pins + [b]
            util.save_state("ganit-pinned", {"codes": pins})
            self.say(f"{'Pinned' if b in pins else 'Unpinned'} {b}")
            self.convert_now()
            return True
        return False

    # ================================================================ keys
    def key(self, name, row, mods):
        if name in ("r", "R") and mods == {"ctrl"}:
            self.update_rates()
            return True
        if self.tab == "calc" and getattr(self, "entry", None) is not None:
            return self.calc_key(name, mods)
        if self.tab == "convert" and getattr(self, "from_entry", None) is not None:
            return self.convert_key(name, mods)
        return False
