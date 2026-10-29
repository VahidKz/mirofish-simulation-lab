# Modified 2026-10-29 for the independent Simulation Lab edition; see NOTICE and MODIFICATIONS.md.
"""Shared guarded Codex / local Ollama interface for original MiroFish services."""
import json
import re
from ..simlab.provider import ModelProvider

class LLMClient:
    def __init__(self, api_key=None, base_url=None, model=None, timeout=180.0):
        if base_url:
            from ..simlab.provider import local_url
            local_url(base_url)
        self.provider = ModelProvider()

    def chat(self, messages, temperature=0.7, max_tokens=4096, response_format=None):
        content = self.provider.complete(messages, temperature=temperature,
            max_tokens=max_tokens, json_mode=bool(response_format))['content']
        return re.sub(r'<think>[\s\S]*?</think>', '', content).strip()

    def chat_json(self, messages, temperature=0.3, max_tokens=4096):
        content = self.chat(messages, temperature, max_tokens, {'type': 'json_object'})
        content = re.sub(r'^```(?:json)?\s*|\s*```$', '', content.strip())
        result = json.loads(content)
        if not isinstance(result, dict):
            raise ValueError('Model must return a JSON object')
        return result
