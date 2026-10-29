# Modified 2026-10-29 for the independent Simulation Lab edition; see NOTICE and MODIFICATIONS.md.
from io import BytesIO
from types import SimpleNamespace
import pytest
from app import create_app


@pytest.fixture
def client(monkeypatch):
    import app.storage
    monkeypatch.setattr(app.storage,'Neo4jStorage',lambda:SimpleNamespace())
    return create_app().test_client()


def test_journey_templates_do_not_change_existing_lab_routes(client):
    result=client.get('/api/simlab/journeys/templates').json
    assert set(result['data'])=={'buyer','seller_offer','merchant'}
    assert result['targets'][0]['id']=='sample'
    assert client.get('/api/simlab/templates').status_code==200
    assert client.get('/api/simlab/runs').status_code==200


def test_no_api_can_authorize_an_arbitrary_production_url(client):
    response=client.post('/api/simlab/journeys/runs',json={'target_id':'https://example.test','mode':'ai'})
    assert response.status_code==400
    response=client.post('/api/simlab/journeys/runs',json={'target_id':'sample','origin':'https://example.test','authorized':True})
    assert response.status_code==400


def test_journey_bundle_upload_does_not_modify_read_only_materials(client):
    response=client.post('/api/simlab/journeys/bundles',data={'files':(BytesIO(b'<h1>Sample</h1>'),'index.html')})
    assert response.status_code==201
    assert client.get('/api/simlab/materials').json['data']==[]
    assert client.get('/api/simlab/journeys/runs/not-a-uuid').status_code==400


def test_custom_script_is_required_instead_of_inventing_controls(client):
    target=client.post('/api/simlab/journeys/bundles',data={'files':(BytesIO(b'<h1>Sample</h1>'),'index.html')}).json['data']
    response=client.post('/api/simlab/journeys/runs',json={'target_id':target['id'],'mode':'scripted'})
    assert response.status_code==400
    assert 'explicit script' in response.json['error']
