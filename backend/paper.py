"""Local long-only simulation. Orders/fills/signals/valuations are retained evidence."""
from decimal import Decimal
import hashlib
import json
import time
from uuid import uuid4

from .candles import aggregate, epoch, minute_candles, session
from .indicators import moving_averages


def money(value):
    result = Decimal(str(value))
    if not result.is_finite():
        raise ValueError('Amount must be finite')
    return result


class Paper:
    def __init__(self, db):
        self.db = db
        for statement in (
            'CREATE TABLE IF NOT EXISTS paper_accounts (id TEXT PRIMARY KEY, config TEXT NOT NULL, state TEXT NOT NULL)',
            'CREATE TABLE IF NOT EXISTS paper_orders (id TEXT PRIMARY KEY, account_id TEXT NOT NULL, request_id TEXT NOT NULL, data TEXT NOT NULL, UNIQUE(account_id,request_id))',
            'CREATE TABLE IF NOT EXISTS paper_order_events (sequence INTEGER PRIMARY KEY, order_id TEXT NOT NULL, data TEXT NOT NULL)',
            'CREATE TABLE IF NOT EXISTS paper_fills (id TEXT PRIMARY KEY, account_id TEXT NOT NULL, order_id TEXT UNIQUE NOT NULL, data TEXT NOT NULL)',
            'CREATE TABLE IF NOT EXISTS paper_pnl (sequence INTEGER PRIMARY KEY, account_id TEXT NOT NULL, event_key TEXT NOT NULL, data TEXT NOT NULL, UNIQUE(account_id,event_key))',
            'CREATE TABLE IF NOT EXISTS paper_signals (sequence INTEGER PRIMARY KEY, account_id TEXT NOT NULL, candle TEXT NOT NULL, data TEXT NOT NULL, UNIQUE(account_id,candle))',
            'CREATE TABLE IF NOT EXISTS backtest_inputs (account_id TEXT PRIMARY KEY, data TEXT NOT NULL)',
        ):
            db.execute(statement)
        db.commit()

    def create(self, symbol, initial=1000, short=2, long=3, size=4, interval='1m', source='live', strategy=False, last_sequence=0):
        moving_averages([], {}, short, long)
        if money(initial) <= 0 or isinstance(size, bool) or not isinstance(size, int) or size <= 0:
            raise ValueError('Starting cash and whole-share order size must be positive')
        identifier = str(uuid4())
        config = dict(symbol=symbol, initial=str(money(initial)), short=short, long=long, size=size, interval=interval, source=source, created=time.time())
        state = dict(cash=config['initial'], quantity=0, average_cost='0', realized='0', price=None,
                     price_time=None, price_source=None, price_source_time=None, last_sequence=last_sequence, source_watermark=0,
                     completed_through=None, strategy=strategy, event_time=None)
        with self.db:
            self.db.execute('INSERT INTO paper_accounts VALUES (?,?,?)', (identifier, json.dumps(config), json.dumps(state)))
        return identifier

    def load(self, identifier):
        row = self.db.execute('SELECT * FROM paper_accounts WHERE id=?', (identifier,)).fetchone()
        if row is None:
            raise ValueError('Unknown paper account')
        return json.loads(row['config']), json.loads(row['state'])

    def save(self, identifier, state):
        self.db.execute('UPDATE paper_accounts SET state=? WHERE id=?', (json.dumps(state), identifier))

    def strategy(self, identifier, enabled):
        config, state = self.load(identifier)
        if config['source'] != 'live':
            raise ValueError('Historical runs are immutable; create another run')
        state['strategy'] = enabled
        with self.db:
            self.save(identifier, state)

    def orders(self, identifier):
        result = []
        for row in self.db.execute('SELECT * FROM paper_orders WHERE account_id=? ORDER BY rowid', (identifier,)):
            order = json.loads(row['data'])
            events = [json.loads(r[0]) for r in self.db.execute('SELECT data FROM paper_order_events WHERE order_id=? ORDER BY sequence', (row['id'],))]
            result.append(dict(**order, **events[-1], events=events))
        return result

    def status(self, order, status, clock, reason=None):
        self.db.execute('INSERT INTO paper_order_events(order_id,data) VALUES (?,?)', (order['id'], json.dumps(dict(status=status, status_time=clock, reason=reason))))

    def submit(self, identifier, request_id, side, quantity=None, clock=None, sequence=None, eligible_source=None, origin='manual'):
        with self.db:
            return self._submit(identifier, request_id, side, quantity, clock, sequence, eligible_source, origin)

    def _submit(self, identifier, request_id, side, quantity, clock, sequence, eligible_source, origin):
        config, state = self.load(identifier)
        existing = self.db.execute('SELECT data FROM paper_orders WHERE account_id=? AND request_id=?', (identifier, request_id)).fetchone()
        if existing:
            order = json.loads(existing[0])
            if order['side'] != side or order['requested_quantity'] != quantity:
                raise ValueError('This request ID was already used for a different order')
            return order['id']
        if side not in ('buy', 'sell', 'close'):
            raise ValueError('Choose buy, sell or close')
        clock = time.time() if clock is None else clock
        qty = state['quantity'] if side == 'close' else quantity
        order = dict(id=str(uuid4()), account_id=identifier, request_id=request_id, symbol=config['symbol'], side=side,
                     requested_quantity=quantity, quantity=qty, submitted=clock, after_sequence=state['last_sequence'] if sequence is None else sequence,
                     eligible_source=clock if eligible_source is None else eligible_source, origin=origin)
        self.db.execute('INSERT INTO paper_orders VALUES (?,?,?,?)', (order['id'], identifier, request_id, json.dumps(order)))
        reason = None
        if isinstance(qty, bool) or not isinstance(qty, int) or qty <= 0:
            reason = 'Quantity must be a positive whole number; close requires an open position'
        elif side in ('sell', 'close') and qty > state['quantity']:
            reason = 'Insufficient shares'
        self.status(order, 'rejected' if reason else 'pending', clock, reason)
        return order['id']

    def valuation(self, identifier, config, state, event_key, price, clock, source, event, source_time=None):
        price = money(price)
        unrealized = state['quantity'] * (price - money(state['average_cost']))
        realized = money(state['realized'])
        row = dict(event=event, event_key=event_key, timestamp=clock, price=float(price), source=source,
                   source_time=clock if source_time is None else source_time, cash=float(money(state['cash'])), quantity=state['quantity'], average_cost=float(money(state['average_cost'])),
                   realized=float(realized), unrealized=float(unrealized), total=float(realized+unrealized),
                   equity=float(money(state['cash'])+state['quantity']*price))
        self.db.execute('INSERT OR IGNORE INTO paper_pnl(account_id,event_key,data) VALUES (?,?,?)', (identifier, event_key, json.dumps(row)))
        state.update(price=str(price), price_time=clock, price_source=source, price_source_time=clock if source_time is None else source_time)

    def process(self, identifier, rows):
        """Rows are the recorded arrival prefix, in sequence order. Repeated prefixes are no-ops."""
        config, state = self.load(identifier)
        prefix = []
        for row in rows:
            prefix.append(row)
            if row['sequence'] <= state['last_sequence']:
                continue
            clock = max(row['received_time'], state['event_time'] or row['received_time'])
            with self.db:
                eligible = (row.get('supersedes') is None and row['source_time'] >= state['source_watermark']
                            and session(config['symbol'], row['source_time']) is not None)
                if eligible:
                    for order in self.orders(identifier):
                        if order['status'] != 'pending' or row['sequence'] <= order['after_sequence'] or clock < order['submitted'] or row['source_time'] < order['eligible_source']:
                            continue
                        price, qty = money(row['price']), order['quantity']
                        cash, average = money(state['cash']), money(state['average_cost'])
                        if order['side'] == 'buy':
                            reason = 'Insufficient cash at fill' if cash < qty*price else None
                        else:
                            reason = 'Insufficient shares at fill' if qty > state['quantity'] else None
                        if reason:
                            self.status(order, 'rejected', clock, reason)
                            continue
                        if order['side'] == 'buy':
                            state['average_cost'] = str((average*state['quantity']+price*qty)/(state['quantity']+qty))
                            state['quantity'] += qty
                            state['cash'] = str(cash-qty*price)
                        else:
                            state['quantity'] -= qty
                            state['cash'] = str(cash+qty*price)
                            state['realized'] = str(money(state['realized'])+qty*(price-average))
                            if not state['quantity']:
                                state['average_cost'] = '0'
                        fill = dict(id=str(uuid4()), order_id=order['id'], symbol=config['symbol'], side=order['side'], quantity=qty,
                                    price=float(price), observation_sequence=row['sequence'], source_time=row['source_time'], executed=clock)
                        self.db.execute('INSERT INTO paper_fills VALUES (?,?,?,?)', (fill['id'], identifier, order['id'], json.dumps(fill)))
                        self.status(order, 'filled', clock)
                        self.valuation(identifier, config, state, 'fill:'+order['id'], price, clock, 'observation #'+str(row['sequence']), 'fill', row['source_time'])
                bars, metadata = aggregate(minute_candles(prefix, config['symbol']), config['symbol'], config['interval'], clock)
                averages = moving_averages(bars, metadata, config['short'], config['long'])
                for bar, sma in zip(bars, averages):
                    if not metadata[bar['timestamp']]['complete'] or (state['completed_through'] is not None and bar['timestamp'] <= state['completed_through']):
                        continue
                    signal = dict(**sma, available_at=clock, observation_sequence=row['sequence'])
                    self.db.execute('INSERT OR IGNORE INTO paper_signals(account_id,candle,data) VALUES (?,?,?)', (identifier, bar['timestamp'], json.dumps(signal)))
                    if state['quantity']:
                        self.valuation(identifier, config, state, 'candle:'+bar['timestamp'], bar['close'], clock, 'completed candle '+bar['timestamp'], 'valuation', epoch(bar['timestamp']))
                    if state['strategy'] and sma['crossover']:
                        pending = any(o['status'] == 'pending' for o in self.orders(identifier))
                        side = 'buy' if sma['crossover'] == 'up' else 'close'
                        if not pending and ((side == 'buy' and not state['quantity']) or (side == 'close' and state['quantity'])):
                            self.save(identifier, state)
                            self._submit(identifier, 'sma:'+bar['timestamp'], side, config['size'] if side == 'buy' else None,
                                         clock, row['sequence'], epoch(metadata[bar['timestamp']]['end']), 'SMA '+sma['crossover'])
                    state['completed_through'] = bar['timestamp']
                state['last_sequence'] = row['sequence']
                state['source_watermark'] = max(state['source_watermark'], row['source_time'])
                state['event_time'] = clock
                self.save(identifier, state)

    def view(self, identifier):
        config, state = self.load(identifier)
        valuations = [json.loads(r[0]) for r in self.db.execute('SELECT data FROM paper_pnl WHERE account_id=? ORDER BY sequence', (identifier,))]
        fills = [json.loads(r[0]) for r in self.db.execute('SELECT data FROM paper_fills WHERE account_id=? ORDER BY rowid', (identifier,))]
        signals = [json.loads(r[0]) for r in self.db.execute('SELECT data FROM paper_signals WHERE account_id=? ORDER BY sequence', (identifier,))]
        unrealized = None if state['quantity'] and state['price'] is None else state['quantity']*(money(state['price'] or 0)-money(state['average_cost']))
        equity = None if unrealized is None else money(state['cash'])+state['quantity']*money(state['price'] or 0)
        peak, drawdown = money(config['initial']), Decimal(0)
        for v in valuations:
            peak = max(peak, money(v['equity']))
            drawdown = max(drawdown, (peak-money(v['equity']))/peak)
        summary = dict(cash=float(money(state['cash'])), quantity=state['quantity'], average_cost=float(money(state['average_cost'])),
                       realized=float(money(state['realized'])), unrealized=float(unrealized) if unrealized is not None else None,
                       equity=float(equity) if equity is not None else None, return_percent=float((equity/money(config['initial'])-1)*100) if equity is not None else None,
                       max_drawdown_percent=float(drawdown*100), fills=len(fills), price=float(money(state['price'])) if state['price'] else None,
                       price_time=state['price_time'], price_source_time=state.get('price_source_time'), price_source=state['price_source'], strategy=state['strategy'])
        inputs = self.db.execute('SELECT data FROM backtest_inputs WHERE account_id=?', (identifier,)).fetchone()
        evidence = None
        if inputs:
            frozen = json.loads(inputs[0])
            evidence = dict(sha256=frozen['sha256'], observations=len(frozen['rows']),
                            first_receipt=frozen['rows'][0]['received_time'], last_receipt=frozen['rows'][-1]['received_time'])
        return dict(id=identifier, config=config, summary=summary, orders=self.orders(identifier), fills=fills, pnl=valuations, signals=signals, inputs=evidence)


def reference_events():
    """Explicitly synthetic seven-close SMA example with later observations for fills."""
    start = epoch('2026-11-09T15:00:00Z')
    return [dict(sequence=i+1, symbol='AAPL', source_time=start+i*60, received_time=start+i*60+1,
                 price=p, day_volume=None, supersedes=None) for i, p in enumerate([13, 10, 7, 13, 19, 7, 1, 8, 9])]


def backtest(paper, rows, symbol, initial, short, long, size, interval, source):
    if not rows:
        raise ValueError('No recorded observations in this range; select a different range or the labeled synthetic reference')
    if len(rows) > 3000:
        raise ValueError('Limit this educational backtest to 3,000 observations using the UTC receipt-time range')
    identifier = paper.create(symbol, initial, short, long, size, interval, source, strategy=True)
    frozen = json.dumps(rows, sort_keys=True)
    with paper.db:
        paper.db.execute('INSERT INTO backtest_inputs VALUES (?,?)', (identifier, json.dumps(dict(rows=rows, sha256=hashlib.sha256(frozen.encode()).hexdigest()))))
    paper.process(identifier, rows)
    return paper.view(identifier)
