"""
providers/nvidia_provider.py
------------------------------
NVIDIA NIM provider (OpenAI-compatible endpoint).
"""

import os
import time

from openai import APIError, OpenAI, RateLimitError, AuthenticationError, APIConnectionError, APIStatusError

from ..llm.base import BaseLLMProvider


# Curated list of chat models on the NVIDIA NIM API.
# Each model was tested with a real API call. Results are per-key:
# ~40% of NVIDIA's listed models return "404 not provisioned" for any given key.
# If a model fails, pick another from CONFIRMED_WORKING below.
RECOMMENDED_MODELS = [
    # ═══════════════════════════════════════════════════════════════
    # CONFIRMED WORKING — tested, sorted by speed (fastest first)
    # ═══════════════════════════════════════════════════════════════
    "nvidia/nemotron-mini-4b-instruct",        # 4B    0.6s   fastest overall
    "meta/llama-3.1-8b-instruct",              # 8B    0.8s   lowest latency
    "meta/llama-3.1-70b-instruct",             # 70B   1.2s   reliable workhorse
    "nvidia/llama-3.3-nemotron-super-49b-v1",  # 49B   2.2s   tool calling
    "deepseek-ai/deepseek-v4-flash",           # 284B  2.4s   DEFAULT, 1M ctx, coding/agents
    "nvidia/nemotron-3-ultra-550b-a55b",       # 550B  6.9s   1M ctx, agentic reasoning
    "google/gemma-4-31b-it",                   # 31B   12s    frontier reasoning
    "poolside/laguna-xs-2.1",                  # 33B   14s    agentic coding
    "mistralai/mistral-small-4-119b-2603",     # 119B  0.5s   ⚡ fastest large model
    "mistralai/mistral-medium-3.5-128b",       # 128B  89s    general high quality
    "deepseek-ai/deepseek-v4-pro",             # 1.6T  132s   frontier reasoning
    "mistralai/mistral-large-3-675b-instruct-2512",  # 675B 141s  state-of-the-art
    "z-ai/glm-5.2",                            # ?     346s   long-horizon tasks

    # ═══════════════════════════════════════════════════════════════
    # UNTESTED — expected to work based on NVIDIA docs
    # ═══════════════════════════════════════════════════════════════
    "nvidia/nemotron-3-nano-30b-a3b",          # 30B   ~250 tok/s, 1M ctx
    "meta/llama-3.2-3b-instruct",              # 3B    tiny/fast
]

# ⚠ NOT PROVISIONED for this key (YMMV — try yours):
#   mistralai/mistral-7b-instruct-v0.3     -> 404
#   mistralai/ministral-14b-instruct-2512  -> connection error
#   stepfun-ai/step-3.7-flash              -> empty response
#   nvidia/llama-3.1-nemotron-70b-instruct -> 404
#   moonshotai/kimi-k2.6                   -> 404
#   microsoft/phi-3.5-moe-instruct         -> 404
#   meta/llama-3.3-70b-instruct            -> timeout (>9 min)
#   minimaxai/minimax-m2.7                 -> NoneType error
#   qwen/qwen3-next-80b-a3b-instruct       -> timeout (>6 min)


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
        model: str = "deepseek-ai/deepseek-v4-flash",
        temperature: float = 0.7,
        top_p: float = 0.95,
        max_tokens: int = 4096,
        base_url: str = "https://integrate.api.nvidia.com/v1",
        max_retries: int = 5,
    ):
        if api_key is None:
            api_key = os.environ.get("NVIDIA_API_KEY")
        if not api_key or not api_key.startswith("nvapi-"):
            raise AuthenticationErrorWrapper(
                "NVIDIA API key is invalid or missing. "
                "Set NVIDIA_API_KEY environment variable or pass api_key parameter. "
                "Get a key from: https://build.nvidia.com"
            )

        self.api_key = api_key
        self.base_url = base_url
        self.client = OpenAI(base_url=base_url, api_key=api_key, timeout=120.0, max_retries=1)

        self.model = model
        if self.model not in RECOMMENDED_MODELS:
            import warnings
            warnings.warn(
                f"Model '{model}' is not in the curated RECOMMENDED_MODELS list. "
                f"It may not be provisioned for your key or may have poor performance. "
                f"See RECOMMENDED_MODELS in nvidia_provider.py for tested options."
            )
        self.temperature = temperature
        self.top_p = top_p
        self.max_tokens = max_tokens
        self.max_retries = max_retries

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
            except (RateLimitError, APIStatusError) as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    time.sleep(5 * (2 ** attempt))
            except (APIConnectionError, APIError) as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    time.sleep(1)
            except Exception as e:
                raise NvidiaProviderError(f"Unexpected error during streaming: {e}")

        if isinstance(last_error, (RateLimitError, APIStatusError)):
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
