"""Streamlit front end for the scientific calculator.

Run with:  streamlit run app.py
"""

from html import escape
from pathlib import Path

import streamlit as st

from calculator import Calculator

ASSETS = Path(__file__).parent / "assets"

# (key id, label) rows. Key ids are the actions understood by Calculator.press.
SCIENTIFIC_KEYS = [
    [("angle", None), ("mc", "MC"), ("mr", "MR"), ("mplus", "M+"), ("mminus", "M−")],
    [("sin", "sin"), ("cos", "cos"), ("tan", "tan"), ("pi", "π"), ("e", "e")],
    [("asin", "sin⁻¹"), ("acos", "cos⁻¹"), ("atan", "tan⁻¹"), ("lparen", "("), ("rparen", ")")],
    [("sinh", "sinh"), ("cosh", "cosh"), ("tanh", "tanh"), ("sq", "x²"), ("cube", "x³")],
    [("pow", "xʸ"), ("sqrt", "√x"), ("cbrt", "∛x"), ("pow10", "10ˣ"), ("exp_e", "eˣ")],
    [("log", "log"), ("ln", "ln"), ("log2", "log₂"), ("inv", "1/x"), ("fact", "n!")],
    [("abs", "abs"), ("mod", "mod"), ("exp", "EXP"), ("ans", "Ans"), ("pct", "%")],
]

NUMBER_KEYS = [
    [("clear", "C"), ("ce", "CE"), ("back", "⌫"), ("div", "÷")],
    [("7", "7"), ("8", "8"), ("9", "9"), ("mul", "×")],
    [("4", "4"), ("5", "5"), ("6", "6"), ("sub", "−")],
    [("1", "1"), ("2", "2"), ("3", "3"), ("add", "+")],
    [("neg", "±"), ("0", "0"), ("dot", "."), ("equals", "=")],
]

KEY_HELP = {
    "angle": "Switch angle unit: DEG → RAD → GRAD",
    "mc": "Memory clear", "mr": "Memory recall",
    "mplus": "Add display value to memory", "mminus": "Subtract display value from memory",
    "exp": "Enter a power-of-ten exponent (×10ⁿ)", "ans": "Last result",
    "clear": "Clear all (Esc)", "ce": "Clear entry (Delete)", "back": "Backspace",
    "neg": "Change sign (F9)", "equals": "Calculate (Enter)",
}

SHORTCUTS = [
    ("0–9  .", "Digits, decimal point"),
    ("+  -  *  /  ^", "Operators, power"),
    ("(  )  %  !", "Brackets, percent, factorial"),
    ("Enter  =", "Calculate"),
    ("Backspace", "Delete last key"),
    ("Delete", "Clear entry (CE)"),
    ("Esc", "Clear all (C)"),
    ("F9", "Change sign (±)"),
    ("s  c  t", "sin, cos, tan"),
    ("S  C  T", "sin⁻¹, cos⁻¹, tan⁻¹"),
    ("l  n", "log, ln"),
    ("r  q  i", "√x, x², 1/x"),
    ("p  e", "π, e"),
    ("E", "EXP (×10ⁿ)"),
    ("a  m  d", "Ans, mod, DEG/RAD/GRAD"),
]

keyboard_listener = st.components.v2.component(
    "calculator_keyboard",
    js=(ASSETS / "keyboard.js").read_text(encoding="utf-8"),
)


def get_calculator():
    if "calc" not in st.session_state:
        st.session_state.calc = Calculator()
        st.session_state.keyboard_seen = {}
    return st.session_state.calc


def press(key):
    get_calculator().press(key)


def process_keyboard(calc):
    """Apply key presses captured by the browser that have not been seen yet."""
    result = keyboard_listener(key="keyboard", on_events_change=lambda: None)
    payload = result.get("events") if result else None
    if not payload:
        return
    nonce = payload.get("nonce")
    last_seen = st.session_state.keyboard_seen.get(nonce, 0)
    for seq, action in payload.get("items", []):
        if seq <= last_seen:
            continue
        last_seen = seq
        try:
            calc.press(action)
        except ValueError:
            pass  # unknown action from the browser: ignore it
    st.session_state.keyboard_seen = {nonce: last_seen}


def display_size(text):
    length = len(text)
    if length <= 13:
        return "xl"
    if length <= 19:
        return "lg"
    if length <= 28:
        return "md"
    return "sm"


def render_display(calc):
    indicators = "".join(
        f'<span class="{"on" if calc.angle_mode == mode else ""}">{mode}</span>'
        for mode in ("DEG", "RAD", "GRAD")
    )
    indicators += f'<span class="{"on" if calc.memory is not None else ""}">M</span>'
    main_classes = "error" if calc.error else display_size(calc.display)
    preview = escape(f"= {calc.preview}") if calc.preview else "&nbsp;"
    st.html(
        f"""
        <div class="calc-display" role="status" aria-live="polite">
          <div class="calc-indicators">{indicators}</div>
          <div class="calc-equation">{escape(calc.last_equation) or "&nbsp;"}</div>
          <div class="calc-main {main_classes}">{escape(calc.display)}</div>
          <div class="calc-preview">{preview}</div>
        </div>
        """
    )


def render_keys(rows, container_key, calc):
    with st.container(key=container_key, gap=None):
        for row in rows:
            for column, (key, label) in zip(st.columns(len(row), gap=None, wrap=False), row):
                if key == "angle":
                    label = calc.angle_mode
                column.button(
                    label,
                    key=f"k_{key}",
                    on_click=press,
                    args=(key,),
                    help=KEY_HELP.get(key),
                    width="stretch",
                )


def render_sidebar(calc):
    with st.sidebar:
        st.subheader("History")
        if calc.history:
            items = "".join(
                f'<div class="history-item"><div class="eq">{escape(eq)} =</div>'
                f'<div class="res">{escape(res)}</div></div>'
                for eq, res in calc.history
            )
            st.html(items)
            if st.button("Clear history", icon=":material/delete:", width="stretch"):
                calc.history.clear()
                st.rerun()
        else:
            st.caption("Calculations you run will appear here.")

        with st.expander("Keyboard shortcuts", icon=":material/keyboard:"):
            rows = "".join(
                f"<tr><td>{' '.join(f'<kbd>{escape(k)}</kbd>' for k in keys.split('  '))}</td>"
                f"<td>{escape(desc)}</td></tr>"
                for keys, desc in SHORTCUTS
            )
            st.html(f'<table class="shortcut-table">{rows}</table>')


def main():
    st.set_page_config(page_title="Scientific Calculator", page_icon="🧮", layout="wide")
    st.html(f"<style>{(ASSETS / 'style.css').read_text(encoding='utf-8')}</style>")

    calc = get_calculator()
    process_keyboard(calc)

    st.html(
        '<div class="calc-header"><h1>Scientific Calculator</h1>'
        "<p>Click the keys or type on your keyboard. Press Enter to calculate.</p></div>"
    )

    with st.container(key="calc_card"):
        render_display(calc)
        left, right = st.columns([5, 4], gap="large")
        with left:
            render_keys(SCIENTIFIC_KEYS, "sci_pad", calc)
        with right:
            render_keys(NUMBER_KEYS, "num_pad", calc)

    render_sidebar(calc)


main()
