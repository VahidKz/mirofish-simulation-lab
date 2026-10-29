# Modified 2026-10-29 for the independent Simulation Lab edition; see NOTICE and MODIFICATIONS.md.
"""One guarded inference path for Flask, graph services and CAMEL/OASIS.

Budgets, cache and audit are persisted in SQLite. A process-wide file lock
serializes inference across Flask threads AND legacy OASIS subprocesses.
Every attempted turn, including retries and failures, consumes the run budget.
"""
import contextvars
import fcntl
import hashlib
import json
import logging
import os
from pathlib import Path
import signal
import sqlite3
import subprocess
import sys
import time
from contextlib import contextmanager
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[3]
RUN = contextvars.ContextVar('simlab_run', default=None)
log = logging.getLogger('mirofish.provider')


class ProviderError(RuntimeError):
    pass


class BudgetExceeded(ProviderError):
    pass


class UsageUnavailable(ProviderError):
    pass


def data_dir():
    path = Path(os.getenv('SIMLAB_DATA_DIR', 'backend/uploads/simlab'))
    if not path.is_absolute():
        path = ROOT / path
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    return path


def local_url(url):
    parsed = urlparse(url)
    if parsed.scheme != 'http' or parsed.hostname not in {'localhost', '127.0.0.1', '::1', 'ollama'} or parsed.username or parsed.password:
        raise ProviderError('Only a local HTTP Ollama endpoint is allowed. Paid API fallback is disabled.')
    return url


@contextmanager
def db():
    conn = sqlite3.connect(data_dir() / 'usage.sqlite3', timeout=30)
    conn.row_factory = sqlite3.Row
    conn.executescript('''
      CREATE TABLE IF NOT EXISTS budgets (run_id TEXT PRIMARY KEY, maximum INTEGER NOT NULL);
      CREATE TABLE IF NOT EXISTS calls (id INTEGER PRIMARY KEY, run_id TEXT, provider TEXT,
        started REAL, elapsed REAL, status TEXT, usage TEXT, error TEXT);
      CREATE TABLE IF NOT EXISTS cache (key TEXT PRIMARY KEY, content TEXT);
    ''')
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def create_budget(run_id, maximum):
    cap = int(os.getenv('SIMLAB_MAX_CALLS', '24'))
    if not 1 <= maximum <= cap:
        raise ValueError(f'Maximum calls must be between 1 and server cap {cap}.')
    with db() as conn:
        conn.execute('INSERT OR IGNORE INTO budgets VALUES (?, ?)', (run_id, maximum))


@contextmanager
def run_scope(run_id, maximum=None):
    if maximum is not None:
        create_budget(run_id, maximum)
    token = RUN.set(run_id)
    try:
        yield
    finally:
        RUN.reset(token)


def usage(run_id=None):
    with db() as conn:
        where, args = ('WHERE run_id=?', (run_id,)) if run_id else ('', ())
        calls = [dict(x) for x in conn.execute(f'SELECT * FROM calls {where} ORDER BY id DESC LIMIT 1000', args)]
        for c in calls:
            c['usage'] = json.loads(c['usage'] or '{}')
        budgets = [dict(x) for x in conn.execute(f'SELECT * FROM budgets {where}', args)]
        counts = {r['run_id']: r['n'] for r in conn.execute('SELECT run_id, COUNT(*) n FROM calls GROUP BY run_id')}
        for b in budgets:
            b['attempted'] = counts.get(b['run_id'], 0)
            b['remaining'] = max(0, b['maximum'] - b['attempted'])
        return {'budgets': budgets, 'calls': calls, 'concurrency_limit': 1,
                'paid_api_fallback': False, 'unit': 'attempted SDK turns (not billing requests)'}


def worker(payload, timeout=None):
    # Never pass API credentials into the runtime. ChatGPT login is read only
    # by the official SDK, from its normal credential store.
    blocked = {'OPENAI_API_KEY', 'CODEX_API_KEY', 'OPENAI_BASE_URL', 'OPENAI_API_BASE',
               'OPENAI_API_BASE_URL', 'LLM_API_KEY', 'CODEX_ACCESS_TOKEN'}
    env = {k: v for k, v in os.environ.items() if k not in blocked}
    env['PYTHONPATH'] = str(ROOT / 'backend')
    proc = subprocess.Popen([sys.executable, '-m', 'app.simlab.codex_worker'],
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            text=True, env=env, cwd=ROOT / 'backend', start_new_session=True)
    try:
        out, _ = proc.communicate(json.dumps(payload), timeout=timeout or int(os.getenv('SIMLAB_CALL_TIMEOUT', '180')))
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGKILL)
        proc.communicate()
        raise UsageUnavailable('Codex timed out; attempt counted. No paid fallback was used.') from None
    try:
        result = json.loads(out)
    except (ValueError, TypeError):
        raise ProviderError('Codex SDK runtime failed; check installation or sign in using codex login.') from None
    if 'error' in result:
        raise UsageUnavailable(result['error'])
    return result


def codex_status():
    return worker({'op': 'status'}, timeout=30)


