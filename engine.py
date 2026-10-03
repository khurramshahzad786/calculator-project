"""Expression parsing and evaluation for the scientific calculator.

Expressions are parsed by a small recursive-descent parser and evaluated with
the ``math`` module, so Python's ``eval`` is never used.

Grammar (highest precedence last)::

    expr    := term (("+" | "-") term)*
    term    := unary (("*" | "/" | "mod") unary | <implicit ×> power)*
    unary   := ("-" | "+") unary | power
    power   := postfix ("^" unary)?            # right-associative, -2^2 = -4
    postfix := primary ("!" | "%")*
    primary := number | constant | function "(" expr ")" | "(" expr ")"

Missing closing parentheses at the end of the input are closed automatically.
"""

import math
import re

ANGLE_MODES = ("DEG", "RAD", "GRAD")

# Display symbols -> parser syntax. Order matters: longer symbols first.
_NORMALIZE = (
    ("sin⁻¹", "asin"),
    ("cos⁻¹", "acos"),
    ("tan⁻¹", "atan"),
    ("log₂", "log2"),
    ("⁻¹", "^(-1)"),
    ("²", "^(2)"),
    ("³", "^(3)"),
    ("×", "*"),
    ("÷", "/"),
    ("−", "-"),
    ("π", "pi"),
    ("√", "sqrt"),
    ("∛", "cbrt"),
)

_NAMES = (
    "Ans", "asin", "acos", "atan", "sinh", "cosh", "tanh", "sin", "cos", "tan",
    "log2", "log", "ln", "sqrt", "cbrt", "abs", "mod", "pi", "e",
)

_TOKEN_RE = re.compile(
    r"\s*(?:"
    r"(?P<num>(?:\d+\.?\d*|\.\d+)(?:E[+-]?\d+)?)"
    r"|(?P<name>" + "|".join(_NAMES) + r")"
    r"|(?P<op>[-+*/^()!%])"
    r")"
)

_CONSTANTS = {"pi": math.pi, "e": math.e}
_TRIG = {"sin": math.sin, "cos": math.cos, "tan": math.tan}
_INVERSE_TRIG = {"asin": math.asin, "acos": math.acos, "atan": math.atan}
_FUNCTIONS = {
    "sinh": math.sinh,
    "cosh": math.cosh,
    "tanh": math.tanh,
    "log": math.log10,
    "ln": math.log,
    "log2": math.log2,
    "sqrt": math.sqrt,
    "cbrt": math.cbrt,
    "abs": math.fabs,
}

# Values this close to zero after a trig call are floating-point noise.
_TRIG_EPSILON = 1e-12
MAX_FACTORIAL = 170  # largest n whose factorial fits in a float


class CalcError(Exception):
    """An expression could not be evaluated. The message is shown to the user."""


def normalize(expression):
    """Translate display symbols (×, ÷, π, sin⁻¹ …) into parser syntax."""
    for symbol, replacement in _NORMALIZE:
        expression = expression.replace(symbol, replacement)
    return expression


def tokenize(expression):
    """Split a display expression into (kind, value) tokens."""
    text = normalize(expression)
    tokens = []
    pos = 0
    while pos < len(text):
        if text[pos:].strip() == "":
            break
        match = _TOKEN_RE.match(text, pos)
        if not match or match.end() == pos:
            raise CalcError("Syntax error")
        pos = match.end()
        if match.group("num") is not None:
            tokens.append(("num", float(match.group("num"))))
        elif match.group("name") is not None:
            tokens.append(("name", match.group("name")))
        else:
            tokens.append(("op", match.group("op")))
    return tokens


def _to_radians(value, angle_mode):
    if angle_mode == "DEG":
        return math.radians(value)
    if angle_mode == "GRAD":
        return value * math.pi / 200
    return value


def _from_radians(value, angle_mode):
    if angle_mode == "DEG":
        return math.degrees(value)
    if angle_mode == "GRAD":
        return value * 200 / math.pi
    return value


def _factorial(value):
    if value < 0 and value == int(value):
        raise CalcError("Math error")
    if value > MAX_FACTORIAL:
        raise CalcError("Overflow")
    if value == int(value):
        return float(math.factorial(int(value)))
    return math.gamma(value + 1)


def _power(base, exponent):
    if base == 0 and exponent < 0:
        raise CalcError("Cannot divide by zero")
    try:
        return math.pow(base, exponent)
    except OverflowError:
        raise CalcError("Overflow") from None
    except ValueError:
        raise CalcError("Math error") from None


