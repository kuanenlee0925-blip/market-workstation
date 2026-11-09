import asyncio
from contextlib import asynccontextmanager, suppress
import os
from pathlib import Path
import time

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import yfinance as yf

from .store import Store

SYMBOLS = ['AAPL', 'MSFT', 'SPY', 'BTC-USD']
store = Store(os.getenv('MARKET_DB', 'market.sqlite'))
feed = {'status': 'connecting', 'detail': 'Opening Yahoo Finance WebSocket', 'last_message': None}


async def stream():
    while True:
        try:
            feed.update(status='connecting', detail='Subscribing to Yahoo Finance')
            async with yf.AsyncWebSocket(verbose=False) as upstream:
                await upstream.subscribe(SYMBOLS)
                feed.update(status='waiting', detail='Connected; waiting for source observations')

                async def receive(message):
                    try:
                        store.ingest(message)
                        feed.update(status='connected', detail='Yahoo Finance streaming', last_message=time.time())
                    except (ValueError, TypeError, OverflowError):
                        feed.update(detail='Ignored malformed source observation')

                await upstream.listen(receive)
                # yfinance's listener consumes CancelledError during cleanup.
                if asyncio.current_task().cancelling():
                    return
            feed.update(status='unavailable', detail='Source connection ended; reconnecting')
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            feed.update(status='unavailable', detail=f'{type(exc).__name__}: source unavailable; retrying in 5 seconds')
        await asyncio.sleep(5)


@asynccontextmanager
async def lifespan(app):
    task = asyncio.create_task(stream())
    yield
    task.cancel()
    with suppress(asyncio.CancelledError):
        await task


app = FastAPI(title='Market Workstation', lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=['http://localhost:5173', 'http://127.0.0.1:5173'], allow_methods=['GET'], allow_headers=['*'])


@app.get('/api/status')
async def status():
    return dict(feed=feed, symbols=SYMBOLS, server_time=time.time())


@app.get('/api/observations/{symbol}')
async def observations(symbol: str):
    return store.observations(symbol)


@app.websocket('/ws/{symbol}')
async def socket(ws: WebSocket, symbol: str):
    await ws.accept()
    if symbol not in SYMBOLS:
        await ws.close(code=1008)
        return
    replay_rows = None
    index = 0
    mode = 'live'
    try:
        while True:
            cutoff = None
            clock = time.time()
            if mode == 'replay':
                if replay_rows:
                    row = replay_rows[min(index, len(replay_rows)-1)]
                    cutoff, clock = row['sequence'], row['received_time']
                    index = min(index+1, len(replay_rows))
                else:
                    cutoff = 0
            state = store.snapshot(symbol, cutoff, clock)
            await ws.send_json(dict(type='snapshot', mode=mode, feed=feed.copy(), server_time=time.time(),
                                    replay_finished=mode == 'replay' and index >= len(replay_rows or []), **state))
            try:
                command = await asyncio.wait_for(ws.receive_json(), timeout=1)
                if command.get('mode') == 'replay':
                    replay_rows = store.observations(symbol)
                    index, mode = 0, 'replay'
                elif command.get('mode') == 'live':
                    mode = 'live'
            except asyncio.TimeoutError:
                pass
    except (WebSocketDisconnect, RuntimeError):
        pass


dist = Path(__file__).resolve().parents[1] / 'frontend' / 'dist'
if dist.exists():
    app.mount('/', StaticFiles(directory=dist, html=True), name='frontend')
