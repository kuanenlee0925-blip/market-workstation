"""Append-only revisions and deterministic minute bars from Yahoo quote observations."""
import hashlib
import json
import math
import sqlite3
import time


class Store:
    def __init__(self, path):
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.execute('''CREATE TABLE IF NOT EXISTS observations (
            sequence INTEGER PRIMARY KEY, identity TEXT NOT NULL, revision INTEGER NOT NULL,
            symbol TEXT NOT NULL, source_time REAL NOT NULL, received_time REAL NOT NULL,
            price REAL NOT NULL, day_volume REAL, payload TEXT NOT NULL, digest TEXT UNIQUE,
            UNIQUE(identity, revision))''')
        self.db.execute('CREATE INDEX IF NOT EXISTS observations_symbol ON observations(symbol, source_time)')
        self.db.commit()

    def ingest(self, payload, received=None):
        symbol = str(payload.get('id', ''))
        price = float(payload.get('price', 0))
        timestamp = float(payload.get('time', 0)) / 1000
        if not symbol or not math.isfinite(price) or price <= 0 or not math.isfinite(timestamp) or timestamp <= 0:
            raise ValueError('Invalid symbol, price, or source timestamp')
        volume = payload.get('day_volume')
        volume = float(volume) if volume is not None else None
        if volume is not None and (not math.isfinite(volume) or volume < 0):
            raise ValueError('Invalid cumulative volume')
        raw = json.dumps(payload, sort_keys=True, separators=(',', ':'), allow_nan=False)
        digest = hashlib.sha256(raw.encode()).hexdigest()
        identity = f'yahoo:{symbol}:{timestamp}'
        revision = self.db.execute('SELECT COALESCE(MAX(revision), 0)+1 FROM observations WHERE identity=?', (identity,)).fetchone()[0]
        cursor = self.db.execute('INSERT OR IGNORE INTO observations(identity,revision,symbol,source_time,received_time,price,day_volume,payload,digest) VALUES(?,?,?,?,?,?,?,?,?)',
                                (identity, revision, symbol, timestamp, received or time.time(), price, volume, raw, digest))
        self.db.commit()
        return cursor.rowcount == 1

    def observations(self, symbol, cutoff=None):
        rows = self.db.execute('SELECT * FROM observations WHERE symbol=? AND sequence<=? ORDER BY sequence', (symbol, cutoff if cutoff is not None else 2**63-1)).fetchall()
        return [dict(row) for row in rows]

    def bars(self, symbol, cutoff=None, now=None):
        rows = self.observations(symbol, cutoff)
        latest = {r['identity']: r for r in rows}
        ordered = sorted(latest.values(), key=lambda r: (r['source_time'], r['sequence']))
        bars = {}
        previous = None
        for row in ordered:
            bucket = int(row['source_time'] // 60) * 60
            price = row['price']
            bar = bars.setdefault(bucket, dict(time=bucket, open=price, high=price, low=price, close=price, volume=0))
            bar.update(high=max(bar['high'], price), low=min(bar['low'], price), close=price)
            # Yahoo provides cumulative volume, not trade size. Never count the first total.
            volume = row['day_volume']
            if volume is not None:
                if previous is not None and volume >= previous:
                    bar['volume'] += volume - previous
                previous = volume
        clock = now if now is not None else time.time()
        for bar in bars.values():
            bar['complete'] = bar['time'] + 60 <= clock
        return list(bars.values())

    def snapshot(self, symbol, cutoff=None, now=None):
        rows = self.observations(symbol, cutoff)
        newest = max(rows, key=lambda r: r['source_time']) if rows else None
        return dict(symbol=symbol, bars=self.bars(symbol, cutoff, now), count=len(rows),
                    last_source_time=newest['source_time'] if newest else None,
                    last_received_time=rows[-1]['received_time'] if rows else None)
