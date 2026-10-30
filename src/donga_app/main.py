def greet(name="world"):
    if not isinstance(name, str):
        raise TypeError("name must be a string")
    name = name.strip()
    if not name:
        raise ValueError("name must not be empty")
    return f"Hello, {name}!"


def main():
    print(greet())


if __name__ == "__main__":
    main()
