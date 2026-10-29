# Modified 2026-10-29 for the independent Simulation Lab edition; see NOTICE and MODIFICATIONS.md.
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import pytest
from app.simlab.provider import (ModelProvider, ProviderError, BudgetExceeded,
    UsageUnavailable, run_scope, usage, local_url, create_budget)


def test_budget_is_persistent_and_failed_attempts_count(monkeypatch):
    monkeypatch.setattr(ModelProvider, '_invoke', lambda *_: (_ for _ in ()).throw(UsageUnavailable('exhausted')))
    with run_scope('limited', 1):
        with pytest.raises(UsageUnavailable):
            ModelProvider().complete([{'role': 'user', 'content': 'a'}])
    # Recreating a run never replenishes or raises its previous budget.
    with run_scope('limited', 24):
        with pytest.raises(BudgetExceeded):
            ModelProvider().complete([{'role': 'user', 'content': 'b'}])
    assert usage('limited')['budgets'][0]['remaining'] == 0
    assert usage('limited')['calls'][0]['status'] == 'failed'


def test_cached_retry_does_not_call_model_again_but_other_run_is_independent(monkeypatch):
    calls = []
    def invoke(self, request):
        calls.append(request)
        return {'content': '{"ok":true}', 'usage': {'test': 1}}
    monkeypatch.setattr(ModelProvider, '_invoke', invoke)
    for run_id in ['same', 'same', 'independent']:
        with run_scope(run_id, 2):
            assert ModelProvider().complete([{'role': 'user', 'content': 'test'}], json_mode=True)['content']
    assert len(calls) == 2
    assert len(usage('same')['calls']) == 1


def test_retry_is_bounded_and_each_attempt_is_charged(monkeypatch):
    monkeypatch.setenv('SIMLAB_MODEL_RETRIES', '1')
    monkeypatch.setattr('app.simlab.provider.time.sleep', lambda _: None)
    calls = []
    def invoke(*_):
        calls.append(1)
        if len(calls) == 1:
            raise ConnectionError('transient')
        return {'content': '{}'}
    monkeypatch.setattr(ModelProvider, '_invoke', invoke)
    with run_scope('retry', 2):
        ModelProvider().complete([], json_mode=True)
    assert len(usage('retry')['calls']) == 2
    assert [x['status'] for x in usage('retry')['calls']] == ['completed', 'failed']


def test_schema_validation_records_failure(monkeypatch):
    monkeypatch.setattr(ModelProvider, '_invoke', lambda *_: {'content': '{"number":"bad"}'})
    with run_scope('schema', 1):
        with pytest.raises(Exception):
            ModelProvider().complete([], schema={'type': 'object', 'properties': {'number': {'type': 'number'}}})
    assert usage('schema')['calls'][0]['status'] == 'failed'


def test_all_threads_share_a_strict_single_inference_slot(monkeypatch):
    active = 0
    peak = 0
    guard = threading.Lock()
    def invoke(*_):
        nonlocal active, peak
        with guard:
            active += 1
            peak = max(peak, active)
        time.sleep(.03)
        with guard:
            active -= 1
        return {'content': '{}'}
    monkeypatch.setattr(ModelProvider, '_invoke', invoke)
    def work(i):
        with run_scope('threaded', 6):
            return ModelProvider().complete([{'role': 'user', 'content': str(i)}], cache=False)
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(work, range(4)))
    assert peak == 1
    assert len(usage('threaded')['calls']) == 4


@pytest.mark.parametrize('url', ['https://api.openai.com/v1', 'http://example.com', 'http://127.0.0.1.evil.com', 'http://user:pass@localhost:11434'])
def test_remote_or_credentialed_ollama_is_rejected(url):
    with pytest.raises(ProviderError):
        local_url(url)


def test_paid_provider_and_over_cap_budget_rejected():
    with pytest.raises(ProviderError):
        ModelProvider(provider='openai')
    with pytest.raises(ValueError):
        create_budget('huge', 100)


def test_expired_journey_deadline_never_starts_or_charges_a_turn(monkeypatch):
    monkeypatch.setattr(ModelProvider,'_invoke',lambda *_:pytest.fail('Expired deadline must not call inference'))
    with run_scope('expired',1):
        with pytest.raises(UsageUnavailable,match='deadline'):
            ModelProvider().complete([],deadline=time.monotonic()-1)
    assert usage('expired')['budgets'][0]['attempted']==0


def test_journey_deadline_bounds_the_existing_sdk_worker(monkeypatch):
    captured=[]
    def invoke(self,request):
        captured.append(request['_timeout'])
        return {'content':'{}'}
    monkeypatch.setattr(ModelProvider,'_invoke',invoke)
    with run_scope('bounded',1):
        ModelProvider().complete([],deadline=time.monotonic()+2)
    assert 0<captured[0]<=2
    assert usage('bounded')['budgets'][0]['attempted']==1
