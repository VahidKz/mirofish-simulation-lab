# Modified 2026-10-29 for the independent Simulation Lab edition; see NOTICE and MODIFICATIONS.md.
import json
import os
from pathlib import Path
import pytest

from app.simlab.journeys.models import JourneyConfig, Action
from app.simlab.journeys.policy import (TargetPolicy, SafetyError, validate_target,
    save_bundle, redact, evidence_url, LOCAL_ORIGIN)
from app.simlab.journeys.service import artifact


def registry(monkeypatch,tmp_path,value):
    path=tmp_path/'targets.json'
    path.write_text(json.dumps(value))
    monkeypatch.setenv('SIMLAB_JOURNEY_TARGETS_FILE',str(path))


def test_production_and_unregistered_targets_cannot_be_enabled():
    with pytest.raises(SafetyError):
        TargetPolicy('https://example.test','buyer')
    with pytest.raises(SafetyError):
        validate_target({'kind':'production','origin':'https://production.example.org'})
    with pytest.raises(SafetyError):
        validate_target({'kind':'staging','origin':'https://production.example.org','read_paths':['/'],
            'interactive_authorized':True,'seeded_test_data_only':True,'sandbox_services_confirmed':True})


@pytest.mark.parametrize('url', ['http://localhost:5001/health','https://evil.example',
    'file:///etc/passwd',LOCAL_ORIGIN+'/../.env',LOCAL_ORIGIN+'/buyer.html?token=secret',
    'http://user:password@simlab-journey.test/buyer.html'])
def test_fixture_blocks_external_system_and_credential_requests(url):
    policy=TargetPolicy('sample','buyer')
    with pytest.raises(SafetyError):
        policy.permit(url,'GET')


def test_all_local_write_methods_are_blocked():
    policy=TargetPolicy('sample','buyer')
    for method in ['POST','PUT','PATCH','DELETE']:
        with pytest.raises(SafetyError):
            policy.permit(LOCAL_ORIGIN+'/buyer.html',method)


def test_server_registry_requires_three_explicit_authorizations():
    target={'kind':'staging','origin':'https://staging.example.com','read_paths':['/catalog'],
        'interactive_authorized':True,'seeded_test_data_only':True,'sandbox_services_confirmed':True}
    validate_target(target)
    for flag in ['interactive_authorized','seeded_test_data_only','sandbox_services_confirmed']:
        with pytest.raises(SafetyError):
            validate_target({**target,flag:False})


def test_session_requires_explicit_login_grant_and_private_file(tmp_path):
    path=tmp_path/'seeded-session.json';path.write_text('{"cookies":[],"origins":[]}');path.chmod(0o600)
    target={'kind':'staging','origin':'https://staging.example.com','read_paths':['/catalog'],
        'interactive_authorized':True,'seeded_test_data_only':True,'sandbox_services_confirmed':True,
        'session_file':str(path)}
    with pytest.raises(SafetyError):
        validate_target(target)
    validate_target({**target,'login_authorized':True})
    path.chmod(0o644)
    with pytest.raises(SafetyError):
        validate_target({**target,'login_authorized':True})


def test_lab_origin_cannot_be_registered_as_interactive_target():
    with pytest.raises(SafetyError):
        validate_target({'kind':'local','origin':'http://127.0.0.1:5001','read_paths':['/'],
            'interactive_authorized':True,'seeded_test_data_only':True,'sandbox_services_confirmed':True})


def test_mock_write_has_no_real_forwarding_permission(monkeypatch,tmp_path):
    registry(monkeypatch,tmp_path,{'sandbox':{'kind':'staging','origin':'https://staging.example.com',
        'interactive_authorized':True,'seeded_test_data_only':True,'sandbox_services_confirmed':True,
        'read_paths':['/catalog'],'entries':{'buyer':'/catalog'},'mock_routes':{'POST /sandbox-checkout':{'mock':True}}}})
    policy=TargetPolicy('sandbox','buyer')
    assert policy.permit('https://staging.example.com/sandbox-checkout','POST')=='mock'
    for path in ['/payout','/send-email','/orders','/sandbox-checkout']:
        with pytest.raises(SafetyError):
            policy.permit('https://staging.example.com'+path,'GET')
    with pytest.raises(SafetyError):
        policy.permit('https://staging.example.com/orders','POST')


def test_upload_bundles_are_separate_from_importer_materials():
    value=save_bundle({'index.html':b'<h1>Wireframe</h1>'})
    policy=TargetPolicy(value['id'],'buyer')
    assert policy.target['kind']=='bundle'
    assert policy.files['index.html']==b'<h1>Wireframe</h1>'
    with pytest.raises(SafetyError):
        save_bundle({'../auth.html':b'x'})
    with pytest.raises(SafetyError):
        save_bundle({'.env':b'x'})
    with pytest.raises(SafetyError):
        TargetPolicy(value['id'],'buyer','missing.html')


def test_sensitive_metadata_is_redacted_and_artifacts_cannot_traverse():
    text=redact('password=hidden mail@real.example 1234567890123456 Bearer abc123')
    assert 'hidden' not in text and 'mail@real.example' not in text and '1234567890123456' not in text
    assert 'username' not in evidence_url('https://username:password@evil.example/x?token=secret')
    assert 'password' not in evidence_url('https://username:password@evil.example/x?token=secret')
    assert 'secret' not in evidence_url('https://evil.example/x?token=secret')
    with pytest.raises(ValueError):
        artifact('00000000-0000-0000-0000-000000000000','../../.env')


def test_action_data_and_run_limits_are_validated():
    with pytest.raises(ValueError):
        Action(kind='fill',target='#name',data_key='a-real-password')
    with pytest.raises(ValueError):
        JourneyConfig(max_steps=1000)
    with pytest.raises(ValueError):
        JourneyConfig(persona_count=100)
    with pytest.raises(ValueError):
        JourneyConfig(target_id='sample',storage_state='/private/example/session.json')


def test_personas_match_journey_roles():
    from app.simlab.journeys.templates import roster
    assert all(p['name']!='Private seller' for p in roster(JourneyConfig(template='merchant',persona_count=3)))
    assert all(p['name'].startswith('Private seller') for p in roster(JourneyConfig(template='seller_offer',persona_count=3)))


def test_checkpoint_bindings_are_bounded_and_use_known_ids():
    with pytest.raises(ValueError):
        JourneyConfig(checkpoint_selectors={'invented_backend_success':'h1'})
    with pytest.raises(ValueError):
        JourneyConfig(checkpoint_selectors={'plp':'x'*201})
