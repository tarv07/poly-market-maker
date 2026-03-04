"""Local L2 orderbook model for a single asset. BUY -> bids, SELL -> asks."""

from decimal import Decimal
from typing import Any

# Side mapping: BUY -> bids, SELL -> asks
BUY, SELL = "BUY", "SELL"


def _to_decimal(value: Any) -> Decimal:
    """Parse price or size to Decimal; handles strings like '.48'."""
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float)):
        return Decimal(str(value))
    return Decimal(str(value).strip())


class L2OrderBook:
    """
    L2 order book for one asset. Bids sorted descending, asks ascending.
    Prices and sizes stored as Decimal; getters return float for API use.
    """

    def __init__(self) -> None:
        # List of (price, size) — bids desc, asks asc
        self._bids: list[tuple[Decimal, Decimal]] = []
        self._asks: list[tuple[Decimal, Decimal]] = []

    def apply_snapshot(
        self,
        bids: list[tuple[Any, Any]],
        asks: list[tuple[Any, Any]],
    ) -> None:
        """Replace book with snapshot. Inputs are (price, size); we sort internally."""
        self._bids = [
            (_to_decimal(p), _to_decimal(s))
            for p, s in (bids or [])
            if _to_decimal(s) > 0
        ]
        self._asks = [
            (_to_decimal(p), _to_decimal(s))
            for p, s in (asks or [])
            if _to_decimal(s) > 0
        ]
        self._bids.sort(key=lambda x: x[0], reverse=True)
        self._asks.sort(key=lambda x: x[0])

    def apply_price_change(self, side: str, price: Any, size: Any) -> None:
        """Update one level. BUY -> bids, SELL -> asks. size 0 removes the level."""
        p = _to_decimal(price)
        s = _to_decimal(size)
        if side.upper() == BUY:
            self._update_side(self._bids, p, s, descending=True)
        else:
            self._update_side(self._asks, p, s, descending=False)

    def _update_side(
        self,
        side_list: list[tuple[Decimal, Decimal]],
        price: Decimal,
        size: Decimal,
        *,
        descending: bool,
    ) -> None:
        for i, (px, _) in enumerate(side_list):
            if px == price:
                if size <= 0:
                    side_list.pop(i)
                else:
                    side_list[i] = (price, size)
                return
        if size > 0:
            side_list.append((price, size))
            side_list.sort(key=lambda x: x[0], reverse=descending)

    def best_bid(self) -> float | None:
        if not self._bids:
            return None
        return float(self._bids[0][0])

    def best_ask(self) -> float | None:
        if not self._asks:
            return None
        return float(self._asks[0][0])

    def midpoint(self) -> float | None:
        bb, ba = self.best_bid(), self.best_ask()
        if bb is None or ba is None:
            return None
        return (bb + ba) / 2.0
