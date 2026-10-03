"""Calculator input state: turns key presses into an editable expression.

The expression is kept as a list of display tokens (``"7"``, ``"×"``,
``"sin("`` …) so that backspace removes whole function names and the UI can
show exactly what was typed. Evaluation is delegated to :mod:`engine`.
"""

from dataclasses import dataclass, field

from engine import ANGLE_MODES, CalcError, evaluate, format_number

DIGITS = frozenset("0123456789")
NUMBER_CHARS = DIGITS | {"."}
BINARY_OPERATORS = {"add": "+", "sub": "−", "mul": "×", "div": "÷", "pow": "^", "mod": " mod "}
OPERATOR_TOKENS = frozenset(BINARY_OPERATORS.values())
POSTFIX = {"sq": "²", "cube": "³", "inv": "⁻¹", "fact": "!", "pct": "%"}
FUNCTIONS = {
    "sin": "sin(", "cos": "cos(", "tan": "tan(",
    "asin": "sin⁻¹(", "acos": "cos⁻¹(", "atan": "tan⁻¹(",
    "sinh": "sinh(", "cosh": "cosh(", "tanh": "tanh(",
    "log": "log(", "ln": "ln(", "log2": "log₂(",
    "sqrt": "√(", "cbrt": "∛(", "abs": "abs(",
    "pow10": "10^(", "exp_e": "e^(",
}
CONSTANTS = {"pi": "π", "e": "e", "ans": "Ans"}
HISTORY_LIMIT = 20

# Tokens after which a new number cannot simply be appended (it would merge
# or be ambiguous), so an explicit "×" is inserted first.
_CLOSING = frozenset({")", "π", "e", "Ans"} | set(POSTFIX.values()))


def display_number(value):
    """A result formatted for the display, using the typographic minus sign."""
    return format_number(value).replace("-", "−")


