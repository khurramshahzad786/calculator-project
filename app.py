"""Scientific Calculator - a Streamlit class project by Khurram Shahzad.

Run locally:  streamlit run app.py
Use the buttons or your keyboard (digits, numpad, + - * / ^ ( ) %, Enter, Backspace, Esc).
"""

import ast
import math
import re

import streamlit as st

# ------------------------------------------------------------------
# Buttons: (id, label). The id is also used for keyboard input.
# ------------------------------------------------------------------
SCIENTIFIC_KEYS = [
    [("deg", "DEG"), ("lpar", "("), ("rpar", ")"), ("pct", "%"), ("mod", "mod")],
    [("sin", "sin"), ("cos", "cos"), ("tan", "tan"), ("pi", "π"), ("e", "e")],
    [("asin", "sin⁻¹"), ("acos", "cos⁻¹"), ("atan", "tan⁻¹"), ("fact", "n!"), ("abs", "|x|")],
    [("sinh", "sinh"), ("cosh", "cosh"), ("tanh", "tanh"), ("inv", "1/x"), ("ans", "Ans")],
    [("sq", "x²"), ("cube", "x³"), ("pow", "xʸ"), ("sqrt", "√x"), ("cbrt", "∛x")],
    [("log", "log"), ("ln", "ln"), ("log2", "log₂"), ("pow10", "10ˣ"), ("exp", "eˣ")],
]
NUMBER_KEYS = [
    [("clear", "C"), ("ce", "CE"), ("back", "⌫"), ("div", "÷")],
    [("7", "7"), ("8", "8"), ("9", "9"), ("mul", "×")],
    [("4", "4"), ("5", "5"), ("6", "6"), ("sub", "−")],
    [("1", "1"), ("2", "2"), ("3", "3"), ("add", "+")],
    [("neg", "±"), ("0", "0"), ("dot", "."), ("equals", "=")],
]

# Text each key adds to the expression.
TOKENS = {str(d): str(d) for d in range(10)} | {
    "dot": ".", "add": "+", "sub": "−", "mul": "×", "div": "÷", "pow": "^", "mod": " mod ",
    "sq": "²", "cube": "³", "inv": "⁻¹", "pct": "%",
    "sin": "sin(", "cos": "cos(", "tan": "tan(", "asin": "sin⁻¹(", "acos": "cos⁻¹(",
    "atan": "tan⁻¹(", "sinh": "sinh(", "cosh": "cosh(", "tanh": "tanh(",
    "log": "log(", "ln": "ln(", "log2": "log₂(", "sqrt": "√(", "cbrt": "∛(",
    "abs": "abs(", "fact": "fact(", "pow10": "10^(", "exp": "e^(",
    "pi": "π", "e": "e", "ans": "Ans", "lpar": "(", "rpar": ")",
}
OPERATORS = ("+", "−", "×", "÷", "^", " mod ")
# After a result, these keys keep calculating with it; all other keys start fresh.
CONTINUE_KEYS = {"add", "sub", "mul", "div", "pow", "mod", "sq", "cube", "inv", "pct"}
HISTORY_SIZE = 50

# Display symbols -> Python syntax (order matters).
TO_PYTHON = [
    ("sin⁻¹", "asin"), ("cos⁻¹", "acos"), ("tan⁻¹", "atan"), ("log₂", "log2"),
    ("⁻¹", "**(-1)"), ("²", "**2"), ("³", "**3"), ("^", "**"), ("×", "*"), ("÷", "/"),
    ("−", "-"), ("%", "/100"), (" mod ", "%"), ("π", "pi"), ("√", "sqrt"), ("∛", "cbrt"),
    ("∞", "inf"), ("Ans", "ans"),
]
NUMBER = re.compile(r"\d+\.?\d*(?:E[+−]\d+)?")
LAST_TOKEN = re.compile(
    r"((?:sin⁻¹|cos⁻¹|tan⁻¹|sinh|cosh|tanh|sin|cos|tan|log₂|log|ln|abs|fact|10\^|e\^|√|∛)\(| mod |Ans|⁻¹)$"
)
# Only plain arithmetic and function calls may appear in an expression.
ALLOWED_NODES = (
    ast.Expression, ast.BinOp, ast.UnaryOp, ast.Call, ast.Name, ast.Load, ast.Constant,
    ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod, ast.Pow, ast.UAdd, ast.USub,
)
SAFE_OPERATORS = {ast.Div: "_div", ast.Mod: "_mod", ast.Pow: "_pow"}


