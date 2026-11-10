"""Bounded real-provider diagnostic; no synthetic fallback and no database writes."""
import argparse
import asyncio
from contextlib import suppress
import json
import time
from pathlib import Path
import sys

import yfinance as yf

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.feed import YahooConnection


async def check(symbol, timeout):
    opened, received = False, asyncio.Event()
    result = dict(provider='Yahoo via yfinance', yfinance_version=yf.__version__, symbol=symbol, source_time_units='milliseconds since UTC epoch', receipt_time_units='seconds since UTC epoch', volume_semantics='day_volume: provider cumulative total, not an individual trade size')
    listener = None
    try:
        async with YahooConnection(verbose=False) as ws:
            opened = True
            await ws.subscribe([symbol])

            def message(payload):
                if payload.get('id') == symbol and 'price' in payload:
                    result.update(price=payload['price'], source_time=payload.get('time'), received_time=time.time(), day_volume=payload.get('day_volume'))
                    received.set()

            listener = asyncio.create_task(ws.listen(message))
            await asyncio.wait_for(received.wait(), timeout)
    except asyncio.TimeoutError:
        result['receipt_status'] = 'unverified: no observation before timeout'
    except Exception as exc:
        result['receipt_status'] = f'unverified: {type(exc).__name__}'
    finally:
        if listener:
            listener.cancel()
            with suppress(asyncio.CancelledError, Exception):
                await listener
    result.update(connection_opened=opened, observation_received=received.is_set())
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--symbol', default='AAPL')
    parser.add_argument('--timeout', type=float, default=15)
    args = parser.parse_args()
    asyncio.run(check(args.symbol, args.timeout))
