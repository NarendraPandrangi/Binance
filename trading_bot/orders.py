from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from trading_bot.validators import (
    ValidationError,
    decimal_to_api_string,
    normalize_order_type,
    normalize_side,
    normalize_symbol,
    positive_decimal,
)


@dataclass(frozen=True)
class OrderRequest:
    symbol: str
    side: str
    order_type: str
    quantity: Decimal
    price: Decimal | None = None
    stop_price: Decimal | None = None

    @classmethod
    def from_cli(
        cls,
        symbol: str,
        side: str,
        order_type: str,
        quantity: str,
        price: str | None = None,
        stop_price: str | None = None,
    ) -> "OrderRequest":
        normalized_type = normalize_order_type(order_type)
        parsed_price = positive_decimal(price, "Price") if price else None
        parsed_stop_price = (
            positive_decimal(stop_price, "Stop price") if stop_price else None
        )

        if normalized_type == "MARKET" and parsed_price is not None:
            raise ValidationError("Price is not accepted for MARKET orders.")

        if normalized_type == "LIMIT" and parsed_price is None:
            raise ValidationError("Price is required for LIMIT orders.")

        if normalized_type == "STOP_LIMIT":
            if parsed_price is None:
                raise ValidationError("Price is required for STOP_LIMIT orders.")
            if parsed_stop_price is None:
                raise ValidationError("Stop price is required for STOP_LIMIT orders.")

        return cls(
            symbol=normalize_symbol(symbol),
            side=normalize_side(side),
            order_type=normalized_type,
            quantity=positive_decimal(quantity, "Quantity"),
            price=parsed_price,
            stop_price=parsed_stop_price,
        )

    def to_api_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "symbol": self.symbol,
            "side": self.side,
            "type": "STOP" if self.order_type == "STOP_LIMIT" else self.order_type,
            "quantity": decimal_to_api_string(self.quantity),
        }

        if self.order_type in {"LIMIT", "STOP_LIMIT"}:
            payload["price"] = decimal_to_api_string(self.price)  # type: ignore[arg-type]
            payload["timeInForce"] = "GTC"

        if self.order_type == "STOP_LIMIT":
            payload["stopPrice"] = decimal_to_api_string(self.stop_price)  # type: ignore[arg-type]

        return payload

    def summary(self) -> dict[str, str]:
        data = {
            "symbol": self.symbol,
            "side": self.side,
            "type": self.order_type,
            "quantity": decimal_to_api_string(self.quantity),
        }
        if self.price is not None:
            data["price"] = decimal_to_api_string(self.price)
        if self.stop_price is not None:
            data["stopPrice"] = decimal_to_api_string(self.stop_price)
        return data


class OrderService:
    def __init__(self, client: Any) -> None:
        self.client = client

    def place(self, order_request: OrderRequest) -> dict[str, Any]:
        return self.client.place_order(order_request.to_api_payload())
