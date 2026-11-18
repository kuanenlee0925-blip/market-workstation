import json

import pytest

from backend.paper import Paper, backtest, reference_events
from backend.store import Store


def event(seq, source, price, received=None, supersedes=None):
    return dict(sequence=seq, source_time=source, received_time=source+1 if received is None else received,
                price=price, day_volume=None, supersedes=supersedes)


def test_known_accounting_retry_rejections_and_restart(tmp_path):
    path = tmp_path/'paper.sqlite'
    store = Store(path); paper = Paper(store.db)
    account = paper.create('BTC-USD')
    paper.submit(account, 'buy', 'buy', 4, clock=119)
    rows = [event(1, 120, 100)]
    paper.process(account, rows)
    assert paper.view(account)['summary']['cash'] == 600
    rows += [event(2, 180, 110), event(3, 240, 110)]
    paper.process(account, rows)
    assert paper.view(account)['summary']['unrealized'] == 40
    paper.submit(account, 'sell', 'sell', 1, clock=242)
    rows.append(event(4, 250, 110)); paper.process(account, rows)
    fill_pnl = [r for r in paper.view(account)['pnl'] if r['event'] == 'fill'][-1]
    assert [fill_pnl[k] for k in ('cash', 'quantity', 'realized', 'unrealized', 'total')] == [710, 3, 10, 30, 40]
    rows += [event(5, 300, 95), event(6, 360, 95)]
    paper.process(account, rows)
    assert paper.view(account)['summary']['unrealized'] == -15
    paper.submit(account, 'close', 'close', clock=362)
    rows.append(event(7, 370, 105)); paper.process(account, rows)
    result = paper.view(account)
    assert [result['summary'][k] for k in ('cash', 'quantity', 'realized', 'unrealized', 'equity')] == [1025, 0, 25, 0, 1025]
    paper.submit(account, 'close', 'close', clock=400)
    paper.process(account, rows)
    assert len(paper.view(account)['fills']) == 3
    paper.submit(account, 'empty-sale', 'sell', 1, clock=400)
    assert paper.view(account)['orders'][-1]['status'] == 'rejected'
    before = paper.view(account)
    store.db.close()
    reopened = Store(path)
    assert Paper(reopened.db).view(account) == before
    reopened.db.close()


def test_pending_cash_recheck_and_old_revision_prices_are_not_fills():
    store = Store(':memory:'); paper = Paper(store.db)
    account = paper.create('BTC-USD')
    paper.submit(account, 'first', 'buy', 6, clock=119)
    paper.submit(account, 'second', 'buy', 6, clock=119)
    assert [o['status'] for o in paper.view(account)['orders']] == ['pending', 'pending']
    paper.process(account, [event(1, 120, 100)])
    assert [o['status'] for o in paper.view(account)['orders']] == ['filled', 'rejected']
    paper.submit(account, 'next', 'buy', 1, clock=121)
    rows = [event(1, 120, 100), event(2, 110, 50, 122), event(3, 130, 50, 132, supersedes=1)]
    paper.process(account, rows)
    assert len(paper.view(account)['fills']) == 1
    with pytest.raises(ValueError):
        paper.submit(account, 'next', 'sell', 1, clock=140)


def test_reference_strategy_batch_incremental_and_no_lookahead():
    store = Store(':memory:'); paper = Paper(store.db)
    rows = reference_events()
    batch = backtest(paper, rows, 'AAPL', 1000, 2, 3, 4, '1m', 'synthetic reference; not live')
    account = paper.create('AAPL', strategy=True)
    for n in range(1, len(rows)+1):
        paper.process(account, rows[:n])
        for order in paper.view(account)['orders']:
            assert order['after_sequence'] <= rows[n-1]['sequence']
        if n <= 5:
            assert paper.view(account)['fills'] == []
    incremental = paper.view(account)
    assert batch['summary'] == incremental['summary']
    assert [(r['side'], r['price'], r['observation_sequence']) for r in batch['fills']] == [('buy', 1, 7), ('close', 9, 9)]
    assert batch['summary']['cash'] == 1032
    assert batch['summary']['realized'] == 32
    for fill in batch['fills']:
        order = next(o for o in batch['orders'] if o['id'] == fill['order_id'])
        assert fill['observation_sequence'] > order['after_sequence']
    assert [(s['short'], s['long'], s['crossover']) for s in batch['signals'][:7]] == [
        (None, None, None), (11.5, None, None), (8.5, 10, None), (10, 10, None), (16, 13, 'up'), (13, 13, None), (4, 9, 'down')]
    saved = json.loads(store.db.execute('SELECT data FROM backtest_inputs WHERE account_id=?', (batch['id'],)).fetchone()[0])
    assert saved['rows'] == rows and len(saved['sha256']) == 64
    assert batch['signals'] == incremental['signals']


def test_late_correction_preserves_decisions_and_fills_already_recorded():
    store = Store(':memory:'); paper = Paper(store.db)
    rows = reference_events()
    account = paper.create('AAPL', strategy=True)
    paper.process(account, rows)
    before = paper.view(account)
    # Arrives after the reference decisions; it cannot rewrite their evidence.
    correction = dict(rows[4], sequence=10, price=1, received_time=rows[-1]['received_time']+2, supersedes=5)
    rows.append(correction)
    paper.process(account, rows)
    paper.process(account, rows)
    after = paper.view(account)
    assert after['signals'] == before['signals']
    assert after['fills'] == before['fills']
    assert after['orders'] == before['orders']
    assert after['pnl'] == before['pnl']
