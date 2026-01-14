"""同花顺数据客户端

通过 AkShare 提供的同花顺数据接口获取行情、资金流向等数据。
作为 Tushare 的备选/补充数据源。
"""

from datetime import datetime, date
from typing import Optional

import pandas as pd
from loguru import logger


class THSClient:
    """同花顺数据客户端
    
    使用 AkShare 封装的同花顺接口获取数据。
    """
    
    def __init__(self):
        """初始化客户端"""
        try:
            import akshare as ak
            self.ak = ak
            logger.info("同花顺数据客户端初始化成功 (via AkShare)")
        except ImportError as e:
            logger.error("AkShare 未安装，请运行: pip install akshare")
            raise
    
    def get_realtime_quote(self, ts_code: str) -> Optional[dict]:
        """获取实时行情
        
        Args:
            ts_code: 股票代码（如 000001.SZ）
            
        Returns:
            实时行情数据
        """
        stock_code = ts_code.split(".")[0]
        
        try:
            # 使用东方财富实时行情（通过 AkShare）
            df = self.ak.stock_zh_a_spot_em()
            
            if df is None or df.empty:
                return None
            
            row = df[df["代码"] == stock_code]
            if row.empty:
                return None
            
            row = row.iloc[0]
            return {
                "ts_code": ts_code,
                "name": row.get("名称", ""),
                "price": float(row.get("最新价", 0)),
                "change": float(row.get("涨跌幅", 0)),
                "volume": float(row.get("成交量", 0)),
                "amount": float(row.get("成交额", 0)),
                "high": float(row.get("最高", 0)),
                "low": float(row.get("最低", 0)),
                "open": float(row.get("今开", 0)),
                "pre_close": float(row.get("昨收", 0)),
            }
        except Exception as e:
            logger.error(f"获取实时行情失败: {e}")
            return None
    
    def get_money_flow(self, ts_code: str) -> Optional[dict]:
        """获取资金流向
        
        Args:
            ts_code: 股票代码
            
        Returns:
            资金流向数据
        """
        stock_code = ts_code.split(".")[0]
        
        try:
            df = self.ak.stock_individual_fund_flow(stock=stock_code, market="sh" if ts_code.endswith(".SH") else "sz")
            
            if df is None or df.empty:
                return None
            
            latest = df.iloc[-1]
            return {
                "ts_code": ts_code,
                "date": str(latest.get("日期", "")),
                "main_net_inflow": float(latest.get("主力净流入-净额", 0)),
                "small_net_inflow": float(latest.get("小单净流入-净额", 0)),
                "medium_net_inflow": float(latest.get("中单净流入-净额", 0)),
                "large_net_inflow": float(latest.get("大单净流入-净额", 0)),
                "super_large_net_inflow": float(latest.get("超大单净流入-净额", 0)),
            }
        except Exception as e:
            logger.error(f"获取资金流向失败: {e}")
            return None
    
    def get_sector_flow(self) -> pd.DataFrame:
        """获取板块资金流向
        
        Returns:
            板块资金流向 DataFrame
        """
        try:
            df = self.ak.stock_sector_fund_flow_rank(indicator="今日")
            logger.info(f"获取板块资金流向: {len(df)} 条")
            return df
        except Exception as e:
            logger.error(f"获取板块资金流向失败: {e}")
            return pd.DataFrame()
    
    def get_hot_stocks(self) -> pd.DataFrame:
        """获取热门股票/人气榜
        
        Returns:
            热门股票 DataFrame
        """
        try:
            df = self.ak.stock_hot_rank_em()
            logger.info(f"获取热门股票: {len(df)} 条")
            return df
        except Exception as e:
            logger.error(f"获取热门股票失败: {e}")
            return pd.DataFrame()
    
    def get_dragon_tiger_list(self, trade_date: Optional[str] = None) -> pd.DataFrame:
        """获取龙虎榜数据
        
        Args:
            trade_date: 交易日期 (YYYYMMDD)，默认最新
            
        Returns:
            龙虎榜数据 DataFrame
        """
        try:
            if trade_date:
                df = self.ak.stock_lhb_detail_em(start_date=trade_date, end_date=trade_date)
            else:
                df = self.ak.stock_lhb_detail_em()
            logger.info(f"获取龙虎榜: {len(df)} 条")
            return df
        except Exception as e:
            logger.error(f"获取龙虎榜失败: {e}")
            return pd.DataFrame()
    
    def get_daily_data(
        self,
        ts_code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> pd.DataFrame:
        """获取历史日线数据
        
        Args:
            ts_code: 股票代码
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
            
        Returns:
            日线数据 DataFrame
        """
        stock_code = ts_code.split(".")[0]
        
        try:
            df = self.ak.stock_zh_a_hist(
                symbol=stock_code,
                period="daily",
                start_date=start_date or "20200101",
                end_date=end_date or datetime.now().strftime("%Y%m%d"),
                adjust="qfq",  # 前复权
            )
            
            if df is not None and not df.empty:
                # 重命名列以匹配 Tushare 格式
                df = df.rename(columns={
                    "日期": "trade_date",
                    "开盘": "open",
                    "收盘": "close",
                    "最高": "high",
                    "最低": "low",
                    "成交量": "vol",
                    "成交额": "amount",
                    "涨跌幅": "pct_chg",
                })
                df["ts_code"] = ts_code
                
            logger.info(f"获取日线数据 {ts_code}: {len(df)} 条")
            return df
        except Exception as e:
            logger.error(f"获取日线数据失败: {e}")
            return pd.DataFrame()
    
    def get_batch_quotes(self, ts_codes: list[str]) -> dict[str, float]:
        """批量获取实时价格
        
        Args:
            ts_codes: 股票代码列表
            
        Returns:
            {ts_code: current_price}
        """
        prices = {}
        
        try:
            df = self.ak.stock_zh_a_spot_em()
            
            if df is None or df.empty:
                return prices
            
            for ts_code in ts_codes:
                stock_code = ts_code.split(".")[0]
                row = df[df["代码"] == stock_code]
                if not row.empty:
                    prices[ts_code] = float(row.iloc[0].get("最新价", 0))
                    
        except Exception as e:
            logger.error(f"批量获取价格失败: {e}")
        
        return prices
    
    def get_stock_info(self, ts_code: str) -> dict:
        """获取个股基本信息 (使用东方财富接口)
        
        Args:
            ts_code: 股票代码
            
        Returns:
            股票基本信息字典
        """
        stock_code = ts_code.split(".")[0]
        try:
            df = self.ak.stock_individual_info_em(symbol=stock_code)
            info = {}
            for _, row in df.iterrows():
                key = row["item"]
                val = row["value"]
                info[key] = val
            
            return {
                "ts_code": ts_code,
                "name": info.get("股票简称", ""),
                "industry": info.get("行业", ""),
                "total_mv": float(info.get("总市值", 0)),
                "circ_mv": float(info.get("流通市值", 0)),
                "pe": info.get("市盈率", None),  # 需注意字段名可能不同
                "list_date": str(info.get("上市时间", "")),
            }
        except Exception as e:
            logger.error(f"获取个股及信息失败: {e}")
            return {}

    def get_5_levels_quote(self, ts_code: str) -> dict:
        """获取五档行情
        
        Args:
            ts_code: 股票代码
            
        Returns:
            五档行情字典
        """
        stock_code = ts_code.split(".")[0]
        try:
            df = self.ak.stock_bid_ask_em(symbol=stock_code)
            if df is None or df.empty:
                return {}
            
            data = {}
            for _, row in df.iterrows():
                key = row["item"]
                val = row["value"]
                data[key] = val
                
            return data
        except Exception as e:
            logger.error(f"获取五档行情失败: {e}")
            return {}

    def get_index_spot(self) -> pd.DataFrame:
        """获取大盘指数实时行情
        
        Returns:
            指数行情 DataFrame
        """
        try:
            # 获取所有 A 股指数实时行情
            df = self.ak.stock_zh_index_spot_em()
            logger.info(f"获取指数行情: {len(df)} 条")
            return df
        except Exception as e:
            logger.error(f"获取指数行情失败: {e}")
            return pd.DataFrame()

    def get_sector_index(self) -> pd.DataFrame:
        """获取行业板块行情
        
        Returns:
            行业板块行情 DataFrame
        """
        try:
            df = self.ak.stock_board_industry_name_em()
            logger.info(f"获取行业板块: {len(df)} 条")
            return df
        except Exception as e:
            logger.error(f"获取行业板块失败: {e}")
            return pd.DataFrame()

    def get_north_flow(self) -> Optional[dict]:
        """获取北向资金流向
        
        Returns:
            北向资金数据
        """
        try:
            df = self.ak.stock_hsgt_north_net_flow_in_em()
            if df is None or df.empty:
                return None
                
            latest = df.iloc[-1]
            return {
                "date": str(latest.get("date", "")),
                "value": float(latest.get("value", 0)),  # 单位：万元
            }
        except Exception as e:
            logger.error(f"获取北向资金失败: {e}")
            return None

    def format_for_llm(self, data: dict) -> str:
        """格式化数据供 LLM 分析"""
        if not data:
            return "暂无数据"
        
        lines = []
        for key, value in data.items():
            if isinstance(value, float):
                lines.append(f"- {key}: {value:.2f}")
            else:
                lines.append(f"- {key}: {value}")
        
        return "\n".join(lines)

    # ==================== 消息面数据（优先级最高）====================
    
    def get_stock_news(self, ts_code: str, limit: int = 10) -> list[dict]:
        """获取个股新闻
        
        Args:
            ts_code: 股票代码
            limit: 返回条数
            
        Returns:
            新闻列表
        """
        stock_code = ts_code.split(".")[0]
        try:
            df = self.ak.stock_news_em(symbol=stock_code)
            if df is None or df.empty:
                return []
            
            news_list = []
            for _, row in df.head(limit).iterrows():
                news_list.append({
                    "title": row.get("新闻标题", ""),
                    "content": row.get("新闻内容", "")[:200],  # 截取前200字
                    "source": row.get("文章来源", ""),
                    "time": row.get("发布时间", ""),
                })
            logger.info(f"获取个股新闻 {ts_code}: {len(news_list)} 条")
            return news_list
        except Exception as e:
            logger.error(f"获取个股新闻失败: {e}")
            return []
    
    def get_stock_yjyg(self, date: str = None) -> pd.DataFrame:
        """获取业绩预告
        
        Args:
            date: 报告期，如 20241231
            
        Returns:
            业绩预告 DataFrame
        """
        try:
            if date is None:
                date = datetime.now().strftime("%Y") + "1231"
            df = self.ak.stock_yjyg_em(date=date)
            logger.info(f"获取业绩预告: {len(df)} 条")
            return df
        except Exception as e:
            logger.error(f"获取业绩预告失败: {e}")
            return pd.DataFrame()
    
    def get_restricted_release(self, ts_code: str) -> pd.DataFrame:
        """获取限售解禁数据
        
        Args:
            ts_code: 股票代码
            
        Returns:
            限售解禁 DataFrame
        """
        stock_code = ts_code.split(".")[0]
        try:
            df = self.ak.stock_restricted_release_queue_sina(symbol=stock_code)
            logger.info(f"获取限售解禁 {ts_code}: {len(df)} 条")
            return df
        except Exception as e:
            logger.error(f"获取限售解禁失败: {e}")
            return pd.DataFrame()

    # ==================== 基本面数据 ====================
    
    def get_financial_abstract(self, ts_code: str) -> pd.DataFrame:
        """获取财务摘要
        
        Args:
            ts_code: 股票代码
            
        Returns:
            财务摘要 DataFrame
        """
        stock_code = ts_code.split(".")[0]
        try:
            df = self.ak.stock_financial_abstract(symbol=stock_code)
            logger.info(f"获取财务摘要 {ts_code}")
            return df
        except Exception as e:
            logger.error(f"获取财务摘要失败: {e}")
            return pd.DataFrame()
    
    def get_valuation_indicator(self, ts_code: str) -> dict:
        """获取估值指标（PE/PB等）
        
        Args:
            ts_code: 股票代码
            
        Returns:
            估值指标字典
        """
        stock_code = ts_code.split(".")[0]
        try:
            df = self.ak.stock_a_indicator_lg(symbol=stock_code)
            if df is None or df.empty:
                return {}
            
            latest = df.iloc[-1]
            return {
                "trade_date": str(latest.get("trade_date", "")),
                "pe": float(latest.get("pe", 0)) if latest.get("pe") else None,
                "pe_ttm": float(latest.get("pe_ttm", 0)) if latest.get("pe_ttm") else None,
                "pb": float(latest.get("pb", 0)) if latest.get("pb") else None,
                "ps": float(latest.get("ps", 0)) if latest.get("ps") else None,
                "dv_ratio": float(latest.get("dv_ratio", 0)) if latest.get("dv_ratio") else None,
                "total_mv": float(latest.get("total_mv", 0)) if latest.get("total_mv") else None,
            }
        except Exception as e:
            logger.error(f"获取估值指标失败: {e}")
            return {}
    
    def get_main_holders(self, ts_code: str) -> pd.DataFrame:
        """获取主要股东信息
        
        Args:
            ts_code: 股票代码
            
        Returns:
            主要股东 DataFrame
        """
        stock_code = ts_code.split(".")[0]
        try:
            df = self.ak.stock_main_stock_holder(stock=stock_code)
            logger.info(f"获取主要股东 {ts_code}")
            return df
        except Exception as e:
            logger.error(f"获取主要股东失败: {e}")
            return pd.DataFrame()

    # ==================== 宏观数据 ====================
    
    def get_shibor(self, indicator: str = "隔夜") -> dict:
        """获取 Shibor 利率
        
        Args:
            indicator: 期限，如 "隔夜", "1周", "1月", "3月"
            
        Returns:
            Shibor 数据
        """
        try:
            df = self.ak.rate_interbank(
                market="上海银行同业拆借市场",
                symbol="Shibor人民币",
                indicator=indicator
            )
            if df is None or df.empty:
                return {}
            
            latest = df.iloc[-1]
            return {
                "date": str(latest.get("报告日", "")),
                "rate": float(latest.get("利率", 0)),
                "change": float(latest.get("涨跌", 0)),
                "indicator": indicator,
            }
        except Exception as e:
            logger.error(f"获取 Shibor 失败: {e}")
            return {}
    
    def get_shibor_all(self) -> dict:
        """获取所有期限的 Shibor 利率"""
        indicators = ["隔夜", "1周", "1月", "3月"]
        result = {}
        for ind in indicators:
            data = self.get_shibor(indicator=ind)
            if data:
                result[ind] = data.get("rate", 0)
        return result

    # ==================== 涨停跌停数据 ====================
    
    def get_zt_pool(self, trade_date: str = None) -> pd.DataFrame:
        """获取涨停板数据
        
        Args:
            trade_date: 交易日期 (YYYYMMDD)
            
        Returns:
            涨停板 DataFrame
        """
        try:
            if trade_date is None:
                trade_date = datetime.now().strftime("%Y%m%d")
            df = self.ak.stock_zt_pool_em(date=trade_date)
            logger.info(f"获取涨停板: {len(df)} 只")
            return df
        except Exception as e:
            logger.error(f"获取涨停板失败: {e}")
            return pd.DataFrame()
    
    def get_hot_rank(self) -> pd.DataFrame:
        """获取热门股票排行
        
        Returns:
            热门股票 DataFrame
        """
        try:
            df = self.ak.stock_hot_rank_em()
            logger.info(f"获取热门股票: {len(df)} 只")
            return df
        except Exception as e:
            logger.error(f"获取热门股票失败: {e}")
            return pd.DataFrame()

    # ==================== 研报数据 ====================
    
    def get_research_report(self, ts_code: str) -> pd.DataFrame:
        """获取个股研报
        
        Args:
            ts_code: 股票代码
            
        Returns:
            研报 DataFrame
        """
        stock_code = ts_code.split(".")[0]
        try:
            df = self.ak.stock_research_report_em(symbol=stock_code)
            logger.info(f"获取研报 {ts_code}: {len(df)} 条")
            return df
        except Exception as e:
            logger.error(f"获取研报失败: {e}")
            return pd.DataFrame()

