from plugins.tool_use.ontology import ABSTAIN, normalize


def test_abstain_is_none():
    assert ABSTAIN is None


def test_normalize_trims_and_lowercases():
    assert normalize("  Hanoi ") == "hanoi"
    assert normalize("HANOI") == "hanoi"


def test_normalize_coerces_non_strings():
    assert normalize(42) == "42"
    assert normalize(None) == "none"
