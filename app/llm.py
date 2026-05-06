import os
import logging
from langchain_core.language_models.chat_models import BaseChatModel

logger = logging.getLogger(__name__)

def is_llm_configured() -> bool:
    """Check if the currently selected LLM provider has its required API key set."""
    provider = os.getenv("LLM_PROVIDER", "openai").lower()
    
    if provider == "openai":
        return bool(os.getenv("OPENAI_API_KEY"))
    elif provider == "anthropic":
        return bool(os.getenv("ANTHROPIC_API_KEY"))
    elif provider == "github":
        return bool(os.getenv("GITHUB_TOKEN"))
        
    return False

def get_llm() -> BaseChatModel:
    """Factory function to initialize and return the appropriate LangChain chat model."""
    provider = os.getenv("LLM_PROVIDER", "openai").lower()
    temperature = float(os.getenv("LLM_TEMPERATURE", "0"))
    
    if provider == "openai":
        model = os.getenv("LLM_MODEL", "gpt-4o")
        from langchain_openai import ChatOpenAI
        
        if not os.getenv("OPENAI_API_KEY"):
            logger.warning("OPENAI_API_KEY not set for OpenAI provider.")
            
        return ChatOpenAI(model=model, temperature=temperature)
        
    elif provider == "anthropic":
        model = os.getenv("LLM_MODEL", "claude-3-5-sonnet-20240620")
        from langchain_anthropic import ChatAnthropic
        
        if not os.getenv("ANTHROPIC_API_KEY"):
            logger.warning("ANTHROPIC_API_KEY not set for Anthropic provider.")
            
        return ChatAnthropic(model=model, temperature=temperature)
        
    elif provider == "github":
        model = os.getenv("LLM_MODEL", "gpt-4o")
        from langchain_openai import ChatOpenAI
        
        if not os.getenv("GITHUB_TOKEN"):
            logger.warning("GITHUB_TOKEN not set for GitHub provider.")
            
        # GitHub Models API acts as an OpenAI-compatible endpoint
        return ChatOpenAI(
            api_key=os.getenv("GITHUB_TOKEN", ""),
            base_url="https://models.inference.ai.azure.com",
            model=model,
            temperature=temperature
        )
        
    else:
        logger.error(f"Unknown LLM_PROVIDER '{provider}'. Falling back to OpenAI.")
        model = os.getenv("LLM_MODEL", "gpt-4o")
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model=model, temperature=temperature)