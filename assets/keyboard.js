// Captures keyboard input for the calculator and sends it to Python.
//
// Key presses are sent as a numbered, cumulative event list (state value,
// not a trigger) so that fast typing cannot lose or merge keys while the
// Streamlit script is re-running. Python processes only unseen numbers.

const KEYMAP = {
  "0": "0", "1": "1", "2": "2", "3": "3", "4": "4",
  "5": "5", "6": "6", "7": "7", "8": "8", "9": "9",
  ".": "dot", ",": "dot",
  "+": "add", "-": "sub", "*": "mul", "/": "div", "^": "pow",
  "(": "lparen", ")": "rparen", "%": "pct", "!": "fact",
  "Enter": "equals", "=": "equals",
  "Backspace": "back", "Delete": "ce", "Escape": "clear", "F9": "neg",
  "s": "sin", "c": "cos", "t": "tan",
  "S": "asin", "C": "acos", "T": "atan",
  "l": "log", "n": "ln", "r": "sqrt", "q": "sq", "i": "inv",
  "p": "pi", "e": "e", "E": "exp", "a": "ans", "m": "mod", "d": "angle",
};

const MAX_EVENTS = 50;

export default function (component) {
  const { setStateValue } = component;
  // Survives Streamlit re-runs; a page reload gets a fresh nonce.
  const state = (window.__calcKeyboard ??= {
    nonce: Math.random().toString(36).slice(2),
    seq: 0,
    events: [],
  });

  function flash(action) {
    const button = document.querySelector(`.st-key-k_${action} button`);
    if (!button) return;
    button.classList.add("kbd-active");
    setTimeout(() => button.classList.remove("kbd-active"), 140);
  }

  function onKeyDown(event) {
    if (event.ctrlKey || event.metaKey || event.altKey) return;
    const target = event.target;
    if (target && (target.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName))) {
      return;
    }
    const action = KEYMAP[event.key];
    if (!action) return;
    // Also stops Enter from "clicking" a calculator key that has focus.
    event.preventDefault();
    state.seq += 1;
    state.events.push([state.seq, action]);
    if (state.events.length > MAX_EVENTS) state.events.splice(0, state.events.length - MAX_EVENTS);
    setStateValue("events", { nonce: state.nonce, items: state.events.slice() });
    flash(action);
  }

  document.addEventListener("keydown", onKeyDown, true);
  return () => document.removeEventListener("keydown", onKeyDown, true);
}
