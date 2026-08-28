from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any


@dataclass
class AngelOneSession:
    client: Any
    refresh_token: str | None = None


class AngelOneAdapter:
    """Lazy Angel One SmartAPI adapter.

    This class intentionally has no order-placement method. The first release
    can authenticate and read market data, while all order previews remain
    paper-only until the safety and compliance review is complete.
    """

    def __init__(self) -> None:
        self.api_key = os.getenv("ANGELONE_API_KEY", "").strip()
        self.client_id = os.getenv("ANGELONE_CLIENT_ID", "").strip()
        self.pin = os.getenv("ANGELONE_PIN", "").strip()
        self.totp_secret = os.getenv("ANGELONE_TOTP_SECRET", "").strip()
        self.session: AngelOneSession | None = None

    @property
    def configured(self) -> bool:
        return all((self.api_key, self.client_id, self.pin, self.totp_secret))

    def configuration_status(self) -> dict[str, Any]:
        return {
            "configured": self.configured,
            "broker": "Angel One SmartAPI",
            "dataAccess": "read-only adapter",
            "liveOrders": False,
            "message": (
                "Credentials are available to the backend; login is explicit."
                if self.configured
                else "Add rotated SmartAPI values to the local backend .env file."
            ),
        }

    def login(self) -> dict[str, Any]:
        if not self.configured:
            return {"status": False, "message": "SmartAPI credentials are not configured."}

        try:
            import pyotp
            from SmartApi import SmartConnect
        except ImportError as exc:
            return {
                "status": False,
                "message": "Install broker extras before connecting: pip install -r services/api/requirements-broker.txt",
                "error": str(exc),
            }

        try:
            client = SmartConnect(self.api_key)
            totp = pyotp.TOTP(self.totp_secret).now()
            response = client.generateSession(self.client_id, self.pin, totp)
            if not response.get("status"):
                return {
                    "status": False,
                    "message": "SmartAPI rejected the read-only session request.",
                    "errorCode": response.get("errorcode"),
                }
            data = response.get("data") or {}
            self.session = AngelOneSession(
                client=client,
                refresh_token=data.get("refreshToken"),
            )
            return {"status": True, "message": "Read-only SmartAPI session established."}
        except Exception as exc:
            return {
                "status": False,
                "message": "SmartAPI connection failed without exposing credentials.",
                "error": type(exc).__name__,
            }

    def _client(self) -> Any:
        if self.session is None:
            result = self.login()
            if not result.get("status"):
                raise RuntimeError(result.get("message", "SmartAPI session unavailable"))
        return self.session.client

    def get_ltp(self, exchange: str, symbol: str, symbol_token: str) -> dict[str, Any]:
        return self._client().ltpData(exchange, symbol, symbol_token)

    def get_candles(
        self,
        exchange: str,
        symbol_token: str,
        interval: str,
        from_date: str,
        to_date: str,
    ) -> dict[str, Any]:
        params = {
            "exchange": exchange,
            "symboltoken": symbol_token,
            "interval": interval,
            "fromdate": from_date,
            "todate": to_date,
        }
        return self._client().getCandleData(params)

    def close(self) -> None:
        if self.session is not None:
            try:
                self.session.client.terminateSession(self.client_id)
            finally:
                self.session = None