class CalcError(Exception):
    """The expression has no real-number result; the message is shown on the display."""


# ------------------------------------------------------------------
# Math
# ------------------------------------------------------------------
def math_functions(degrees, ans, flags):
    """Names allowed inside an expression, built on the math module.

    Limits are shown as ∞ instead of errors: 5÷0 = ∞, tan(90°) = ∞, log(0) = −∞.
    """

    def infinity(sign=1.0):
        flags["infinite"] = True  # a real infinity, not a number that was too large
        return math.copysign(math.inf, sign)

    def clean(value):
        return 0.0 if abs(value) < 1e-12 else value  # e.g. sin(180°) = 1.2e-16 → 0

    def to_radians(x):
        if math.isinf(x):
            raise CalcError("Undefined")
        return math.radians(x) if degrees else x

    def sin(x):
        return clean(math.sin(to_radians(x)))

    def cos(x):
        return clean(math.cos(to_radians(x)))

    def tan(x):
        angle = to_radians(x)
        if clean(math.cos(angle)) == 0:  # tan(90°) = ∞, tan(270°) = −∞
            return infinity(math.sin(angle))
        return clean(math.tan(angle))

    def inverse(func):
        return lambda x: math.degrees(func(x)) if degrees else func(x)

    def logarithm(func):
        return lambda x: infinity(-1) if x == 0 else func(x)  # log(0) = −∞

    def fact(x):
        if math.isinf(x):
            return infinity()
        if x < 0 and x == int(x):
            raise CalcError("Undefined")
        if x > 170:
            raise OverflowError
        return float(math.factorial(int(x))) if x == int(x) else math.gamma(x + 1)

    def div(a, b):
        if b == 0:
            if a == 0:
                raise CalcError("Undefined")  # 0 ÷ 0
            return infinity(a)  # 5 ÷ 0 = ∞, −5 ÷ 0 = −∞
        return a / b

    def mod(a, b):
        if b == 0:
            raise CalcError("Undefined")
        return a % b

    def power(a, b):
        if a == 0 and b < 0:
            return infinity()  # 0⁻¹ = ∞
        if a < 0 and math.isfinite(b) and b != int(b):
            root = 1 / b
            if abs(root - round(root)) < 1e-9 and round(root) % 2 == 1:
                return -math.pow(-a, b)  # odd roots of negatives are real: (−8)^(1/3) = −2
            raise CalcError("Not a real number")
        return math.pow(a, b)

    return {
        "sin": sin, "cos": cos, "tan": tan,
        "asin": inverse(math.asin), "acos": inverse(math.acos), "atan": inverse(math.atan),
        "sinh": math.sinh, "cosh": math.cosh, "tanh": math.tanh,
        "log": logarithm(math.log10), "ln": logarithm(math.log), "log2": logarithm(math.log2),
        "sqrt": math.sqrt, "cbrt": math.cbrt, "abs": math.fabs, "fact": fact,
        "pi": math.pi, "e": math.e, "inf": math.inf, "ans": ans,
        "_div": div, "_mod": mod, "_pow": power,
    }


