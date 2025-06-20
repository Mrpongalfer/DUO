# new_code_for_calculator.py
# V1.1 - Updated by Scribe Test
def add(x: int, y: int) -> int:
    """Adds two integers and returns the result."""
    return x + y


def subtract(a: int, b: int) -> int:
    """Subtracts second integer from the first."""
    return a - b


class Greeter:
    def __init__(self, name: str):
        self.name: str = name  # Explicit type hint for instance var

    def greet(self) -> None:  # Added return type hint
        print(f"Hello, {self.name}!")  # Added exclamation
