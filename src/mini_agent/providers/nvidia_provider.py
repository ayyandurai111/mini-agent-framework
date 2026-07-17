"""
providers/nvidia_provider.py
------------------------------
NVIDIA NIM provider (OpenAI-compatible endpoint).
"""

import os
import time

from openai import APIError, OpenAI, RateLimitError, AuthenticationError, APIConnectionError

from ..llm.base import BaseLLMProvider


ALLOWED_MODELS = [
    "z-ai/glm-5.2",
    "poolside/laguna-xs-2.1",
    "nvidia/nemotron-3-ultra-550b-a55b",
    "stepfun-ai/step-3.7-flash",
    "moonshotai/kimi-k2.6",
    "mistralai/mistral-medium-3.5-128b",
    "deepseek-ai/deepseek-v4-flash",
    "deepseek-ai/deepseek-v4-pro",
]


class NvidiaProviderError(Exception):
    """Base exception for NVIDIA provider errors."""
    pass


class AuthenticationErrorWrapper(NvidiaProviderError):
    """Raised when API key is invalid or missing."""
    pass


class RateLimitErrorWrapper(NvidiaProviderError):
    """Raised when rate limit is exceeded after retries."""
    pass


class ConnectionErrorWrapper(NvidiaProviderError):
    """Raised when connection to NVIDIA API fails."""
    pass


class NvidiaProvider(BaseLLMProvider):
    def __init__(
        self,
        api_key: str = None,
        model: str = "mistralai/mistral-medium-3.5-128b",
        temperature: float = 0.7,
        top_p: float = 0.95,
        max_tokens: int = 4096,
        base_url: str = "https://integrate.api.nvidia.com/v1",
        max_retries: int = 2,
    ):
        # Validate API key
        if api_key is None:
            api_key = os.environ.get("NVIDIA_API_KEY")
        if not api_key or not api_key.startswith("nvapi-"):
            raise AuthenticationErrorWrapper(
                "NVIDIA API key is invalid or missing. "
                "Set NVIDIA_API_KEY environment variable or pass api_key parameter. "
                "Get a key from: https://build.nvidia.com"
            )

        self.client = OpenAI(base_url=base_url, api_key=api_key, timeout=120.0, max_retries=1)

        self.model = model
        if self.model not in ALLOWED_MODELS:
            raise NvidiaProviderError(
                f"Model '{model}' is not allowed. Choose from:\n"
                + "\n".join(f"  - {m}" for m in ALLOWED_MODELS)
            )
        self.temperature = temperature
        self.top_p = top_p
        self.max_tokens = max_tokens
        self.max_retries = max_retries

    def generate(self, system_prompt: str, user_message: str) -> str:
        last_error = None
        for attempt in range(self.max_retries):
            try:
                completion = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message},
                    ],
                    temperature=self.temperature,
                    top_p=self.top_p,
                    max_tokens=self.max_tokens,
                    stream=False,
                )
                return completion.choices[0].message.content
            except AuthenticationError as e:
                raise AuthenticationErrorWrapper(f"API key authentication failed: {e}")
            except RateLimitError as e:
                last_error = e
                wait_time = 2 ** attempt
                if attempt < self.max_retries - 1:
                    time.sleep(wait_time)
            except APIConnectionError as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    time.sleep(1)
            except APIError as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    time.sleep(1)
            except Exception as e:
                raise NvidiaProviderError(f"Unexpected error during generation: {e}")

        # All retries exhausted
        if isinstance(last_error, RateLimitError):
            raise RateLimitErrorWrapper(
                f"NVIDIA API rate limit exceeded after {self.max_retries} attempts. "
                "Wait a moment and try again, or reduce concurrent requests."
            )
        elif isinstance(last_error, APIConnectionError):
            raise ConnectionErrorWrapper(
                f"Connection to NVIDIA API failed after {self.max_retries} attempts. "
                "Check your internet connection."
            )
        else:
            raise NvidiaProviderError(
                f"LLM generation failed after {self.max_retries} attempts: {last_error}"
            )

    def generate_stream(self, system_prompt: str, user_message: str):
        last_error = None
        for attempt in range(self.max_retries):
            try:
                stream = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message},
                    ],
                    temperature=self.temperature,
                    top_p=self.top_p,
                    max_tokens=self.max_tokens,
                    stream=True,
                )
                for chunk in stream:
                    if chunk.choices and len(chunk.choices) > 0:
                        delta = chunk.choices[0].delta
                        if delta and delta.content:
                            yield delta.content
                return
            except AuthenticationError as e:
                raise AuthenticationErrorWrapper(f"API key authentication failed: {e}")
            except RateLimitError as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)
            except (APIConnectionError, APIError) as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    time.sleep(1)
            except Exception as e:
                raise NvidiaProviderError(f"Unexpected error during streaming: {e}")

        if isinstance(last_error, RateLimitError):
            raise RateLimitErrorWrapper(
                f"NVIDIA API rate limit exceeded after {self.max_retries} attempts. "
                "Wait a moment and try again."
            )
        elif isinstance(last_error, APIConnectionError):
            raise ConnectionErrorWrapper(
                f"Connection to NVIDIA API failed after {self.max_retries} attempts. "
                "Check your internet connection."
            )
        else:
            raise NvidiaProviderError(
                f"LLM streaming failed after {self.max_retries} attempts: {last_error}"
            )
