"""Deep Dive Diagnostic - 个股深度诊疗模块

实现：
- 个股多维度分析
- 多因子评分
- Buy/Hold/Sell 评级
- 支撑阻力位计算
- 情景推演
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from loguru import logger

from src.ai.llm import get_default_llm, LLMMessage
from src.ai.llm.base import MessageRole
from src.ai.llm.prompts import DEEP_DIVE_TEMPLATE, render_prompt
from src.analysis.technical import TechnicalIndicators, SignalDetector
from src.data.sources.factory import get_data_source


@dataclass
class StockInfo:
    """股票基本信息"""
    ts_code: str          # 股票代码
    name: str             # 股票名称
    industry: str         # 所属行业
    market: str = ""      # 市场（主板/创业板等）
    list_date: str = ""   # 上市日期


@dataclass
class DiagnosticReport:
    """诊疗报告"""
    stock: StockInfo
    content: str
    technical_summary: dict
    signal: dict
    generated_at: datetime


class DeepDiveDiagnostic:
    """个股深度诊疗引擎"""
    
    def __init__(self):
        """初始化引擎"""
        self.llm = None
        self.data_source = None
    
    def _ensure_initialized(self):
        """确保组件已初始化"""
        if self.llm is None:
            self.llm = get_default_llm()
        if self.data_source is None:
            self.data_source = get_data_source()
    
    async def get_stock_info(self, ts_code: str) -> Optional[StockInfo]:
        """获取股票基本信息
        
        Args:
            ts_code: 股票代码（如 000001.SZ）
            
        Returns:
            StockInfo 对象
        """
        self._ensure_initialized()
        
        try:
            # 使用统一数据源获取股票信息
            info = self.data_source.get_stock_info(ts_code)
            if info:
                return StockInfo(
                    ts_code=info.get('ts_code', ts_code),
                    name=info.get('name', '未知'),
                    industry=info.get('industry', '未知'),
                    market=info.get('market', ''),
                    list_date=info.get('list_date', ''),
                )
            
            # 如果获取失败，尝试从股票列表中查找
            df = self.data_source.get_stock_list()
            if not df.empty:
                stock = df[df["ts_code"] == ts_code]
                if not stock.empty:
                    row = stock.iloc[0]
                    return StockInfo(
                        ts_code=row.get("ts_code", ts_code),
                        name=row.get("name", "未知"),
                        industry=row.get("industry", "未知"),
                        market=row.get("market", ""),
                        list_date=row.get("list_date", ""),
                    )
            
            logger.warning(f"未找到股票: {ts_code}")
            return None
            
        except Exception as e:
            logger.error(f"获取股票信息失败: {e}")
            return None
    
    async def collect_stock_data(
        self,
        ts_code: str,
        lookback_days: int = 120,
    ) -> dict:
        """采集个股数据
        
        Args:
            ts_code: 股票代码
            lookback_days: 回看天数
            
        Returns:
            数据字典
        """
        import asyncio
        # 使用线程池运行同步代码
        return await asyncio.to_thread(
            self._collect_stock_data_sync, ts_code, lookback_days
        )
    
    def _collect_stock_data_sync(
        self,
        ts_code: str,
        lookback_days: int = 120,
    ) -> dict:
        """同步采集个股数据"""
        self._ensure_initialized()
        
        from datetime import date, timedelta
        
        end_date = date.today().strftime("%Y%m%d")
        start_date = (date.today() - timedelta(days=lookback_days)).strftime("%Y%m%d")
        
        data = {
            "daily": None,
            "daily_basic": None,
            "technical": None,
            "signal": None,
        }
        
        try:
            # 日线数据
            data["daily"] = self.data_source.get_daily_data(
                ts_code=ts_code,
                start_date=start_date,
                end_date=end_date,
            )
            
            # 基本面数据
            if self.data_source.is_tushare:
                # Tushare 模式
                data["daily_basic"] = self.data_source._tushare.get_daily_basic(
                    ts_code=ts_code,
                    trade_date=end_date,
                )
            elif self.data_source.is_akshare:
                # AkShare 模式 - 获取更丰富的数据
                from src.data.sources.ths_client import THSClient
                ths = THSClient()
                
                stock_code = ts_code.split(".")[0]
                market = "sz" if ts_code.endswith(".SZ") else "sh"
                
                # 获取财务摘要
                try:
                    financial = ths.get_financial_abstract(ts_code)
                    if financial is not None and not financial.empty:
                        data["financial_abstract"] = financial
                except Exception as e:
                    logger.warning(f"获取财务摘要失败: {e}")
                
                # 获取个股新闻
                try:
                    news = ths.get_stock_news(ts_code, limit=5)
                    if news:
                        data["news"] = news
                except Exception as e:
                    logger.warning(f"获取个股新闻失败: {e}")
                
                # 获取资金流向
                try:
                    flow = ths.ak.stock_individual_fund_flow(stock=stock_code, market=market)
                    if flow is not None and not flow.empty:
                        data["fund_flow"] = flow.tail(5)
                except Exception as e:
                    logger.warning(f"获取资金流向失败: {e}")
                
                # 获取估值指标
                try:
                    indicator = ths.ak.stock_a_indicator_lg(symbol=stock_code)
                    if indicator is not None and not indicator.empty:
                        data["valuation"] = indicator.tail(1)
                except Exception as e:
                    logger.warning(f"获取估值指标失败: {e}")
                
                # 获取历史价格统计（用于技术分析）
                if data["daily"] is not None and not data["daily"].empty:
                    df = data["daily"]
                    try:
                        # 计算历史价格区间
                        data["price_stats"] = {
                            "high_52w": df["high"].max() if "high" in df.columns else None,
                            "low_52w": df["low"].min() if "low" in df.columns else None,
                            "avg_volume": df["vol"].mean() if "vol" in df.columns else None,
                            "current_close": df["close"].iloc[-1] if "close" in df.columns and len(df) > 0 else None,
                        }
                    except Exception as e:
                        logger.warning(f"计算价格统计失败: {e}")
                
                # 获取公司公告（限售解禁等）
                try:
                    announcements = ths.get_restrict_stock_release(ts_code)
                    if announcements is not None and not announcements.empty:
                        data["announcements"] = announcements.head(5)
                except Exception as e:
                    logger.warning(f"获取公告信息失败: {e}")
                
                # 获取所属行业及行业排名
                try:
                    industry_info = ths.ak.stock_board_industry_cons_em()
                    if industry_info is not None:
                        matched = industry_info[industry_info["代码"] == stock_code]
                        if not matched.empty:
                            data["industry_info"] = matched.iloc[0].to_dict()
                except Exception as e:
                    logger.warning(f"获取行业信息失败: {e}")
            
            # 技术指标分析
            if data["daily"] is not None and not data["daily"].empty:
                # 按日期排序（升序）
                df = data["daily"].sort_values("trade_date").reset_index(drop=True)
                
                indicators = TechnicalIndicators(df)
                data["technical"] = indicators.get_summary()
                
                detector = SignalDetector(df)
                data["signal"] = detector.detect().to_dict()
            
        except Exception as e:
            logger.error(f"采集个股数据失败: {e}")
        
        return data
    
    def format_fundamental_data(self, data: dict) -> str:
        """格式化基本面数据"""
        result = []
        
        # Tushare 基本面数据
        basic = data.get("daily_basic")
        if basic is not None and not basic.empty:
            row = basic.iloc[0]
            result.append("### Tushare 基本面")
            result.append("| 指标 | 数值 |")
            result.append("|------|------|")
            result.append(f"| 收盘价 | {row.get('close', 'N/A')} |")
            result.append(f"| 市盈率 (PE-TTM) | {row.get('pe_ttm', 'N/A'):.2f} |")
            result.append(f"| 市净率 (PB) | {row.get('pb', 'N/A'):.2f} |")
            result.append(f"| 市销率 (PS-TTM) | {row.get('ps_ttm', 'N/A'):.2f} |")
            result.append(f"| 股息率 | {row.get('dv_ratio', 'N/A'):.2f}% |")
            result.append(f"| 换手率 | {row.get('turnover_rate', 'N/A'):.2f}% |")
            result.append(f"| 总市值 | {row.get('total_mv', 0) / 10000:.2f} 亿 |")
            result.append(f"| 流通市值 | {row.get('circ_mv', 0) / 10000:.2f} 亿 |")
        
        # AkShare 财务摘要
        financial = data.get("financial_abstract")
        if financial is not None and not financial.empty:
            result.append("\n### 财务摘要")
            result.append(financial.head(5).to_markdown(index=False))
        
        # AkShare 估值指标
        valuation = data.get("valuation")
        if valuation is not None and not valuation.empty:
            result.append("\n### 估值指标")
            result.append(valuation.to_markdown(index=False))
        
        # 资金流向
        fund_flow = data.get("fund_flow")
        if fund_flow is not None and not fund_flow.empty:
            result.append("\n### 近期资金流向")
            result.append(fund_flow.to_markdown(index=False))
        
        # 历史价格统计
        price_stats = data.get("price_stats")
        if price_stats:
            result.append("\n### 历史价格统计")
            result.append("| 指标 | 数值 |")
            result.append("|------|------|")
            if price_stats.get("high_52w"):
                result.append(f"| 52周最高价 | {price_stats['high_52w']:.2f} |")
            if price_stats.get("low_52w"):
                result.append(f"| 52周最低价 | {price_stats['low_52w']:.2f} |")
            if price_stats.get("avg_volume"):
                result.append(f"| 平均成交量 | {price_stats['avg_volume']/10000:.0f} 万手 |")
            if price_stats.get("current_close"):
                result.append(f"| 当前收盘价 | {price_stats['current_close']:.2f} |")
        
        # 公告/解禁信息
        announcements = data.get("announcements")
        if announcements is not None and not announcements.empty:
            result.append("\n### 近期公告/解禁")
            result.append(announcements.to_markdown(index=False))
        
        # 行业信息
        industry_info = data.get("industry_info")
        if industry_info:
            result.append("\n### 所属行业")
            result.append(f"- 行业板块: {industry_info.get('板块名称', 'N/A')}")
        
        # 新闻
        news = data.get("news")
        if news:
            result.append("\n### 最新新闻")
            for item in news[:3]:
                title = item.get("title", "")
                date = item.get("datetime", "")
                result.append(f"- [{date}] {title}")
        
        if not result:
            return "暂无基本面数据"
        
        return "\n".join(result)
    
    def format_technical_data(self, data: dict) -> str:
        """格式化技术面数据"""
        tech = data.get("technical")
        if tech is None:
            return "暂无技术面数据"
        
        macd = tech.get("macd", {})
        kdj = tech.get("kdj", {})
        ma = tech.get("ma_alignment", {})
        levels = tech.get("levels", {})
        
        return f"""
