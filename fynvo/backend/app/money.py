from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


def parse_money(value) -> int:
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("Invalid monetary amount") from exc
    cents = (amount * Decimal("100")).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return int(cents)


def format_money(cents: int) -> str:
    sign = "-" if cents < 0 else ""
    absolute = abs(cents)
    return f"{sign}${absolute // 100:,}.{absolute % 100:02d}"


def cents_to_decimal(cents: int) -> str:
    sign = "-" if cents < 0 else ""
    absolute = abs(cents)
    return f"{sign}{absolute // 100}.{absolute % 100:02d}"
