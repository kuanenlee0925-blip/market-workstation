import asyncio

import pytest

from backend.feed import YahooConnection


def test_yahoo_adapter_propagates_clean_close():
    class ClosedTransport:
        def __aiter__(self):
            return self

        async def __anext__(self):
            raise StopAsyncIteration

    async def check():
        connection = YahooConnection(verbose=False)
        connection._ws = ClosedTransport()
        with pytest.raises(ConnectionError):
            await asyncio.wait_for(connection.listen(lambda message: None), .2)
    asyncio.run(check())


def test_yahoo_adapter_does_not_swallow_cancellation():
    class WaitingTransport:
        def __aiter__(self):
            return self

        async def __anext__(self):
            await asyncio.Future()

    async def check():
        connection = YahooConnection(verbose=False)
        connection._ws = WaitingTransport()
        task = asyncio.create_task(connection.listen(lambda message: None))
        await asyncio.sleep(0)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await asyncio.wait_for(task, .2)
    asyncio.run(check())