### MACD 状态
- DIF: {macd.get('dif', 'N/A')}
- DEA: {macd.get('dea', 'N/A')}
- 柱状图: {macd.get('histogram', 'N/A')}
- 金叉: {'是' if macd.get('golden_cross') else '否'}
- 零轴上方: {'是' if macd.get('above_zero') else '否'}

### KDJ 状态
- K: {kdj.get('k', 'N/A')}
- D: {kdj.get('d', 'N/A')}
- J: {kdj.get('j', 'N/A')}
- 金叉: {'是' if kdj.get('golden_cross') else '否'}
- 超买: {'是' if kdj.get('overbought') else '否'}
- 超卖: {'是' if kdj.get('oversold') else '否'}

### 均线状态
- 多头排列: {'是' if ma.get('bullish') else '否'}
- 空头排列: {'是' if ma.get('bearish') else '否'}

### 关键价位
- 支撑位: {levels.get('supports', [])}
- 阻力位: {levels.get('resistances', [])}
"""
    
    def format_signal_data(self, data: dict) -> str:
        """格式化信号数据"""
        signal = data.get("signal")
        if signal is None:
            return "暂无信号数据"
        
        return f"""
### 综合信号
- 方向: {signal.get('direction', 'N/A').upper()}
- 强度: {signal.get('strength', 'N/A')}
- 评分: {signal.get('score', 'N/A')}

