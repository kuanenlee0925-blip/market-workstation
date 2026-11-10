"""Part 1 SmokeTest: real local services/browser, temporary DB, no provider keys."""
import json
from contextlib import closing
import os
from pathlib import Path
import shutil
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def read(url):
    with urllib.request.urlopen(url, timeout=2) as response:
        return json.load(response)


def ready(url, process):
    deadline = time.monotonic()+40
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError('Service exited during startup; see log output')
        try:
            return read(url)
        except (OSError, ValueError):
            time.sleep(.25)
    raise RuntimeError('Service did not become ready')


def stop(process):
    if process and process.poll() is None:
        if os.name == 'nt':
            subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            import signal
            os.killpg(process.pid, signal.SIGTERM)
        process.wait(timeout=15)


def main():
    backend = frontend = None
    with tempfile.TemporaryDirectory(prefix='market-smoke-') as temp:
        db = Path(temp)/'smoke.sqlite'
        api, base = f'http://127.0.0.1:{port()}', f'http://127.0.0.1:{port()}'
        env = dict(os.environ, MARKET_DB=str(db), MARKET_TEST_MODE='1', FEED_ENABLED='0', MARKET_API_URL=api, MARKET_BASE_URL=base, SMOKE_TEST='1')
        env.pop('LIVE_TEST', None)
        npm = shutil.which('npm.cmd' if os.name == 'nt' else 'npm')
        if not npm:
            raise RuntimeError('npm is required; no dependencies were installed by SmokeTest')
        with (Path(temp)/'backend.log').open('w+', encoding='utf-8') as blog, (Path(temp)/'frontend.log').open('w+', encoding='utf-8') as flog:
            def start_backend():
                return subprocess.Popen([sys.executable, '-m', 'uvicorn', 'backend.main:app', '--host', '127.0.0.1', '--port', api.rsplit(':',1)[1]], cwd=ROOT, env=env, stdout=blog, stderr=blog, start_new_session=os.name != 'nt')
            try:
                backend = start_backend()
                expected = ready(api+'/api/health', backend)
                frontend = subprocess.Popen([npm, 'run', 'dev', '--', '--port', base.rsplit(':',1)[1], '--strictPort'], cwd=ROOT/'frontend', env=env, stdout=flog, stderr=flog, start_new_session=os.name != 'nt')
                assert ready(base+'/api/health', frontend) == expected
                print('PASS: direct and frontend-proxied health JSON match', flush=True)
                subprocess.run([npm, 'exec', '--', 'playwright', 'test'], cwd=ROOT/'frontend', env=env, check=True)
                with closing(sqlite3.connect(db)) as conn:
                    before = conn.execute('SELECT sequence,digest FROM observations ORDER BY sequence').fetchall()
                assert len(before) == 4
                stop(backend)
                try:
                    read(base+'/api/health')
                    raise AssertionError('Proxy succeeded while backend was stopped')
                except urllib.error.HTTPError as exc:
                    assert exc.code >= 500
                print('PASS: frontend proxy fails with backend stopped', flush=True)
                backend = start_backend()
                ready(api+'/api/health', backend)
                assert read(base+'/api/health') == expected
                with closing(sqlite3.connect(db)) as conn:
                    assert conn.execute('SELECT sequence,digest FROM observations ORDER BY sequence').fetchall() == before
                print('PASS: restart recovery and all 4 persisted observations verified', flush=True)
                replay_env = dict(env, SMOKE_RESTART='1')
                subprocess.run([npm, 'exec', '--', 'playwright', 'test', '--grep', 'persisted offline replay'], cwd=ROOT/'frontend', env=replay_env, check=True)
            except Exception:
                for name, stream in [('Backend', blog), ('Frontend', flog)]:
                    stream.flush(); stream.seek(0)
                    print(name+' log tail:\n'+stream.read()[-5000:])
                raise
            finally:
                stop(frontend); stop(backend)
    print('PASS: SmokeTest complete; temporary database and owned services cleaned up')


if __name__ == '__main__':
    main()
