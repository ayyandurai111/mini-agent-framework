"""Tests for NVIDIA LLM provider."""
import os
import pytest
from mini_agent.providers.nvidia_provider import (
    NvidiaProvider, NvidiaProviderError, AuthenticationErrorWrapper,
)


class TestNvidiaProviderInit:
    def test_missing_api_key_raises(self):
        if "NVIDIA_API_KEY" in os.environ:
            del os.environ["NVIDIA_API_KEY"]
        with pytest.raises(AuthenticationErrorWrapper):
            NvidiaProvider(api_key=None)

    def test_invalid_api_key_raises(self):
        with pytest.raises(AuthenticationErrorWrapper):
            NvidiaProvider(api_key="invalid-key")

    def test_valid_api_key_does_not_store_attr(self):
        provider = NvidiaProvider(api_key="nvapi-valid-key-test-here")
        assert provider is not None
        assert provider.model is not None

    def test_default_model(self):
        provider = NvidiaProvider(api_key="nvapi-test-key-here")
        assert provider.model == "deepseek-ai/deepseek-v4-flash"

    def test_custom_model(self):
        provider = NvidiaProvider(api_key="nvapi-test-key-here", model="deepseek-ai/deepseek-v4-flash")
        assert provider.model == "deepseek-ai/deepseek-v4-flash"

    def test_unknown_model_warns(self):
        import warnings
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            provider = NvidiaProvider(api_key="nvapi-test-key-here", model="gpt-4")
            assert len(w) >= 1
            assert any("not in the curated" in str(x.message) for x in w)
        assert provider.model == "gpt-4"

    def test_custom_temperature(self):
        provider = NvidiaProvider(api_key="nvapi-test-key-here", temperature=0.5)
        assert provider.temperature == 0.5

    def test_custom_base_url(self):
        provider = NvidiaProvider(api_key="nvapi-test-key-here", base_url="https://custom.example.com/v1")
        assert "custom.example.com" in str(provider.client.base_url)


class TestNvidiaProviderEdgeCases:
    def test_generate_stream_type(self):
        provider = NvidiaProvider(api_key="nvapi-test-key-here")
        gen = provider.generate_stream("system", "user")
        import types
        assert isinstance(gen, types.GeneratorType)

    def test_recommended_models_list(self):
        from mini_agent.providers.nvidia_provider import RECOMMENDED_MODELS
        assert len(RECOMMENDED_MODELS) > 0
        assert "deepseek-ai/deepseek-v4-flash" in RECOMMENDED_MODELS

    def test_env_var_read_does_not_store_attr(self, monkeypatch):
        monkeypatch.setenv("NVIDIA_API_KEY", "nvapi-env-key-test")
        provider = NvidiaProvider()
        assert provider is not None

    def test_max_retries_default(self):
        provider = NvidiaProvider(api_key="nvapi-test-key-here")
        assert provider.max_retries == 2
