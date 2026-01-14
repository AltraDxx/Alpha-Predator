"""LLM 基础类定义

定义统一的 LLM 接口，支持多提供商切换。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import AsyncIterator, Optional


class MessageRole(str, Enum):
    """消息角色"""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


@dataclass
class LLMMessage:
    """LLM 消息"""
    role: MessageRole
    content: str
    
    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            "role": self.role.value,
            "content": self.content,
        }


@dataclass
class LLMResponse:
    """LLM 响应"""
    content: str
    model: str
    finish_reason: Optional[str] = None
    usage: Optional[dict] = None
    
    @property
    def total_tokens(self) -> int:
        """总 Token 数"""
        if self.usage:
            return self.usage.get("total_tokens", 0)
        return 0


@dataclass
class LLMConfig:
    """LLM 配置"""
    model: str
    temperature: float = 0.7
    max_tokens: int = 4096
    top_p: float = 1.0
    timeout: float = 60.0
    
    # 额外参数
    extra_params: dict = field(default_factory=dict)


class BaseLLM(ABC):
    """LLM 基础抽象类
    
    所有 LLM 提供商都需要实现此接口。
    """
    
    def __init__(self, config: Optional[LLMConfig] = None):
        """初始化 LLM
        
        Args:
            config: LLM 配置
        """
        self.config = config or LLMConfig(model="")
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """提供商名称"""
        pass
    
    @abstractmethod
    async def chat(
        self,
        messages: list[LLMMessage],
        **kwargs,
    ) -> LLMResponse:
        """发送聊天请求
        
        Args:
            messages: 消息列表
            **kwargs: 额外参数（覆盖默认配置）
            
        Returns:
            LLM 响应
        """
        pass
    
    @abstractmethod
    async def chat_stream(
        self,
        messages: list[LLMMessage],
        **kwargs,
    ) -> AsyncIterator[str]:
        """流式聊天请求
        
        Args:
            messages: 消息列表
            **kwargs: 额外参数
            
        Yields:
            响应文本片段
        """
        pass
    
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs,
    ) -> str:
        """便捷生成方法
        
        Args:
            prompt: 用户提示词
            system_prompt: 系统提示词（可选）
            **kwargs: 额外参数
            
        Returns:
            生成的文本
        """
        messages = []
        if system_prompt:
            messages.append(LLMMessage(role=MessageRole.SYSTEM, content=system_prompt))
        messages.append(LLMMessage(role=MessageRole.USER, content=prompt))
        
        response = await self.chat(messages, **kwargs)
        return response.content
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} provider={self.provider_name} model={self.config.model}>"