def to_python(expr):
    """Turn the display text (e.g. '2π×sin(30)') into Python code."""
    expr += ")" * (expr.count("(") - expr.count(")"))  # close open brackets
    # Implicit multiplication: 2π, 3sin(30), (1+2)(3), π2
    expr = re.sub(r"(?<=[\d)πe²³∞])(?=[(πe√∛∞a-zA])", "×", expr)
    expr = re.sub(r"(?<=[)πe²³∞])(?=\d)", "×", expr)
    # Every number becomes a float so huge powers stop with OverflowError instead of hanging.
    expr = NUMBER.sub(lambda m: repr(float(m.group().replace("E", "e").replace("−", "-"))), expr)
    for symbol, python in TO_PYTHON:
        expr = expr.replace(symbol, python)
    return expr


class UseSafeOperators(ast.NodeTransformer):
    """Replace a / b, a % b and a ** b with the functions above, which handle 0 and ∞."""

    def visit_BinOp(self, node):
        self.generic_visit(node)
        name = SAFE_OPERATORS.get(type(node.op))
        if name is None:
            return node
        return ast.Call(func=ast.Name(name, ast.Load()), args=[node.left, node.right], keywords=[])


def calculate(expr, degrees, ans):
    try:
        tree = ast.parse(to_python(expr), mode="eval")
    except SyntaxError:
        raise CalcError("Invalid expression") from None
    if not all(isinstance(node, ALLOWED_NODES) for node in ast.walk(tree)):
        raise CalcError("Invalid expression")
    tree = ast.fix_missing_locations(UseSafeOperators().visit(tree))
    flags = {"infinite": "∞" in expr or ("Ans" in expr and math.isinf(ans))}
    names = math_functions(degrees, ans, flags)
    try:
        value = eval(compile(tree, "<calculator>", "eval"), {"__builtins__": {}}, names)
    except OverflowError:
        raise CalcError("Number too large") from None
    except ValueError:  # math domain error, e.g. √(−1), log(−5), sin⁻¹(2)
        raise CalcError("Not a real number") from None
    except (TypeError, NameError):
        raise CalcError("Invalid expression") from None
    if math.isnan(value):  # e.g. ∞ − ∞, 0 × ∞
        raise CalcError("Undefined")
    if math.isinf(value) and not flags["infinite"]:
        raise CalcError("Number too large")  # e.g. 10^300 × 10^300
    return float(value)


def format_number(value):
    if math.isinf(value):
        return "∞" if value > 0 else "−∞"
    if value == 0:
        return "0"
    if value.is_integer() and abs(value) < 1e15:
        text = str(int(value))
    else:
        text = f"{value:.12g}".replace("e", "E")
    return text.replace("-", "−")


# ------------------------------------------------------------------
# Key presses
# ------------------------------------------------------------------
def press(key):
    s = st.session_state
    if key in ACTIONS:
        ACTIONS[key](s)
        return
    if key not in TOKENS:
        return
    token = TOKENS[key]

    if s.error:  # any new input clears the message
        s.expr, s.error = "", ""
    if s.done:  # a result is on the display
        s.done = False
        if key not in CONTINUE_KEYS:
            s.expr = ""
        elif s.expr.startswith("−") and key in ("pow", "sq", "cube", "inv"):
            s.expr = f"({s.expr})"

    trailing_number = re.search(r"[\d.]*$", s.expr).group()
    if token in OPERATORS:
        for op in OPERATORS:  # pressing a new operator replaces the previous one
            if s.expr.endswith(op) and token != "−":
                s.expr = s.expr[: -len(op)]
                break
        if not s.expr and token != "−":
            s.expr = "0"
    elif key == "dot":
        if "." in trailing_number:
            return
        if not trailing_number:
            token = "0."
    elif key.isdigit() and trailing_number == "0":
        s.expr = s.expr[:-1]  # replace a leading zero
    s.expr += token


def clear(s):
    s.expr, s.last, s.error, s.done = "", "", "", False


