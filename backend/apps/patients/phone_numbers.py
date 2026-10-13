import phonenumbers


DEFAULT_REGION = "PH"


def normalize_contact_number(value: str, default_region: str = DEFAULT_REGION) -> str:
    """Parse flexible phone input and return canonical E.164 format."""
    raw = (value or "").strip()
    if not raw:
        raise ValueError("Contact number is required.")

    try:
        parsed = phonenumbers.parse(raw, default_region)
    except phonenumbers.NumberParseException as exc:
        raise ValueError("Enter a valid contact number.") from exc

    if not phonenumbers.is_valid_number(parsed):
        raise ValueError("Enter a valid contact number.")

    return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)


def format_contact_number(value: str, default_region: str = DEFAULT_REGION) -> str:
    """Format stored/legacy values to international display format when possible."""
    raw = (value or "").strip()
    if not raw:
        return ""

    try:
        parsed = phonenumbers.parse(raw, default_region)
    except phonenumbers.NumberParseException:
        return raw

    if not phonenumbers.is_valid_number(parsed):
        return raw

    return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL)