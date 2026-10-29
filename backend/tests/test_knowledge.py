# Modified 2026-10-29 for the independent Simulation Lab edition; see NOTICE and MODIFICATIONS.md.
import hashlib
import json
from pathlib import Path
import subprocess
from types import SimpleNamespace

import pytest
from app import create_app
from app.simlab import knowledge
from app.simlab.knowledge_collection import public_document


def seed_source(source_id,text,category='selected_canonical',approval='pending'):
    folder=knowledge.kb_dir()/'sources';folder.mkdir(exist_ok=True)
    (folder/(source_id+'.json')).write_text(json.dumps({'id':source_id,'title':'Test source','path':source_id+'.html',
        'category':category,'approval_status':approval,'sha256':'test','text':text,'blocks':[],
        'source_kind':'user_supplied_design_repository'}))


def test_extract_preserves_line_evidence_and_distinguishes_static_controls_from_scripts():
    html='''<html><head><title>Test</title><style>secret-style</style></head>
<body><h1>Deposit route</h1>
<button id="next">Next</button><input type="password" value="do-not-store">
<script>fetch('never-execute');</script><div hidden>Draft hidden rule</div></body></html>'''
    doc=knowledge.extract_html(html)
    assert 'Draft hidden rule' in doc['text']
    assert 'never-execute' not in doc['text'] and 'secret-style' not in doc['text']
    assert 'do-not-store' not in json.dumps(doc)
    assert doc['controls'][0]['selector']=='#next'
    assert any(b['html_line']==2 and 'Deposit route' in b['text'] for b in doc['blocks'])


def test_search_excludes_old_catalog_versions_unless_requested():
    seed_source('local-current','deposit policy current','selected_canonical','approved')
    seed_source('local-old','deposit policy old','catalog_history')
    seed_source('local-draft','deposit policy unselected','unselected_or_draft')
    knowledge.rebuild_index()
    found=knowledge.search('deposit')
    assert {r['id'] for r in found}=={'local-current'}
    assert found[0]['approval']=='approved'
    assert 'L1' in found[0]['excerpt']
    assert {r['id'] for r in knowledge.search('deposit',include_history=True)}=={'local-current','local-old','local-draft'}
    assert knowledge.search('"; DROP TABLE documents; --')==[]
    assert knowledge.search('deposit')[0]['id']=='local-current'


def test_collect_user_repo_is_read_only_and_does_not_promote_newer_filename(tmp_path):
    root=tmp_path/'design';root.mkdir();(root/'wireframes').mkdir()
    (root/'wireframes/design_v1.0.0.html').write_text('<h1>Selected</h1>')
    (root/'wireframes/design_v2.0.0.html').write_text('<h1>Newer unapproved</h1>')
    (root/'wireframes/design_v0.9.0.html').write_text('<h1>Old</h1>')
    (root/'index.html').write_text('<a href="./wireframes/design_v1.0.0.html">current</a><a href="./wireframes/design_v0.9.0.html">old</a>')
    (root/'artifact-metadata.json').write_text(json.dumps({'artifacts':[{'id':'design','canonicalHtml':'wireframes/design_v1.0.0.html','approval':{'status':'pending'}}]}))
    for name in ['README.md','AGENTS.md','PRODUCT_DEVELOPMENT_ARTIFACTS.md']:(root/name).write_text('Test source governance')
    subprocess.run(['git','init','-q',str(root)],check=True)
    subprocess.run(['git','-C',str(root),'add','.'],check=True)
    subprocess.run(['git','-C',str(root),'-c','user.name=Fixture','-c','user.email=fixture@example.test','commit','-qm','test fixture'],check=True)
    before={str(p.relative_to(root)):p.read_bytes() for p in root.rglob('*') if p.is_file() and '.git' not in p.parts}
    result=knowledge.collect_local(root)
    after={str(p.relative_to(root)):p.read_bytes() for p in root.rglob('*') if p.is_file() and '.git' not in p.parts}
    assert before==after
    rows={r['path']:r for r in result['inventory']}
    assert rows['wireframes/design_v1.0.0.html']['category']=='selected_canonical'
    assert rows['wireframes/design_v1.0.0.html']['approval_status']=='pending'
    assert rows['wireframes/design_v2.0.0.html']['category']=='unselected_or_draft'
    assert rows['wireframes/design_v0.9.0.html']['category']=='catalog_history'
    assert result['source_repository_changed'] is False


@pytest.mark.parametrize('url',['https://public.example.test/en/checkout','https://public.example.test/en/shopping-cart',
    'https://public.example.test/en/login','https://public.example.test/en/my-listings','https://public.example.test/en/sell/confirm',
    'https://public.example.test/en/shop?token=x','https://evil.example/en/','file:///etc/passwd'])
def test_production_knowledge_collection_rejects_private_or_action_documents(url,monkeypatch):
    monkeypatch.setattr('app.simlab.knowledge_collection.HOST','public.example.test')
    assert not public_document(url)


def test_public_capture_does_not_grant_interactive_permission(monkeypatch):
    monkeypatch.setattr('app.simlab.knowledge_collection.HOST','public.example.test')
    assert public_document('https://public.example.test/en/page/buyers-protection')
    from app.simlab.journeys.policy import TargetPolicy,SafetyError
    with pytest.raises(SafetyError):TargetPolicy('https://public.example.test/en/','buyer')


def test_source_and_summary_paths_are_not_arbitrary_filesystem_reads():
    with pytest.raises(ValueError):knowledge.source('../../.env')
    with pytest.raises(ValueError):knowledge.document('../../.env')
    with pytest.raises(FileNotFoundError):knowledge.source('local-missing')


@pytest.fixture
def client(monkeypatch):
    import app.storage
    monkeypatch.setattr(app.storage,'Neo4jStorage',lambda:SimpleNamespace())
    return create_app().test_client()


def test_knowledge_endpoints_return_evidence_without_inference(client,monkeypatch):
    from app.simlab.provider import ModelProvider
    monkeypatch.setattr(ModelProvider,'complete',lambda *_a,**_kw:pytest.fail('Knowledge lookup must not call inference'))
    seed_source('local-policy','deposit authentication is pending','selected_canonical','pending')
    knowledge.rebuild_index()
    response=client.get('/api/simlab/knowledge/search?q=deposit')
    assert response.status_code==200 and response.json['data'][0]['approval']=='pending'
    assert client.get('/api/simlab/knowledge/sources/local-policy').json['data']['text']=='deposit authentication is pending'
    assert client.get('/api/simlab/knowledge').json['data']['production_interactive_authorized'] is False
    assert client.get('/api/simlab/knowledge/documents/buyer').status_code==200
    item=client.post('/api/simlab/knowledge/materials/buyer',json={})
    assert item.status_code==201 and item.json['data']['assumptions']==[]
    assert 'provenance' in item.json['data']['observations'][0]
    assert client.get('/api/simlab/runs').json['data']==[]


def test_no_private_ledger_or_conflicts_are_distributed():
    assert knowledge.facts()=={'facts':[]}
    assert knowledge.conflicts()=={'conflicts':[]}
    assert knowledge.overview()['local_documents']==0