@dataclass
class Calculator:
    tokens: list = field(default_factory=list)
    angle_mode: str = "DEG"
    ans: float = 0.0
    memory: float | None = None
    last_equation: str = ""
    error: str | None = None
    just_evaluated: bool = False
    history: list = field(default_factory=list)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    @property
    def expression(self):
        return "".join(self.tokens)

    @property
    def display(self):
        """Text for the main display line."""
        return self.error or self.expression or "0"

    @property
    def preview(self):
        """Live result of the expression being typed ('' when not applicable)."""
        if self.error or self.just_evaluated or not self.tokens:
            return ""
        if all(token in NUMBER_CHARS for token in self.tokens):
            return ""
        try:
            return display_number(evaluate(self.expression, self.angle_mode, self.ans))
        except CalcError:
            return ""

    def press(self, key):
        """Apply one key press. ``key`` is a key id such as "7", "add", "sin"."""
        if key in DIGITS:
            self._digit(key)
        elif key in BINARY_OPERATORS:
            self._operator(BINARY_OPERATORS[key])
        elif key in POSTFIX:
            self._postfix(POSTFIX[key])
        elif key in FUNCTIONS:
            self._open_group(FUNCTIONS[key])
        elif key in CONSTANTS:
            self._constant(CONSTANTS[key])
        else:
            action = self._ACTIONS.get(key)
            if action is None:
                raise ValueError(f"Unknown key: {key}")
            action(self)

    # ------------------------------------------------------------------
    # Token helpers
    # ------------------------------------------------------------------
    def _last(self):
        return self.tokens[-1] if self.tokens else None

    def _ends_closed(self):
        """True when the expression ends with a complete operand."""
        last = self._last()
        return last is not None and (last in NUMBER_CHARS or last in _CLOSING)

    def _is_unary_minus(self, index):
        if self.tokens[index] != "−":
            return False
        if index == 0:
            return True
        before = self.tokens[index - 1]
        return before in OPERATOR_TOKENS or before.endswith("(") or before == "E"

    def _number_start(self):
        """Index where the trailing numeric literal (incl. E exponent) starts."""
        tokens = self.tokens
        start = len(tokens)
        while start > 0 and tokens[start - 1] in NUMBER_CHARS:
            start -= 1
        mantissa_end = start
        if mantissa_end > 1 and tokens[mantissa_end - 1] in ("+", "−") and tokens[mantissa_end - 2] == "E":
            mantissa_end -= 2
        elif mantissa_end > 0 and tokens[mantissa_end - 1] == "E":
            mantissa_end -= 1
        if mantissa_end != start:
            mantissa_start = mantissa_end
            while mantissa_start > 0 and tokens[mantissa_start - 1] in NUMBER_CHARS:
                mantissa_start -= 1
            if mantissa_start < mantissa_end:
                start = mantissa_start
        return start

    def _trailing_number(self):
        return self.tokens[self._number_start():]

    def _start_fresh_if_done(self):
        """After a result or an error, new operand input starts a new expression."""
        if self.just_evaluated or self.error:
            self.tokens = []
            self.error = None
            self.just_evaluated = False

    def _continue_from_result(self, wrap_negative):
        """After a result, operators continue the calculation with that result."""
        if self.error:
            self.tokens = []
            self.error = None
        if self.just_evaluated:
            self.just_evaluated = False
            if wrap_negative and self.tokens and self.tokens[0] == "−":
                self.tokens = ["(", *self.tokens, ")"]

    def _append_operand(self, *tokens):
        """Append tokens that start a new operand.

        Implicit multiplication (2π, 3sin(30), (1+2)(3)) is understood by the
        parser, but a number written after a complete operand would merge with
        it ("π2", "5²3"), so an explicit "×" is inserted in that case.
        """
        if self._ends_closed() and tokens[0][0] in NUMBER_CHARS:
            self.tokens.append("×")
        self.tokens.extend(tokens)

    def _is_exponent_sign(self):
        """True when the expression ends with the sign of an E exponent ("2E−")."""
        return len(self.tokens) > 1 and self._last() in ("+", "−") and self.tokens[-2] == "E"

    @staticmethod
    def _value_tokens(value):
        return list(display_number(value))

    # ------------------------------------------------------------------
    # Input actions
    # ------------------------------------------------------------------
    def _digit(self, digit):
        self._start_fresh_if_done()
        if self._last() == "E" or self._is_exponent_sign():
            self.tokens.append(digit)
            return
        if self._trailing_number() == ["0"]:
            self.tokens[-1] = digit
            return
        if self._last() in NUMBER_CHARS:
            self.tokens.append(digit)
        else:
            self._append_operand(digit)

    def _decimal(self):
        self._start_fresh_if_done()
        number = self._trailing_number()
        if "." in number or "E" in number:
            return
        if number:
            self.tokens.append(".")
        else:
            self._append_operand("0", ".")

    def _exponent(self):
        if self.error:
            return
        self.just_evaluated = False
        number = self._trailing_number()
        if number and "E" not in number and number[-1] in DIGITS:
            self.tokens.append("E")

    def _operator(self, op):
        self._continue_from_result(wrap_negative=op == "^")
        last = self._last()
        if last == "E":  # sign of the exponent: 2E−5
            if op in ("+", "−"):
                self.tokens.append(op)
            return
        if self._is_exponent_sign():
            return
        if op == "−" and (last is None or last.endswith("(") or last in ("×", "÷", "^", " mod ")):
            self.tokens.append(op)  # unary minus
            return
        # Pressing another operator replaces the pending one(s).
        while self.tokens and self._last() in OPERATOR_TOKENS:
            self.tokens.pop()
        if not self.tokens:
            self.tokens = ["0", op]
        elif not self._last().endswith("("):
            self.tokens.append(op)

    def _postfix(self, symbol):
        self._continue_from_result(wrap_negative=True)
        if self._ends_closed():
            self.tokens.append(symbol)

    def _open_group(self, token):
        """Functions like "sin(" and the plain "(" bracket."""
        self._start_fresh_if_done()
        if self._last() == "E" or self._is_exponent_sign():
            return
        self._append_operand(token)

    def _constant(self, symbol):
        self._start_fresh_if_done()
        if self._last() == "E" or self._is_exponent_sign():
            return
        self._append_operand(symbol)

    def _left_paren(self):
        self._open_group("(")

    def _right_paren(self):
        if self.error or self.just_evaluated:
            return
        opened = sum(token.endswith("(") for token in self.tokens)
        closed = self.tokens.count(")")
        if opened > closed and self._ends_closed():
            self.tokens.append(")")

    def _toggle_sign(self):
        if self.error:
            return
        if self.just_evaluated:
            self.ans = -self.ans  # the displayed result is negated in place
        start = self._number_start()
        if start == len(self.tokens):  # no trailing number
            last = self._last()
            if last == "−" and self._is_unary_minus(len(self.tokens) - 1):
                self.tokens.pop()
            elif last is None or last in OPERATOR_TOKENS or last.endswith("("):
                self.tokens.append("−")
            else:
                self.tokens = ["−", "(", *self.tokens, ")"]
            return
        before = start - 1
        if before >= 0 and self._is_unary_minus(before):
            del self.tokens[before]
        elif before >= 0 and self.tokens[before] == "−":
            self.tokens[before] = "+"
        elif before >= 0 and self.tokens[before] == "+":
            self.tokens[before] = "−"
        else:
            self.tokens.insert(start, "−")

    def _backspace(self):
        if self.error:
            self.error = None  # back to editing the failed expression
            return
        self.just_evaluated = False
        if self.tokens:
            self.tokens.pop()

    def _clear_entry(self):
        if self.error or self.just_evaluated:
            self._clear()
            return
        start = self._number_start()
        if start < len(self.tokens):
            del self.tokens[start:]
        elif self.tokens:
            self.tokens.pop()

    def _clear(self):
        self.tokens = []
        self.error = None
        self.just_evaluated = False
        self.last_equation = ""

    def _closed_expression(self):
        opened = sum(token.endswith("(") for token in self.tokens)
        missing = opened - self.tokens.count(")")
        return self.expression + ")" * max(missing, 0)

    def _equals(self):
        if self.error or self.just_evaluated or not self.tokens:
            return
        equation = self._closed_expression()
        try:
            value = evaluate(self.expression, self.angle_mode, self.ans)
        except CalcError as exc:
            self.error = str(exc)
            self.last_equation = f"{equation} ="
            return
        self.last_equation = f"{equation} ="
        self.history.insert(0, (equation, display_number(value)))
        del self.history[HISTORY_LIMIT:]
        self.ans = value
        self.tokens = self._value_tokens(value)
        self.just_evaluated = True

    def _toggle_angle(self):
        index = ANGLE_MODES.index(self.angle_mode)
        self.angle_mode = ANGLE_MODES[(index + 1) % len(ANGLE_MODES)]

    # -- memory --------------------------------------------------------
    def _current_value(self):
        """Value of the display for memory keys, or None (and an error) if invalid."""
        if self.error:
            return None
        if self.just_evaluated:
            return self.ans
        if not self.tokens:
            return 0.0
        try:
            return evaluate(self.expression, self.angle_mode, self.ans)
        except CalcError as exc:
            self.error = str(exc)
            return None

    def _memory_add(self, sign):
        value = self._current_value()
        if value is not None:
            self.memory = (self.memory or 0.0) + sign * value

    def _memory_plus(self):
        self._memory_add(1)

    def _memory_minus(self):
        self._memory_add(-1)

    def _memory_clear(self):
        self.memory = None

    def _memory_recall(self):
        if self.memory is None:
            return
        self._start_fresh_if_done()
        if self._last() == "E" or self._is_exponent_sign():
            return
        value_tokens = self._value_tokens(self.memory)
        if value_tokens[0] == "−":
            value_tokens = ["(", *value_tokens, ")"]
        self._append_operand(*value_tokens)

    _ACTIONS = {
        "dot": _decimal,
        "exp": _exponent,
        "lparen": _left_paren,
        "rparen": _right_paren,
        "neg": _toggle_sign,
        "back": _backspace,
        "ce": _clear_entry,
        "clear": _clear,
        "equals": _equals,
        "angle": _toggle_angle,
        "mc": _memory_clear,
        "mr": _memory_recall,
        "mplus": _memory_plus,
        "mminus": _memory_minus,
    }
