"""Tushare Pro 数据源客户端

封装 Tushare Pro API，提供：
- 日线/分钟线行情数据
- 指数数据
- 集合竞价数据
- 本地缓存与增量更新
"""

from datetime import date, datetime
from typing import Optional

import pandas as pd
import tushare as ts
from loguru import logger

from src.config import get_settings


class TushareClient:
    """Tushare Pro API 客户端"""
    
    def __init__(self, token: Optional[str] = None):
        """初始化客户端
        
        Args:
            token: Tushare Pro Token，默认从配置读取
        """
        settings = get_settings()
        self.token = token or settings.tushare.token.get_secret_value()
        
        if not self.token:
            raise ValueError("Tushare Token 未配置，请在 .env 中设置 TUSHARE_TOKEN")
        
        # 初始化 Tushare Pro API
        ts.set_token(self.token)
        self.pro = ts.pro_api()
        logger.info("Tushare Pro 客户端初始化成功")
    
    def get_daily(
        self,
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> pd.DataFrame:
        """获取日线行情数据
        
        Args:
            ts_code: 股票代码（如 000001.SZ）
            trade_date: 交易日期（YYYYMMDD）
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            包含 OHLCV 数据的 DataFrame
        """
        try:
            df = self.pro.daily(
                ts_code=ts_code,
                trade_date=trade_date,
                start_date=start_date,
                end_date=end_date,
            )
            logger.debug(f"获取日线数据: {ts_code}, 记录数: {len(df)}")
            return df
        except Exception as e:
            logger.error(f"获取日线数据失败: {e}")
            raise
    
    def get_daily_basic(
        self,
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
    ) -> pd.DataFrame:
        """获取每日基本面指标（PE、PB、换手率等）
        
        Args:
            ts_code: 股票代码
            trade_date: 交易日期
            
        Returns:
            基本面指标 DataFrame
        """
        try:
            df = self.pro.daily_basic(
                ts_code=ts_code,
                trade_date=trade_date,
                fields="ts_code,trade_date,close,turnover_rate,turnover_rate_f,"
                       "volume_ratio,pe,pe_ttm,pb,ps,ps_ttm,dv_ratio,dv_ttm,"
                       "total_share,float_share,free_share,total_mv,circ_mv",
            )
            logger.debug(f"获取基本面数据: {ts_code}, 记录数: {len(df)}")
            return df
        except Exception as e:
            logger.error(f"获取基本面数据失败: {e}")
            raise
    
    def get_index_daily(
        self,
        ts_code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> pd.DataFrame:
        """获取指数日线行情
        
        Args:
            ts_code: 指数代码（如 000001.SH 上证指数）
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            指数行情 DataFrame
        """
        try:
            df = self.pro.index_daily(
                ts_code=ts_code,
                start_date=start_date,
                end_date=end_date,
            )
            logger.debug(f"获取指数数据: {ts_code}, 记录数: {len(df)}")
            return df
        except Exception as e:
            logger.error(f"获取指数数据失败: {e}")
            raise
    
    def get_stock_list(self, market: Optional[str] = None) -> pd.DataFrame:
        """获取股票列表
        
        Args:
            market: 市场类型（主板/创业板/科创板/北交所）
            
        Returns:
            股票列表 DataFrame
        """
        try:
            df = self.pro.stock_basic(
                exchange="",
                list_status="L",
                fields="ts_code,symbol,name,area,industry,market,list_date",
            )
            if market:
                df = df[df["market"] == market]
            logger.debug(f"获取股票列表, 记录数: {len(df)}")
            return df
        except Exception as e:
            logger.error(f"获取股票列表失败: {e}")
            raise
    
    def get_trade_cal(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        is_open: Optional[int] = None,
    ) -> pd.DataFrame:
        """获取交易日历
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            is_open: 是否交易日（1=是，0=否）
            
        Returns:
            交易日历 DataFrame
        """
        try:
            df = self.pro.trade_cal(
                exchange="SSE",
                start_date=start_date,
                end_date=end_date,
                is_open=is_open,
            )
            return df
        except Exception as e:
            logger.error(f"获取交易日历失败: {e}")
            raise
    
    def get_today_str(self) -> str:
        """获取今日日期字符串（YYYYMMDD）"""
        return date.today().strftime("%Y%m%d")
    
    def get_moneyflow_hsgt(
        self,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> pd.DataFrame:
        """获取沪深港通资金流向
        
        Args:
            trade_date: 交易日期
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            北向资金数据 DataFrame
        """
        try:
            df = self.pro.moneyflow_hsgt(
                trade_date=trade_date,
                start_date=start_date,
                end_date=end_date,
            )
            logger.debug(f"获取北向资金数据, 记录数: {len(df)}")
            return df
        except Exception as e:
            logger.error(f"获取北向资金数据失败: {e}")
            raise
    
    def get_shibor(
        self,
        date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> pd.DataFrame:
        """获取 Shibor 利率数据
        
        Args:
            date: 日期
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            Shibor 数据 DataFrame
        """
        try:
            df = self.pro.shibor(
                date=date,
                start_date=start_date,
                end_date=end_date,
            )
            logger.debug(f"获取 Shibor 数据, 记录数: {len(df)}")
            return df
        except Exception as e:
            logger.error(f"获取 Shibor 数据失败: {e}")
            raise


# 全局客户端单例
_client: Optional[TushareClient] = None


def get_tushare_client() -> TushareClient:
    """获取 Tushare 客户端单例"""
    global _client
    if _client is None:
        _client = TushareClient()
    return _client
