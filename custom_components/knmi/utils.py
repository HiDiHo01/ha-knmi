from datetime import datetime


def safe_int(value: object) -> int | None:
    """
    Safely convert a value to an integer.

    Supports:
    - int
    - float
    - str (if numeric)
    - datetime (converted to UNIX timestamp)

    Returns None if conversion fails.
    """
    try:
        if isinstance(value, datetime):
            return int(value.timestamp())
        if isinstance(value, (int, float)):
            return int(value)
        if isinstance(value, str) and value.isdigit():
            return int(value)
    except (TypeError, ValueError):
        pass
    return None


def safe_float(value: object) -> float | None:
    """
    Safely convert a value to a float.

    Supports:
    - int
    - float
    - str (if numeric)
    - datetime (converted to UNIX timestamp)

    Returns None if conversion fails.
    """
    try:
        if isinstance(value, datetime):
            return float(value.timestamp())
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            return float(value)
    except (TypeError, ValueError):
        pass
    return None


def safe_string(value: object) -> str | None:
    """
    Safely convert a value to a string.

    Supports:
    - str
    - int
    - float
    - datetime (converted to ISO format)

    Returns None if conversion fails.
    """
    try:
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, (int, float)):
            return str(value)
        if isinstance(value, str):
            return value
    except (TypeError, ValueError):
        pass
    return None
