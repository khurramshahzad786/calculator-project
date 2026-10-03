import math

import pytest

from engine import CalcError, evaluate, format_number


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        ("1+2×3", 7),
        ("(1+2)×3", 9),
        ("10÷4", 2.5),
        ("2^3^2", 512),          # right-associative
        ("−2^2", -4),            # unary minus binds looser than ^
        ("(−2)^2", 4),
        ("2^−1", 0.5),
        ("5−−3", 8),
        ("7 mod 3", 1),
        ("6÷2(1+2)", 9),         # implicit multiplication, left to right
        ("2π", 2 * math.pi),
        ("3e", 3 * math.e),
        ("2sin(30)", 1),
        ("(1+2)(3+4)", 21),
        ("5!", 120),
        ("0!", 1),
        ("3²", 9),
        ("2³", 8),
        ("4⁻¹", 0.25),
        ("√(16)", 4),
        ("∛(−27)", -3),
        ("abs(−5)", 5),
        ("10^(3)", 1000),
        ("e^(1)", math.e),
        ("log(1000)", 3),
        ("ln(e)", 1),
        ("log₂(8)", 3),
        ("1.5E3", 1500),
        ("2E−3", 0.002),
        ("50%", 0.5),
        ("200+10%", 220),        # percent of the left operand
        ("200−10%", 180),
        ("200×10%", 20),
        ("sin(30", 0.5),         # missing ")" closed automatically
        ("((2+3", 5),
    ],
)
def test_evaluate(expression, expected):
    assert evaluate(expression) == pytest.approx(expected)


@pytest.mark.parametrize(
    ("expression", "mode", "expected"),
    [
        ("sin(30)", "DEG", 0.5),
        ("cos(60)", "DEG", 0.5),
        ("tan(45)", "DEG", 1),
        ("sin(180)", "DEG", 0),
        ("cos(90)", "DEG", 0),
        ("sin(π÷2)", "RAD", 1),
        ("sin(100)", "GRAD", 1),
        ("sin⁻¹(1)", "DEG", 90),
        ("cos⁻¹(0)", "RAD", math.pi / 2),
        ("tan⁻¹(1)", "GRAD", 50),
        ("sinh(0)", "DEG", 0),     # hyperbolic functions ignore angle mode
        ("cosh(0)", "RAD", 1),
    ],
)
def test_angle_modes(expression, mode, expected):
    assert evaluate(expression, mode) == pytest.approx(expected, abs=1e-12)


def test_ans_value():
    assert evaluate("Ans×2", ans=21) == 42


@pytest.mark.parametrize(
    ("expression", "message"),
    [
        ("5÷0", "Cannot divide by zero"),
        ("5 mod 0", "Cannot divide by zero"),
        ("0⁻¹", "Cannot divide by zero"),
        ("√(−1)", "Math error"),
        ("log(0)", "Math error"),
        ("ln(−1)", "Math error"),
        ("sin⁻¹(2)", "Math error"),
        ("tan(90)", "Math error"),
        ("tan(−270)", "Math error"),
        ("(−8)^(1÷3)", "Math error"),
        ("(−1)!", "Math error"),
        ("171!", "Overflow"),
        ("10^(400)", "Overflow"),
        ("1E300×1E300", "Overflow"),
        ("5+", "Syntax error"),
        ("×5", "Syntax error"),
        ("()", "Syntax error"),
        ("2)", "Syntax error"),
        ("2E", "Syntax error"),
        ("sin", "Syntax error"),
        ("", "Syntax error"),
    ],
)
def test_errors(expression, message):
    with pytest.raises(CalcError, match=message):
        evaluate(expression)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (0.0, "0"),
        (-0.0, "0"),
        (42.0, "42"),
        (-7.0, "-7"),
        (0.1 + 0.2, "0.3"),
        (1 / 3, "0.333333333333"),
        (2.5, "2.5"),
        (1.5e-7, "0.00000015"),
        (123456789012345.0, "123456789012345"),
        (1.5e20, "1.5E+20"),
        (-2.5e-12, "-2.5E-12"),
    ],
)
def test_format_number(value, expected):
    assert format_number(value) == expected


@pytest.mark.parametrize("value", [1.5e20, -2.5e-12, 1 / 3, 1.5e-7, 123456789012345.0])
def test_formatted_numbers_parse_back(value):
    text = format_number(value).replace("-", "−")
    assert evaluate(text) == pytest.approx(value, rel=1e-11)