def clear_entry(s):
    if s.done or s.error:
        clear(s)
    elif re.search(r"[\d.]+$", s.expr):
        s.expr = re.sub(r"[\d.]+$", "", s.expr)
    else:
        backspace(s)


def backspace(s):
    if s.error:
        s.error = ""  # go back to editing the expression
        return
    s.done = False
    match = LAST_TOKEN.search(s.expr)
    s.expr = s.expr[: match.start()] if match else s.expr[:-1]


def negate(s):
    if s.error:
        return
    if s.done:
        s.ans = -s.ans
        s.expr = format_number(s.ans)
    elif s.expr.startswith("−(") and s.expr.endswith(")"):
        s.expr = s.expr[2:-1]
    elif s.expr:
        s.expr = f"−({s.expr})"
    else:
        s.expr = "−"


def toggle_degrees(s):
    s.degrees = not s.degrees


def equals(s):
    if not s.expr or s.done or s.error:
        return
    closed = s.expr + ")" * (s.expr.count("(") - s.expr.count(")"))
    s.last = closed + " ="
    try:
        s.ans = calculate(s.expr, s.degrees, s.ans)
    except CalcError as error:
        s.error = str(error)
        return
    s.expr = format_number(s.ans)
    s.done = True
    s.history.insert(0, (closed, s.expr, s.ans))
    del s.history[HISTORY_SIZE:]


def use_history(index):
    """Put a previous result back on the display to keep calculating with it."""
    s = st.session_state
    equation, result, value = s.history[index]
    s.expr, s.ans, s.last, s.error, s.done = result, value, equation + " =", "", True


def clear_history():
    st.session_state.history = []


ACTIONS = {"clear": clear, "ce": clear_entry, "back": backspace, "neg": negate,
           "deg": toggle_degrees, "equals": equals}

# ------------------------------------------------------------------
# Keyboard: a small JavaScript component that sends key presses to Python.
# - Takes keyboard focus as soon as the page opens (no click needed).
# - Also listens on the outer page when the app is embedded (Streamlit Cloud).
# - Keys are numbered so fast typing never loses or repeats a key.
# ------------------------------------------------------------------
KEYBOARD_JS = """
const KEYS = {
  "+": "add", "-": "sub", "*": "mul", "/": "div", "^": "pow", "%": "pct",
  "(": "lpar", ")": "rpar", ".": "dot", ",": "dot", "!": "fact",
  "Enter": "equals", "=": "equals", "Backspace": "back", "Delete": "ce", "Escape": "clear",
  "s": "sin", "c": "cos", "t": "tan", "l": "log", "n": "ln", "r": "sqrt", "p": "pi", "e": "e",
};
const NUMPAD = {  // by physical key, so the numpad works even with Num Lock off
  NumpadDecimal: "dot", NumpadAdd: "add", NumpadSubtract: "sub",
  NumpadMultiply: "mul", NumpadDivide: "div", NumpadEnter: "equals",
};

export default function ({ setStateValue }) {
  const state = (window.calcKeys ??= { count: 0, keys: [] });

  const docs = [document];  // this page plus any same-site page that embeds it
  try {
    for (let w = window; w !== w.parent; w = w.parent) docs.push(w.parent.document);
  } catch (e) { /* the outer page belongs to another site: listen on this page only */ }

  function showStatus() {
    const active = docs.some((d) => d.hasFocus());
    document.documentElement.dataset.keyboard = active ? "on" : "off";
  }

  function grabFocus() {
    const app = document.querySelector('[data-testid="stApp"]') || document.body;
    app.setAttribute("tabindex", "-1");
    if (!docs.some((d) => d.hasFocus())) {
      try { window.focus(); app.focus({ preventScroll: true }); } catch (e) {}
    }
    showStatus();
  }

  function flash(key) {
    const button = document.querySelector(`.st-key-b_${key} button`);
    if (!button) return;
    button.classList.add("pressed");
    setTimeout(() => button.classList.remove("pressed"), 140);
  }

  function onKey(event) {
    if (event.ctrlKey || event.altKey || event.metaKey) return;
    const pad = /^Numpad([0-9])$/.exec(event.code);
    const key = pad ? pad[1]
      : NUMPAD[event.code] ?? (/^[0-9]$/.test(event.key) ? event.key : KEYS[event.key]);
    if (!key) return;
    event.preventDefault();
    state.count += 1;
    state.keys = [...state.keys.slice(-30), [state.count, key]];
    setStateValue("keys", state.keys);
    flash(key);
  }

  for (const d of docs) {
    d.addEventListener("keydown", onKey, true);
    d.defaultView.addEventListener("focus", showStatus);
    d.defaultView.addEventListener("blur", showStatus);
  }
  grabFocus();
  const timer = setTimeout(grabFocus, 400);

  return () => {
    clearTimeout(timer);
    for (const d of docs) {
      d.removeEventListener("keydown", onKey, true);
      d.defaultView.removeEventListener("focus", showStatus);
      d.defaultView.removeEventListener("blur", showStatus);
    }
  };
}
"""
keyboard = st.components.v2.component("calculator_keyboard", js=KEYBOARD_JS)

