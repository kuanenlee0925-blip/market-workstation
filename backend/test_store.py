from backend.store import Store


def quote(second, price, volume=100):
    return dict(id='AAPL', time=second*1000, price=price, day_volume=volume)


def test_duplicates_revisions_and_out_of_order():
    store = Store(':memory:')
    assert store.ingest(quote(120, 10), 121)
    assert not store.ingest(quote(120, 10), 122)
    store.ingest(quote(140, 14, 120), 141)
    store.ingest(quote(130, 8, 110), 142)
    store.ingest(quote(140, 12, 125), 143)
    assert len(store.observations('AAPL')) == 4
    assert store.bars('AAPL', now=150) == [dict(time=120, open=10, high=12, low=8, close=12, volume=25, complete=False)]
    assert store.bars('AAPL', now=180)[0]['complete']
    # Replay before the revision cannot see a future correction.
    assert store.bars('AAPL', cutoff=2, now=141)[0]['close'] == 14


def test_cumulative_volume_reset_and_missing_volume():
    store = Store(':memory:')
    store.ingest(quote(120, 10, 500))
    store.ingest(quote(180, 11, 10))
    store.ingest(quote(190, 12, 15))
    assert [b['volume'] for b in store.bars('AAPL')] == [0, 5]


def test_persistence(tmp_path):
    path = tmp_path / 'test.sqlite'
    store = Store(path)
    store.ingest(quote(120, 10))
    store.db.close()
    assert Store(path).snapshot('AAPL')['count'] == 1


def test_invalid_quote():
    import pytest
    with pytest.raises(ValueError):
        Store(':memory:').ingest(quote(120, float('nan')))
