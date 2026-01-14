"""系统配置管理模块

支持从环境变量和 .env 文件加载配置，包含多 LLM 提供商配置。
"""

from enum import Enum
from pathlib import Path
from typing import Optional

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMProvider(str, Enum):
    """LLM 提供商枚举"""
    OPENAI = "openai"
    GOOGLE = "google"
    QWEN = "qwen"  # 通义千问
    CUSTOM = "custom"


class TushareSettings(BaseSettings):
    """Tushare 数据源配置"""
    token: SecretStr = Field(default=SecretStr(""), description="Tushare Pro API Token")
    
    model_config = SettingsConfigDict(env_prefix="TUSHARE_")


class GoogleLLMSettings(BaseSettings):
    """Google Gemini LLM 配置"""
    api_key: SecretStr = Field(default=SecretStr(""), description="Google API Key")
    model: str = Field(default="gemini-2.0-flash", description="模型名称")
    
    model_config = SettingsConfigDict(env_prefix="GOOGLE_")


class OpenAILLMSettings(BaseSettings):
    """OpenAI LLM 配置"""
    api_key: SecretStr = Field(default=SecretStr(""), description="OpenAI API Key")
    base_url: str = Field(default="https://api.openai.com/v1", description="API Base URL")
    model: str = Field(default="gpt-4o", description="模型名称")
    
    model_config = SettingsConfigDict(env_prefix="OPENAI_")


class CustomLLMSettings(BaseSettings):
    """自定义 LLM 配置（兼容 OpenAI API 格式）"""
    api_key: SecretStr = Field(default=SecretStr(""), description="API Key")
    base_url: str = Field(default="http://localhost:8000/v1", description="API Base URL")
    model: str = Field(default="", description="模型名称")
    
    model_config = SettingsConfigDict(env_prefix="CUSTOM_LLM_")


class QwenLLMSettings(BaseSettings):
    """阿里通义千问 LLM 配置"""
    api_key: SecretStr = Field(default=SecretStr(""), description="DashScope API Key")
    model: str = Field(default="qwen-turbo", description="模型名称 (qwen-turbo/qwen-plus/qwen-max)")
    
    model_config = SettingsConfigDict(env_prefix="QWEN_")


class NotificationSettings(BaseSettings):
    """通知服务配置"""
    # 飞书
    feishu_webhook_url: Optional[str] = Field(default=None, description="飞书 Webhook URL")
    
    # 钉钉
    dingtalk_webhook_url: Optional[str] = Field(default=None, description="钉钉 Webhook URL")
    dingtalk_secret: Optional[str] = Field(default=None, description="钉钉签名密钥")
    
    # 邮件
    smtp_host: str = Field(default="smtp.gmail.com", description="SMTP 服务器地址")
    smtp_port: int = Field(default=587, description="SMTP 端口")
    smtp_user: Optional[str] = Field(default=None, description="SMTP 用户名")
    smtp_password: Optional[SecretStr] = Field(default=None, description="SMTP 密码")
    smtp_from: Optional[str] = Field(default=None, description="发件人地址")


class Settings(BaseSettings):
    """全局配置"""
    
    # LLM 配置
    default_llm_provider: LLMProvider = Field(
        default=LLMProvider.GOOGLE,
        description="默认 LLM 提供商"
    )
    
    # 子配置
    tushare: TushareSettings = Field(default_factory=TushareSettings)
    google: GoogleLLMSettings = Field(default_factory=GoogleLLMSettings)
    openai: OpenAILLMSettings = Field(default_factory=OpenAILLMSettings)
    qwen: QwenLLMSettings = Field(default_factory=QwenLLMSettings)
    custom_llm: CustomLLMSettings = Field(default_factory=CustomLLMSettings)
    notification: NotificationSettings = Field(default_factory=NotificationSettings)
    
    # 系统配置
    fallback_cutoff_time: str = Field(
        default="09:29:30",
        description="早盘推送熔断时间"
    )
    log_level: str = Field(default="INFO", description="日志级别")
    
    # 数据目录
    data_dir: Path = Field(default=Path("data"), description="数据存储目录")
    cache_dir: Path = Field(default=Path(".cache"), description="缓存目录")
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore",
    )
    
    def get_llm_config(self, provider: Optional[LLMProvider] = None):
        """获取指定提供商的 LLM 配置"""
        provider = provider or self.default_llm_provider
        
        if provider == LLMProvider.GOOGLE:
            return self.google
        elif provider == LLMProvider.OPENAI:
            return self.openai
        elif provider == LLMProvider.QWEN:
            return self.qwen
        elif provider == LLMProvider.CUSTOM:
            return self.custom_llm
        else:
            raise ValueError(f"未知的 LLM 提供商: {provider}")


# 全局配置单例
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """获取全局配置单例"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reload_settings() -> Settings:
    """重新加载配置"""
    global _settings
    _settings = Settings()
    return _settings
