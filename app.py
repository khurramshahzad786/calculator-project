"""Scientific Calculator - a Streamlit class project.

Run locally:  streamlit run app.py
Use the buttons or your keyboard (digits, + - * / ^ ( ) %, Enter, Backspace, Esc).
"""

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

# Display symbols -> Python syntax (order matters).
TO_PYTHON = [
    ("sin⁻¹", "asin"), ("cos⁻¹", "acos"), ("tan⁻¹", "atan"), ("log₂", "log2"),
    ("⁻¹", "**(-1)"), ("²", "**2"), ("³", "**3"), ("^", "**"), ("×", "*"), ("÷", "/"),
    ("−", "-"), ("%", "/100"), (" mod ", "%"), ("π", "pi"), ("√", "sqrt"), ("∛", "cbrt"),
    ("Ans", "ans"),
]
NUMBER = re.compile(r"\d+\.?\d*(?:E[+−]\d+)?")
LAST_TOKEN = re.compile(
    r"((?:sin⁻¹|cos⁻¹|tan⁻¹|sinh|cosh|tanh|sin|cos|tan|log₂|log|ln|abs|fact|10\^|e\^|√|∛)\(| mod |Ans|⁻¹)$"
)


class CalcError(Exception):
    pass


# ------------------------------------------------------------------
# Math
# ------------------------------------------------------------------
def math_functions(degrees, ans):
    """Names allowed inside an expression (all from the math module)."""
    to_rad = math.radians if degrees else float
    from_rad = math.degrees if degrees else float

    def trig(func):
        # Round tiny floating-point noise to 0, e.g. sin(180°) = 1.2e-16.
        return lambda x: 0.0 if abs(func(to_rad(x))) < 1e-12 else func(to_rad(x))

    def tan(x):
        if degrees and (x - 90) % 180 == 0:
            raise ValueError("tan undefined")
        return trig(math.tan)(x)

    def fact(x):
        if x < 0 or x != int(x):
            raise ValueError("factorial needs a whole number ≥ 0")
        if x > 170:
            raise OverflowError
        return float(math.factorial(int(x)))

    return {
        "sin": trig(math.sin), "cos": trig(math.cos), "tan": tan,
        "asin": lambda x: from_rad(math.asin(x)), "acos": lambda x: from_rad(math.acos(x)),
        "atan": lambda x: from_rad(math.atan(x)),
        "sinh": math.sinh, "cosh": math.cosh, "tanh": math.tanh,
        "log": math.log10, "ln": math.log, "log2": math.log2,
        "sqrt": math.sqrt, "cbrt": math.cbrt, "abs": math.fabs, "fact": fact,
        "pi": math.pi, "e": math.e, "ans": ans,
    }


def to_python(expr):
    """Turn the display text (e.g. '2π×sin(30)') into Python code."""
    expr += ")" * (expr.count("(") - expr.count(")"))  # close open brackets
    # Implicit multiplication: 2π, 3sin(30), (1+2)(3), π2
    expr = re.sub(r"(?<=[\d)πe²³])(?=[(πe√∛a-zA])", "×", expr)
    expr = re.sub(r"(?<=[)πe²³])(?=\d)", "×", expr)
    # Every number becomes a float so huge powers raise OverflowError instead of hanging.
    expr = NUMBER.sub(lambda m: repr(float(m.group().replace("E", "e").replace("−", "-"))), expr)
    for symbol, python in TO_PYTHON:
        expr = expr.replace(symbol, python)
    return expr


def calculate(expr, degrees, ans):
    try:
        value = eval(to_python(expr), {"__builtins__": {}}, math_functions(degrees, ans))
    except ZeroDivisionError:
        raise CalcError("Cannot divide by zero")
    except OverflowError:
        raise CalcError("Overflow")
    except (ValueError, TypeError):
        raise CalcError("Math error")
    except (SyntaxError, NameError):
        raise CalcError("Syntax error")
    if not isinstance(value, (int, float, complex)):  # e.g. "()"
        raise CalcError("Syntax error")
    if isinstance(value, complex) or math.isnan(value):
        raise CalcError("Math error")
    if math.isinf(value):
        raise CalcError("Overflow")
    return float(value)


def format_number(value):
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

    if s.error:  # any new input clears the error message
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


ACTIONS = {"clear": clear, "ce": clear_entry, "back": backspace, "neg": negate,
           "deg": toggle_degrees, "equals": equals}

