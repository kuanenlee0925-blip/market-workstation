"""Completed-candle simple moving averages and confirmed side changes."""
from collections import deque


def moving_averages(bars, metadata, short, long):
    if any(isinstance(n, bool) or not isinstance(n, int) or n <= 0 for n in (short, long)) or short >= long:
        raise ValueError('SMA windows must be positive whole numbers, with short smaller than long')
    short_values = calculate_indicator(bars, metadata, 'sma', short)
    long_values = calculate_indicator(bars, metadata, 'sma', long)
    side, result = 0, []
    for bar, short_point, long_point in zip(bars, short_values, long_values):
        item = dict(timestamp=bar['timestamp'], short=short_point['value'], long=long_point['value'], crossover=None)
        if item['short'] is not None and item['long'] is not None:
            current = (item['short'] > item['long']) - (item['short'] < item['long'])
            if current:
                if side and current != side:
                    item['crossover'] = 'up' if current > 0 else 'down'
                side = current
        result.append(item)
    return result


INDICATOR_TYPES = {
    'sma': {'label': 'Simple moving average', 'units': 'price'},
    'range': {'label': 'Rolling price range', 'units': 'price'},
}


def calculate_indicator(bars, metadata, kind, window):
    if kind not in INDICATOR_TYPES or isinstance(window, bool) or not isinstance(window, int) or window <= 0:
        raise ValueError('Choose an indicator type and a positive whole-number window')
    completed, result = deque(maxlen=window), []
    for bar in bars:
        value = None
        if metadata.get(bar['timestamp'], {}).get('complete'):
            completed.append(bar)
            if len(completed) == window:
                value = (sum(b['close'] for b in completed) / window if kind == 'sma'
                         else max(b['high'] for b in completed) - min(b['low'] for b in completed))
        result.append(dict(timestamp=bar['timestamp'], value=value))
    return result
