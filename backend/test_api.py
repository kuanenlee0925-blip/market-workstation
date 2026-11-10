import importlib

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def server(monkeypatch, tmp_path):
    monkeypatch.setenv('MARKET_DB', str(tmp_path/'api.sqlite'))
    monkeypatch.setenv('FEED_ENABLED', '0')
    monkeypatch.setenv('MARKET_TEST_MODE', '1')
    from backend import main
    main = importlib.reload(main)
    with TestClient(main.app) as client:
        yield client, main
    main.store.db.close()


def test_health_history_and_validation(server):
    client, main = server
    assert client.get('/api/health').json()['status'] == 'ok'
    history = client.get('/api/history')
    assert 'synthetic' in history.headers['x-data-source']
    assert history.json()[1]['close'] == 101
    assert client.get('/api/history?interval=5m').json()[0]['volume'] == 3550
    assert client.get('/api/history?interval=bad').status_code == 422
    assert client.get('/api/history?start=2026-11-09T14:30').status_code == 422


def test_real_backend_replay_is_readonly_and_handles_errors(server):
    client, main = server
    events = [dict(payload=dict(id='BTC-USD', time=t*1000, price=p, day_volume=v), received=t+1) for t, p, v in [(119, 99, 100), (120, 100, 104), (130, 103, 109), (170, 101, 111)]]
    client.post('/api/test/ingest', json=events)
    before = client.get('/api/observations/BTC-USD').json()
    with client.websocket_connect('/ws/BTC-USD') as ws:
        assert ws.receive_json()['type'] == 'snapshot'
        for repeat in range(2):
            ws.send_json(dict(mode='replay', start='1970-01-01T00:02:00Z', end='1970-01-01T00:03:00Z'))
            packet = ws.receive_json()
            assert packet['replay_point']['source_time'] == '1970-01-01T00:02:00Z'
            while not packet['replay_finished']:
                packet = ws.receive_json()
            assert packet['count'] == 4
        ws.send_json(dict(mode='replay', interval='invalid'))
        assert ws.receive_json()['type'] == 'error'
    assert client.get('/api/observations/BTC-USD').json() == before


def test_pause_keeps_browser_connected(server):
    client, main = server
    with client.websocket_connect('/ws/AAPL') as ws:
        ws.receive_json()
        client.post('/api/feed', json={'enabled': True})
        assert ws.receive_json()['feed']['status'] == 'waiting'
        client.post('/api/feed', json={'enabled': False})
        packet = ws.receive_json()
        assert packet['feed']['status'] == 'offline'
        assert packet['type'] == 'update'
