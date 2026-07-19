"""Unit tests for wrapper.wrap_field — Requirements 12.1-12.5."""
import sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))

from wrapper import wrap_field, PREFIX


def test_none_passthrough():
    assert wrap_field(None) is None


def test_empty_string_passthrough():
    assert wrap_field("") == ""


def test_normal_string_gets_prefix():
    assert wrap_field("hello") == PREFIX + "hello"


def test_idempotent():
    once = wrap_field("hello")
    twice = wrap_field(once)
    assert once == twice


def test_content_preserved_after_prefix():
    content = "línea 1\nlínea 2\t\ttabs  y  espacios"
    result = wrap_field(content)
    assert result == PREFIX + content  # no truncation, no escaping


if __name__ == "__main__":
    test_none_passthrough()
    test_empty_string_passthrough()
    test_normal_string_gets_prefix()
    test_idempotent()
    test_content_preserved_after_prefix()
    print("All wrapper tests passed.")
