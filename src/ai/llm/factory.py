"""LLM 工厂模块

提供 LLM 实例创建和管理功能。
"""

from typing import Optional

from loguru import logger

from src.ai.llm.base import BaseLLM, LLMConfig
from src.config import LLMProvider, get_settings


def create_llm(
    provider: Optional[LLMProvider] = None,
    config: Optional[LLMConfig] = None,
    **kwargs,
) -> BaseLLM:
    """创建 LLM 实例
    
    Args:
        provider: LLM 提供商，默认使用配置中的默认值
        config: LLM 配置
        **kwargs: 传递给具体实现的额外参数
        
    Returns:
        LLM 实例
    """
    settings = get_settings()
    provider = provider or settings.default_llm_provider
    
    logger.info(f"创建 LLM 实例: {provider.value}")
    
    if provider == LLMProvider.GOOGLE:
        from src.ai.llm.gemini import GeminiLLM
        return GeminiLLM(config=config, **kwargs)
    
    elif provider == LLMProvider.OPENAI:
        from src.ai.llm.openai_llm import OpenAILLM
        return OpenAILLM(config=config, provider=LLMProvider.OPENAI, **kwargs)
    
    elif provider == LLMProvider.QWEN:
        from src.ai.llm.qwen import QwenLLM
        return QwenLLM(config=config, **kwargs)
    
    elif provider == LLMProvider.CUSTOM:
        from src.ai.llm.openai_llm import OpenAILLM
        return OpenAILLM(config=config, provider=LLMProvider.CUSTOM, **kwargs)
    
    else:
        raise ValueError(f"未知的 LLM 提供商: {provider}")


# 默认 LLM 实例缓存
_default_llm: Optional[BaseLLM] = None
# 运行时激活的提供商（用于跟踪用户切换）
_active_provider: Optional[LLMProvider] = None


def get_default_llm() -> BaseLLM:
    """获取默认 LLM 实例（单例）
    
    Returns:
        默认配置的 LLM 实例
    """
    global _default_llm, _active_provider
    if _default_llm is None:
        # 优先使用运行时激活的提供商
        provider = _active_provider if _active_provider is not None else None
        _default_llm = create_llm(provider=provider)
    return _default_llm


def reset_default_llm() -> None:
    """重置默认 LLM 实例"""
    global _default_llm
    _default_llm = None


def get_active_provider() -> LLMProvider:
    """获取当前激活的 LLM 提供商
    
    Returns:
        当前激活的提供商，如果未设置则返回配置中的默认值
    """
    global _active_provider
    if _active_provider is not None:
        return _active_provider
    return get_settings().default_llm_provider


async def switch_llm_provider(provider: LLMProvider) -> BaseLLM:
    """切换 LLM 提供商
    
    Args:
        provider: 新的提供商
        
    Returns:
        新的 LLM 实例
    """
    global _default_llm, _active_provider
    logger.info(f"切换 LLM 提供商: {provider.value}")
    # 先尝试创建新实例，成功后再更新状态
    new_llm = create_llm(provider=provider)
    _active_provider = provider
    _default_llm = new_llm
    return _default_llm

