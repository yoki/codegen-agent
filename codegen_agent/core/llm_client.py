# %%
import sys, os
from pathlib import Path

# needed to run in interactive mode or standalone
module_folder = Path(__file__).resolve().parent.parent
if module_folder not in sys.path:
    sys.path.append(str(module_folder.resolve()))
from data_agency.shared import load_dotenv  # type: ignore. nessesary for loading .env file

# %%
from diskcache import Cache
from autogen_ext.cache_store.diskcache import DiskCacheStore
from autogen_ext.models.cache import ChatCompletionCache, CHAT_CACHE_VALUE_TYPE
from autogen_core.models import UserMessage
from autogen_core.models import ModelInfo
from autogen_ext.models.openai import OpenAIChatCompletionClient
from data_agency.shared.mypath import CACHE_PATH
from os import environ
from enum import Enum

# logging.basicConfig(level=logging.DEBUG)
# %%
GOOGLE_OPENAI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"


class LLMModels(Enum):
    GEMINI25_FLASH = "gemini-2.5-flash"
    GEMINI25_FLASH_LITE = "gemini-2.5-flash-lite-preview-06-17"
    GEMINI25_PRO = "gemini-2.5-pro"
    OPENAI_GPT_4 = "gpt-4"  # no key for now
    OPENAI_GPT_3_5 = "gpt-3.5-turbo"


def get_model_client(model: LLMModels = LLMModels.GEMINI25_FLASH):
    if model in {
        LLMModels.GEMINI25_FLASH,
        LLMModels.GEMINI25_FLASH_LITE,
        LLMModels.GEMINI25_PRO,
    }:
        return OpenAIChatCompletionClient(
            model=model.value,
            api_key=environ.get("GEMINI_API_KEY_FOR_DATA_AGENCY"),  # type: ignore
            base_url=GOOGLE_OPENAI_BASE_URL,
            temperature=0.0,
            max_tokens=100000,
            model_info=ModelInfo(
                vision=False, function_calling=True, json_output=True, family="unknown", structured_output=True
            ),
        )
    elif model in {LLMModels.OPENAI_GPT_4, LLMModels.OPENAI_GPT_3_5}:
        return OpenAIChatCompletionClient(
            model=model.value,
            api_key=environ.get("OPENAI_API_KEY"),  # type: ignore
            temperature=0.0,
            max_tokens=100000,
            model_info=ModelInfo(
                vision=False, function_calling=True, json_output=True, family="openai", structured_output=True
            ),
        )
    else:
        raise ValueError(f"Unsupported model: {model}")


MAX_TOTAL_CALLS = 1000  # Maximum number of API calls
MAX_TOTAL_TOKENS = 1_000_000  # Maximum total tokens (input + output)

DEBUG = False
from data_agency.shared.mylog import get_logger

cache_store = DiskCacheStore[CHAT_CACHE_VALUE_TYPE](Cache(CACHE_PATH))

GEMINI_MODEL = "gemini-2.5-flash-lite-preview-06-17"
# Configure the Gemini model client
# Replace 'gemini-1.5-flash-8b' with the desired Gemini model name
model_client = OpenAIChatCompletionClient(
    model=GEMINI_MODEL,
    api_key=environ.get("GEMINI_API_KEY_FOR_DATA_AGENCY"),  # type: ignore
    base_url=GOOGLE_OPENAI_BASE_URL,
    temperature=0.0,
    max_tokens=100000,
    model_info=ModelInfo(
        vision=False, function_calling=True, json_output=True, family="unknown", structured_output=True
    ),
)

import os

os.environ["OPENAI_LOG"] = "debug"

from autogen_core.models import (
    CreateResult,
    ModelInfo,
)

from typing import Sequence
from autogen_core.models import LLMMessage

import datetime


class UsageLimitExceededError(Exception):
    pass


class GeminiAPIError(Exception):
    pass