class ModelProvider:
    def __init__(self, provider=None, model=None):
        self.provider = provider or os.getenv('MODEL_PROVIDER', 'codex')
        if self.provider not in {'codex', 'ollama'}:
            raise ProviderError('Only codex and local ollama are supported. No paid providers.')
        self.model = model or (os.getenv('CODEX_MODEL') if self.provider == 'codex' else os.getenv('OLLAMA_MODEL', 'qwen2.5:3b'))

    def complete(self, messages, schema=None, json_mode=False, temperature=0.3, max_tokens=4096, cache=True, deadline=None):
        run_id = RUN.get() or os.getenv('SIMLAB_RUN_ID', 'legacy-session')
        create_budget(run_id, int(os.getenv('SIMLAB_MAX_CALLS', '24')))
        request = {'messages': messages, 'schema': schema, 'json_mode': json_mode,
                   'model': self.model, 'provider': self.provider, 'temperature': temperature,
                   'max_tokens': max_tokens, 'run_id': run_id}
        key = hashlib.sha256(json.dumps(request, sort_keys=True).encode()).hexdigest()
        with (data_dir() / 'inference.lock').open('a') as lock:
            if deadline is None:
                fcntl.flock(lock, fcntl.LOCK_EX)
            else:
                while True:
                    if time.monotonic() >= deadline:
                        raise UsageUnavailable('Inference deadline expired while waiting for the shared slot.')
                    try:
                        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                        break
                    except BlockingIOError:
                        time.sleep(min(.05, max(0, deadline-time.monotonic())))
            if cache:
                with db() as conn:
                    hit = conn.execute('SELECT content FROM cache WHERE key=?', (key,)).fetchone()
                if hit:
                    return json.loads(hit[0])
            retries = min(2, max(0, int(os.getenv('SIMLAB_MODEL_RETRIES', '1'))))
            for attempt in range(retries + 1):
                if deadline is not None:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise UsageUnavailable('Inference deadline expired. No fallback was used.')
                    request['_timeout'] = min(remaining, int(os.getenv('SIMLAB_CALL_TIMEOUT', '180')))
                with db() as conn:
                    conn.execute('BEGIN IMMEDIATE')
                    maximum = conn.execute('SELECT maximum FROM budgets WHERE run_id=?', (run_id,)).fetchone()[0]
                    n = conn.execute('SELECT COUNT(*) FROM calls WHERE run_id=?', (run_id,)).fetchone()[0]
                    if n >= maximum:
                        raise BudgetExceeded(f'Run {run_id} exhausted its {maximum} model-call budget. No fallback was used.')
                    call_id = conn.execute('INSERT INTO calls(run_id,provider,started,status) VALUES(?,?,?,?)',
                                           (run_id, self.provider, time.time(), 'started')).lastrowid
                started = time.monotonic()
                try:
                    result = self._invoke(request)
                    if json_mode or schema:
                        parsed = json.loads(result['content'])
                        if schema:
                            from jsonschema import validate
                            validate(parsed, schema)
                    with db() as conn:
                        conn.execute('UPDATE calls SET status=?,elapsed=?,usage=? WHERE id=?',
                                     ('completed', time.monotonic()-started, json.dumps(result.get('usage', {})), call_id))
                        if cache:
                            conn.execute('INSERT OR REPLACE INTO cache VALUES (?,?)', (key, json.dumps(result)))
                    log.info('Model call %s run=%s provider=%s completed', call_id, run_id, self.provider)
                    return result
                except Exception as exc:
                    # Store classifications, never raw transport/auth exceptions.
                    with db() as conn:
                        conn.execute('UPDATE calls SET status=?,elapsed=?,error=? WHERE id=?',
                                     ('failed', time.monotonic()-started, type(exc).__name__, call_id))
                    log.error('Model call %s run=%s failed: %s', call_id, run_id, type(exc).__name__)
                    if isinstance(exc, UsageUnavailable) or attempt == retries:
                        raise
                    time.sleep(min(4, 2 ** attempt))

    def _invoke(self, request):
        if self.provider == 'codex':
            return worker(request, timeout=request.get('_timeout'))
        from openai import OpenAI
        url = local_url(os.getenv('LLM_BASE_URL', 'http://127.0.0.1:11434/v1'))
        kwargs = dict(model=self.model, messages=request['messages'],
                      temperature=request['temperature'], max_tokens=request['max_tokens'])
        if request['schema'] or request['json_mode']:
            kwargs['response_format'] = {'type': 'json_object'}
        with OpenAI(api_key='ollama', base_url=url, max_retries=0,
                    timeout=request.get('_timeout', int(os.getenv('SIMLAB_CALL_TIMEOUT', '180')))) as client:
            result = client.chat.completions.create(**kwargs)
        return {'content': result.choices[0].message.content, 'usage': result.usage.model_dump() if result.usage else {}}


class CompletionFacade:
    """Narrow in-process compatibility facade for two original service classes."""
    def __init__(self, model=None):
        from types import SimpleNamespace
        self.provider = ModelProvider(model=model if os.getenv('MODEL_PROVIDER') == 'ollama' else None)
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    def create(self, messages, response_format=None, temperature=0.3, max_tokens=4096, **ignored):
        from types import SimpleNamespace as NS
        result = self.provider.complete(messages, json_mode=bool(response_format),
                                        temperature=temperature, max_tokens=max_tokens)
        return NS(choices=[NS(message=NS(content=result['content']), finish_reason='stop')])
