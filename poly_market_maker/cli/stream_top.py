"""CLI: print best bid/ask/midpoint once per second. No auth."""

import argparse
import asyncio
import logging
import sys

from poly_market_maker.ws.market_ws import DEFAULT_WS_URL, MarketWsClient


def _fmt(v: float | None) -> str:
    return f"{v:.4f}" if v is not None else "N/A"


def main() -> None:
    parser = argparse.ArgumentParser(description="Stream best bid/ask/midpoint from Polymarket WS")
    parser.add_argument(
        "--asset-ids",
        nargs="+",
        required=True,
        help="One or more asset (token) IDs to subscribe to",
    )
    parser.add_argument(
        "--ws-url",
        default=DEFAULT_WS_URL,
        help="WebSocket URL (default: Polymarket market channel)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable debug logging",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    async def run() -> None:
        client = MarketWsClient(asset_ids=args.asset_ids, ws_url=args.ws_url)
        recv_task = asyncio.create_task(client.run())

        try:
            while True:
                await asyncio.sleep(1.0)
                for aid in args.asset_ids:
                    bid = client.get_best_bid(aid)
                    ask = client.get_best_ask(aid)
                    mid = client.get_midpoint(aid)
                    print(f"{aid}\tbid={_fmt(bid)}\task={_fmt(ask)}\tmid={_fmt(mid)}")
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
