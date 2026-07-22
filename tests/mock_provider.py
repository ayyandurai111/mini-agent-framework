from typing import Generator
from mini_agent.llm.base import BaseLLMProvider


class MockLLMProvider(BaseLLMProvider):
    """Mock LLM provider that returns pre-configured responses. No API key needed."""

    def __init__(self, responses: list = None, model: str = "mock-model"):
        self.responses = responses or []
        self._call_count = 0
        self.system_prompts = []
        self.user_messages = []
        self.model = model
        self.temperature = 0.0
        self.top_p = 0.0
        self.max_tokens = 4096

    def _next_response(self) -> str:
        if self._call_count < len(self.responses):
            resp = self.responses[self._call_count]
        else:
            resp = '{"final_answer": "mock default response"}'
        self._call_count += 1
        return resp

    def generate_stream(self, system_prompt: str, user_message: str) -> Generator[str, None, None]:
        self.system_prompts.append(system_prompt)
        self.user_messages.append(user_message)
        yield self._next_response()

    def generate(self, system_prompt: str, user_message: str) -> str:
        self.system_prompts.append(system_prompt)
        self.user_messages.append(user_message)
        return self._next_response()

    def reset(self):
        self._call_count = 0
        self.system_prompts = []
        self.user_messages = []
