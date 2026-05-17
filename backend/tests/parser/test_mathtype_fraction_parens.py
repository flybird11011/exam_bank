from app.parser.mathtype import _wrap_fraction_side_if_needed


def test_wrap_fraction_side_adds_parentheses_for_ambiguous_expression():
    assert _wrap_fraction_side_if_needed("2/(x\u22121)+1") == "(2/(x\u22121)+1)"
    assert _wrap_fraction_side_if_needed("x") == "x"


def test_wrap_fraction_side_adds_parentheses_for_ambiguous_denominator():
    assert _wrap_fraction_side_if_needed("x+1") == "(x+1)"
    assert _wrap_fraction_side_if_needed("x") == "x"