class _Parser:
    def __init__(self, tokens, angle_mode, ans):
        self.tokens = tokens
        self.pos = 0
        self.angle_mode = angle_mode
        self.ans = ans

    def parse(self):
        if not self.tokens:
            raise CalcError("Syntax error")
        value, _ = self._expr()
        if self.pos != len(self.tokens):
            raise CalcError("Syntax error")
        return value

    # -- token helpers -------------------------------------------------
    def _peek(self):
        return self.tokens[self.pos] if self.pos < len(self.tokens) else (None, None)

    def _next(self):
        token = self._peek()
        self.pos += 1
        return token

    def _peek_is(self, kind, value):
        return self._peek() == (kind, value)

    def _starts_primary(self):
        kind, value = self._peek()
        return kind == "num" or (kind == "name" and value != "mod") or (kind, value) == ("op", "(")

    def _close_paren(self):
        # A missing ")" at the very end of the input is closed implicitly.
        if self.pos == len(self.tokens):
            return
        if not self._peek_is("op", ")"):
            raise CalcError("Syntax error")
        self.pos += 1

    # -- grammar -------------------------------------------------------
    def _expr(self):
        left, is_percent = self._term()
        while self._peek() in (("op", "+"), ("op", "-")):
            _, op = self._next()
            right, right_is_percent = self._term()
            if right_is_percent:
                # Standard calculator percent: 200 + 10% = 200 + 20.
                right = left * right
            left = left + right if op == "+" else left - right
            is_percent = False
        return left, is_percent

    def _term(self):
        left, is_percent = self._unary()
        while True:
            token = self._peek()
            if token in (("op", "*"), ("op", "/"), ("name", "mod")):
                self.pos += 1
                right, _ = self._unary()
                if token[1] == "*":
                    left = left * right
                elif right == 0:
                    raise CalcError("Cannot divide by zero")
                elif token[1] == "/":
                    left = left / right
                else:
                    left = left % right
            elif self._starts_primary():
                right, _ = self._power()
                left = left * right
            else:
                return left, is_percent
            is_percent = False

    def _unary(self):
        if self._peek_is("op", "-"):
            self.pos += 1
            value, is_percent = self._unary()
            return -value, is_percent
        if self._peek_is("op", "+"):
            self.pos += 1
            return self._unary()
        return self._power()

    def _power(self):
        base, is_percent = self._postfix()
        if self._peek_is("op", "^"):
            self.pos += 1
            exponent, _ = self._unary()
            return _power(base, exponent), False
        return base, is_percent

    def _postfix(self):
        value = self._primary()
        is_percent = False
        while True:
            if self._peek_is("op", "!"):
                self.pos += 1
                value = _factorial(value)
                is_percent = False
            elif self._peek_is("op", "%"):
                self.pos += 1
                value = value / 100
                is_percent = True
            else:
                return value, is_percent

    def _primary(self):
        kind, value = self._next()
        if kind == "num":
            return value
        if (kind, value) == ("op", "("):
            inner, _ = self._expr()
            self._close_paren()
            return inner
        if kind == "name":
            if value in _CONSTANTS:
                return _CONSTANTS[value]
            if value == "Ans":
                return self.ans
            if value != "mod":
                if not self._peek_is("op", "("):
                    raise CalcError("Syntax error")
                self.pos += 1
                argument, _ = self._expr()
                self._close_paren()
                return self._apply(value, argument)
        raise CalcError("Syntax error")

    def _apply(self, name, x):
        try:
            if name in _TRIG:
                if name == "tan" and self._is_odd_right_angle(x):
                    raise CalcError("Math error")
                result = _TRIG[name](_to_radians(x, self.angle_mode))
                return 0.0 if abs(result) < _TRIG_EPSILON else result
            if name in _INVERSE_TRIG:
                return _from_radians(_INVERSE_TRIG[name](x), self.angle_mode)
            return _FUNCTIONS[name](x)
        except ValueError:
            raise CalcError("Math error") from None
        except OverflowError:
            raise CalcError("Overflow") from None

    def _is_odd_right_angle(self, x):
        """tan is undefined at 90°, 270°, … (exactly representable in DEG/GRAD)."""
        quarter = {"DEG": 90.0, "GRAD": 100.0}.get(self.angle_mode)
        return quarter is not None and (x / quarter) % 2 == 1


def evaluate(expression, angle_mode="DEG", ans=0.0):
    """Evaluate a display expression and return a float, or raise CalcError."""
    if angle_mode not in ANGLE_MODES:
        raise ValueError(f"Unknown angle mode: {angle_mode}")
    try:
        result = _Parser(tokenize(expression), angle_mode, ans).parse()
    except OverflowError:
        raise CalcError("Overflow") from None
    except RecursionError:
        raise CalcError("Expression too complex") from None
    if math.isnan(result):
        raise CalcError("Math error")
    if math.isinf(result):
        raise CalcError("Overflow")
    return result


def format_number(value):
    """Format a result for the display (12 significant digits, E notation when needed).

    The output can be parsed back by ``evaluate`` so results can be reused.
    """
    if value == 0:
        return "0"
    magnitude = abs(value)
    if magnitude >= 1e15 or magnitude < 1e-9:
        mantissa, exponent = f"{value:.11e}".split("e")
        mantissa = mantissa.rstrip("0").rstrip(".")
        return f"{mantissa}E{int(exponent):+d}"
    if value == int(value):
        return str(int(value))
    text = f"{value:.12g}"
    if "e" in text:  # small values such as 1.5e-07 → plain decimal
        text = f"{float(text):.{12 + abs(int(text.split('e')[1]))}f}".rstrip("0").rstrip(".")
    return text
