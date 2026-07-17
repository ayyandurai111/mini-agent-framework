"""
llm/base.py
-----------
Abstract base class for LLM providers. All providers must implement generate_stream().
"""

from abc import ABC, abstractmethod


class BaseLLMProvider(ABC):
    """
    Any LLM provider must inherit this class and implement generate_stream().
    generate() is a convenience wrapper that accumulates stream tokens.
    """

    def generate(self, system_prompt: str, user_message: str) -> str:
        """
        Accumulates tokens from generate_stream() and returns full response.
        """
        return "".join(self.generate_stream(system_prompt, user_message))

    @abstractmethod
    def generate_stream(self, system_prompt: str, user_message: str):
        """
        Generator that yields response tokens incrementally.
        Subclasses must implement this with stream=True.
        """
        if False:
            yield
        raise NotImplementedError
