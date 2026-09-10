def greet(name: str = "world") -> str:
    """Return a friendly greeting for the provided name."""
    return f"Hello, {name}!"


if __name__ == "__main__":
    print(greet())
