"""Phone normalization helpers."""

import re

E164 = re.compile(r"^\+[1-9]\d{7,14}$")


def normalize_phone(value: str, default_country_code: str = "52") -> str:
    digits = "".join(character for character in value if character.isdigit())
    if value.strip().startswith("+"):
        normalized = f"+{digits}"
    elif len(digits) == 10:
        normalized = f"+{default_country_code}{digits}"
    else:
        normalized = f"+{digits}"
    if not E164.fullmatch(normalized):
        raise ValueError("Phone number is not valid E.164")
    return normalized
