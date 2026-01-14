"""阿里通义千问 LLM 实现

支持阿里云 DashScope API，兼容国内网络环境。
"""

from typing import AsyncIterator, Optional

from loguru import logger

from src.ai.llm.base import BaseLLM, LLMConfig, LLMMessage, LLMResponse, MessageRole
from src.config import get_settings


class QwenLLM(BaseLLM):
    """通义千问 LLM 客户端
    
    使用阿里云 DashScope API，支持 qwen-turbo、qwen-plus、qwen-max 等模型。
    """
    
    def __init__(
        self,
        config: Optional[LLMConfig] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        **kwargs,
    ):
        """初始化通义千问客户端
        
        Args:
            config: LLM 配置
            api_key: DashScope API Key
            model: 模型名称（如 qwen-turbo, qwen-plus, qwen-max）
        """
        super().__init__(config, **kwargs)
        
        settings = get_settings()
        
        # 获取 API Key（优先使用参数，其次使用配置）
        self.api_key = api_key or settings.qwen.api_key.get_secret_value()
        if not self.api_key:
            raise ValueError("通义千问 API Key 未配置，请在 .env 中设置 QWEN_API_KEY")
        
        # 模型选择
        self.model = model or settings.qwen.model or "qwen-turbo"
        
        # DashScope API 端点
        self.base_url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"
        
        logger.info(f"通义千问 LLM 初始化成功: {self.model}")
    
    @property
    def provider_name(self) -> str:
        """提供商名称"""
        return "qwen"
    
    def _convert_messages(self, messages: list[LLMMessage]) -> list[dict]:
        """转换消息格式为 DashScope 格式"""
        converted = []
        for msg in messages:
            role = msg.role.value
            # DashScope 使用 "user" 和 "assistant"，system 消息需要特殊处理
            if role == "system":
                # 将 system 消息作为第一条 user 消息的前缀
                continue
            converted.append({
                "role": role,
                "content": msg.content,
            })
        return converted
    
    def _get_system_prompt(self, messages: list[LLMMessage]) -> Optional[str]:
        """提取 system prompt"""
        for msg in messages:
            if msg.role == MessageRole.SYSTEM:
                return msg.content
        return None
    
    async def chat(
        self,
        messages: list[LLMMessage],
        **kwargs,
    ) -> LLMResponse:
        """发送对话请求
        
        Args:
            messages: 消息列表
            **kwargs: 额外参数
            
        Returns:
            LLMResponse 响应对象
        """
        import httpx
        
        converted_messages = self._convert_messages(messages)
        system_prompt = self._get_system_prompt(messages)
        
        # 构建请求体
        payload = {
            "model": self.model,
            "input": {
                "messages": converted_messages,
            },
            "parameters": {
                "temperature": kwargs.get("temperature", self.config.temperature),
                "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
                "top_p": kwargs.get("top_p", 0.8),
                "result_format": "message",
            },
        }
        
        # 如果有 system prompt，添加到参数中
        if system_prompt:
            payload["input"]["messages"].insert(0, {
                "role": "system",
                "content": system_prompt,
            })
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    self.base_url,
                    json=payload,
                    headers=headers,
                )
                response.raise_for_status()
                
                data = response.json()
                
                # 解析响应
                output = data.get("output", {})
                choices = output.get("choices", [])
                
                if not choices:
                    # 兼容旧版 API 响应格式
                    content = output.get("text", "")
                else:
                    content = choices[0].get("message", {}).get("content", "")
                
                # 获取 token 用量
                usage = data.get("usage", {})
                
                return LLMResponse(
                    content=content,
                    model=self.model,
                    usage={
                        "prompt_tokens": usage.get("input_tokens", 0),
                        "completion_tokens": usage.get("output_tokens", 0),
                        "total_tokens": usage.get("total_tokens", 0),
                    },
                )
                
        except httpx.HTTPStatusError as e:
            error_msg = f"通义千问请求失败: {e.response.status_code}"
            try:
                error_data = e.response.json()
                error_msg = f"{error_msg} - {error_data.get('message', str(error_data))}"
            except:
                pass
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e
        except Exception as e:
            logger.error(f"通义千问请求异常: {e}")
            raise
    
    async def chat_stream(
        self,
        messages: list[LLMMessage],
        **kwargs,
    ) -> AsyncIterator[str]:
        """流式对话
        
        Args:
            messages: 消息列表
            **kwargs: 额外参数
            
        Yields:
            响应内容片段
        """
        import httpx
        
        converted_messages = self._convert_messages(messages)
        system_prompt = self._get_system_prompt(messages)
        
        # 构建请求体（启用流式输出）
        payload = {
            "model": self.model,
            "input": {
                "messages": converted_messages,
            },
            "parameters": {
                "temperature": kwargs.get("temperature", self.config.temperature),
                "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
                "top_p": kwargs.get("top_p", 0.8),
                "result_format": "message",
                "incremental_output": True,  # 增量输出
            },
        }
        
        if system_prompt:
            payload["input"]["messages"].insert(0, {
                "role": "system",
                "content": system_prompt,
            })
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-DashScope-SSE": "enable",  # 启用 SSE
        }
        
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream(
                    "POST",
                    self.base_url,
                    json=payload,
                    headers=headers,
                ) as response:
                    response.raise_for_status()
                    
                    async for line in response.aiter_lines():
                        if line.startswith("data:"):
                            import json
                            try:
                                data = json.loads(line[5:].strip())
                                output = data.get("output", {})
                                choices = output.get("choices", [])
                                
                                if choices:
                                    content = choices[0].get("message", {}).get("content", "")
                                    if content:
                                        yield content
                                else:
                                    # 兼容旧格式
                                    text = output.get("text", "")
                                    if text:
                                        yield text
                            except json.JSONDecodeError:
                                continue
                                
        except httpx.HTTPStatusError as e:
            error_msg = f"通义千问流式请求失败: {e.response.status_code}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e
        except Exception as e:
            logger.error(f"通义千问流式请求异常: {e}")
            raise
    
    def __repr__(self) -> str:
        return f"<QwenLLM provider=qwen model={self.model}>"
