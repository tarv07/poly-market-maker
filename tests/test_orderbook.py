"""Unit tests for L2 orderbook (poly_market_maker.book.orderbook)."""

from unittest import TestCase

from poly_market_maker.book.orderbook import L2OrderBook


class TestL2OrderBook(TestCase):
    """Tests for L2OrderBook — snapshot, price_change, best bid/ask, midpoint."""

    def test_empty_book_returns_none(self) -> None:
        book = L2OrderBook()
        self.assertIsNone(book.best_bid())
        self.assertIsNone(book.best_ask())
        self.assertIsNone(book.midpoint())

    def test_snapshot_sorted_internally(self) -> None:
        """Input order is ignored; we sort bids desc, asks asc."""
        book = L2OrderBook()
        # Bids out of order; asks out of order
        book.apply_snapshot(
            bids=[(0.49, 10), (0.48, 20), (0.50, 5)],
            asks=[(0.53, 60), (0.52, 25), (0.51, 15)],
        )
        self.assertEqual(book.best_bid(), 0.50)
        self.assertEqual(book.best_ask(), 0.51)
        self.assertAlmostEqual(book.midpoint(), (0.50 + 0.51) / 2)

    def test_snapshot_parses_decimal_strings(self) -> None:
        """Prices/sizes like '.48' and '30' are parsed correctly."""
        book = L2OrderBook()
        book.apply_snapshot(
            bids=[(".48", "30"), (".49", "20")],
            asks=[(".52", "25"), (".53", "60")],
        )
        self.assertAlmostEqual(book.best_bid(), 0.49)  # .49 > .48 after sort
        self.assertAlmostEqual(book.best_ask(), 0.52)
        self.assertAlmostEqual(book.midpoint(), (0.49 + 0.52) / 2)

    def test_only_bids_midpoint_none(self) -> None:
        book = L2OrderBook()
        book.apply_snapshot(bids=[(0.5, 10)], asks=[])
        self.assertEqual(book.best_bid(), 0.5)
        self.assertIsNone(book.best_ask())
        self.assertIsNone(book.midpoint())

    def test_only_asks_midpoint_none(self) -> None:
        book = L2OrderBook()
        book.apply_snapshot(bids=[], asks=[(0.5, 10)])
        self.assertIsNone(book.best_bid())
        self.assertEqual(book.best_ask(), 0.5)
        self.assertIsNone(book.midpoint())

    def test_apply_price_change_buy_updates_bids(self) -> None:
        book = L2OrderBook()
        book.apply_snapshot(bids=[(0.48, 10), (0.47, 20)], asks=[(0.52, 15)])
        book.apply_price_change("BUY", 0.49, 50)
        self.assertEqual(book.best_bid(), 0.49)
        book.apply_price_change("BUY", 0.49, 25)  # update same level
        self.assertEqual(book.best_bid(), 0.49)

    def test_apply_price_change_sell_updates_asks(self) -> None:
        book = L2OrderBook()
        book.apply_snapshot(bids=[(0.48, 10)], asks=[(0.52, 15), (0.53, 20)])
        book.apply_price_change("SELL", 0.51, 40)
        self.assertEqual(book.best_ask(), 0.51)
        book.apply_price_change("SELL", 0.51, 10)
        self.assertEqual(book.best_ask(), 0.51)

    def test_apply_price_change_size_zero_removes_level(self) -> None:
        book = L2OrderBook()
        book.apply_snapshot(bids=[(0.50, 10), (0.49, 20)], asks=[(0.52, 15)])
        book.apply_price_change("BUY", 0.50, 0)
        self.assertEqual(book.best_bid(), 0.49)
        book.apply_price_change("SELL", 0.52, "0")
        self.assertIsNone(book.best_ask())

    def test_price_change_parses_strings(self) -> None:
        book = L2OrderBook()
        book.apply_snapshot(bids=[], asks=[])
        book.apply_price_change("BUY", ".48", "100")
        book.apply_price_change("SELL", ".52", "50")
        self.assertAlmostEqual(book.best_bid(), 0.48)
        self.assertAlmostEqual(book.best_ask(), 0.52)
        self.assertAlmostEqual(book.midpoint(), 0.50)

    def test_snapshot_then_price_changes(self) -> None:
        book = L2OrderBook()
        book.apply_snapshot(
            bids=[(0.48, 30), (0.47, 20)],
            asks=[(0.52, 25), (0.53, 60)],
        )
        book.apply_price_change("BUY", 0.49, 10)
        book.apply_price_change("SELL", 0.51, 5)
        book.apply_price_change("BUY", 0.48, 0)  # remove 0.48
        self.assertEqual(book.best_bid(), 0.49)
        self.assertEqual(book.best_ask(), 0.51)
        self.assertAlmostEqual(book.midpoint(), 0.50)

    def test_snapshot_filters_zero_size_levels(self) -> None:
        book = L2OrderBook()
        book.apply_snapshot(
            bids=[(0.50, 10), (0.49, 0), (0.48, 5)],
            asks=[(0.52, 0), (0.53, 20)],
        )
        self.assertEqual(book.best_bid(), 0.50)
        self.assertEqual(book.best_ask(), 0.53)
