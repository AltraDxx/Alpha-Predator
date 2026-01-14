"""证监会和交易所公告采集模块

支持采集：
- 中国证监会官网公告
- 上海证券交易所公告
- 深圳证券交易所公告
"""

from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Optional
from enum import Enum

import httpx
from loguru import logger


class AnnouncementSource(str, Enum):
    """公告来源"""
    CSRC = "csrc"  # 证监会
    SSE = "sse"    # 上交所
    SZSE = "szse"  # 深交所


class AnnouncementType(str, Enum):
    """公告类型"""
    IPO = "ipo"                    # IPO 相关
    REFINANCING = "refinancing"    # 再融资
    SUSPENSION = "suspension"      # 停复牌
    REDUCTION = "reduction"        # 减持计划
    INVESTIGATION = "investigation"  # 立案调查
    PENALTY = "penalty"            # 处罚
    OTHER = "other"                # 其他


@dataclass
class Announcement:
    """公告数据模型"""
    title: str                     # 公告标题
    source: AnnouncementSource     # 来源
    publish_date: date             # 发布日期
    url: str                       # 原文链接
    announcement_type: AnnouncementType = AnnouncementType.OTHER
    summary: str = ""              # 摘要
    related_stocks: list[str] = field(default_factory=list)  # 相关股票代码
    raw_content: str = ""          # 原始内容


