"""Dry-run quoting: compute target two-sided quotes from midpoint. No order placement."""

from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR


def round_down_to_tick(price: float, tick: float) -> float:
    """Round price down to nearest tick using Decimal (no float round())."""
    if tick <= 0:
        raise ValueError("tick must be positive")
    p = Decimal(str(price))
    t = Decimal(str(tick))
    return float((p / t).to_integral_value(rounding=ROUND_FLOOR) * t)


def round_up_to_tick(price: float, tick: float) -> float:
    """Round price up to nearest tick using Decimal (no float round())."""
    if tick <= 0:
        raise ValueError("tick must be positive")
    p = Decimal(str(price))
    t = Decimal(str(tick))
    return float((p / t).to_integral_value(rounding=ROUND_CEILING) * t)


def compute_quotes(
    mid: float | None,
    tick: float,
    spread: float,
    size: float,
) -> list[dict] | None:
    """
    Produce target two-sided quotes. Spread is in absolute price units (0–1).
    BUY at mid - spread/2 (round down to tick), SELL at mid + spread/2 (round up to tick).
    Returns None if insufficient book (mid is None) or validation fails.
    Validation: tick > 0, size > 0, spread >= 0, 0 < mid < 1.
    """
    if mid is None:
        return None
    if tick <= 0 or size <= 0 or spread < 0:
        return None
    if not (0 < mid < 1):
        return None
    buy_price = round_down_to_tick(mid - spread / 2, tick)
    sell_price = round_up_to_tick(mid + spread / 2, tick)
    return [
        {"side": "BUY", "price": buy_price, "size": size},
        {"side": "SELL", "price": sell_price, "size": size},
    ]