# ------------------------------------------------------------------
# Page style
# ------------------------------------------------------------------
CSS = """
<style>
:root { --key: 46px; --gap: 8px; }
.stApp {
  background: radial-gradient(900px 500px at 15% -10%, #312e81 0%, transparent 60%),
              radial-gradient(800px 500px at 110% 110%, #4c1d95 0%, transparent 55%), #0b1020;
}
[data-testid="stApp"]:focus { outline: none; }
[data-testid="stHeader"] { background: transparent; }
[data-testid="stMainBlockContainer"] { max-width: 1180px; padding: 1.1rem 1.5rem 1rem; }
.st-key-keyboard { display: none; }

/* header */
.app-head { display: flex; align-items: center; gap: 12px; }
.app-head .logo {
  width: 40px; height: 40px; border-radius: 12px; display: grid; place-items: center;
  font-size: 1.3rem; background: linear-gradient(135deg, #6366f1, #a855f7);
  box-shadow: 0 6px 18px -4px rgba(139, 92, 246, .7);
}
.app-head .title {
  font-size: 1.35rem; font-weight: 700; line-height: 1.15; letter-spacing: -.01em;
  background: linear-gradient(90deg, #e0e7ff, #c4b5fd 60%, #f0abfc);
  -webkit-background-clip: text; background-clip: text; color: transparent;
}
.app-head .by { font-size: .8rem; color: #94a3b8; }

/* cards */
.st-key-calc, .st-key-hist {
  background: linear-gradient(160deg, rgba(30, 41, 59, .92), rgba(15, 23, 42, .95));
  border: 1px solid rgba(148, 163, 184, .15); border-radius: 22px; padding: 16px;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, .6); gap: 12px;
}

/* display */
.display {
  background: linear-gradient(180deg, #050816, #0b1124); border: 1px solid rgba(129, 140, 248, .3);
  border-radius: 16px; padding: 10px 18px; text-align: right; height: 112px;
  font-family: "Cascadia Code", Consolas, monospace; display: flex; flex-direction: column;
  justify-content: space-between; box-shadow: inset 0 2px 10px rgba(0, 0, 0, .6);
}
.display .chips { display: flex; gap: 6px; font-family: system-ui, sans-serif; }
.display .chip {
  font-size: .68rem; font-weight: 700; letter-spacing: .05em; padding: 1px 8px;
  border-radius: 99px; color: #c7d2fe; background: rgba(129, 140, 248, .18);
  border: 1px solid rgba(129, 140, 248, .45);
}
.display .chip.kbd { color: #86efac; background: rgba(34, 197, 94, .12); border-color: rgba(34, 197, 94, .4); }
.display .chip.kbd .off { display: none; }
html[data-keyboard="off"] .display .chip.kbd { color: #fcd34d; background: rgba(250, 204, 21, .1);
  border-color: rgba(250, 204, 21, .4); }
html[data-keyboard="off"] .display .chip.kbd .on { display: none; }
html[data-keyboard="off"] .display .chip.kbd .off { display: inline; }
.display .last { color: #94a3b8; font-size: .9rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.display .main { color: #f8fafc; font-size: 2.3rem; font-weight: 600; line-height: 1.1;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis; direction: ltr; }
.display .main.small { font-size: 1.6rem; }
.display .main.tiny { font-size: 1.15rem; }
.display .main.msg { color: #fda4af; font-size: 1.6rem; }
.display .preview { color: #a5b4fc; font-size: .9rem; min-height: 1.1rem; }

/* keys */
.st-key-left, .st-key-right, .st-key-calc [data-testid="stHorizontalBlock"] { gap: var(--gap) !important; }
.st-key-calc [data-testid="stColumn"] { min-width: 0; }
.st-key-calc button {
  width: 100%; min-width: 0; min-height: 0; height: var(--key); padding: 0 4px;
  border-radius: 13px; border: 1px solid rgba(148, 163, 184, .16);
  background: linear-gradient(180deg, #1f2740, #182033); color: #cbd5e1;
  box-shadow: 0 3px 8px -3px rgba(0, 0, 0, .6), inset 0 1px 0 rgba(255, 255, 255, .04);
  transition: transform .08s, border-color .15s, box-shadow .15s;
}
.st-key-calc button p { font-size: .95rem; }
.st-key-calc button:hover { border-color: #818cf8; color: #fff; transform: translateY(-1px); }
.st-key-calc button:focus:not(:focus-visible) { box-shadow: 0 3px 8px -3px rgba(0, 0, 0, .6); }
.st-key-calc button:active, .st-key-calc button.pressed {
  transform: scale(.95); border-color: #a5b4fc; box-shadow: 0 0 0 3px rgba(129, 140, 248, .35);
}
.st-key-right button { height: calc((6 * var(--key) + var(--gap)) / 5); background: linear-gradient(180deg, #2a3350, #222a43); color: #f1f5f9; }
.st-key-right button p { font-size: 1.35rem; font-weight: 600; }
.st-key-b_add button, .st-key-b_sub button, .st-key-b_mul button, .st-key-b_div button {
  background: linear-gradient(180deg, #4338ca, #3730a3); border-color: #6366f1; color: #e0e7ff; }
.st-key-b_clear button, .st-key-b_ce button, .st-key-b_back button {
  background: linear-gradient(180deg, #9f1239, #7f1d1d); border-color: #e11d48; color: #ffe4e6; }
.st-key-b_equals button {
  background: linear-gradient(135deg, #6366f1, #a855f7 60%, #d946ef); border: none; color: #fff;
  box-shadow: 0 8px 20px -6px rgba(168, 85, 247, .8); }
.st-key-b_deg button { border-color: rgba(250, 204, 21, .45); }
.st-key-b_deg button p { color: #fcd34d; font-weight: 700; }

/* history */
.hist-title { color: #e2e8f0; font-weight: 700; font-size: 1rem; padding-top: 4px; }
.hist-empty { color: #64748b; font-size: .85rem; text-align: center; padding-top: 40px; }
.st-key-hist_clear button {
  min-height: 0; height: 30px; padding: 0 10px; border-radius: 10px; background: transparent;
  border: 1px solid rgba(251, 113, 133, .4); color: #fda4af; }
.st-key-hist_clear button p { font-size: .8rem; }
.st-key-hist_list { gap: 6px; }
.st-key-hist_list button {
  min-height: 0; padding: 6px 12px; border-radius: 12px; justify-content: flex-end;
  background: rgba(255, 255, 255, .03); border: 1px solid rgba(148, 163, 184, .12);
  color: #94a3b8; font-family: "Cascadia Code", Consolas, monospace; text-align: right;
}
.st-key-hist_list button p { font-size: .82rem; text-align: right; overflow-wrap: anywhere; }
.st-key-hist_list button strong { color: #f1f5f9; font-size: 1rem; }
.st-key-hist_list button:hover { border-color: #818cf8; background: rgba(129, 140, 248, .08); }
</style>
"""


