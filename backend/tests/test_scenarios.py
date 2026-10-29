# Modified 2026-10-29 for the independent Simulation Lab edition; see NOTICE and MODIFICATIONS.md.
import pytest
from app.simlab.scenarios import LabConfig, TEMPLATES, estimate, personas, treatments, transaction_rules
from app.simlab.lab import report_markdown


def test_all_required_treatments_and_roles_exist():
    assert [x['commission'] for x in TEMPLATES['A']['variants']] == [5, 10, 15]
    assert len(TEMPLATES['B']['variants']) == 5
    assert len(TEMPLATES['C']['variants']) == 4
    roster = personas(LabConfig(buyer_agents=5, merchant_agents=4, operations_agents=5))
    assert len(roster) == 14
    assert len({p['name'] for p in roster}) == 14
    assert all('hypothetical' in p['assumption'] or 'Invented' in p['assumption'] for p in roster)


def test_small_default_and_estimate_and_treatments():
    config = LabConfig()
    assert estimate(config)['planned_turns'] == 7
    assert len(personas(config)) == 3
    assert treatments(config)[0]['commission'] == 5
    with pytest.raises(ValueError):
        LabConfig(template='D')
    with pytest.raises(ValueError):
        LabConfig(variant_indices=[0, 0])


def test_deterministic_fee_math_is_separate_from_behavior():
    values = transaction_rules(2000, 15)
    assert values['commission_usd'] == 300
    assert values['seller_net_before_other_costs_usd'] == 1700
    assert values['buyer_total_if_buyer_pays_shipping_and_auth_usd'] == 2100
    assert 'No simulated or real purchase' in values['meaning']


def test_report_has_all_sections_and_labels_partial_evidence():
    value = report_markdown({'id': 'test', 'configuration': {}, 'status': 'failed', 'error': 'budget exhausted'})
    for i in range(1, 11):
        assert f'## {i}.' in value
    assert 'Status: failed' in value
    assert 'AI interpretation' in value
    assert 'OASIS records' in value
