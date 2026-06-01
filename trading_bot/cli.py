from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:
    def load_dotenv() -> bool:
        env_path = Path(".env")
        if not env_path.exists():
            return False
        for line in env_path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
        return True

from trading_bot.client import (
    BinanceAPIError,
    BinanceFuturesClient,
    BinanceNetworkError,
)
from trading_bot.logging_config import configure_logging
from trading_bot.orders import OrderRequest, OrderService
from trading_bot.validators import ValidationError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Place Binance USDT-M Futures Testnet orders."
    )
    parser.add_argument("--symbol", required=True, help="Trading pair, e.g. BTCUSDT")
    parser.add_argument("--side", required=True, help="BUY or SELL")
    parser.add_argument(
        "--type",
        required=True,
        dest="order_type",
        help="MARKET, LIMIT, or STOP_LIMIT",
    )
    parser.add_argument("--quantity", required=True, help="Order quantity")
    parser.add_argument("--price", help="Required for LIMIT and STOP_LIMIT orders")
    parser.add_argument("--stop-price", help="Required for STOP_LIMIT orders")
    parser.add_argument(
        "--base-url",
        default=None,
        help="Binance Futures base URL. Defaults to testnet env value.",
    )
    parser.add_argument("--api-key", default=None, help="Optional API key override")
    parser.add_argument("--api-secret", default=None, help="Optional API secret override")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and print the order without sending it to Binance.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    logger = configure_logging()
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        order_request = OrderRequest.from_cli(
            symbol=args.symbol,
            side=args.side,
            order_type=args.order_type,
            quantity=args.quantity,
            price=args.price,
            stop_price=args.stop_price,
        )
    except ValidationError as exc:
        logger.error("Validation error: %s", exc)
        print(f"Invalid input: {exc}")
        return 2

    print_order_summary(order_request.summary())
    logger.info("Validated order request: %s", order_request.summary())

    if args.dry_run:
        print("\nDry run complete. No order was sent to Binance.")
        return 0

    api_key = args.api_key or os.getenv("BINANCE_API_KEY", "")
    api_secret = args.api_secret or os.getenv("BINANCE_API_SECRET", "")
    base_url = (
        args.base_url
        or os.getenv("BINANCE_FUTURES_BASE_URL")
        or "https://testnet.binancefuture.com"
    )

    try:
        client = BinanceFuturesClient(
            api_key=api_key,
            api_secret=api_secret,
            base_url=base_url,
            logger=logger,
        )
        response = OrderService(client).place(order_request)
    except ValueError as exc:
        logger.error("Configuration error: %s", exc)
        print(f"\nFailure: {exc}")
        print("Check BINANCE_API_KEY and BINANCE_API_SECRET in your .env file.")
        return 2
    except BinanceNetworkError as exc:
        print(f"\nFailure: {exc}")
        return 1
    except BinanceAPIError as exc:
        print(f"\nFailure: {exc}")
        return 1
    except Exception as exc:
        logger.exception("Unexpected application error: %s", exc)
        print(f"\nFailure: unexpected error: {exc}")
        return 1

    print_order_response(response)
    print("\nSuccess: order submitted to Binance Futures Testnet.")
    return 0


def print_order_summary(summary: dict[str, str]) -> None:
    print("Order request summary")
    print("---------------------")
    for key, value in summary.items():
        print(f"{key}: {value}")


def print_order_response(response: dict[str, Any]) -> None:
    print("\nOrder response details")
    print("----------------------")
    fields = {
        "orderId": response.get("orderId"),
        "status": response.get("status"),
        "executedQty": response.get("executedQty"),
        "avgPrice": response.get("avgPrice"),
    }
    for key, value in fields.items():
        print(f"{key}: {value if value is not None else 'N/A'}")

    client_order_id = response.get("clientOrderId")
    if client_order_id:
        print(f"clientOrderId: {client_order_id}")


if __name__ == "__main__":
    sys.exit(main())
