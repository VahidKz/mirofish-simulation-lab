# Modified 2026-10-29 for the independent Simulation Lab edition; see NOTICE and MODIFICATIONS.md.
import asyncio
import hashlib
import json

import pytest

from app.simlab import case_review, lab
from app.simlab.scenarios import LabConfig, estimate, personas, treatments


@pytest.fixture
def definition(tmp_path,monkeypatch):
    root=tmp_path/'evidence';root.mkdir()
    raw=b'Fictional widget design, not a real service.';(root/'source.md').write_bytes(raw)
    case={'title':'Fictional widget review','evidence_root':str(root),
      'phases':[{'id':f'phase-{i}','label':f'Phase {i}','question':'Review the supplied fictional evidence only.','facts':['RULE-001']} for i in range(5)],
      'personas':[{'id':i,'role':role,'name':role.title(),'goal':'Review a hypothetical widget process',
          'concerns':'Unknown requirements','behavior':'Ask questions, never claim executed transactions'}
          for i,role in enumerate(['customer','specialist','supplier','reviewer'])],
      'sources':[{'id':'local-fixture','path':'source.md','original_snapshot':'source.md',
          'sha256':hashlib.sha256(raw).hexdigest(),'approval_status':'unreviewed'}],
      'facts':[{'id':'RULE-001','claim':'The widget procedure is unspecified.','evidence':[{
          'source_id':'local-fixture','line_start':1,'line_end':1}]}],
      'conflicts':[{'id':'OPEN-001','title':'Unspecified procedure','handling':'Do not infer a service','resolved':False}]}
    path=tmp_path/'case.json';path.write_text(json.dumps(case))
    monkeypatch.setenv('SIMLAB_CASE_FILE',str(path))
    return path,root,case


def test_case_is_explicit_and_fails_before_spending(monkeypatch):
    monkeypatch.delenv('SIMLAB_CASE_FILE',raising=False)
    assert not case_review.available()
    with pytest.raises(ValueError,match='Private case unavailable'):
        lab.start({'template':'CASE','maximum_calls':24},object())
    assert lab.list_items('runs')==[]


def test_private_case_is_bounded_and_hash_checked(definition):
    path,root,case=definition
    assert case_review.available()
    assert len(personas(LabConfig(template='CASE')))==4
    assert estimate(LabConfig(template='CASE'))['planned_turns']==24
    assert case_review.evidence_packet()['conflicts'][0]['resolved'] is False
    (root/'source.md').write_bytes(b'Changed')
    with pytest.raises(ValueError,match='hash mismatch'):case_review.evidence_packet()


def test_source_escape_and_unknown_fact_fail_closed(definition):
    path,root,case=definition
    case['sources'][0]['original_snapshot']='../outside.md';path.write_text(json.dumps(case))
    with pytest.raises(ValueError,match='within the private evidence root'):case_review.evidence_packet()
    case['phases'][0]['facts']=['MISSING'];path.write_text(json.dumps(case))
    with pytest.raises(ValueError,match='unknown fact'):case_review.evidence_packet()


def test_private_case_uses_real_oasis_with_model_doubles(definition,monkeypatch):
    from app.simlab.provider import ModelProvider
    import re
    calls=[]
    def complete(self,messages,**_):
        context='\n'.join(m.get('content') or '' for m in messages)
        post_id=int(re.findall(r'"reply_to_post_id": (\d+)',context)[-1])
        calls.insert(0,{'id':len(calls)+1,'status':'completed'})
        # Explicitly exercise no-comment records as well as phase replies.
        quiet=post_id==5 and len(calls) in {18,19}
        return {'content':json.dumps({'kind':'action','name':'do_nothing' if quiet else 'create_comment',
            'arguments_json':json.dumps({} if quiet else {'post_id':post_id,'content':'Intent: request_clarification. RULE-001 is unresolved.'}),
            'content':''})}
    monkeypatch.setattr(ModelProvider,'complete',complete)
    monkeypatch.setattr('app.simlab.provider.usage',lambda *_:{'calls':list(calls)})
    c=LabConfig(template='CASE');roster=personas(c)
    for p in roster:p.update(bio=p['assumption'],persona=p['behavior'])
    result=asyncio.run(lab.social_run('private-fixture',treatments(c)[0],roster,'RULE-001 is fictional.'))
    assert len(calls)==20
    assert len([e for e in result['events'] if e['kind']=='post'])==5
    assert len([e for e in result['events'] if e['kind']=='comment'])==18
    assert all(s['status']=='reviewed' and len(s['agent_turns'])==4 for s in result['phase_coverage'])
    assert result['fee_illustration'] is None
