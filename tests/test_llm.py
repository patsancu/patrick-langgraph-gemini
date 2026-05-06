import os
from unittest.mock import patch
from app.llm import is_llm_configured, get_llm

def test_is_llm_configured_openai():
    with patch.dict(os.environ, {"LLM_PROVIDER": "openai", "OPENAI_API_KEY": "test"}):
        assert is_llm_configured() is True
    with patch.dict(os.environ, {"LLM_PROVIDER": "openai", "OPENAI_API_KEY": ""}):
        assert is_llm_configured() is False

def test_is_llm_configured_anthropic():
    with patch.dict(os.environ, {"LLM_PROVIDER": "anthropic", "ANTHROPIC_API_KEY": "test"}):
        assert is_llm_configured() is True

def test_is_llm_configured_github():
    with patch.dict(os.environ, {"LLM_PROVIDER": "github", "GITHUB_TOKEN": "test"}):
        assert is_llm_configured() is True

def test_is_llm_configured_unknown():
    with patch.dict(os.environ, {"LLM_PROVIDER": "unknown"}):
        assert is_llm_configured() is False

def test_get_llm_openai():
    with patch.dict(os.environ, {"LLM_PROVIDER": "openai", "OPENAI_API_KEY": "test", "LLM_TEMPERATURE": "0.5", "LLM_MODEL": "gpt-3.5-turbo"}):
        llm = get_llm()
        assert llm.__class__.__name__ == "ChatOpenAI"
        assert llm.model_name == "gpt-3.5-turbo"
        assert llm.temperature == 0.5

def test_get_llm_anthropic():
    with patch.dict(os.environ, {"LLM_PROVIDER": "anthropic", "ANTHROPIC_API_KEY": "test", "LLM_MODEL": "claude-test"}):
        llm = get_llm()
        assert llm.__class__.__name__ == "ChatAnthropic"
        assert llm.model == "claude-test"

def test_get_llm_github():
    with patch.dict(os.environ, {"LLM_PROVIDER": "github", "GITHUB_TOKEN": "test"}):
        llm = get_llm()
        assert llm.__class__.__name__ == "ChatOpenAI"
        assert llm.openai_api_base == "https://models.inference.ai.azure.com"

def test_get_llm_unknown_fallback():
    with patch.dict(os.environ, {"LLM_PROVIDER": "unknown", "OPENAI_API_KEY": "test"}):
        llm = get_llm()
        assert llm.__class__.__name__ == "ChatOpenAI"
