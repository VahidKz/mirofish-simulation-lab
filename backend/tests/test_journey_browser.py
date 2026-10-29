# Modified 2026-10-29 for the independent Simulation Lab edition; see NOTICE and MODIFICATIONS.md.
import json
import zipfile
import pytest

from app.simlab.journeys.runner import run, inspect_page, execute_action, choose_action
from app.simlab.journeys.models import JourneyConfig, Action
from app.simlab.journeys.policy import TargetPolicy, save_bundle, SafetyError
from app.simlab.provider import ModelProvider, BudgetExceeded


@pytest.mark.browser
@pytest.mark.parametrize('template,actions',[('buyer',10),('seller_offer',6),('merchant',8)])
def test_scripted_journeys_have_real_screenshots_traces_and_checkpoints(tmp_path,template,actions,monkeypatch):
    monkeypatch.setattr(ModelProvider,'complete',lambda *_a,**_kw:pytest.fail('Scripted mode must not use inference'))
    events=[]
    value=run(JourneyConfig(template=template),TargetPolicy('sample',template),tmp_path,events.append)
    assert value['status']=='completed'
    persona=value['personas'][0]
    assert persona['actions']==actions
    assert all(c['status']=='observed' and c['evidence'] for c in persona['checkpoints'].values())
    assert not value['browser_failures']
    assert (tmp_path/'persona-0-step-00.png').read_bytes().startswith(b'\x89PNG')
    assert zipfile.is_zipfile(tmp_path/'persona-0-trace.zip')
    assert not any(e['kind']=='blocked_request' for e in events)
    assert any(e['kind']=='navigation' and e.get('route') for e in events)


@pytest.mark.browser
def test_personas_have_separate_browser_storage(tmp_path):
    # A page writes localStorage then increments it on every fresh page load.
    # Each new persona should observe only its own initial value.
    target=save_bundle({'index.html':b'<h1 data-journey-checkpoint="plp">Product list</h1><script>let n=+(localStorage.getItem("n")||0)+1;localStorage.setItem("n",n);document.querySelector("h1").textContent="Isolated visit "+n;</script>'})
    observations=[]
    def stop(snapshot,*_):
        observations.append(snapshot['headings'])
        return Action(kind='stop')
    value=run(JourneyConfig(target_id=target['id'],mode='ai',persona_count=2),TargetPolicy(target['id'],'buyer'),tmp_path,lambda _:None,decide=stop)
    assert observations==[['Isolated visit 1'],['Isolated visit 1']]
    assert len(value['personas'])==2
    assert not list(tmp_path.glob('*.zip'))  # Untrusted uploads never get raw traces.


@pytest.mark.browser
def test_inert_original_wireframe_is_not_claimed_as_working_journey(tmp_path):
    target=save_bundle({'index.html':b'<h1>Original wireframe</h1><button>Add to cart</button>'})
    value=run(JourneyConfig(target_id=target['id'],script=[Action(kind='click',target='#nonexistent')]),
        TargetPolicy(target['id'],'buyer'),tmp_path,lambda _:None)
    assert value['status']=='incomplete'
    assert value['browser_failures'][0]['category']=='LookupError'
    assert all(c['status']=='unsupported_or_not_reached' for c in value['personas'][0]['checkpoints'].values())
    assert value['ux_hypotheses'] and 'not proof' in value['ux_hypotheses'][0]['basis']


@pytest.mark.browser
def test_validation_errors_are_observed_without_false_completion(tmp_path):
    config=JourneyConfig(script=[Action(kind='click',target='#product'),Action(kind='click',target='#add-cart'),
        Action(kind='click',target='#checkout'),Action(kind='click',target='#complete')])
    value=run(config,TargetPolicy('sample','buyer'),tmp_path,lambda _:None)
    assert value['status']=='incomplete'
    assert value['personas'][0]['validation_errors']
    assert value['personas'][0]['checkpoints']['test_checkout']['status']!='observed'


@pytest.mark.browser
def test_step_limit_and_budget_failure_stop_the_loop(tmp_path):
    one=run(JourneyConfig(max_steps=1),TargetPolicy('sample','buyer'),tmp_path/'step',lambda _:None)
    assert one['personas'][0]['status']=='step_limit'
    def exhausted(*_):
        raise BudgetExceeded('Test cap')
    two=run(JourneyConfig(mode='ai'),TargetPolicy('sample','buyer'),tmp_path/'cap',lambda _:None,decide=exhausted)
    assert two['personas'][0]['status']=='budget_exhausted'
    assert two['personas'][0]['actions']==0


