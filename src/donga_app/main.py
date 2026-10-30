def greet(name="world"):
    """이름에 대한 인사말을 반환한다.

    앞뒤 공백은 제거된다.

    Raises:
        TypeError: name이 문자열이 아닌 경우
        ValueError: name이 비어 있거나 공백만 있는 경우
    """
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
