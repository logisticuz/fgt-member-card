"""
Personnummer validation — copied from fgt-checkin-system/backend/validation.py.
Swedish personal ID number validation with Luhn algorithm.
"""


def sanitize_personnummer(value: str) -> str:
    """Remove dashes, spaces, keep only digits."""
    if not value:
        return ""
    return "".join(c for c in value if c.isdigit())


def validate_personnummer(value: str) -> tuple[bool, str | None]:
    """
    Validate a Swedish personnummer (10 or 12 digits).
    Returns (is_valid, error_message).
    """
    if not value:
        return False, "Personnummer krävs"

    digits = sanitize_personnummer(value)

    if len(digits) not in (10, 12):
        return False, "Personnummer måste vara 10 eller 12 siffror"

    # Use last 10 digits for validation
    check_digits = digits[-10:]

    # Validate month (1-12)
    month = int(check_digits[2:4])
    if month < 1 or month > 12:
        return False, "Ogiltig månad i personnummer"

    # Validate day (1-31)
    day = int(check_digits[4:6])
    if day < 1 or day > 31:
        return False, "Ogiltig dag i personnummer"

    # Luhn checksum
    weights = [2, 1, 2, 1, 2, 1, 2, 1, 2, 1]
    total = 0
    for i, digit in enumerate(check_digits):
        product = int(digit) * weights[i]
        if product >= 10:
            product -= 9
        total += product

    if total % 10 != 0:
        return False, "Ogiltigt personnummer (kontrollsiffra stämmer inte)"

    return True, None
