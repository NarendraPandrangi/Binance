from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
from typing import Any
from urllib.parse import urlencode
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class BinanceAPIError(RuntimeError):
    """Raised when Binance returns an error response."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class BinanceNetworkError(RuntimeError):
    """Raised when the HTTP request cannot reach Binance."""


class BinanceFuturesClient:
    def __init__(
        self,
        api_key: str,
        api_secret: str,
        base_url: str = "https://testnet.binancefuture.com",
        timeout: int = 15,
        logger: logging.Logger | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("API key is required.")
        if not api_secret:
            raise ValueError("API secret is required.")

        self.api_key = api_key
        self.api_secret = api_secret.encode("utf-8")
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.logger = logger or logging.getLogger("trading_bot")

    def place_order(self, order_payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", "/fapi/v1/order", params=order_payload, signed=True)

    def _request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        signed: bool = False,
    ) -> dict[str, Any]:
        request_params = dict(params or {})

        if signed:
            request_params["timestamp"] = int(time.time() * 1000)
            request_params.setdefault("recvWindow", 5000)
            request_params["signature"] = self._signature(request_params)

        url = f"{self.base_url}{path}"
        headers = {"X-MBX-APIKEY": self.api_key}
        safe_params = self._safe_params(request_params)
        query_string = urlencode(request_params, doseq=True)
        request_url = f"{url}?{query_string}" if query_string else url

        self.logger.info(
            "API request | method=%s | path=%s | params=%s",
            method,
            path,
            safe_params,
        )

        try:
            request = Request(request_url, headers=headers, method=method)
            with urlopen(request, timeout=self.timeout) as response:
                status_code = response.status
                body_text = response.read().decode("utf-8")
        except HTTPError as exc:
            status_code = exc.code
            body_text = exc.read().decode("utf-8")
            body = self._parse_json(body_text)
            self.logger.info(
                "API response | status_code=%s | body=%s",
                status_code,
                body,
            )
            message = body.get("msg") if isinstance(body, dict) else body_text
            code = body.get("code") if isinstance(body, dict) else "unknown"
            error_message = f"Binance API error {code}: {message}"
            self.logger.error(error_message)
            raise BinanceAPIError(error_message, status_code) from exc
        except URLError as exc:
            self.logger.exception("Network failure while calling Binance: %s", exc)
            raise BinanceNetworkError(f"Network failure: {exc}") from exc

        body = self._parse_json(body_text)
        self.logger.info(
            "API response | status_code=%s | body=%s",
            status_code,
            body,
        )

        if not isinstance(body, dict):
            raise BinanceAPIError("Unexpected non-JSON response from Binance.")

        return body

    def _signature(self, params: dict[str, Any]) -> str:
        query_string = urlencode(params, doseq=True)
        return hmac.new(
            self.api_secret,
            query_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    @staticmethod
    def _parse_json(body_text: str) -> Any:
        try:
            return json.loads(body_text)
        except json.JSONDecodeError:
            return {"raw": body_text}

    @staticmethod
    def _safe_params(params: dict[str, Any]) -> dict[str, Any]:
        safe = dict(params)
        if "signature" in safe:
            safe["signature"] = "***"
        return safe
