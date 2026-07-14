"""
llm/base.py
------------
Abstract base class for LLM providers. All providers must implement generate().
"""

from abc import ABC, abstractmethod


class BaseLLMProvider(ABC):
    """
    Any LLM provider must inherit this class and implement generate().
    """

    @abstractmethod
    def generate(self, system_prompt: str, user_message: str) -> str:
        """
        system_prompt : role & instructions for the caller (orchestrator/agent)
        user_message  : the task/question being asked
        return        : the LLM's reply as plain text
        """
        raise NotImplementedError
