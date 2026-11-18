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


def test_sma_replay_uses_observations_available_at_each_step(server):
    client, _ = server
    prices = [13, 10, 7, 13, 19, 7, 1, 1]
    events = [dict(payload=dict(id='BTC-USD', time=(120+i*60)*1000, price=p), received=121+i*60) for i, p in enumerate(prices)]
    assert client.post('/api/test/ingest', json=events).status_code == 200
    with client.websocket_connect('/ws/BTC-USD') as ws:
        ws.receive_json()
        ws.send_json(dict(mode='replay', short=2, long=3))
        packets = []
        while True:
            packet = ws.receive_json()
            packets.append(packet)
            if packet['replay_finished']:
                break
        signals = [(v['short'], v['long'], v['crossover']) for v in packets[-1]['sma'][:7]]
        assert signals == [(None, None, None), (11.5, None, None), (8.5, 10, None), (10, 10, None), (16, 13, 'up'), (13, 13, None), (4, 9, 'down')]
        assert all(not v['crossover'] for packet in packets[:5] for v in packet['sma'])


def test_named_indicator_settings_and_values(server):
    client, main = server
    for window in (2, 3):
        assert client.post('/api/indicators', json=dict(name=f'Range {window}', kind='range', window=window)).status_code == 201
    assert client.post('/api/indicators', json=dict(name='Bad', kind='range', window=0)).status_code == 422
    instances = client.get('/api/indicators').json()['instances']
    assert [i['name'] for i in instances] == ['Range 2', 'Range 3']
    from backend.indicators import calculate_indicator
    bars = [dict(timestamp=str(i), high=h, low=l, close=l) for i, (h, l) in enumerate([(12, 9), (15, 10), (13, 11)])]
    metadata = {b['timestamp']: {'complete': True} for b in bars}
    assert [calculate_indicator(bars, metadata, i['kind'], i['window'])[-1]['value'] for i in instances] == [5, 6]
    main.store.db.commit()
    from backend.store import Store
    other = Store(main.store.db.execute('PRAGMA database_list').fetchone()[2])
    assert other.db.execute('SELECT COUNT(*) FROM indicators').fetchone()[0] == 2
    other.db.close()


def test_paper_api_backtest_persistence_and_validation(server):
    client, main = server
    assert client.post('/api/paper/accounts', json=dict(short=3,long=2)).status_code == 422
    response = client.post('/api/backtests', json=dict(source='reference'))
    assert response.status_code == 201
    result = response.json()
    assert result['summary']['cash'] == 1032
    assert result['config']['source'] == 'synthetic reference; not live'
    assert client.get('/api/paper/accounts/'+result['id']).json() == result
    assert client.post('/api/paper/accounts/'+result['id']+'/orders', json=dict(request_id='x',side='buy',quantity=1)).status_code == 422
    created = client.post('/api/paper/accounts', json=dict(symbol='BTC-USD')).json()
    pending = client.post('/api/paper/accounts/'+created['id']+'/orders', json=dict(request_id='buy',side='buy',quantity=4)).json()
    assert pending['orders'][0]['status'] == 'pending'
    assert pending['fills'] == []
    assert client.post('/api/paper/accounts/'+created['id']+'/strategy', json={'enabled':True}).json()['summary']['strategy']
