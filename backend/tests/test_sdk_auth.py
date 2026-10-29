# Modified 2026-10-29 for the independent Simulation Lab edition; see NOTICE and MODIFICATIONS.md.
"""Test SDK auth decisions using fakes, without inspecting local credentials."""
from types import SimpleNamespace
import pytest
import openai_codex
from app.simlab.codex_worker import main


def fake_sdk(monkeypatch, account_type):
    class FakeCodex:
        def __init__(self, config):
            assert 'forced_login_method="chatgpt"' in config.config_overrides
            assert 'features.shell_tool=false' in config.config_overrides
            assert 'mcp_servers={}' in config.config_overrides
        def __enter__(self):
            return self
        def __exit__(self, *_):
            pass
        def account(self):
            return SimpleNamespace(account=SimpleNamespace(model_dump=lambda **_: {'type': account_type, 'plan_type': 'test'}))
        def thread_start(self, **kwargs):
            raise AssertionError('Status/auth validation must not start a model turn')
    monkeypatch.setattr(openai_codex, 'Codex', FakeCodex)


def test_chatgpt_auth_status_never_reveals_tokens(monkeypatch):
    fake_sdk(monkeypatch, 'chatgpt')
    assert main({'op': 'status'}) == {'authenticated': True, 'auth_type': 'chatgpt', 'plan': 'test', 'paid_api_fallback': False}


@pytest.mark.parametrize('kind', ['apiKey', 'apikey', None])
def test_api_key_or_missing_auth_is_rejected_before_inference(monkeypatch, kind):
    fake_sdk(monkeypatch, kind)
    with pytest.raises(RuntimeError, match='ChatGPT authentication is required'):
        main({'messages': []})
