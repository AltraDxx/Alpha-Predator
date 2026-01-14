"""Webhook 通知服务

支持飞书、钉钉等 Webhook 推送。
"""

import hashlib
import hmac
import time
import base64
from typing import Optional
from urllib.parse import quote_plus

import httpx
from loguru import logger

from src.config import get_settings


class WebhookNotifier:
    """Webhook 通知器"""
    
    def __init__(self):
        """初始化通知器"""
        settings = get_settings()
        self.feishu_url = settings.notification.feishu_webhook_url
        self.dingtalk_url = settings.notification.dingtalk_webhook_url
        self.dingtalk_secret = settings.notification.dingtalk_secret
    
    async def send_feishu(
        self,
        title: str,
        content: str,
        message_type: str = "interactive",
    ) -> bool:
        """发送飞书消息
        
        Args:
            title: 消息标题
            content: 消息内容（支持 Markdown）
            message_type: 消息类型
            
        Returns:
            是否发送成功
        """
        if not self.feishu_url:
            logger.warning("飞书 Webhook URL 未配置")
            return False
        
        # 构建富文本卡片消息
        payload = {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {
                        "content": title,
                        "tag": "plain_text"
                    },
                    "template": "blue"
                },
                "elements": [
                    {
                        "tag": "markdown",
                        "content": content
                    }
                ]
            }
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.feishu_url,
                    json=payload,
                    timeout=10.0,
                )
                response.raise_for_status()
                
                result = response.json()
                if result.get("code") == 0 or result.get("StatusCode") == 0:
                    logger.info(f"飞书消息发送成功: {title}")
                    return True
                else:
                    logger.error(f"飞书消息发送失败: {result}")
                    return False
                    
        except Exception as e:
            logger.error(f"飞书消息发送异常: {e}")
            return False
    
    def _generate_dingtalk_sign(self, timestamp: int) -> str:
        """生成钉钉签名
        
        Args:
            timestamp: 时间戳（毫秒）
            
        Returns:
            签名字符串
        """
        if not self.dingtalk_secret:
            return ""
        
        string_to_sign = f"{timestamp}\n{self.dingtalk_secret}"
        hmac_code = hmac.new(
            self.dingtalk_secret.encode("utf-8"),
            string_to_sign.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).digest()
        sign = quote_plus(base64.b64encode(hmac_code))
        return sign
    
    async def send_dingtalk(
        self,
        title: str,
        content: str,
        at_all: bool = False,
    ) -> bool:
        """发送钉钉消息
        
        Args:
            title: 消息标题
            content: 消息内容（支持 Markdown）
            at_all: 是否 @所有人
            
        Returns:
            是否发送成功
        """
        if not self.dingtalk_url:
            logger.warning("钉钉 Webhook URL 未配置")
            return False
        
        # 添加签名
        url = self.dingtalk_url
        if self.dingtalk_secret:
            timestamp = int(time.time() * 1000)
            sign = self._generate_dingtalk_sign(timestamp)
            url = f"{self.dingtalk_url}&timestamp={timestamp}&sign={sign}"
        
        # 构建 Markdown 消息
        payload = {
            "msgtype": "markdown",
            "markdown": {
                "title": title,
                "text": f"## {title}\n\n{content}"
            },
            "at": {
                "isAtAll": at_all
            }
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    json=payload,
                    timeout=10.0,
                )
                response.raise_for_status()
                
                result = response.json()
                if result.get("errcode") == 0:
                    logger.info(f"钉钉消息发送成功: {title}")
                    return True
                else:
                    logger.error(f"钉钉消息发送失败: {result}")
                    return False
                    
        except Exception as e:
            logger.error(f"钉钉消息发送异常: {e}")
            return False
    
    async def send_all(
        self,
        title: str,
        content: str,
    ) -> dict[str, bool]:
        """发送到所有已配置的渠道
        
        Args:
            title: 消息标题
            content: 消息内容
            
        Returns:
            各渠道发送结果
        """
        results = {}
        
        if self.feishu_url:
            results["feishu"] = await self.send_feishu(title, content)
        
        if self.dingtalk_url:
            results["dingtalk"] = await self.send_dingtalk(title, content)
        
        return results


# 全局通知器
_notifier: Optional[WebhookNotifier] = None


def get_webhook_notifier() -> WebhookNotifier:
    """获取 Webhook 通知器单例"""
    global _notifier
    if _notifier is None:
        _notifier = WebhookNotifier()
    return _notifier
