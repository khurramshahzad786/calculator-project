import pytest

from calculator import Calculator


def press(calc, *keys):
    for key in keys:
        calc.press(key)
    return calc


def run(*keys):
    return press(Calculator(), *keys)


def test_basic_arithmetic():
    calc = run("1", "2", "add", "7", "mul", "3", "equals")
    assert calc.display == "33"
    assert calc.last_equation == "12+7×3 ="
    assert calc.history[0] == ("12+7×3", "33")


def test_initial_display_is_zero():
    assert Calculator().display == "0"


def test_leading_zero_is_replaced():
    assert run("0", "0", "5").display == "5"


def test_single_decimal_point_per_number():
    assert run("1", "dot", "5", "dot", "2").display == "1.52"
    assert run("dot", "5").display == "0.5"
    assert run("2", "add", "dot").display == "2+0."


def test_operator_replaces_pending_operator():
    assert run("5", "add", "mul").display == "5×"
    assert run("5", "mul", "sub").display == "5×−"      # unary minus allowed
    assert run("5", "mul", "sub", "add").display == "5+"


def test_operator_on_empty_starts_from_zero():
    assert run("mul", "3", "equals").display == "0"
    assert run("sub", "3", "equals").display == "−3"


def test_digit_after_result_starts_new_expression():
    calc = run("2", "add", "3", "equals", "7")
    assert calc.display == "7"


def test_operator_after_result_continues():
    calc = run("2", "add", "3", "equals", "mul", "4", "equals")
    assert calc.display == "20"


def test_postfix_after_negative_result_wraps_it():
    calc = run("sub", "5", "equals", "sq")
    assert calc.display == "(−5)²"
    assert press(calc, "equals").display == "25"


def test_power_after_negative_result_wraps_it():
    calc = run("sub", "2", "equals", "pow", "2", "equals")
    assert calc.display == "4"


def test_function_after_result_starts_new_expression():
    assert run("9", "equals", "sqrt", "4", "equals").display == "2"


def test_scientific_functions_in_degrees():
    assert run("sin", "3", "0", "equals").display == "0.5"
    assert run("asin", "1", "equals").display == "90"


def test_angle_mode_cycles():
    calc = Calculator()
    modes = [calc.angle_mode]
    for _ in range(3):
        calc.press("angle")
        modes.append(calc.angle_mode)
    assert modes == ["DEG", "RAD", "GRAD", "DEG"]
    assert press(Calculator(angle_mode="RAD"), "cos", "pi", "equals").display == "−1"


def test_implicit_multiplication_inserts_times_before_numbers():
    assert run("pi", "2").display == "π×2"
    assert run("2", "pi").display == "2π"
    assert run("2", "pow10", "3", "equals").display == "2000"
    assert run("lparen", "1", "add", "2", "rparen", "3", "equals").display == "9"
    assert run("5", "sq", "3", "equals").display == "75"


def test_right_paren_only_when_balanced_possible():
    assert run("2", "rparen").display == "2"
    assert run("lparen", "2", "add", "rparen").display == "(2+"
    assert run("lparen", "2", "rparen", "rparen").display == "(2)"


def test_auto_close_parentheses_on_equals():
    calc = run("sqrt", "1", "6", "equals")
    assert calc.display == "4"
    assert calc.last_equation == "√(16) ="


def test_exponent_entry():
    assert run("1", "dot", "5", "exp", "3", "equals").display == "1500"
    assert run("2", "exp", "sub", "3", "equals").display == "0.002"
    assert run("exp").display == "0"                     # nothing to scale
    assert run("2", "exp", "dot").display == "2E"        # no decimals in exponent


def test_percent():
    assert run("2", "0", "0", "add", "1", "0", "pct", "equals").display == "220"
    assert run("5", "0", "pct", "equals").display == "0.5"


def test_factorial_and_inverse():
    assert run("5", "fact", "equals").display == "120"
    assert run("4", "inv", "equals").display == "0.25"


def test_toggle_sign():
    assert run("5", "neg").display == "−5"
    assert run("5", "neg", "neg").display == "5"
    assert run("8", "sub", "3", "neg").display == "8+3"
    assert run("8", "add", "3", "neg").display == "8−3"
    assert run("8", "mul", "3", "neg").display == "8×−3"
    assert run("8", "mul", "neg").display == "8×−"
    assert run("lparen", "1", "rparen", "neg").display == "−((1))"


def test_toggle_sign_on_result_updates_ans():
    calc = run("6", "equals", "neg")
    assert calc.display == "−6"
    assert press(calc, "add", "ans", "equals").display == "−12"


def test_backspace_removes_whole_function_token():
    assert run("2", "add", "sin", "back").display == "2+"
    assert run("1", "2", "back").display == "1"
    assert run("1", "back").display == "0"


def test_clear_entry_removes_trailing_number():
    assert run("1", "2", "add", "3", "4", "ce").display == "12+"
    assert run("1", "2", "add", "ce").display == "12"
    assert run("2", "exp", "sub", "3", "ce").display == "0"


def test_clear_resets_but_keeps_memory_and_mode():
    calc = run("angle", "5", "mplus", "add", "2", "clear")
    assert calc.display == "0"
    assert calc.last_equation == ""
    assert calc.memory == 5
    assert calc.angle_mode == "RAD"


def test_division_by_zero_shows_error_and_recovers():
    calc = run("5", "div", "0", "equals")
    assert calc.display == "Cannot divide by zero"
    assert calc.last_equation == "5÷0 ="
    assert press(calc, "7").display == "7"


def test_backspace_after_error_returns_to_expression():
    calc = run("5", "div", "0", "equals", "back")
    assert calc.error is None
    assert calc.display == "5÷0"


def test_operator_after_error_starts_fresh():
    assert run("5", "div", "0", "equals", "add").display == "0+"


def test_equals_on_empty_or_twice_is_noop():
    assert run("equals").display == "0"
    calc = run("2", "add", "3", "equals", "equals")
    assert calc.display == "5"
    assert len(calc.history) == 1


def test_memory_keys():
    calc = run("5", "mplus", "clear", "3", "mplus", "clear", "1", "mminus")
    assert calc.memory == 7
    assert press(calc, "clear", "mr").display == "7"
    assert press(calc, "mul", "mr", "equals").display == "49"
    assert press(calc, "mc").memory is None
    assert press(calc, "clear", "mr").display == "0"


def test_memory_recall_negative_is_parenthesised():
    calc = run("4", "mminus", "clear", "2", "mr")
    assert calc.display == "2(−4)"
    assert press(calc, "equals").display == "−8"


def test_memory_add_with_invalid_expression_shows_error():
    calc = run("5", "add", "mplus")
    assert calc.error == "Syntax error"
    assert calc.memory is None


def test_ans_key_uses_last_result():
    assert run("6", "mul", "7", "equals", "clear", "ans", "add", "1", "equals").display == "43"


def test_live_preview():
    calc = run("2", "add", "3")
    assert calc.preview == "5"
    assert run("4", "2").preview == ""               # plain number: no preview
    assert run("2", "add").preview == ""              # incomplete: no preview
    assert run("2", "add", "3", "equals").preview == ""


def test_large_result_reusable():
    calc = run("1", "0", "pow", "2", "0", "equals")
    assert calc.display == "1E+20"
    assert press(calc, "mul", "2", "equals").display == "2E+20"


def test_history_is_capped():
    calc = Calculator()
    for _ in range(25):
        press(calc, "1", "add", "1", "equals")
    assert len(calc.history) == 20


def test_unknown_key_rejected():
    with pytest.raises(ValueError):
        Calculator().press("bogus")