# ------------------------------------------------------------------
# Page
# ------------------------------------------------------------------
def markdown_text(text):
    """Escape characters that Markdown would treat as formatting in button labels."""
    return re.sub(r"([\\`*_{}\[\]()#+\-.!|>~])", r"\\\1", text)


def draw_keys(rows, container_key):
    with st.container(key=container_key, gap=None):
        for row in rows:
            for column, (key, label) in zip(st.columns(len(row), gap=None, wrap=False), row):
                if key == "deg":
                    label = "DEG" if st.session_state.degrees else "RAD"
                column.button(label, key=f"b_{key}", on_click=press, args=(key,), width="stretch")


def draw_display(s):
    text = s.error or s.expr or "0"
    size = "msg" if s.error else ("tiny" if len(text) > 30 else "small" if len(text) > 18 else "")
    preview = ""
    if s.expr and not s.done and not s.error and not re.fullmatch(r"[\d.]+", s.expr):
        try:
            preview = "= " + format_number(calculate(s.expr, s.degrees, s.ans))
        except CalcError:
            pass
    st.html(
        '<div class="display"><div class="chips">'
        f'<span class="chip">{"DEG" if s.degrees else "RAD"}</span>'
        '<span class="chip kbd"><span class="on">⌨ Keyboard on</span>'
        '<span class="off">⌨ Click page to type</span></span></div>'
        f'<div class="last">{s.last or "&nbsp;"}</div>'
        f'<div class="main {size}">{text}</div>'
        f'<div class="preview">{preview}</div></div>'
    )