class FullLogChatClientCache(ChatCompletionCache):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._calls_key = "llm_total_calls"
        self._tokens_key = "llm_total_tokens"

    def _get_usage(self, key: str) -> int:
        return cache_store.cache.get(key, 0)  # type: ignore

    def _increment_usage(self, key: str, amount: int = 1) -> int:
        current = self._get_usage(key)
        new_total = current + amount
        cache_store.cache.set(key, new_total)
        return new_total

    def _estimate_tokens(self, content: str) -> int:
        return len(content) // 4 if content else 0

    async def create(self, messages: Sequence[LLMMessage], *args, **kwargs) -> CreateResult:
        if self._get_usage(self._calls_key) >= MAX_TOTAL_CALLS:
            raise UsageLimitExceededError(f"Max calls exceeded: {MAX_TOTAL_CALLS}")
        if self._get_usage(self._tokens_key) >= MAX_TOTAL_TOKENS:
            raise UsageLimitExceededError(f"Max tokens exceeded: {MAX_TOTAL_TOKENS}")
        logger = get_logger()
        logger.info(f"========{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}========")
        req = []
        for msg in messages:
            if hasattr(msg, "content") and hasattr(msg, "source"):
                req.append(f"{msg.source}: {msg.content}")  # type: ignore
            else:
                req.append(f"{msg.content}")

        if DEBUG:
            logger.info("*********************Request*********************")
            for msg in messages:
                logger.info(f"{msg=}")
            logger.info("**************************************************")

        try:
            result = await super().create(messages, *args, **kwargs)
        except Exception as e:
            logger.error(f"Error during LLM request: {e}")
            if not DEBUG:
                logger.info("*********************Full Request********************* \n" + "\n".join(req))

            # raise GeminiAPIError(f"LLM request failed: {e}") from None
            raise e from None

        # logger.warning("====LLM request and response logged====")

        if not result.cached:
            # price for "gemini-2.5-flash-lite-preview-06-17"
            # prompt_tokens: USD 0.1 per 1M tokens.
            # Completion tokens: USD 0.4 per 1M tokens
            total_token = result.usage.prompt_tokens + result.usage.completion_tokens * 4
            self._increment_usage(self._calls_key, 1)
            self._increment_usage(self._tokens_key, total_token)
            logger.info(f"Usage: {total_token}/{MAX_TOTAL_TOKENS} tokens")

        req = req[-1]
        logger.info("Request: \n" + req)
        logger.info("------")
        logger.info("Response: ")
        logger.info(result.content)

        return result

    def get_usage_stats(self) -> dict:
        return {
            "from": cache_store.cache.get("llm_usage_from", "unknown"),
            "calls": cache_store.cache.get("llm_total_calls", 0),
            "tokens": cache_store.cache.get("llm_total_tokens", 0),
            "cost_in_usd": cache_store.cache.get("llm_total_tokens", 0)
            / 1_000_000  # type: ignore
            * 0.1,  # gemini-2.5-flash-lite-preview-06-17
            "max_calls": MAX_TOTAL_CALLS,
            "max_tokens": MAX_TOTAL_TOKENS,
        }

    def reset_usage(self):
        cache_store.cache.set("llm_usage_from", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        cache_store.cache.set("llm_total_calls", 0)
        cache_store.cache.set("llm_total_tokens", 0)


def create_client(*args, model: LLMModels = LLMModels.GEMINI25_FLASH, **kwargs) -> FullLogChatClientCache:
    """
    Returns a FullLogChatClientCache instance with the configured model client and cache store.
    """
    client = get_model_client(model)
    return FullLogChatClientCache(client, cache_store, *args, **kwargs)


async def sample():
    # Use a persistent cache directory instead of temporary
    # cache_client = ChatCompletionCache(model_client, cache_store)
    cache_client = create_client()
    msg = "Hello.how are you doing today"

    response = await cache_client.create([UserMessage(content=msg, source="user")])
    # print(response)  # Should print response from OpenAI
    response = await cache_client.create([UserMessage(content=msg, source="user")])
    print(response)  # Should print cached response
    print("done")


import asyncio


def main():
    import nest_asyncio

    nest_asyncio.apply()
    asyncio.run(sample())


if __name__ == "__main__":
    main()

# %%
