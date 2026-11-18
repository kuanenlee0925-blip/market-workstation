from backend.indicators import moving_averages
import pytest


def test_sma_reference_replay_and_unfinished():
    bars = [dict(timestamp=str(i), close=p) for i, p in enumerate([13, 10, 7, 13, 19, 7, 1])]
    metadata = {b['timestamp']: {'complete': True} for b in bars}
    full = moving_averages(bars, metadata, 2, 3)
    assert [(v['short'], v['long'], v['crossover']) for v in full] == [
        (None, None, None), (11.5, None, None), (8.5, 10, None),
        (10, 10, None), (16, 13, 'up'), (13, 13, None), (4, 9, 'down')]
    for n in range(1, len(bars) + 1):
        assert moving_averages(bars[:n], metadata, 2, 3) == full[:n]
    metadata['4']['complete'] = False
    assert moving_averages(bars[:5], metadata, 2, 3)[-1]['crossover'] is None


@pytest.mark.parametrize('short,long', [(0, 3), (3, 3), (4, 3), (1.5, 3), (True, 3)])
def test_invalid_windows(short, long):
    with pytest.raises(ValueError):
        moving_averages([], {}, short, long)


def test_independent_pandas_reference_and_generic_sma():
    import pandas as pd
    from backend.indicators import calculate_indicator
    closes = [13, 10, 7, 13, 19, 7, 1]
    bars = [dict(timestamp=str(i), close=close) for i, close in enumerate(closes)]
    metadata = {b['timestamp']: {'complete': True} for b in bars}
    result = moving_averages(bars, metadata, 2, 3)
    for key, window in [('short', 2), ('long', 3)]:
        expected = pd.Series(closes, dtype=float).rolling(window).mean()
        assert [row[key] for row in result] == [None if pd.isna(value) else value for value in expected]
        assert [row[key] for row in result] == [v['value'] for v in calculate_indicator(bars, metadata, 'sma', window)]
