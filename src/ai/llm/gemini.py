"""Google Gemini LLM 实现"""

from typing import AsyncIterator, Optional

import google.generativeai as genai
from loguru import logger

from src.ai.llm.base import BaseLLM, LLMConfig, LLMMessage, LLMResponse, MessageRole
from src.config import get_settings


class GeminiLLM(BaseLLM):
    """Google Gemini LLM 实现"""
    
    def __init__(self, config: Optional[LLMConfig] = None, api_key: Optional[str] = None):
        """初始化 Gemini LLM
        
        Args:
            config: LLM 配置
            api_key: API Key，默认从配置读取
        """
        settings = get_settings()
        self.api_key = api_key or settings.google.api_key.get_secret_value()
        
        if not self.api_key:
            raise ValueError("Google API Key 未配置，请在 .env 中设置 GOOGLE_API_KEY")
        
        # 设置默认模型
        default_model = settings.google.model
        if config is None:
            config = LLMConfig(model=default_model)
        elif not config.model:
            config.model = default_model
        
        super().__init__(config)
        
        # 配置 API
        genai.configure(api_key=self.api_key)
        
        # 创建模型实例
        self.model = genai.GenerativeModel(
            model_name=self.config.model,
            generation_config=genai.GenerationConfig(
                temperature=self.config.temperature,
                max_output_tokens=self.config.max_tokens,
                top_p=self.config.top_p,
            ),
        )
        
        logger.info(f"Gemini LLM 初始化成功: {self.config.model}")
    
    @property
    def provider_name(self) -> str:
        return "google"
    
    def _convert_messages(self, messages: list[LLMMessage]) -> tuple[Optional[str], list[dict]]:
        """转换消息格式为 Gemini 格式
        
        Gemini 使用 contents 列表，系统提示需要单独处理。
        
        Returns:
            (system_instruction, contents)
        """
        system_instruction = None
        contents = []
        
        for msg in messages:
            if msg.role == MessageRole.SYSTEM:
                # Gemini 的系统提示需要在模型初始化时设置
                system_instruction = msg.content
            elif msg.role == MessageRole.USER:
                contents.append({"role": "user", "parts": [msg.content]})
            elif msg.role == MessageRole.ASSISTANT:
                contents.append({"role": "model", "parts": [msg.content]})
        
        return system_instruction, contents
    
    async def chat(
        self,
        messages: list[LLMMessage],
        **kwargs,
    ) -> LLMResponse:
        """发送聊天请求"""
        system_instruction, contents = self._convert_messages(messages)
        
        try:
            # 如果有系统提示，需要重新创建模型实例
            model = self.model
            if system_instruction:
                model = genai.GenerativeModel(
                    model_name=self.config.model,
                    system_instruction=system_instruction,
                    generation_config=genai.GenerationConfig(
                        temperature=kwargs.get("temperature", self.config.temperature),
                        max_output_tokens=kwargs.get("max_tokens", self.config.max_tokens),
                        top_p=kwargs.get("top_p", self.config.top_p),
                    ),
                )
            
            # 发送请求
            response = await model.generate_content_async(
                contents,
                request_options={"timeout": self.config.timeout},
            )
            
            # 解析响应
            content = response.text
            usage = None
            if hasattr(response, "usage_metadata") and response.usage_metadata:
                usage = {
                    "prompt_tokens": response.usage_metadata.prompt_token_count,
                    "completion_tokens": response.usage_metadata.candidates_token_count,
                    "total_tokens": response.usage_metadata.total_token_count,
                }
            
            return LLMResponse(
                content=content,
                model=self.config.model,
                finish_reason="stop",
                usage=usage,
            )
            
        except Exception as e:
            logger.error(f"Gemini 请求失败: {e}")
            raise
    
    async def chat_stream(
        self,
        messages: list[LLMMessage],
        **kwargs,
    ) -> AsyncIterator[str]:
        """流式聊天请求"""
        system_instruction, contents = self._convert_messages(messages)
        
        try:
            model = self.model
            if system_instruction:
                model = genai.GenerativeModel(
                    model_name=self.config.model,
                    system_instruction=system_instruction,
                    generation_config=genai.GenerationConfig(
                        temperature=kwargs.get("temperature", self.config.temperature),
                        max_output_tokens=kwargs.get("max_tokens", self.config.max_tokens),
                        top_p=kwargs.get("top_p", self.config.top_p),
                    ),
                )
            
            # 流式请求
            response = await model.generate_content_async(
                contents,
                stream=True,
                request_options={"timeout": self.config.timeout},
            )
            
            async for chunk in response:
                if chunk.text:
                    yield chunk.text
                    
        except Exception as e:
            logger.error(f"Gemini 流式请求失败: {e}")
            raise
