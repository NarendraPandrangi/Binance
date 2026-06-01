from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation


VALID_SIDES = {"BUY", "SELL"}
VALID_ORDER_TYPES = {"MARKET", "LIMIT", "STOP_LIMIT"}
SYMBOL_PATTERN = re.compile(r"^[A-Z0-9]{5,20}$")


class ValidationError(ValueError):
    """Raised when CLI input is invalid."""


def normalize_symbol(symbol: str) -> str:
    normalized = symbol.strip().upper()
    if not SYMBOL_PATTERN.fullmatch(normalized):
        raise ValidationError(
            "Symbol must contain only letters/numbers, for example BTCUSDT."
        )
    return normalized


def normalize_side(side: str) -> str:
    normalized = side.strip().upper()
    if normalized not in VALID_SIDES:
        raise ValidationError("Side must be BUY or SELL.")
    return normalized


def normalize_order_type(order_type: str) -> str:
    normalized = order_type.strip().upper().replace("-", "_")
    if normalized not in VALID_ORDER_TYPES:
        raise ValidationError("Order type must be MARKET, LIMIT, or STOP_LIMIT.")
    return normalized


def positive_decimal(value: str, field_name: str) -> Decimal:
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValidationError(f"{field_name} must be a valid number.") from exc

    if parsed <= 0:
        raise ValidationError(f"{field_name} must be greater than zero.")
    return parsed


def decimal_to_api_string(value: Decimal) -> str:
    return format(value.normalize(), "f")
