"""LLM Provider 适配层"""

from app.engine.llm_providers.registry import ProviderRegistry
from app.engine.llm_providers.adapters.openai import OpenAIProvider
from app.engine.llm_providers.adapters.bob_maas import BobMaasProvider
from app.engine.llm_providers.adapters.unsupported import UnsupportedProvider

# 向后兼容别名
BeijingBankProvider = BobMaasProvider

__all__ = [
    "ProviderRegistry",
    "OpenAIProvider",
    "BobMaasProvider",
    "BeijingBankProvider",
    "UnsupportedProvider",
]
