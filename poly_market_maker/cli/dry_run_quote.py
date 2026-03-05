"""CLI: dry-run two-sided quotes from WS midpoint. No auth; no order placement."""

import argparse
import asyncio
import logging
import sys

from poly_market_maker.quoting import compute_quotes
from poly_market_maker.ws.market_ws import DEFAULT_WS_URL, MarketWsClient


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Dry-run: compute target quotes from WS midpoint (no order placement)"
    )
    parser.add_argument("--asset-id", required=True, help="Single asset (token) ID to subscribe to")
    parser.add_argument("--tick", type=float, required=True, help="Tick size (min price increment)")
    parser.add_argument("--spread", type=float, required=True, help="Spread in absolute price units (0-1)")
    parser.add_argument("--size", type=float, required=True, help="Order size per side")
    parser.add_argument(
        "--ws-url",
        default=DEFAULT_WS_URL,
        help="WebSocket URL (default: Polymarket market channel)",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging")
    args = parser.parse_args()

    # Validation: tick > 0, size > 0, spread >= 0
    if args.tick <= 0:
        parser.error("tick must be positive")
    if args.size <= 0:
        parser.error("size must be positive")
    if args.spread < 0:
        parser.error("spread must be >= 0")

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    asset_id = args.asset_id

    async def run() -> None:
        client = MarketWsClient(asset_ids=[asset_id], ws_url=args.ws_url)
        recv_task = asyncio.create_task(client.run())

        try:
            while True:
                await asyncio.sleep(1.0)
                mid = client.get_midpoint(asset_id)
                quotes = compute_quotes(mid, args.tick, args.spread, args.size)
                if quotes is None:
                    print("insufficient book")
                else:
                    for q in quotes:
                        print(f"{q['side']} @ {q['price']:.4f} size {q['size']}")
        except asyncio.CancelledError:
            pass
        finally:
            recv_task.cancel()
            try:
                await recv_task
            except asyncio.CancelledError:
                pass

    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
