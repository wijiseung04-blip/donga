import pytest

from donga_app.main import greet


def test_greet_default():
    assert greet() == "Hello, world!"


def test_greet_custom_name():
    assert greet("OSS") == "Hello, OSS!"


def test_greet_strips_whitespace():
    assert greet("  OSS  ") == "Hello, OSS!"


@pytest.mark.parametrize("name", ["", "   "])
def test_greet_rejects_blank_name(name):
    with pytest.raises(ValueError, match="empty"):
        greet(name)


def test_greet_rejects_non_string():
    with pytest.raises(TypeError):
        greet(None)
