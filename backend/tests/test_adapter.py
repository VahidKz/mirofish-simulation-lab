# Modified 2026-10-29 for the independent Simulation Lab edition; see NOTICE and MODIFICATIONS.md.
import json
import pytest
from app.simlab.camel_adapter import SubscriptionModel
from app.simlab.provider import ProviderError

TOOLS = [{'type': 'function', 'function': {'name': 'create_post', 'parameters': {
    'type': 'object', 'properties': {'content': {'type': 'string'}}, 'required': ['content'], 'additionalProperties': False}}}]


class FakeProvider:
    model = 'fake-test'
    def __init__(self, chosen):
        self.chosen = chosen
    def complete(self, *_, **kwargs):
        return {'content': json.dumps(self.chosen)}


def test_native_action_translation_and_deterministic_tool_acknowledgement():
    adapter = SubscriptionModel(FakeProvider({'kind': 'action', 'name': 'create_post',
        'arguments_json': '{"content":"Please explain the fee"}', 'content': ''}))
    value = adapter.run([{'role': 'user', 'content': 'Discuss'}], tools=TOOLS)
    call = value.choices[0].message.tool_calls[0]
    assert value.choices[0].finish_reason == 'tool_calls'
    assert call.function.name == 'create_post'
    assert json.loads(call.function.arguments)['content'] == 'Please explain the fee'
    final = adapter.run([{'role': 'tool', 'content': 'done', 'tool_call_id': call.id}], tools=TOOLS)
    assert final.choices[0].finish_reason == 'stop'


def test_unknown_action_is_never_executed():
    adapter = SubscriptionModel(FakeProvider({'kind': 'action', 'name': 'purchase_real_item',
        'arguments_json': '{}', 'content': ''}))
    with pytest.raises(ProviderError):
        adapter.run([], tools=TOOLS)


def test_action_arguments_are_validated():
    adapter = SubscriptionModel(FakeProvider({'kind': 'action', 'name': 'create_post',
        'arguments_json': '{"content":123}', 'content': ''}))
    from jsonschema import ValidationError
    with pytest.raises(ValidationError):
        adapter.run([], tools=TOOLS)
