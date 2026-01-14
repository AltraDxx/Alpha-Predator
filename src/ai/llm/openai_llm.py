"""OpenAI 兼容 LLM 实现

支持 OpenAI API 及兼容格式的第三方服务。
"""

from typing import AsyncIterator, Optional

from loguru import logger
from openai import AsyncOpenAI

from src.ai.llm.base import BaseLLM, LLMConfig, LLMMessage, LLMResponse
from src.config import LLMProvider, get_settings


class OpenAILLM(BaseLLM):
    """OpenAI 兼容 LLM 实现
    
    支持：
    - OpenAI 官方 API
    - 自定义兼容服务（如 Ollama、vLLM 等）
    """
    
    def __init__(
        self,
        config: Optional[LLMConfig] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        provider: LLMProvider = LLMProvider.OPENAI,
    ):
        """初始化 OpenAI 兼容 LLM
        
        Args:
            config: LLM 配置
            api_key: API Key
            base_url: API Base URL
            provider: 提供商类型（openai 或 custom）
        """
        settings = get_settings()
        self._provider = provider
        
        # 根据提供商类型获取配置
        if provider == LLMProvider.CUSTOM:
            llm_settings = settings.custom_llm
        else:
            llm_settings = settings.openai
        
        self.api_key = api_key or llm_settings.api_key.get_secret_value()
        self.base_url = base_url or llm_settings.base_url
        
        if not self.api_key:
            raise ValueError(f"{provider.value} API Key 未配置")
        
        # 设置默认模型
        default_model = llm_settings.model
        if config is None:
            config = LLMConfig(model=default_model)
        elif not config.model:
            config.model = default_model
        
        super().__init__(config)
        
        # 创建客户端
        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self.config.timeout,
        )
        
        logger.info(f"OpenAI 兼容 LLM 初始化成功: {self.base_url}, 模型: {self.config.model}")
    
    @property
    def provider_name(self) -> str:
        return self._provider.value
    
    async def chat(
        self,
        messages: list[LLMMessage],
        **kwargs,
    ) -> LLMResponse:
        """发送聊天请求"""
        try:
            response = await self.client.chat.completions.create(
                model=kwargs.get("model", self.config.model),
                messages=[msg.to_dict() for msg in messages],
                temperature=kwargs.get("temperature", self.config.temperature),
                max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
                top_p=kwargs.get("top_p", self.config.top_p),
            )
            
            choice = response.choices[0]
            usage = None
            if response.usage:
                usage = {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                }
            
            return LLMResponse(
                content=choice.message.content or "",
                model=response.model,
                finish_reason=choice.finish_reason,
                usage=usage,
            )
            
        except Exception as e:
            logger.error(f"OpenAI 请求失败: {e}")
            raise
    
    async def chat_stream(
        self,
        messages: list[LLMMessage],
        **kwargs,
    ) -> AsyncIterator[str]:
        """流式聊天请求"""
        try:
            stream = await self.client.chat.completions.create(
                model=kwargs.get("model", self.config.model),
                messages=[msg.to_dict() for msg in messages],
                temperature=kwargs.get("temperature", self.config.temperature),
                max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
                top_p=kwargs.get("top_p", self.config.top_p),
                stream=True,
            )
            
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            logger.error(f"OpenAI 流式请求失败: {e}")
            raise
