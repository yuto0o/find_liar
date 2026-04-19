import asyncio
from typing import Any, List, Optional

from feature.llm import llama
from feature.rag import embed as _embed


async def llm_model_if_func(
    prompt: str,
    system_prompt: Optional[str] = None,
    history_messages: list = None,
    **kwargs,
) -> str:
    """Async wrapper for the existing synchronous `generate` function.

    LightRAG expects an async callable. We call the blocking `llama.generate`
    in a thread via `asyncio.to_thread`.
    """
    if history_messages is None:
        history_messages = []

    def _call():
        # incorporate system_prompt if given by prepending to prompt
        full_prompt = (system_prompt + "\n" + prompt) if system_prompt else prompt
        return llama.generate(full_prompt, **kwargs)

    return await asyncio.to_thread(_call)


async def embedding_func(texts: List[str]):
    """Async wrapper around feature.rag.embed.embed returning a numpy array.

    LightRAG's EmbeddingFunc expects an array-like result (numpy array),
    so we return the raw array rather than converting to Python lists.
    """

    def _call():
        arr = _embed.embed(texts)
        return arr

    return await asyncio.to_thread(_call)


# Synchronous adapters (in case needed elsewhere)
def llm_model_if_func_sync(
    prompt: str,
    system_prompt: Optional[str] = None,
    history_messages: list = None,
    **kwargs,
) -> str:
    if history_messages is None:
        history_messages = []
    full_prompt = (system_prompt + "\n" + prompt) if system_prompt else prompt
    return llama.generate(full_prompt, **kwargs)


def embedding_func_sync(texts: List[str]):
    arr = _embed.embed(texts)
    return arr
