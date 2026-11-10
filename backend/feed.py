"""Own the upstream lifecycle separately from connected browser sockets."""
import asyncio
from contextlib import suppress
import time
import inspect
import json

import yfinance as yf


class YahooConnection(yf.AsyncWebSocket):
    """Keep yfinance subscription/decoding, but don't swallow closure/cancellation.

    The 0.2.66 listen loop can spin after a clean close. Keep this small use of
    its private transport/decoder isolated and covered by lifecycle tests.
    """
    async def listen(self, message_handler):
        await self._connect()
        async for raw in self._ws:
            payload = self._decode_message(json.loads(raw).get('message', ''))
            result = message_handler(payload)
            if inspect.isawaitable(result):
                await result
        raise ConnectionError('Yahoo transport closed')


class Feed:
    def __init__(self, store, symbols, test_mode=False):
        self.store, self.symbols, self.test_mode = store, symbols, test_mode
        self.enabled = False
        self.task = None
        self.upstream = None
        self.state = dict(status='offline', detail='Yahoo feed disabled; stored replay remains available', last_message=None)

    async def set_enabled(self, enabled):
        await self.stop()
        self.enabled = enabled
        if enabled:
            if self.test_mode:
                self.state.update(status='waiting', detail='TEST feed: deterministic events; Yahoo is stubbed')
            else:
                self.state.update(status='connecting', detail='Opening Yahoo Finance WebSocket')
                self.task = asyncio.create_task(self.run())

    async def stop(self):
        self.enabled = False
        if self.task:
            self.task.cancel()
            with suppress(asyncio.CancelledError):
                await self.task
            self.task = None
        self.state.update(status='offline', detail='Yahoo feed disconnected; stored replay remains available')

    async def run(self):
        while self.enabled:
            listener = None
            try:
                self.state.update(status='connecting', detail='Subscribing to Yahoo Finance')
                async with YahooConnection(verbose=False) as ws:
                    self.upstream = ws
                    await ws.subscribe(self.symbols)
                    self.state.update(status='waiting', detail='Yahoo connected; waiting for source observations')

                    async def receive(message):
                        try:
                            self.store.ingest(message)
                            self.state.update(status='connected', detail='Yahoo Finance streaming', last_message=time.time())
                        except (ValueError, TypeError, OverflowError):
                            self.state.update(detail='Ignored malformed source observation')

                    listener = asyncio.create_task(ws.listen(receive))
                    while not listener.done():
                        # yfinance 0.2's listener can consume disconnect errors internally.
                        # Inspect transport state here so a browser never mistakes its own
                        # healthy socket for a healthy Yahoo connection.
                        transport = ws._ws
                        if transport is None or transport.state.name != 'OPEN':
                            raise ConnectionError('Yahoo transport closed')
                        await asyncio.sleep(0.25)
                    await listener
                    raise ConnectionError('Yahoo listener ended')
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                self.state.update(status='unavailable', detail=f'{type(exc).__name__}: Yahoo unavailable; retrying in 5 seconds')
            finally:
                if listener:
                    listener.cancel()
                    with suppress(asyncio.CancelledError, Exception):
                        await listener
                self.upstream = None
            await asyncio.sleep(5)
