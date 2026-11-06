"""Mértékegység-átváltások."""


def c_to_f(celsius: float) -> float:
    """Celsius -> Fahrenheit."""
    return celsius * 9 / 5 + 32


def f_to_c(fahrenheit: float) -> float:
    """Fahrenheit -> Celsius."""
    return (fahrenheit - 32) * 5 / 9


def kpa_to_bar(kpa: float) -> float:
    """Kilopascal -> bar."""
    return kpa / 100.0


def normalize_temperature(value: float, unit: str) -> float:
    """Bármely támogatott hőmérséklet-egységet Celsiusra hoz."""
    unit = unit.upper()
    if unit == "C":
        return value
    if unit == "F":
        return f_to_c(value)
    if unit == "K":
        return value - 273.15
    raise ValueError(f"unsupported temperature unit: {unit}")