# ------------------------------------------------------------------
# Keyboard: a tiny JavaScript component that sends key presses to Python.
# Keys are numbered so fast typing never loses or repeats a key.
# ------------------------------------------------------------------
KEYBOARD_JS = """
const KEYS = {
  "+": "add", "-": "sub", "*": "mul", "/": "div", "^": "pow", "%": "pct",
  "(": "lpar", ")": "rpar", ".": "dot", ",": "dot", "!": "fact",
  "Enter": "equals", "=": "equals", "Backspace": "back", "Delete": "ce", "Escape": "clear",
  "s": "sin", "c": "cos", "t": "tan", "l": "log", "n": "ln", "r": "sqrt", "p": "pi", "e": "e",
};
export default function ({ setStateValue }) {
  const state = (window.calcKeys ??= { count: 0, keys: [] });
  function onKey(event) {
    if (event.ctrlKey || event.altKey || event.metaKey) return;
    const key = /^[0-9]$/.test(event.key) ? event.key : KEYS[event.key];
    if (!key) return;
    event.preventDefault();
    state.count += 1;
    state.keys = [...state.keys.slice(-30), [state.count, key]];
    setStateValue("keys", state.keys);
  }
  document.addEventListener("keydown", onKey, true);
  return () => document.removeEventListener("keydown", onKey, true);
}
"""
keyboard = st.components.v2.component("calculator_keyboard", js=KEYBOARD_JS)

# ------------------------------------------------------------------
# Page style
# ------------------------------------------------------------------
CSS = """
<style>
.st-key-keyboard { display: none; }
.st-key-calc {
  background: linear-gradient(160deg, #1e293b, #0f172a);
  border-radius: 24px; padding: 20px;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, .5);
}
.display {
  background: #050816; border: 1px solid #312e81; border-radius: 16px;
  padding: 12px 20px; text-align: right; font-family: Consolas, monospace; min-height: 130px;
}
.display .mode { text-align: left; font-size: .75rem; font-weight: 700; color: #a5b4fc; }
.display .last { color: #94a3b8; min-height: 1.4rem; overflow-wrap: anywhere; }
.display .main { color: #f8fafc; font-size: 2.6rem; font-weight: 600; overflow-wrap: anywhere; }
.display .main.small { font-size: 1.6rem; }
.display .main.error { color: #fda4af; font-size: 1.8rem; }
.display .preview { color: #a5b4fc; min-height: 1.4rem; }
.st-key-left, .st-key-right, .st-key-calc [data-testid="stHorizontalBlock"] { gap: 10px !important; }
.st-key-calc [data-testid="stColumn"] { min-width: 0; }
.st-key-calc button {
  width: 100%; min-width: 0; padding: 0 4px;
  height: 52px; border-radius: 14px; border: 1px solid #334155;
  background: #1e2538; color: #e2e8f0; transition: transform .08s;
}
.st-key-calc button:hover { border-color: #818cf8; color: #fff; }
.st-key-calc button:active { transform: scale(.95); }
.st-key-right button { height: 64px; background: #283048; }
.st-key-right button p { font-size: 1.4rem; font-weight: 600; }
.st-key-b_add button, .st-key-b_sub button, .st-key-b_mul button, .st-key-b_div button {
  background: #3730a3; border-color: #4f46e5; }
.st-key-b_clear button, .st-key-b_ce button, .st-key-b_back button {
  background: #7f1d1d; border-color: #b91c1c; }
.st-key-b_equals button { background: linear-gradient(135deg, #6366f1, #a855f7); border: none; }
.st-key-b_deg button p { color: #fcd34d; font-weight: 700; }
</style>
"""


# ------------------------------------------------------------------
# Page
# ------------------------------------------------------------------
def draw_keys(rows, container_key):
    with st.container(key=container_key, gap=None):
        for row in rows:
            for column, (key, label) in zip(st.columns(len(row), gap=None, wrap=False), row):
                if key == "deg":
                    label = "DEG" if st.session_state.degrees else "RAD"
                column.button(label, key=f"b_{key}", on_click=press, args=(key,), width="stretch")


def main():
    st.set_page_config(page_title="Scientific Calculator", page_icon="🧮")
    st.html(CSS)
    s = st.session_state
    for name, value in {"expr": "", "last": "", "error": "", "done": False,
                        "ans": 0.0, "degrees": True, "keys_seen": 0}.items():
        s.setdefault(name, value)

    # Apply keyboard presses that have not been handled yet.
    keys = keyboard(key="keyboard", on_keys_change=lambda: None).get("keys") or []
    for number, key in keys:
        if number > s.keys_seen:
            s.keys_seen = number
            press(key)

    st.title("🧮 Scientific Calculator")
    st.caption("Click the buttons or type on your keyboard. Press Enter to calculate.")

    text = s.error or s.expr or "0"
    size = "error" if s.error else ("small" if len(text) > 16 else "")
    preview = ""
    if s.expr and not s.done and not s.error and not re.fullmatch(r"[\d.]+", s.expr):
        try:
            preview = "= " + format_number(calculate(s.expr, s.degrees, s.ans))
        except CalcError:
            pass

    with st.container(key="calc"):
        st.html(
            f'<div class="display"><div class="mode">{"DEG" if s.degrees else "RAD"}</div>'
            f'<div class="last">{s.last}</div><div class="main {size}">{text}</div>'
            f'<div class="preview">{preview}</div></div>'
        )
        left, right = st.columns([5, 4])
        with left:
            draw_keys(SCIENTIFIC_KEYS, "left")
        with right:
            draw_keys(NUMBER_KEYS, "right")


main()
