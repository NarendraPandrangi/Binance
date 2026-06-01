from __future__ import annotations

import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from trading_bot.client import (
    BinanceAPIError,
    BinanceFuturesClient,
    BinanceNetworkError,
)
from trading_bot.logging_config import configure_logging
from trading_bot.orders import OrderRequest, OrderService
from trading_bot.validators import ValidationError


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


LOGGER = configure_logging()


HTML_PAGE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Binance Futures Testnet Bot</title>
  <style>
    :root {
      color-scheme: dark;
      font-family: Inter, Segoe UI, Arial, sans-serif;
      background: #111318;
      color: #eef1f7;
    }
    * { box-sizing: border-box; }
    body { margin: 0; min-height: 100vh; background: #111318; }
    main { width: min(980px, calc(100% - 32px)); margin: 0 auto; padding: 32px 0; }
    h1 {
      margin: 0 0 6px;
      font-size: clamp(28px, 5vw, 44px);
      line-height: 1.05;
      letter-spacing: 0;
    }
    .subtitle { margin: 0 0 28px; color: #aab2c3; font-size: 16px; }
    .layout {
      display: grid;
      grid-template-columns: minmax(0, 1fr) minmax(280px, 380px);
      gap: 18px;
      align-items: start;
    }
    form, .result {
      border: 1px solid #2c3340;
      border-radius: 8px;
      background: #191d25;
      padding: 18px;
    }
    .grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 14px;
    }
    label {
      display: grid;
      gap: 7px;
      color: #c7cede;
      font-size: 13px;
      font-weight: 700;
    }
    input, select {
      width: 100%;
      min-height: 42px;
      border: 1px solid #3a4352;
      border-radius: 6px;
      background: #10131a;
      color: #f6f8fb;
      padding: 10px 11px;
      font: inherit;
    }
    input:focus, select:focus {
      outline: 2px solid #f0b90b;
      outline-offset: 1px;
      border-color: #f0b90b;
    }
    .actions {
      display: flex;
      gap: 12px;
      align-items: center;
      margin-top: 16px;
      flex-wrap: wrap;
    }
    button {
      min-height: 42px;
      border: 0;
      border-radius: 6px;
      background: #f0b90b;
      color: #171717;
      padding: 0 18px;
      font: inherit;
      font-weight: 800;
      cursor: pointer;
    }
    button:disabled { cursor: wait; opacity: .65; }
    .dry-run {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      color: #d6dbea;
      font-size: 14px;
      font-weight: 600;
    }
    .dry-run input { width: 18px; min-height: 18px; }
    .result h2 { margin: 0 0 12px; font-size: 18px; }
    pre {
      min-height: 260px;
      margin: 0;
      white-space: pre-wrap;
      word-break: break-word;
      color: #dfe5f2;
      font-size: 13px;
      line-height: 1.5;
    }
    .status { margin: 0 0 12px; color: #8bd88b; font-weight: 800; }
    .status.error { color: #ff6978; }
    @media (max-width: 760px) {
      .layout, .grid { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <main>
    <h1>Binance Futures Testnet Bot</h1>
    <p class="subtitle">Place USDT-M MARKET, LIMIT, and STOP-LIMIT orders using your local .env credentials.</p>

    <div class="layout">
      <form id="orderForm">
        <div class="grid">
          <label>Symbol
            <input name="symbol" value="BTCUSDT" autocomplete="off" required>
          </label>
          <label>Side
            <select name="side">
              <option>BUY</option>
              <option>SELL</option>
            </select>
          </label>
          <label>Order Type
            <select name="order_type" id="orderType">
              <option>MARKET</option>
              <option>LIMIT</option>
              <option>STOP_LIMIT</option>
            </select>
          </label>
          <label>Quantity
            <input name="quantity" value="0.001" inputmode="decimal" required>
          </label>
          <label id="priceField">Price
            <input name="price" id="priceInput" value="75000" inputmode="decimal">
          </label>
          <label id="stopPriceField">Stop Price
            <input name="stop_price" id="stopPriceInput" value="74500" inputmode="decimal">
          </label>
        </div>
        <div class="actions">
          <button id="submitButton" type="submit">Submit Order</button>
          <label class="dry-run">
            <input name="dry_run" type="checkbox" checked>
            Dry run
          </label>
        </div>
      </form>

      <section class="result">
        <h2>Result</h2>
        <p id="status" class="status">Ready</p>
        <pre id="output">Use dry run first to preview the request. Uncheck dry run only when you want to send the order to Binance Futures Testnet.</pre>
      </section>
    </div>
  </main>

  <script>
    const form = document.querySelector("#orderForm");
    const orderType = document.querySelector("#orderType");
    const priceInput = document.querySelector("#priceInput");
    const stopPriceInput = document.querySelector("#stopPriceInput");
    const priceField = document.querySelector("#priceField");
    const stopPriceField = document.querySelector("#stopPriceField");
    const statusEl = document.querySelector("#status");
    const outputEl = document.querySelector("#output");
    const submitButton = document.querySelector("#submitButton");

    function syncFields() {
      const type = orderType.value;
      priceField.style.display = type === "MARKET" ? "none" : "grid";
      stopPriceField.style.display = type === "STOP_LIMIT" ? "grid" : "none";
      priceInput.required = type !== "MARKET";
      stopPriceInput.required = type === "STOP_LIMIT";
    }

    orderType.addEventListener("change", syncFields);
    syncFields();

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      submitButton.disabled = true;
      statusEl.textContent = "Sending...";
      statusEl.className = "status";

      const data = Object.fromEntries(new FormData(form).entries());
      data.dry_run = form.dry_run.checked;
      if (data.order_type === "MARKET") {
        delete data.price;
        delete data.stop_price;
      }
      if (data.order_type === "LIMIT") {
        delete data.stop_price;
      }

      try {
        const response = await fetch("/api/orders", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(data)
        });
        const body = await response.json();
        statusEl.textContent = body.success ? "Success" : "Failure";
        statusEl.className = body.success ? "status" : "status error";
        outputEl.textContent = JSON.stringify(body, null, 2);
      } catch (error) {
        statusEl.textContent = "Failure";
        statusEl.className = "status error";
        outputEl.textContent = String(error);
      } finally {
        submitButton.disabled = false;
      }
    });
  </script>
</body>
</html>
"""


def place_order_from_ui(data: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    try:
        order_request = OrderRequest.from_cli(
            symbol=str(data.get("symbol", "")),
            side=str(data.get("side", "")),
            order_type=str(data.get("order_type", "")),
            quantity=str(data.get("quantity", "")),
            price=_optional_value(data.get("price")),
            stop_price=_optional_value(data.get("stop_price")),
        )
    except ValidationError as exc:
        LOGGER.error("UI validation error: %s", exc)
        return 400, {"success": False, "message": str(exc)}

    summary = order_request.summary()
    LOGGER.info("UI validated order request: %s", summary)

    if bool(data.get("dry_run", False)):
        return 200, {
            "success": True,
            "message": "Dry run complete. No order was sent to Binance.",
            "request": summary,
        }

    api_key = os.getenv("BINANCE_API_KEY", "")
    api_secret = os.getenv("BINANCE_API_SECRET", "")
    base_url = os.getenv("BINANCE_FUTURES_BASE_URL") or "https://testnet.binancefuture.com"

    try:
        client = BinanceFuturesClient(
            api_key=api_key,
            api_secret=api_secret,
            base_url=base_url,
            logger=LOGGER,
        )
        response = OrderService(client).place(order_request)
    except ValueError as exc:
        LOGGER.error("UI configuration error: %s", exc)
        return 400, {"success": False, "message": str(exc)}
    except (BinanceNetworkError, BinanceAPIError) as exc:
        return 502, {"success": False, "message": str(exc), "request": summary}
    except Exception as exc:
        LOGGER.exception("Unexpected UI application error: %s", exc)
        return 500, {"success": False, "message": f"Unexpected error: {exc}"}

    return 200, {
        "success": True,
        "message": "Order submitted to Binance Futures Testnet.",
        "request": summary,
        "response": {
            "orderId": response.get("orderId"),
            "status": response.get("status"),
            "executedQty": response.get("executedQty"),
            "avgPrice": response.get("avgPrice"),
            "clientOrderId": response.get("clientOrderId"),
        },
    }


def _optional_value(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


class TradingBotRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path in {"/", "/index.html"}:
            self._send_html(HTML_PAGE)
            return
        if self.path == "/api/health":
            self._send_json(200, {"success": True, "message": "OK"})
            return
        self._send_json(404, {"success": False, "message": "Not found"})

    def do_POST(self) -> None:
        if self.path != "/api/orders":
            self._send_json(404, {"success": False, "message": "Not found"})
            return

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            raw_body = self.rfile.read(content_length).decode("utf-8")
            payload = json.loads(raw_body or "{}")
        except (ValueError, json.JSONDecodeError):
            self._send_json(400, {"success": False, "message": "Invalid JSON body"})
            return

        status_code, body = place_order_from_ui(payload)
        self._send_json(status_code, body)

    def log_message(self, format: str, *args: Any) -> None:
        LOGGER.info("UI server | " + format, *args)

    def _send_html(self, body: str) -> None:
        encoded = body.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _send_json(self, status_code: int, body: dict[str, Any]) -> None:
        encoded = json.dumps(body, indent=2).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


def main() -> int:
    load_dotenv()
    host = os.getenv("TRADING_BOT_UI_HOST", "127.0.0.1")
    port = int(os.getenv("TRADING_BOT_UI_PORT", "8000"))
    server = ThreadingHTTPServer((host, port), TradingBotRequestHandler)
    url = f"http://{host}:{port}"
    print(f"Trading bot UI running at {url}")
    print("Press Ctrl+C to stop.")
    LOGGER.info("Trading bot UI started at %s", url)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping trading bot UI.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