def draw_history(s):
    with st.container(key="hist"):
        title, button = st.columns([3, 2], vertical_alignment="center")
        title.html('<div class="hist-title">🕘 History</div>')
        if s.history:
            button.button("Clear", key="hist_clear", on_click=clear_history, width="stretch")
        with st.container(key="hist_list", height=402, border=False):
            if not s.history:
                st.html('<div class="hist-empty">No calculations yet.<br>Results will appear here.</div>')
            for index, (equation, result, _) in enumerate(s.history):
                label = f"{markdown_text(equation)} =  \n**{markdown_text(result)}**"
                st.button(label, key=f"h_{index}", on_click=use_history, args=(index,),
                          help="Use this result", width="stretch")


def main():
    st.set_page_config(page_title="Scientific Calculator", page_icon="🧮", layout="wide")
    st.html(CSS)
    s = st.session_state
    for name, value in {"expr": "", "last": "", "error": "", "done": False, "ans": 0.0,
                        "degrees": True, "keys_seen": 0, "history": []}.items():
        s.setdefault(name, value)

    # Apply keyboard presses that have not been handled yet.
    keys = keyboard(key="keyboard", on_keys_change=lambda: None).get("keys") or []
    for number, key in keys:
        if number > s.keys_seen:
            s.keys_seen = number
            press(key)

    st.html(
        '<div class="app-head"><div class="logo">🧮</div><div>'
        '<div class="title">Scientific Calculator</div>'
        '<div class="by">by Khurram Shahzad</div></div></div>'
    )

    calculator, history = st.columns([3.2, 1.25], gap="medium")
    with calculator, st.container(key="calc"):
        draw_display(s)
        left, right = st.columns([5, 4], gap="small")
        with left:
            draw_keys(SCIENTIFIC_KEYS, "left")
        with right:
            draw_keys(NUMBER_KEYS, "right")
    with history:
        draw_history(s)


main()
