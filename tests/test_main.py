from donga_app.main import greet


def test_greet_default():
    assert greet() == "Hello, world!"


def test_greet_custom_name():
    assert greet("OSS") == "Hello, OSS!"