class CSRCAnnouncements:
    """证监会和交易所公告采集器"""
    
    def __init__(self):
        """初始化采集器"""
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json, text/plain, */*",
        }
        
        # API 端点
        self.endpoints = {
            AnnouncementSource.SSE: "http://www.sse.com.cn/disclosure/listedinfo/announcement/s_docdateQuery.htm",
            AnnouncementSource.SZSE: "https://www.szse.cn/api/disc/announcement/annList",
        }
    
    async def fetch_sse_announcements(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        keyword: Optional[str] = None,
        page: int = 1,
        page_size: int = 25,
    ) -> list[Announcement]:
        """获取上交所公告
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            keyword: 关键词
            page: 页码
            page_size: 每页数量
            
        Returns:
            公告列表
        """
        if start_date is None:
            start_date = date.today()
        if end_date is None:
            end_date = date.today()
        
        params = {
            "isPagination": "true",
            "pageHelp.pageSize": page_size,
            "pageHelp.pageNo": page,
            "pageHelp.beginPage": page,
            "pageHelp.cacheSize": 1,
            "pageHelp.endPage": page + 5,
            "docDateFromRangeDate": start_date.strftime("%Y-%m-%d"),
            "docDateToRangeDate": end_date.strftime("%Y-%m-%d"),
        }
        
        if keyword:
            params["docTitle"] = keyword
        
        announcements = []
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    self.endpoints[AnnouncementSource.SSE],
                    params=params,
                    headers=self.headers,
                )
                response.raise_for_status()
                
                data = response.json()
                result = data.get("result", [])
                
                for item in result:
                    ann = Announcement(
                        title=item.get("docTitleHtml", item.get("docTitle", "")),
                        source=AnnouncementSource.SSE,
                        publish_date=datetime.strptime(
                            item.get("createTime", "")[:10], "%Y-%m-%d"
                        ).date() if item.get("createTime") else date.today(),
                        url=f"http://www.sse.com.cn{item.get('docURL', '')}",
                        announcement_type=self._classify_announcement(item.get("docTitle", "")),
                        related_stocks=[item.get("stockCode", "")] if item.get("stockCode") else [],
                    )
                    announcements.append(ann)
                    
        except Exception as e:
            logger.error(f"获取上交所公告失败: {e}")
        
        return announcements
    
    async def fetch_szse_announcements(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        keyword: Optional[str] = None,
        page: int = 1,
        page_size: int = 25,
    ) -> list[Announcement]:
        """获取深交所公告
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            keyword: 关键词
            page: 页码
            page_size: 每页数量
            
        Returns:
            公告列表
        """
        if start_date is None:
            start_date = date.today()
        if end_date is None:
            end_date = date.today()
        
        payload = {
            "seDate": [
                start_date.strftime("%Y-%m-%d"),
                end_date.strftime("%Y-%m-%d"),
            ],
            "channelCode": ["listedNotice_disc"],
            "pageNum": page,
            "pageSize": page_size,
        }
        
        if keyword:
            payload["title"] = keyword
        
        announcements = []
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.endpoints[AnnouncementSource.SZSE],
                    json=payload,
                    headers=self.headers,
                )
                response.raise_for_status()
                
                data = response.json()
                items = data.get("data", [])
                
                for item in items:
                    ann = Announcement(
                        title=item.get("title", ""),
                        source=AnnouncementSource.SZSE,
                        publish_date=datetime.strptime(
                            item.get("publishTime", "")[:10], "%Y-%m-%d"
                        ).date() if item.get("publishTime") else date.today(),
                        url=f"https://disc.szse.cn/download{item.get('attachPath', '')}",
                        announcement_type=self._classify_announcement(item.get("title", "")),
                        related_stocks=[item.get("secCode", "")] if item.get("secCode") else [],
                    )
                    announcements.append(ann)
                    
        except Exception as e:
            logger.error(f"获取深交所公告失败: {e}")
        
        return announcements
    
    def _classify_announcement(self, title: str) -> AnnouncementType:
        """根据标题分类公告类型"""
        title_lower = title.lower()
        
        if any(kw in title_lower for kw in ["ipo", "首发", "上市", "招股"]):
            return AnnouncementType.IPO
        elif any(kw in title_lower for kw in ["增发", "配股", "定增", "再融资", "可转债"]):
            return AnnouncementType.REFINANCING
        elif any(kw in title_lower for kw in ["停牌", "复牌", "暂停"]):
            return AnnouncementType.SUSPENSION
        elif any(kw in title_lower for kw in ["减持", "股东", "董监高"]):
            return AnnouncementType.REDUCTION
        elif any(kw in title_lower for kw in ["立案", "调查"]):
            return AnnouncementType.INVESTIGATION
        elif any(kw in title_lower for kw in ["处罚", "警示", "纪律处分"]):
            return AnnouncementType.PENALTY
        else:
            return AnnouncementType.OTHER
    
    async def fetch_all(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        keyword: Optional[str] = None,
    ) -> list[Announcement]:
        """获取所有交易所公告
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            keyword: 关键词
            
        Returns:
            合并后的公告列表
        """
        import asyncio
        
        sse_task = self.fetch_sse_announcements(start_date, end_date, keyword)
        szse_task = self.fetch_szse_announcements(start_date, end_date, keyword)
        
        sse_anns, szse_anns = await asyncio.gather(sse_task, szse_task)
        
        # 合并并按日期排序
        all_anns = sse_anns + szse_anns
        all_anns.sort(key=lambda x: x.publish_date, reverse=True)
        
        logger.info(f"获取公告总数: {len(all_anns)} (上交所: {len(sse_anns)}, 深交所: {len(szse_anns)})")
        
        return all_anns
    
    async def search_by_stock(
        self,
        ts_code: str,
        days: int = 30,
    ) -> list[Announcement]:
        """按股票代码搜索公告
        
        Args:
            ts_code: 股票代码（如 000001.SZ）
            days: 回溯天数
            
        Returns:
            相关公告列表
        """
        from datetime import timedelta
        
        # 提取股票代码（去掉后缀）
        stock_code = ts_code.split(".")[0]
        
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        
        # 使用股票代码作为关键词搜索
        all_anns = await self.fetch_all(start_date, end_date, stock_code)
        
        # 过滤只包含该股票的公告
        return [ann for ann in all_anns if stock_code in ann.related_stocks or stock_code in ann.title]
    
    async def get_important_announcements(
        self,
        days: int = 7,
    ) -> list[Announcement]:
        """获取重要公告（停复牌、立案调查、处罚等）
        
        Args:
            days: 回溯天数
            
        Returns:
            重要公告列表
        """
        from datetime import timedelta
        
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        
        all_anns = await self.fetch_all(start_date, end_date)
        
        important_types = {
            AnnouncementType.SUSPENSION,
            AnnouncementType.INVESTIGATION,
            AnnouncementType.PENALTY,
        }
        
        return [ann for ann in all_anns if ann.announcement_type in important_types]
