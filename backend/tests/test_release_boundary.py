# Modified 2026-10-29 for the independent Simulation Lab edition; see NOTICE and MODIFICATIONS.md.
import importlib.util
from pathlib import Path

import pytest


def guard():
    path = Path(__file__).resolve().parents[2] / 'scripts/check-public-release.py'
    spec = importlib.util.spec_from_file_location('release_guard', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_only_reviewed_environment_examples_are_publishable():
    release = guard()
    assert not release.forbidden_path('.env.example')
    assert not release.forbidden_path('.env.simlab.example')
    for name in ['.env', '.env.production', 'backend/.env', 'private/case.json',
                 'backend/uploads/run.json', 'credentials/auth.json',
                 '.run/browser/session.json', 'session.json', 'assets/private.key',
                 'knowledge-base/product/facts.json', 'state.sqlite3']:
        assert release.forbidden_path(name), name


def test_release_checks_redact_credential_values():
    release = guard()
    secret = 'ghp_' + 'X' * 40
    failures = list(release.violations(('key=' + secret).encode()))
    assert failures == [('credential-like token', 1)]
    assert secret not in repr(failures)
    assert not list(release.violations(b'LLM_API_KEY=ollama\nNEO4J_PASSWORD=replace-with-local-password'))


def test_operator_supplied_names_are_blocked_without_bundling_names():
    release = guard()
    name = 'Example Private Client'
    assert list(release.violations(('prefix ' + name.upper()).encode(), [name])) == [
        ('excluded customer reference', 1)]
    assert name not in repr(list(release.violations(name.encode(), [name])))


def test_tracked_environment_file_is_rejected_even_if_ignored(tmp_path, monkeypatch, capsys):
    release = guard()
    (tmp_path/'LICENSE').write_bytes((release.ROOT/'LICENSE').read_bytes())
    secret = 'ghp_' + 'X' * 40
    (tmp_path/'.env').write_text('TOKEN=' + secret)
    names = ['.env', 'LICENSE', 'NOTICE', 'MODIFICATIONS.md', 'README.md',
             'THIRD_PARTY_NOTICES.md', 'PUBLIC_RELEASE.md']
    monkeypatch.setattr(release, 'ROOT', tmp_path)
    monkeypatch.setattr(release.subprocess, 'check_output', lambda *_a, **_k: '\0'.join(names).encode())
    monkeypatch.setattr('sys.argv', ['check-public-release.py'])
    with pytest.raises(SystemExit):
        release.main()
    output = capsys.readouterr().out
    assert 'excluded path: .env' in output
    assert secret not in output
