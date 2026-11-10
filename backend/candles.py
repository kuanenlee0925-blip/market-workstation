"""Six-field OHLCV records; session, completeness and coverage live alongside them."""
import csv
import math
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

import exchange_calendars as xcals
import pandas as pd

INTERVALS = {'1m': 60, '5m': 300, '15m': 900, '1h': 3600, '1d': 86400}
FIELDS = ('timestamp', 'open', 'high', 'low', 'close', 'volume')


def iso(seconds):
    return datetime.fromtimestamp(seconds, timezone.utc).isoformat().replace('+00:00', 'Z')


def epoch(value):
    if value is None or value == '':
        return None
    if isinstance(value, (int, float)):
        if not math.isfinite(value):
            raise ValueError('Timestamp must be finite')
        return float(value)
    date = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if date.tzinfo is None:
        raise ValueError('Use a timezone or Z on each date/time')
    return date.timestamp()


@lru_cache(maxsize=1)
def calendar():
    return xcals.get_calendar('XNYS', start='2000-01-01', end='2035-12-31')


@lru_cache(maxsize=4096)
def equity_session(date):
    cal = calendar()
    if not cal.is_session(date):
        return None
    return cal.session_open(date).timestamp(), cal.session_close(date).timestamp()


def session(symbol, timestamp):
    if symbol == 'BTC-USD':
        start = int(timestamp // 86400)*86400
        return start, start+86400
    date = pd.Timestamp(timestamp, unit='s', tz='UTC').tz_convert('America/New_York').date().isoformat()
    try:
        bounds = equity_session(date)
    except ValueError:
        return None
    return bounds if bounds and bounds[0] <= timestamp < bounds[1] else None


def minute_candles(rows, symbol):
    superseded = {r['supersedes'] for r in rows if r.get('supersedes') is not None}
    ordered = sorted((r for r in rows if r['sequence'] not in superseded), key=lambda r: (r['source_time'], r['sequence']))
    bars, baselines = {}, {}
    for row in ordered:
        bounds = session(symbol, row['source_time'])
        if bounds is None:
            continue
        bucket = int(row['source_time']//60)*60
        p, total = row['price'], row['day_volume']
        bar = bars.setdefault(bucket, dict(timestamp=iso(bucket), open=p, high=p, low=p, close=p, volume=0))
        bar.update(high=max(bar['high'], p), low=min(bar['low'], p), close=p)
        previous = baselines.get(bounds[0])
        known = total is not None and previous is not None and previous[1] is not None and total >= previous[1] and bucket-previous[0] <= 60
        if not known:
            bar['volume'] = None
        elif bar['volume'] is not None:
            bar['volume'] += total-previous[1]
        baselines[bounds[0]] = (bucket, total)
    return list(bars.values())


def aggregate(minutes, symbol, interval, now, start=None, end=None):
    if interval not in INTERVALS:
        raise ValueError('Unsupported timeframe')
    groups, metadata = {}, {}
    for minute in minutes:
        timestamp = epoch(minute['timestamp'])
        if (start is not None and timestamp < start) or (end is not None and timestamp >= end):
            continue
        bounds = session(symbol, timestamp)
        if bounds is None:
            continue
        opening, closing = bounds
        size = INTERVALS[interval]
        bucket = opening if interval == '1d' else opening+int((timestamp-opening)//size)*size
        finish = closing if interval == '1d' else min(bucket+size, closing)
        key = iso(bucket)
        if key not in groups:
            groups[key] = dict(timestamp=key, open=minute['open'], high=minute['high'], low=minute['low'], close=minute['close'], volume=minute['volume'])
            metadata[key] = dict(complete=now >= finish, observed_minutes=1, expected_minutes=int((finish-bucket)/60), session_open=iso(opening), end=iso(finish))
        else:
            b = groups[key]
            b.update(high=max(b['high'], minute['high']), low=min(b['low'], minute['low']), close=minute['close'])
            b['volume'] = None if b['volume'] is None or minute['volume'] is None else b['volume']+minute['volume']
            metadata[key]['observed_minutes'] += 1
    for key, meta in metadata.items():
        meta['coverage_complete'] = meta['observed_minutes'] == meta['expected_minutes']
        meta['volume_known'] = groups[key]['volume'] is not None
    return list(groups.values()), metadata


def sample_minutes():
    path = Path(__file__).parent/'data'/'sample-candles.csv'
    with path.open(newline='', encoding='utf-8-sig') as stream:
        reader = csv.DictReader(stream)
        if tuple(reader.fieldnames or []) != FIELDS:
            raise ValueError('CSV must contain exactly timestamp,open,high,low,close,volume')
        return sorted([dict(timestamp=iso(epoch(r['timestamp'])), **{f: float(r[f]) for f in FIELDS[1:]}) for r in reader], key=lambda r: r['timestamp'])
