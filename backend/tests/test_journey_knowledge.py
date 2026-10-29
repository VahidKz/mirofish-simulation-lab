# Modified 2026-10-29 for the independent Simulation Lab edition; see NOTICE and MODIFICATIONS.md.
import hashlib
import json

import pytest

from app.simlab.journeys import knowledge
from app.simlab.journeys.models import JourneyConfig, KnowledgeReferences
from app.simlab.journeys.report import markdown


@pytest.fixture
def captured_source(tmp_path, monkeypatch):
    kb = tmp_path/'knowledge-base/simlab'
    kb.mkdir(parents=True)
    (kb/'facts.json').write_text(json.dumps({'facts':[{'id':'GG-001','claim':'A design requirement',
        'evidence_class':'approved_design','evidence':[{'source_id':'local-test','line_start':1,'line_end':1}]}]}))
    (kb/'conflicts.json').write_text(json.dumps({'conflicts':[{'id':'C-001','title':'Two incompatible rules',
        'sources':[{'path_or_url':'a'},{'path_or_url':'b'}],'resolved':False}]}))
    monkeypatch.setattr(knowledge,'ROOT',tmp_path)
    captures=knowledge.data_dir()/'knowledge_base'
    captures.mkdir()
    raw=captures/'test.html'
    raw.write_bytes(b'<h1>Original source</h1>')
    (captures/'local-manifest.json').write_text(json.dumps({'inventory':[{'id':'local-test','path':'wireframe.html',
        'sha256':hashlib.sha256(raw.read_bytes()).hexdigest(),'original_snapshot':'test.html',
        'approval_status':'approved','locally_modified':False}]}))
    return raw


def test_citations_and_both_conflict_sides_survive_report_and_prompt(captured_source):
    refs={'pdp':KnowledgeReferences(source_ids=['local-test'],fact_ids=['GG-001'],conflict_ids=['C-001'])}
    resolved=knowledge.resolve(refs)
    assert resolved['pdp']['conflicts'][0]['sources']==[{'path_or_url':'a'},{'path_or_url':'b'}]
    assert resolved['pdp']['facts'][0]['evidence'][0]['line_start']==1
    context=knowledge.decision_context(resolved)
    assert context['pdp']['conflicts'][0]['resolved'] is False
    assert 'evidence' not in context['pdp']['facts'][0]
    report=markdown({'id':'test','status':'incomplete','configuration':{},'result':{'knowledge':resolved}})
    assert 'GG-001' in report and 'C-001' in report and 'wireframe.html' in report


def test_invalid_refs_and_changed_archives_fail_closed(captured_source):
    for refs in [KnowledgeReferences(source_ids=['../../secret']),KnowledgeReferences(fact_ids=['unknown']),
                 KnowledgeReferences(conflict_ids=['unknown'])]:
        with pytest.raises(ValueError):
            knowledge.resolve({'pdp':refs})
    captured_source.write_bytes(b'changed')
    with pytest.raises(ValueError,match='hash mismatch'):
        knowledge.resolve({'pdp':KnowledgeReferences(source_ids=['local-test'])})
    with pytest.raises(ValueError):
        JourneyConfig(knowledge_references={'invented_stage':{}})


@pytest.mark.browser
def test_runner_attaches_original_source_and_unresolved_context(captured_source, tmp_path):
    from app.simlab.journeys.models import Action
    from app.simlab.journeys.policy import save_bundle, TargetPolicy
    from app.simlab.journeys.runner import run
    bundle=save_bundle({'wireframe.html':captured_source.read_bytes()})
    config=JourneyConfig(target_id=bundle['id'],entry_path='wireframe.html',mode='ai',
        research_objective='Inspect this source only',knowledge_references={'pdp':{
            'source_ids':['local-test'],'fact_ids':['GG-001'],'conflict_ids':['C-001']}})
    def decide(snapshot,*_):
        assert snapshot['knowledge']['pdp']['facts'][0]['claim']=='A design requirement'
        assert snapshot['knowledge']['pdp']['conflicts'][0]['resolved'] is False
        assert snapshot['research_objective']=='Inspect this source only'
        return Action(kind='stop')
    result=run(config,TargetPolicy(bundle['id'],'buyer','wireframe.html'),tmp_path/'evidence',lambda _:None,decide=decide)
    assert result['knowledge']['pdp']['sources'][0]['included_as_exact_bundle_source']
    assert result['personas'][0]['status']=='stopped'


@pytest.mark.browser
def test_unlabelled_prototype_payment_fields_are_blocked(tmp_path):
    from playwright.sync_api import sync_playwright
    from app.simlab.journeys.policy import save_bundle, TargetPolicy, SafetyError
    from app.simlab.journeys.runner import inspect_page, execute_action
    from app.simlab.journeys.models import Action
    bundle=save_bundle({'index.html':b'<div class="card-area"><input id="number" placeholder="1234 5678"></div>'})
    policy=TargetPolicy(bundle['id'],'buyer')
    with sync_playwright() as pw:
        browser=pw.chromium.launch()
        context=browser.new_context(service_workers='block')
        policy.install(context,lambda *_:None)
        page=context.new_page()
        page.goto(policy.entry)
        assert inspect_page(page)['controls'][0]['sensitive']
        with pytest.raises(SafetyError):
            execute_action(page,Action(kind='fill',target='#number',data_key='test_name'),policy,1000)
        browser.close()
