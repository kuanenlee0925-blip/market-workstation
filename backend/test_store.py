import sqlite3

import pytest

from backend.candles import FIELDS, aggregate, epoch, sample_minutes
from backend.store import Store


def quote(second, price, volume=100, symbol='BTC-USD'):
    return dict(id=symbol, time=second*1000, price=price, day_volume=volume)


def test_duplicates_are_ignored_but_same_time_quotes_are_distinct():
    store = Store(':memory:')
    assert store.ingest(quote(120, 100), 121)
    assert not store.ingest(quote(120, 100), 122)
    assert store.ingest(quote(120, 105, 105), 123)
    bars, meta = store.candles('BTC-USD', now=180)
    assert (bars[0]['open'], bars[0]['high'], bars[0]['low'], bars[0]['close']) == (100, 105, 100, 105)
    assert len(store.observations('BTC-USD')) == 2
    assert bars[0]['volume'] is None


def test_explicit_corrections_and_replay_cutoff():
    store = Store(':memory:')
    store.ingest(quote(119, 9, 100), 119)
    store.ingest(quote(120, 10, 105), 121)
    store.ingest(quote(140, 14, 120), 141)
    store.ingest(quote(130, 8, 110), 142)
    corrected = quote(140, 12, 125)
    store.ingest(corrected, 143, supersedes=3)
    assert not store.ingest(corrected, 144, supersedes=3)
    bars, meta = store.candles('BTC-USD', now=150)
    assert bars[-1] == dict(timestamp='1970-01-01T00:02:00Z', open=10, high=12, low=8, close=12, volume=25)
    assert not meta[bars[-1]['timestamp']]['complete']
    assert store.candles('BTC-USD', now=180)[1][bars[-1]['timestamp']]['complete']
    assert store.candles('BTC-USD', cutoff=3, now=141)[0][-1]['close'] == 14
    assert len(store.observations('BTC-USD')) == 5


def test_prompt_seven_late_arrival_and_volume_example():
    store = Store(':memory:')
    start = epoch('2026-11-09T15:00:00Z')
    for delta, price, volume in [(-1, 99, 1000), (5, 100, 1004), (50, 101, 1011), (20, 103, 1009)]:
        store.ingest(quote(start+delta, price, volume, 'AAPL'))
    bars, meta = store.candles('AAPL', now=start+55)
    assert bars[-1] == dict(timestamp='2026-11-09T15:00:00Z', open=100, high=103, low=100, close=101, volume=11)
    assert not meta[bars[-1]['timestamp']]['complete']
    assert store.candles('AAPL', now=start+60)[1][bars[-1]['timestamp']]['complete']


@pytest.mark.parametrize('totals,expected', [([500, 10, 15], [None, None, 5]), ([100, None, 120], [None, None, None]), ([100, 100, 100], [None, 0, 0])])
def test_unknown_reset_missing_and_zero_volume(totals, expected):
    store = Store(':memory:')
    for i, v in enumerate(totals):
        store.ingest(quote(120+i*60, 10+i, v))
    assert [b['volume'] for b in store.candles('BTC-USD')[0]] == expected


def test_gap_volume_is_unknown():
    store = Store(':memory:')
    store.ingest(quote(120, 10, 100))
    store.ingest(quote(300, 11, 200))
    assert store.candles('BTC-USD')[0][-1]['volume'] is None


def test_persistence_and_read_only_repeat_replay(tmp_path):
    path = tmp_path/'test.sqlite'
    store = Store(path)
    store.ingest(quote(120, 10))
    store.db.close()
    reopened = Store(path)
    before = reopened.observations('BTC-USD')
    assert reopened.snapshot('BTC-USD', cutoff=1) == reopened.snapshot('BTC-USD', cutoff=1)
    assert reopened.observations('BTC-USD') == before


def test_legacy_migration_keeps_all_observations(tmp_path):
    path = tmp_path/'legacy.sqlite'
    db = sqlite3.connect(path)
    db.execute('CREATE TABLE observations(sequence INTEGER PRIMARY KEY,identity TEXT,revision INTEGER,symbol TEXT,source_time REAL,received_time REAL,price REAL,day_volume REAL,payload TEXT,digest TEXT UNIQUE)')
    for i, p in [(1, 100), (2, 105)]:
        db.execute('INSERT INTO observations VALUES(?,?,?,?,?,?,?,?,?,?)', (i, 'same', i, 'BTC-USD', 120, 121+i, p, None, '{}', str(i)))
    db.commit(); db.close()
    store = Store(path)
    assert len(store.observations('BTC-USD')) == 2
    assert [r['supersedes'] for r in store.observations('BTC-USD')] == [None, None]
    assert store.candles('BTC-USD')[0][0]['open'] == 100


def test_replay_source_and_arrival_times_are_separate():
    store = Store(':memory:')
    store.ingest(quote(140, 105), 141)
    store.ingest(quote(130, 100), 142)
    state = store.snapshot('BTC-USD', cutoff=2)
    assert state['last_source_time'] == 140
    assert store.observations('BTC-USD', 2)[-1]['source_time'] == 130


def test_csv_five_minute_and_daily_coverage():
    rows = sample_minutes()
    assert tuple(rows[0]) == FIELDS
    assert rows[1] == dict(timestamp='2026-11-09T14:31:00Z', open=102, high=104, low=100, close=101, volume=850)
    bars, meta = aggregate(rows, 'AAPL', '5m', epoch('2026-11-10T00:00:00Z'))
    assert bars == [dict(timestamp='2026-11-09T14:30:00Z', open=100, high=105, low=99, close=104, volume=3550)]
    assert meta[bars[0]['timestamp']]['observed_minutes'] == 3
    assert not meta[bars[0]['timestamp']]['coverage_complete']
    rows += [dict(rows[-1], timestamp='2026-11-09T14:35:00Z'), dict(rows[-1], timestamp='2026-11-10T14:30:00Z')]
    assert len(aggregate(rows, 'AAPL', '5m', epoch('2026-11-11T00:00:00Z'))[0]) == 3
    daily = aggregate(rows, 'AAPL', '1d', epoch('2026-11-11T00:00:00Z'))[0]
    assert len(daily) == 2
    assert daily[0]['volume'] == 5050


def test_exchange_early_close_holiday_dst_and_hour_alignment():
    sample = sample_minutes()[0]
    rows = [dict(sample, timestamp=t) for t in ['2026-10-30T13:30:00Z', '2026-11-02T14:30:00Z', '2026-11-26T14:30:00Z', '2026-11-27T14:30:00Z', '2026-11-27T18:01:00Z']]
    bars, meta = aggregate(rows, 'AAPL', '1d', epoch('2026-11-28T00:00:00Z'))
    assert len(bars) == 3
    assert meta['2026-11-27T14:30:00Z']['expected_minutes'] == 210
    assert meta['2026-11-27T14:30:00Z']['end'] == '2026-11-27T18:00:00Z'
    hourly = aggregate([dict(sample, timestamp='2026-11-09T15:31:00Z')], 'AAPL', '1h', epoch('2026-11-10T00:00:00Z'))[0]
    assert hourly[0]['timestamp'] == '2026-11-09T15:30:00Z'


def test_invalid_quote_and_correction():
    with pytest.raises(ValueError):
        Store(':memory:').ingest(quote(120, float('nan')))
    with pytest.raises(ValueError):
        Store(':memory:').ingest(quote(120, 100), supersedes=99)