### 信号理由
{chr(10).join(['- ' + r for r in signal.get('reasons', [])])}
"""
    
    async def diagnose(self, ts_code: str) -> Optional[DiagnosticReport]:
        """执行个股诊疗
        
        Args:
            ts_code: 股票代码
            
        Returns:
            诊疗报告
        """
        self._ensure_initialized()
        
        logger.info(f"开始诊疗: {ts_code}")
        
        # 获取股票信息
        stock_info = await self.get_stock_info(ts_code)
        if stock_info is None:
            logger.error(f"无法获取股票信息: {ts_code}")
            return None
        
        # 采集数据
        data = await self.collect_stock_data(ts_code)
        
        # 格式化数据
        fundamental = self.format_fundamental_data(data)
        technical = self.format_technical_data(data)
        capital = self.format_signal_data(data)
        
        # 渲染 Prompt
        prompt = render_prompt(
            DEEP_DIVE_TEMPLATE,
            ts_code=stock_info.ts_code,
            stock_name=stock_info.name,
            industry=stock_info.industry,
            fundamental_data=fundamental,
            technical_data=technical,
            capital_data=capital,
            events_data="（事件数据需要接入公告 API）",
        )
        
        # 调用 LLM
        messages = [
            LLMMessage(role=MessageRole.SYSTEM, content=DEEP_DIVE_TEMPLATE.system_prompt),
            LLMMessage(role=MessageRole.USER, content=prompt),
        ]
        
        response = await self.llm.chat(messages)
        
        report = DiagnosticReport(
            stock=stock_info,
            content=response.content,
            technical_summary=data.get("technical", {}),
            signal=data.get("signal", {}),
            generated_at=datetime.now(),
        )
        
        logger.info(f"诊疗完成: {ts_code} - {stock_info.name}")
        return report
    
    async def quick_scan(self, ts_code: str) -> dict:
        """快速扫描（仅技术面，不调用 LLM）
        
        Args:
            ts_code: 股票代码
            
        Returns:
            技术面扫描结果
        """
        self._ensure_initialized()
        
        stock_info = await self.get_stock_info(ts_code)
        data = await self.collect_stock_data(ts_code, lookback_days=60)
        
        return {
            "ts_code": ts_code,
            "name": stock_info.name if stock_info else "未知",
            "industry": stock_info.industry if stock_info else "未知",
            "technical": data.get("technical", {}),
            "signal": data.get("signal", {}),
        }
