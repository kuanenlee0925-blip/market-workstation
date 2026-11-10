"""Append-only revisions and deterministic minute bars from Yahoo quote observations."""
import hashlib
import json
import math
import sqlite3
import time

from .candles import aggregate, minute_candles


class Store:
    def __init__(self, path):
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.execute('''CREATE TABLE IF NOT EXISTS observations (
            sequence INTEGER PRIMARY KEY, identity TEXT NOT NULL, revision INTEGER NOT NULL,
            symbol TEXT NOT NULL, source_time REAL NOT NULL, received_time REAL NOT NULL,
            price REAL NOT NULL, day_volume REAL, payload TEXT NOT NULL, digest TEXT UNIQUE,
            UNIQUE(identity, revision))''')
        self.db.execute('CREATE INDEX IF NOT EXISTS observations_symbol ON observations(symbol, source_time)')
        self.db.commit()
        if 'supersedes' not in {r[1] for r in self.db.execute('PRAGMA table_info(observations)')}:
            self.db.execute('ALTER TABLE observations ADD COLUMN supersedes INTEGER REFERENCES observations(sequence)')
            self.db.commit()

    def ingest(self, payload, received=None, supersedes=None):
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
        digest = hashlib.sha256((raw if supersedes is None else f'{raw}:correction:{supersedes}').encode()).hexdigest()
        if self.db.execute('SELECT 1 FROM observations WHERE digest=?', (digest,)).fetchone():
            return False
        identity = f'yahoo:{symbol}:{timestamp}'
        # A timestamp is not a trade ID. Only an explicit, verified link supersedes a quote.
        if supersedes is not None:
            original = self.db.execute('SELECT symbol FROM observations WHERE sequence=?', (supersedes,)).fetchone()
            used = self.db.execute('SELECT 1 FROM observations WHERE supersedes=?', (supersedes,)).fetchone()
            if original is None or original['symbol'] != symbol or used:
                raise ValueError('Correction must reference an existing, current observation of this symbol')
        revision = self.db.execute('SELECT COALESCE(MAX(revision), 0)+1 FROM observations WHERE identity=?', (identity,)).fetchone()[0]
        cursor = self.db.execute('INSERT OR IGNORE INTO observations(identity,revision,symbol,source_time,received_time,price,day_volume,payload,digest,supersedes) VALUES(?,?,?,?,?,?,?,?,?,?)',
                                (identity, revision, symbol, timestamp, time.time() if received is None else received, price, volume, raw, digest, supersedes))
        self.db.commit()
        return cursor.rowcount == 1

    def observations(self, symbol, cutoff=None):
        rows = self.db.execute('SELECT * FROM observations WHERE symbol=? AND sequence<=? ORDER BY sequence', (symbol, cutoff if cutoff is not None else 2**63-1)).fetchall()
        return [dict(row) for row in rows]

    def candles(self, symbol, cutoff=None, now=None, interval='1m', start=None, end=None):
        return aggregate(minute_candles(self.observations(symbol, cutoff), symbol), symbol, interval,
                         time.time() if now is None else now, start, end)

    def snapshot(self, symbol, cutoff=None, now=None, interval='1m', start=None, end=None):
        rows = self.observations(symbol, cutoff)
        newest = max(rows, key=lambda r: r['source_time']) if rows else None
        bars, metadata = self.candles(symbol, cutoff, now, interval, start, end)
        return dict(symbol=symbol, interval=interval, bars=bars, metadata=metadata, count=len(rows),
                    last_source_time=newest['source_time'] if newest else None,
                    last_received_time=rows[-1]['received_time'] if rows else None)