@pytest.mark.browser
def test_untrusted_script_cannot_reach_lab_or_send_writes(tmp_path):
    target=save_bundle({'index.html':b'''<h1>Test page</h1><script>
      fetch('http://127.0.0.1:5001/health');fetch('/index.html',{method:'POST'});
      const ws=new WebSocket('ws://127.0.0.1:5001');
      </script>'''})
    events=[]
    result=run(JourneyConfig(target_id=target['id'],mode='ai'),TargetPolicy(target['id'],'buyer'),tmp_path,events.append,decide=lambda *_:Action(kind='stop'))
    assert any(e['kind']=='blocked_request' for e in events)
    assert not any(e['kind']=='request' and e.get('handling')=='read' for e in events)


def test_ai_prompt_is_bounded_structured_and_uses_shared_provider(monkeypatch):
    calls=[]
    def complete(self,messages,**kwargs):
        calls.append((messages,kwargs))
        return {'content':json.dumps({'kind':'stop','target':'','data_key':'','summary':'No safe next step.'})}
    monkeypatch.setattr(ModelProvider,'complete',complete)
    decision=choose_action({'headings':['Test'],'controls':[]},{'name':'Synthetic buyer'},{},12345)
    assert decision.kind=='stop'
    assert calls[0][1]['deadline']==12345
    assert calls[0][1]['cache'] is False
    assert 'untrusted' in calls[0][0][0]['content']


@pytest.mark.browser
def test_real_local_read_is_allowed_but_writes_are_mocked_without_forwarding(tmp_path,monkeypatch):
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    import threading
    hits=[]
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*_):
            pass
        def do_GET(self):
            hits.append(('GET',self.path))
            body=b'''<h1>Seeded local test app</h1><script>
              fetch('/sandbox-checkout',{method:'POST'});
              fetch('/send-email',{method:'POST'});
              fetch('/not-allowlisted');
              </script>'''
            self.send_response(200);self.send_header('Content-Type','text/html');self.end_headers();self.wfile.write(body)
        def do_POST(self):
            hits.append(('POST',self.path))
            self.send_response(500);self.end_headers()
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    origin=f'http://127.0.0.1:{server.server_port}'
    path=tmp_path/'registry.json'
    path.write_text(json.dumps({'seeded':{'kind':'local','origin':origin,'read_paths':['/index.html'],
        'interactive_authorized':True,'seeded_test_data_only':True,'sandbox_services_confirmed':True,
        'entries':{'buyer':'/index.html'},'mock_routes':{'POST /sandbox-checkout':{'mock':True}}}}))
    monkeypatch.setenv('SIMLAB_JOURNEY_TARGETS_FILE',str(path))
    events=[]
    try:
        value=run(JourneyConfig(target_id='seeded',mode='ai'),TargetPolicy('seeded','buyer'),tmp_path/'evidence',events.append,decide=lambda *_:Action(kind='stop'))
    finally:
        server.shutdown();server.server_close()
    assert hits==[('GET','/index.html')]
    assert any(e['kind']=='request' and e.get('handling')=='mock' for e in events)
    assert sum(e['kind']=='blocked_request' for e in events)>=2
    assert not list((tmp_path/'evidence').glob('*.zip'))


@pytest.mark.browser
def test_back_and_sensitive_field_protection(tmp_path):
    result=run(JourneyConfig(script=[Action(kind='navigate',target='#product'),Action(kind='back')]),
        TargetPolicy('sample','buyer'),tmp_path/'back',lambda _:None)
    assert result['personas'][0]['actions']==2
    assert result['personas'][0]['checkpoints']['pdp']['status']=='observed'
    target=save_bundle({'index.html':b'<h1>password=DO_NOT_SHARE</h1><input id="password" type="password" value="DO_NOT_SHARE">'})
    events=[]
    result=run(JourneyConfig(target_id=target['id'],script=[Action(kind='fill',target='#password',data_key='test_name')]),
        TargetPolicy(target['id'],'buyer'),tmp_path/'sensitive',events.append)
    assert result['personas'][0]['status']=='blocked'
    assert 'DO_NOT_SHARE' not in json.dumps(events)
    assert not list((tmp_path/'sensitive').glob('*.zip'))


@pytest.mark.browser
def test_custom_checkpoint_binding_observes_only_present_pages(tmp_path):
    target=save_bundle({'index.html':b'<h1 id="catalog">Catalog</h1><a id="open" href="product.html">View product</a>',
                        'product.html':b'<h1 id="detail">Test ring</h1>'})
    config=JourneyConfig(target_id=target['id'],checkpoint_selectors={'plp':'#catalog','pdp':'#detail'},
        script=[Action(kind='navigate',target='#open'),Action(kind='stop')])
    result=run(config,TargetPolicy(target['id'],'buyer'),tmp_path,lambda _:None)
    checkpoints=result['personas'][0]['checkpoints']
    assert checkpoints['plp']['status']=='observed' and checkpoints['plp']['criterion']=='#catalog'
    assert checkpoints['pdp']['status']=='observed' and checkpoints['pdp']['criterion']=='#detail'
    assert checkpoints['test_checkout']['status']=='unsupported_or_not_reached'
    assert result['status']=='incomplete'
