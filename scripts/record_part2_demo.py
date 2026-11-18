"""Record actual UI actions against an isolated copy of recorded Yahoo observations."""
from pathlib import Path
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile

from smoke_test import port, ready, stop

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.store import Store


def main():
    process = None
    with tempfile.TemporaryDirectory(prefix='market-part2-video-') as temp:
        target = Store(Path(temp)/'demo.sqlite')
        original = sqlite3.connect('file:'+str(ROOT/'market.sqlite')+'?mode=ro', uri=True)
        original.row_factory = sqlite3.Row
        rows = [dict(r) for r in original.execute("SELECT * FROM observations WHERE symbol='BTC-USD' ORDER BY sequence DESC LIMIT 600")][::-1]
        original.close()
        if not rows:
            raise RuntimeError('Recorded Yahoo observations are required for this video; no synthetic substitution')
        columns = list(rows[0])
        target.db.executemany('INSERT INTO observations('+','.join(columns)+') VALUES ('+','.join('?' for _ in columns)+')', [tuple(row[c] for c in columns) for row in rows])
        target.db.commit(); target.db.close()
        base = f'http://127.0.0.1:{port()}'
        env = dict(os.environ, MARKET_DB=str(Path(temp)/'demo.sqlite'), FEED_ENABLED='0', MARKET_TEST_MODE='0', MARKET_BASE_URL=base)
        with (Path(temp)/'backend.log').open('w', encoding='utf-8') as log:
            try:
                process = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'backend.main:app', '--host', '127.0.0.1', '--port', base.rsplit(':',1)[1]], cwd=ROOT, env=env, stdout=log, stderr=log)
                ready(base+'/api/health', process)
                subprocess.run([shutil.which('node'), 'scripts/record_part2_demo.mjs'], cwd=ROOT/'frontend', env=env, check=True)
            finally:
                stop(process)


if __name__ == '__main__':
    main()
