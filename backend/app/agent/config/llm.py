import logging
from typing import List

from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel

DEFAULT_MODEL = "claude-sonnet-4-5-20250929"
DEFAULT_TEMPERATURE = 0.3
DEFAULT_MAX_TOKENS = 8192
DEFAULT_MAX_RETRIES = 2

logger = logging.getLogger(__name__)


def create_llm(
    model_name: str = DEFAULT_MODEL,
    temperature: float = DEFAULT_TEMPERATURE,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    max_retries: int = DEFAULT_MAX_RETRIES,
) -> BaseChatModel:
    """Create and configure the LLM instance.

    Args:
        model_name: The Claude model to use
        temperature: Sampling temperature (0-1)
        max_tokens: Maximum tokens in response
        max_retries: Number of retry attempts on failure

    Returns:
        Configured ChatAnthropic instance
    """
    logger.info(f"Initializing LLM with model: {model_name}")

    return ChatAnthropic(
        model_name=model_name,
        temperature=temperature,
        max_tokens_to_sample=max_tokens,
        timeout=None,
        max_retries=max_retries,
        stop=None,
    )


def create_llm_with_tools(
    tools: List,
    model_name: str = DEFAULT_MODEL,
    temperature: float = DEFAULT_TEMPERATURE,
) -> BaseChatModel:
    """Create an LLM instance bound with specific tools.

    Args:
        tools: List of tools/schemas to bind to the LLM
        model_name: The Claude model to use
        temperature: Sampling temperature

    Returns:
        LLM instance with tools bound
    """
    llm = create_llm(
        model_name=model_name,
        temperature=temperature,
    )

    logger.info(f"Binding {len(tools)} tools to LLM")
    return llm.bind_tools(tools)  # type: ignore
