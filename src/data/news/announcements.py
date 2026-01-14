"""公告采集模块

使用 AkShare 免费 API 获取公告数据，避免爬虫的不稳定性。
"""

from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Optional
from enum import Enum

import pandas as pd
from loguru import logger


class AnnouncementType(str, Enum):
    """公告类型"""
    REGULAR = "regular"            # 定期报告
    TEMPORARY = "temporary"        # 临时公告
    IPO = "ipo"                    # IPO 相关
    REFINANCING = "refinancing"    # 再融资
    OTHER = "other"                # 其他


@dataclass
class Announcement:
    """公告数据模型"""
    title: str                     # 公告标题
    stock_code: str                # 股票代码
    stock_name: str                # 股票名称
    publish_date: date             # 发布日期
    announcement_type: AnnouncementType = AnnouncementType.OTHER
    summary: str = ""              # 摘要


class AnnouncementClient:
    """公告采集客户端
    
    使用 AkShare 免费 API 获取公告数据。
    """
    
    def __init__(self):
        """初始化客户端"""
        try:
            import akshare as ak
            self.ak = ak
            logger.info("AkShare 公告客户端初始化成功")
        except ImportError as e:
            logger.error("AkShare 未安装，请运行: pip install akshare")
            raise
    
    def get_latest_announcements(self, symbol: str = "全部") -> list[Announcement]:
        """获取最新公告
        
        Args:
            symbol: 公告类型，可选 "全部", "重大事项", "财务报告", "融资公告", "风险提示" 等
            
        Returns:
            公告列表
        """
        announcements = []
        
        try:
            # 使用 AkShare 获取公告数据
            df = self.ak.stock_notice_report(symbol=symbol)
            
            if df is None or df.empty:
                logger.warning(f"未获取到公告数据: {symbol}")
                return []
            
            for _, row in df.iterrows():
                ann = Announcement(
                    title=row.get("公告标题", ""),
                    stock_code=str(row.get("代码", "")),
                    stock_name=row.get("名称", ""),
                    publish_date=self._parse_date(row.get("公告时间", "")),
                    announcement_type=self._classify_type(row.get("公告标题", "")),
                )
                announcements.append(ann)
            
            logger.info(f"获取公告数量: {len(announcements)}")
            
        except Exception as e:
            logger.error(f"获取公告失败: {e}")
        
        return announcements
    
    def get_stock_announcements(self, ts_code: str) -> list[Announcement]:
        """获取指定股票的公告
        
        Args:
            ts_code: 股票代码（如 000001.SZ）
            
        Returns:
            公告列表
        """
        stock_code = ts_code.split(".")[0]
        announcements = []
        
        try:
            # 获取个股公告
            df = self.ak.stock_gsrl_gsdt_em(symbol=stock_code)
            
            if df is None or df.empty:
                logger.warning(f"未获取到股票公告: {ts_code}")
                return []
            
            for _, row in df.iterrows():
                ann = Announcement(
                    title=row.get("事件", row.get("内容", "")),
                    stock_code=stock_code,
                    stock_name="",
                    publish_date=self._parse_date(row.get("日期", "")),
                )
                announcements.append(ann)
            
            logger.info(f"获取股票 {ts_code} 公告数量: {len(announcements)}")
            
        except Exception as e:
            logger.error(f"获取股票公告失败: {e}")
        
        return announcements
    
    def get_ipo_announcements(self) -> pd.DataFrame:
        """获取 IPO 相关公告
        
        Returns:
            IPO 数据 DataFrame
        """
        try:
            # 新股申购信息
            df = self.ak.stock_xgsglb_em(symbol="全部股票")
            logger.info(f"获取 IPO 数据: {len(df)} 条")
            return df
        except Exception as e:
            logger.error(f"获取 IPO 公告失败: {e}")
            return pd.DataFrame()
    
    def get_major_events(self, symbol: str = "000001") -> pd.DataFrame:
        """获取重大事件
        
        Args:
            symbol: 股票代码
            
        Returns:
            重大事件 DataFrame
        """
        try:
            df = self.ak.stock_gsrl_gsdt_em(symbol=symbol)
            logger.info(f"获取重大事件: {len(df)} 条")
            return df
        except Exception as e:
            logger.error(f"获取重大事件失败: {e}")
            return pd.DataFrame()
    
    def _parse_date(self, date_str: str) -> date:
        """解析日期字符串"""
        if not date_str:
            return date.today()
        
        try:
            # 尝试多种格式
            for fmt in ["%Y-%m-%d", "%Y%m%d", "%Y/%m/%d", "%Y-%m-%d %H:%M:%S"]:
                try:
                    return datetime.strptime(str(date_str)[:10], fmt[:10]).date()
                except:
                    continue
            return date.today()
        except:
            return date.today()
    
    def _classify_type(self, title: str) -> AnnouncementType:
        """根据标题分类公告类型"""
        title_lower = title.lower()
        
        if any(kw in title for kw in ["年报", "季报", "半年报", "年度报告"]):
            return AnnouncementType.REGULAR
        elif any(kw in title for kw in ["ipo", "首发", "上市", "招股"]):
            return AnnouncementType.IPO
        elif any(kw in title for kw in ["增发", "配股", "定增", "可转债"]):
            return AnnouncementType.REFINANCING
        elif any(kw in title for kw in ["临时", "重大", "停牌", "复牌"]):
            return AnnouncementType.TEMPORARY
        else:
            return AnnouncementType.OTHER
    
    def format_for_llm(self, announcements: list[Announcement], max_count: int = 10) -> str:
        """格式化公告数据，供 LLM 分析使用
        
        Args:
            announcements: 公告列表
            max_count: 最大数量
            
        Returns:
            格式化的文本
        """
        if not announcements:
            return "暂无公告数据"
        
        lines = ["## 最新公告\n"]
        
        for ann in announcements[:max_count]:
            lines.append(f"- **{ann.stock_name or ann.stock_code}** ({ann.publish_date}): {ann.title}")
        
        if len(announcements) > max_count:
            lines.append(f"\n... 还有 {len(announcements) - max_count} 条公告")
        
        return "\n".join(lines)
