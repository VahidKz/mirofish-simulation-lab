# Modified 2026-10-29 for the independent Simulation Lab edition; see NOTICE and MODIFICATIONS.md.
from io import BytesIO
from types import SimpleNamespace
import pytest

from app import create_app
from app.simlab import lab


@pytest.fixture
def client(monkeypatch):
    import app.storage
    monkeypatch.setattr(app.storage, 'Neo4jStorage', lambda: SimpleNamespace())
    return create_app().test_client()


def test_original_and_new_routes_are_registered_and_origin_is_restricted(client):
    assert client.get('/health').status_code == 200
    assert client.get('/api/simlab/templates').json['data']['A']['variants'][0]['commission'] == 5
    assert client.get('/api/graph/project/list').status_code == 200
    assert client.post('/api/simlab/scenarios', json={}, headers={'Origin': 'https://evil.example'}).status_code == 403
    assert client.get('/health', headers={'Host': 'evil.example'}).status_code == 403


def test_scenario_save_reload_and_input_validation(client):
    value = client.post('/api/simlab/scenarios', json={'name': 'Saved scenario', 'template': 'B'})
    assert value.status_code == 201
    assert client.get('/api/simlab/scenarios').json['data'][0]['configuration']['name'] == 'Saved scenario'
    assert client.post('/api/simlab/scenarios', json={'template': 'Unknown'}).status_code == 400
    assert client.get('/api/simlab/runs/not-a-uuid').status_code == 400


def test_upload_path_validation_and_website_auth_gate(client):
    response = client.post('/api/simlab/materials', data={'files': (BytesIO(b'<h1>x</h1>'), '../index.html')})
    assert response.status_code == 400
    assert client.post('/api/simlab/materials', json={'url': 'https://staging.example.com', 'staging': True}).status_code == 400


def test_report_exports_and_comparison_do_not_make_model_calls(client):
    run = lab.save('runs', {'status': 'completed', 'configuration': {'name': 'Test'},
        'events': [], 'variants': [], 'interpretation': None})
    value = client.get(f"/api/simlab/runs/{run['id']}/export?format=markdown")
    assert value.status_code == 200
    assert b'## 10.' in value.data
    assert 'attachment' in value.headers['Content-Disposition']
    assert client.get(f"/api/simlab/runs/{run['id']}/export?format=json").json['id'] == run['id']
    assert client.post('/api/simlab/compare', json={'run_ids': [run['id']]}).json['data'][0]['id'] == run['id']


def test_liveness_checks_other_process_owner(client):
    import os
    run = lab.save('runs', {'status': 'running', 'configuration': {}, 'owner_pid': os.getpid()})
    assert lab.load('runs', run['id'])['status'] == 'running'
    run = lab.save('runs', {'status': 'running', 'configuration': {}, 'owner_pid': 2147483647})
    assert lab.load('runs', run['id'])['status'] == 'interrupted'
