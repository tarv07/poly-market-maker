"""WebSocket client for Polymarket market channel. Read-only; no auth."""

import asyncio
import json
import logging
from typing import Any

import websockets
from websockets.asyncio.client import ClientConnection

from poly_market_maker.book.orderbook import L2OrderBook

DEFAULT_WS_URL = "wss://ws-subscriptions-clob.polymarket.com/ws/market"
HEARTBEAT_INTERVAL = 10.0
RECONNECT_INITIAL = 1.0
RECONNECT_MAX = 60.0


def _parse_level(obj: Any) -> tuple[Any, Any]:
    """Parse {price, size} from event; book will use Decimal for strings like '.48'."""
    if isinstance(obj, dict):
        return (obj.get("price"), obj.get("size"))
    return (None, None)


class MarketWsClient:
    """
    Subscribes to one or more asset IDs, maintains L2 books, exposes best bid/ask/midpoint.
    Reconnects with exponential backoff. Sends heartbeat {} every 10s while connected.
    """

    def __init__(
        self,
        asset_ids: list[str],
        ws_url: str = DEFAULT_WS_URL,
    ) -> None:
        self._asset_ids = [str(a) for a in asset_ids]
        self._ws_url = ws_url
        self._books: dict[str, L2OrderBook] = {a: L2OrderBook() for a in self._asset_ids}
        self._logger = logging.getLogger(self.__class__.__name__)
        self._ws: ClientConnection | None = None
        self._reconnect_attempt = 0
        self._heartbeat_task: asyncio.Task[None] | None = None

    def get_best_bid(self, asset_id: str) -> float | None:
        book = self._books.get(str(asset_id))
        return book.best_bid() if book else None

    def get_best_ask(self, asset_id: str) -> float | None:
        book = self._books.get(str(asset_id))
        return book.best_ask() if book else None

    def get_midpoint(self, asset_id: str) -> float | None:
        book = self._books.get(str(asset_id))
        return book.midpoint() if book else None

    async def run(self) -> None:
        """Run connect/receive loop with reconnect and heartbeat."""
        while True:
            try:
                async with websockets.connect(
                    self._ws_url,
                    ping_interval=None,
                    ping_timeout=None,
                    close_timeout=5,
                ) as ws:
                    self._ws = ws
                    self._reconnect_attempt = 0
                    await self._subscribe(ws)
                    self._heartbeat_task = asyncio.create_task(self._heartbeat_loop(ws))
                    try:
                        await self._receive_loop(ws)
                    finally:
                        self._cancel_heartbeat()
            except Exception as e:
                self._logger.warning("WebSocket error: %s", e)
            finally:
                self._ws = None
                self._cancel_heartbeat()

            delay = min(
                RECONNECT_INITIAL * (2**self._reconnect_attempt),
                RECONNECT_MAX,
            )
            self._reconnect_attempt += 1
            self._logger.info("Reconnecting in %.1fs (attempt %d)", delay, self._reconnect_attempt)
            await asyncio.sleep(delay)

    def _cancel_heartbeat(self) -> None:
        if self._heartbeat_task and not self._heartbeat_task.done():
            self._heartbeat_task.cancel()
            self._heartbeat_task = None

    async def _heartbeat_loop(self, ws: ClientConnection) -> None:
        """Send {} every 10s while connected."""
        try:
            while True:
                await asyncio.sleep(HEARTBEAT_INTERVAL)
                await ws.send("{}")
                self._logger.debug("Heartbeat sent")
        except asyncio.CancelledError:
            pass

    async def _subscribe(self, ws: ClientConnection) -> None:
        msg = {
            "assets_ids": self._asset_ids,
            "type": "market",
            "custom_feature_enabled": True,
        }
        await ws.send(json.dumps(msg))
        self._logger.info("Subscribed to assets: %s", self._asset_ids)

    async def _receive_loop(self, ws: ClientConnection) -> None:
        async for raw in ws:
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                continue
            event_type = data.get("event_type") or data.get("type")
            if event_type == "book":
                self._on_book(data)
            elif event_type == "price_change":
                self._on_price_change(data)

    def _on_book(self, data: dict[str, Any]) -> None:
        asset_id = str(data.get("asset_id", ""))
        if asset_id not in self._books:
            return
        bids_raw = data.get("bids") or []
        asks_raw = data.get("asks") or []
        bids = [_parse_level(x) for x in bids_raw]
        asks = [_parse_level(x) for x in asks_raw]
        self._books[asset_id].apply_snapshot(bids, asks)
        self._logger.debug("Book snapshot for %s: %d bids, %d asks", asset_id, len(bids), len(asks))

    def _on_price_change(self, data: dict[str, Any]) -> None:
        for pc in data.get("price_changes") or []:
            asset_id = str(pc.get("asset_id", ""))
            if asset_id not in self._books:
                continue
            side = pc.get("side", "BUY")
            price = pc.get("price")
            size = pc.get("size", "0")
            self._books[asset_id].apply_price_change(side, price, size)
