import asyncio
from contextlib import asynccontextmanager
import os
from pathlib import Path
import time
from typing import Literal

from fastapi import FastAPI, HTTPException, Response, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .candles import INTERVALS, aggregate, epoch, iso, sample_minutes
from .feed import Feed
from .store import Store

SYMBOLS = ['AAPL', 'MSFT', 'SPY', 'BTC-USD']
TEST_MODE = os.getenv('MARKET_TEST_MODE') == '1'
store = Store(os.getenv('MARKET_DB', 'market.sqlite'))
feed = Feed(store, SYMBOLS, TEST_MODE)


@asynccontextmanager
async def lifespan(app):
    await feed.set_enabled(os.getenv('FEED_ENABLED', '1') != '0')
    try:
        yield
    finally:
        await feed.stop()
        store.db.close()


app = FastAPI(title='Market Workstation', lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=['http://localhost:5173', 'http://127.0.0.1:5173'], allow_methods=['GET', 'POST'], allow_headers=['*'])


def selection(interval, start=None, end=None):
    if interval not in INTERVALS:
        raise ValueError('Choose 1m, 5m, 15m, 1h, or 1d')
    begin, finish = epoch(start), epoch(end)
    if begin is not None and finish is not None and begin >= finish:
        raise ValueError('Range end must be after its start')
    return begin, finish


@app.get('/api/health')
async def health():
    return dict(status='ok', service='market-workstation')


@app.get('/api/status')
async def status():
    return dict(feed=feed.state, enabled=feed.enabled, symbols=SYMBOLS, intervals=list(INTERVALS), server_time=time.time(), test_mode=TEST_MODE)


class FeedControl(BaseModel):
    enabled: bool


@app.post('/api/feed')
async def control_feed(command: FeedControl):
    await feed.set_enabled(command.enabled)
    return await status()


@app.get('/api/observations/{symbol}')
async def observations(symbol: str):
    return store.observations(symbol)


@app.get('/api/history')
async def history(response: Response, symbol: str = 'AAPL', interval: str = '1m', source: Literal['sample', 'recorded'] = 'sample', start: str | None = None, end: str | None = None, with_metadata: bool = False):
    try:
        begin, finish = selection(interval, start, end)
        if symbol not in SYMBOLS:
            raise ValueError('Unsupported symbol')
        if source == 'sample':
            if symbol != 'AAPL':
                raise ValueError('Synthetic CSV sample is for AAPL')
            bars, metadata = aggregate(sample_minutes(), 'AAPL', interval, time.time(), begin, finish)
            response.headers['X-Data-Source'] = 'synthetic CSV sample; not live'
        else:
            bars, metadata = store.candles(symbol, interval=interval, start=begin, end=finish)
            response.headers['X-Data-Source'] = 'recorded Yahoo observations'
        return dict(bars=bars, metadata=metadata, source=source, interval=interval) if with_metadata else bars
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@app.websocket('/ws/{symbol}')
async def socket(ws: WebSocket, symbol: str):
    await ws.accept()
    if symbol not in SYMBOLS:
        await ws.close(code=1008)
        return
    replay_rows, index, mode, interval = [], 0, 'live', '1m'
    begin = finish = None
    previous = None
    try:
        while True:
            cutoff, clock, point = None, time.time(), None
            if mode == 'replay':
                cutoff = 0
                if replay_rows:
                    row = replay_rows[min(index, len(replay_rows)-1)]
                    cutoff, clock = row['sequence'], row['received_time']
                    point = dict(sequence=cutoff, source_time=iso(row['source_time']), received_time=iso(clock))
                    index = min(index+1, len(replay_rows))
            state = store.snapshot(symbol, cutoff, clock, interval, begin, finish)
            if mode == 'sample':
                state['bars'], state['metadata'] = aggregate(sample_minutes(), 'AAPL', interval, clock, begin, finish)
                state.update(count=0, last_source_time=None, last_received_time=None)
            state.update(mode=mode, source='synthetic CSV sample; not live' if mode == 'sample' else 'recorded Yahoo observations' if mode == 'replay' else 'Yahoo Finance',
                         feed=feed.state.copy(), feed_enabled=feed.enabled, server_time=time.time(), replay_point=point,
                         replay_finished=mode == 'replay' and index >= len(replay_rows), range_start=iso(begin) if begin is not None else None, range_end=iso(finish) if finish is not None else None)
            current = {b['timestamp']: b for b in state['bars']}
            if previous is None:
                packet = dict(type='snapshot', **state)
            else:
                packet = {k: v for k, v in state.items() if k != 'bars'}
                packet.update(type='update', updates=[b for key, b in current.items() if previous.get(key) != b], removed=[key for key in previous if key not in current])
            await ws.send_json(packet)
            previous = current
            try:
                command = await asyncio.wait_for(ws.receive_json(), timeout=1)
                try:
                    next_mode = command.get('mode', mode)
                    next_interval = command.get('interval', interval)
                    if next_mode not in ('live', 'replay', 'sample'):
                        raise ValueError('Invalid view mode')
                    new_begin, new_finish = selection(next_interval, command.get('start'), command.get('end'))
                    if next_mode == 'sample' and symbol != 'AAPL':
                        raise ValueError('Synthetic CSV sample is for AAPL; select AAPL first')
                    mode, interval, begin, finish = next_mode, next_interval, new_begin, new_finish
                    if mode == 'replay':
                        rows = store.observations(symbol)
                        selected, relevant = [], set()
                        for r in rows:
                            if ((begin is None or r['source_time'] >= begin) and (finish is None or r['source_time'] < finish)) or r['supersedes'] in relevant:
                                selected.append(r)
                                relevant.add(r['sequence'])
                        # Include intervening arrivals so late baselines/corrections are
                        # revealed at their actual arrival step, even outside the range.
                        replay_rows = [r for r in rows if selected and selected[0]['sequence'] <= r['sequence'] <= selected[-1]['sequence']]
                        index = 0
                    previous = None
                except (ValueError, TypeError, OverflowError) as exc:
                    await ws.send_json(dict(type='error', message=str(exc)))
            except asyncio.TimeoutError:
                pass
    except (WebSocketDisconnect, RuntimeError):
        pass


if TEST_MODE:
    @app.post('/api/test/ingest')
    async def test_ingest(events: list[dict]):
        for event in events:
            store.ingest(event['payload'], event.get('received'), event.get('supersedes'))
        return dict(test_mode=True, count=len(events))


dist = Path(__file__).resolve().parents[1]/'frontend'/'dist'
if dist.exists():
    app.mount('/', StaticFiles(directory=dist, html=True), name='frontend')
