# Modified 2026-10-29 for the independent Simulation Lab edition; see NOTICE and MODIFICATIONS.md.
"""Native CAMEL model backend, not an HTTP/OAuth proxy.

Codex returns structured action selections. We validate names and arguments
against CAMEL's provided function schemas, then construct its in-memory
ChatCompletion type. Only OASIS executes those functions in its local SQLite
world. No SDK tools or network-facing action tools are supplied to Codex.
"""
import asyncio
import json
import time
import uuid

from camel.models import BaseModelBackend
from camel.types import ModelType
from camel.utils import BaseTokenCounter
from openai.types.chat import ChatCompletion

from .provider import ModelProvider, ProviderError


class LocalTokenCounter(BaseTokenCounter):
    def encode(self, text):
        return list(text.encode('utf-8'))

    def decode(self, token_ids):
        return bytes(token_ids).decode('utf-8', 'replace')

    def count_tokens_from_messages(self, messages):
        # Conservative context estimate only; never presented as billed usage.
        return len(json.dumps(messages, ensure_ascii=False)) // 3 + 1


ACTION_SCHEMA = {
    'type': 'object', 'additionalProperties': False,
    'properties': {'kind': {'type': 'string', 'enum': ['action', 'final']},
                   'name': {'type': 'string'}, 'arguments_json': {'type': 'string'},
                   'content': {'type': 'string'}},
    'required': ['kind', 'name', 'arguments_json', 'content'],
}


class SubscriptionModel(BaseModelBackend):
    def __init__(self, provider=None):
        # CAMEL requires a known enum to select its message formatting rules.
        # This enum never selects the inference model or an OpenAI API endpoint.
        super().__init__(ModelType.GPT_4O_MINI, {'temperature': 0.3}, max_retries=0)
        self.provider = provider or ModelProvider()
        self._counter = LocalTokenCounter()

    @property
    def token_counter(self):
        return self._counter

    @property
    def token_limit(self):
        return 32000

    def _run(self, messages, response_format=None, tools=None):
        tools = tools or self.model_config_dict.get('tools') or []
        # CAMEL requests a final assistant response after executing a function.
        # A deterministic acknowledgement avoids an unnecessary second turn.
        if messages and messages[-1].get('role') == 'tool':
            return self._completion({'role': 'assistant', 'content': 'Simulation tool result received.'})
        if tools:
            prompt = [{'role': 'system', 'content':
                'Choose at most ONE action in this local synthetic social environment. '
                'Select kind=action, the exact function name, and a JSON-encoded arguments object. '
                'Do not invoke real tools. The adapter will validate the selection. '
                'Choose kind=final and empty name/arguments_json if no action is needed. '
                'Available simulation functions: ' + json.dumps(tools)}] + list(messages)
            result = self.provider.complete(prompt, schema=ACTION_SCHEMA)
            chosen = json.loads(result['content'])
            if chosen['kind'] == 'action':
                allowed = {x['function']['name']: x['function'] for x in tools}
                if chosen['name'] not in allowed:
                    raise ProviderError('Model selected an unavailable OASIS action.')
                from jsonschema import validate
                args = json.loads(chosen['arguments_json'])
                validate(args, allowed[chosen['name']].get('parameters', {'type': 'object'}))
                message = {'role': 'assistant', 'content': chosen['content'] or None,
                    'tool_calls': [{'id': 'call_' + uuid.uuid4().hex, 'type': 'function',
                                    'function': {'name': chosen['name'], 'arguments': json.dumps(args)}}]}
                return self._completion(message, 'tool_calls')
            return self._completion({'role': 'assistant', 'content': chosen['content']})
        schema = response_format.model_json_schema() if response_format else None
        result = self.provider.complete(messages, schema=schema)
        return self._completion({'role': 'assistant', 'content': result['content']})

    async def _arun(self, messages, response_format=None, tools=None):
        return await asyncio.to_thread(self._run, messages, response_format, tools)

    def _completion(self, message, finish='stop'):
        return ChatCompletion(id='simlab_' + uuid.uuid4().hex, created=int(time.time()),
            model=self.provider.model or 'codex-configured-default', object='chat.completion',
            choices=[{'index': 0, 'message': message, 'finish_reason': finish}])


def create_simulation_model():
    return SubscriptionModel()
