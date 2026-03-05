"""Unit tests for dry-run quoting: round_down/round_up_to_tick and compute_quotes."""

from unittest import TestCase

from poly_market_maker.quoting import (
    round_down_to_tick,
    round_up_to_tick,
    compute_quotes,
)


class TestRoundToTick(TestCase):
    """Tests for Decimal-based round_down_to_tick and round_up_to_tick."""

    def test_round_down_basic(self) -> None:
        self.assertEqual(round_down_to_tick(0.523, 0.01), 0.52)
        self.assertEqual(round_down_to_tick(0.529, 0.01), 0.52)
        self.assertEqual(round_down_to_tick(0.52, 0.01), 0.52)

    def test_round_up_basic(self) -> None:
        self.assertEqual(round_up_to_tick(0.521, 0.01), 0.53)
        self.assertEqual(round_up_to_tick(0.53, 0.01), 0.53)
        self.assertEqual(round_up_to_tick(0.525, 0.01), 0.53)

    def test_round_down_with_point_one_tick(self) -> None:
        self.assertEqual(round_down_to_tick(0.5, 0.1), 0.5)
        self.assertEqual(round_down_to_tick(0.55, 0.1), 0.5)
        self.assertEqual(round_down_to_tick(0.99, 0.1), 0.9)

    def test_round_up_with_point_one_tick(self) -> None:
        self.assertEqual(round_up_to_tick(0.5, 0.1), 0.5)
        self.assertEqual(round_up_to_tick(0.51, 0.1), 0.6)
        self.assertEqual(round_up_to_tick(0.01, 0.1), 0.1)

    def test_tick_must_be_positive(self) -> None:
        with self.assertRaises(ValueError):
            round_down_to_tick(0.5, 0)
        with self.assertRaises(ValueError):
            round_up_to_tick(0.5, -0.01)


class TestComputeQuotes(TestCase):
    """Tests for compute_quotes: BUY round down, SELL round up; validation."""

    def test_mid_none_returns_none(self) -> None:
        self.assertIsNone(compute_quotes(None, 0.01, 0.04, 10.0))

    def test_mid_valid_produces_two_quotes(self) -> None:
        # mid=0.5, spread=0.04 -> buy at 0.48, sell at 0.52 (tick 0.01)
        quotes = compute_quotes(0.5, 0.01, 0.04, 10.0)
        self.assertIsNotNone(quotes)
        self.assertEqual(len(quotes), 2)
        buy = next(q for q in quotes if q["side"] == "BUY")
        sell = next(q for q in quotes if q["side"] == "SELL")
        self.assertEqual(buy["price"], 0.48)
        self.assertEqual(sell["price"], 0.52)
        self.assertEqual(buy["size"], 10.0)
        self.assertEqual(sell["size"], 10.0)

    def test_buy_uses_round_down(self) -> None:
        # mid - spread/2 = 0.5 - 0.02 = 0.48 exactly; if 0.483 then round_down -> 0.48
        quotes = compute_quotes(0.503, 0.01, 0.04, 5.0)  # buy raw = 0.483
        self.assertIsNotNone(quotes)
        buy = next(q for q in quotes if q["side"] == "BUY")
        self.assertEqual(buy["price"], 0.48)

    def test_sell_uses_round_up(self) -> None:
        # mid + spread/2 = 0.5 + 0.02 = 0.52; if 0.517 then round_up -> 0.52
        quotes = compute_quotes(0.497, 0.01, 0.04, 5.0)  # sell raw = 0.517
        self.assertIsNotNone(quotes)
        sell = next(q for q in quotes if q["side"] == "SELL")
        self.assertEqual(sell["price"], 0.52)

    def test_mid_out_of_range_returns_none(self) -> None:
        self.assertIsNone(compute_quotes(0.0, 0.01, 0.04, 10.0))
        self.assertIsNone(compute_quotes(1.0, 0.01, 0.04, 10.0))
        self.assertIsNone(compute_quotes(-0.1, 0.01, 0.04, 10.0))
        self.assertIsNone(compute_quotes(1.1, 0.01, 0.04, 10.0))

    def test_invalid_tick_returns_none(self) -> None:
        self.assertIsNone(compute_quotes(0.5, 0, 0.04, 10.0))
        self.assertIsNone(compute_quotes(0.5, -0.01, 0.04, 10.0))

    def test_invalid_size_returns_none(self) -> None:
        self.assertIsNone(compute_quotes(0.5, 0.01, 0.04, 0))
        self.assertIsNone(compute_quotes(0.5, 0.01, 0.04, -1))

    def test_negative_spread_returns_none(self) -> None:
        self.assertIsNone(compute_quotes(0.5, 0.01, -0.01, 10.0))
