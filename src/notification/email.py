"""邮件通知服务

支持 SMTP 发送邮件通知。
"""

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

import aiosmtplib
from loguru import logger

from src.config import get_settings


class EmailNotifier:
    """邮件通知器"""
    
    def __init__(self):
        """初始化邮件通知器"""
        settings = get_settings()
        self.host = settings.notification.smtp_host
        self.port = settings.notification.smtp_port
        self.user = settings.notification.smtp_user
        self.password = (
            settings.notification.smtp_password.get_secret_value()
            if settings.notification.smtp_password
            else None
        )
        self.from_addr = settings.notification.smtp_from or self.user
    
    @property
    def is_configured(self) -> bool:
        """是否已配置"""
        return bool(self.host and self.user and self.password)
    
    async def send(
        self,
        to: str | list[str],
        subject: str,
        body: str,
        html: bool = True,
    ) -> bool:
        """发送邮件
        
        Args:
            to: 收件人（单个或列表）
            subject: 邮件主题
            body: 邮件内容
            html: 是否为 HTML 格式
            
        Returns:
            是否发送成功
        """
        if not self.is_configured:
            logger.warning("邮件服务未配置")
            return False
        
        # 构建邮件
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self.from_addr
        msg["To"] = to if isinstance(to, str) else ", ".join(to)
        
        content_type = "html" if html else "plain"
        msg.attach(MIMEText(body, content_type, "utf-8"))
        
        try:
            await aiosmtplib.send(
                msg,
                hostname=self.host,
                port=self.port,
                username=self.user,
                password=self.password,
                start_tls=True,
            )
            logger.info(f"邮件发送成功: {subject} -> {to}")
            return True
            
        except Exception as e:
            logger.error(f"邮件发送失败: {e}")
            return False
    
    async def send_report(
        self,
        to: str | list[str],
        title: str,
        markdown_content: str,
    ) -> bool:
        """发送研报邮件
        
        将 Markdown 内容转换为简单 HTML 格式发送。
        
        Args:
            to: 收件人
            title: 研报标题
            markdown_content: Markdown 格式的研报内容
            
        Returns:
            是否发送成功
        """
        # 简单的 Markdown 到 HTML 转换
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 800px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                h1, h2, h3 {{ color: #1a1a1a; }}
                table {{
                    border-collapse: collapse;
                    width: 100%;
                    margin: 16px 0;
                }}
                th, td {{
                    border: 1px solid #ddd;
                    padding: 8px;
                    text-align: left;
                }}
                th {{ background-color: #f5f5f5; }}
                code {{
                    background-color: #f5f5f5;
                    padding: 2px 6px;
                    border-radius: 3px;
                }}
                blockquote {{
                    border-left: 4px solid #ddd;
                    margin: 16px 0;
                    padding-left: 16px;
                    color: #666;
                }}
            </style>
        </head>
        <body>
            <h1>{title}</h1>
            <pre style="white-space: pre-wrap; font-family: inherit;">{markdown_content}</pre>
        </body>
        </html>
        """
        
        return await self.send(to, f"📊 {title}", html_content, html=True)


# 全局邮件通知器
_email_notifier: Optional[EmailNotifier] = None


def get_email_notifier() -> EmailNotifier:
    """获取邮件通知器单例"""
    global _email_notifier
    if _email_notifier is None:
        _email_notifier = EmailNotifier()
    return _email_notifier
