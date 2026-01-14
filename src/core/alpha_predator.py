"""Alpha Predator - 全市场阿尔法捕获模块

实现：
- 每日早盘定时推送
- 用户按需实时查询
- 双阶段时效优化（预处理 + 增量更新）
- 容灾降级方案
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, time as dt_time
from typing import Optional

from loguru import logger

from src.ai.llm import create_llm, LLMMessage, get_default_llm
from src.ai.llm.base import MessageRole
from src.ai.llm.prompts import (
    ALPHA_PREDATOR_TEMPLATE,
    FALLBACK_TEMPLATE,
    INCREMENTAL_UPDATE_TEMPLATE,
    render_prompt,
)
from src.config import get_settings
from src.data.sources.factory import get_data_source
from src.notification.webhook import get_webhook_notifier


@dataclass
class MarketData:
    """市场数据汇总"""
    trade_date: str
    macro_data: str = ""
    index_data: str = ""
    northbound_data: str = ""
    auction_data: str = ""
    news_data: str = ""


@dataclass
class AnalysisReport:
    """分析报告"""
    title: str
    content: str
    trade_date: str
    generated_at: datetime
    is_fallback: bool = False
    stage: str = "full"  # pre / incremental / full / fallback


class AlphaPredator:
    """Alpha Predator 引擎"""
    
    def __init__(self):
        """初始化引擎"""
        self.settings = get_settings()
        self.llm = None
        self.data_source = None
        
        # 解析熔断时间
        cutoff_str = self.settings.fallback_cutoff_time
        parts = [int(p) for p in cutoff_str.split(":")]
        self.cutoff_time = dt_time(*parts)
        
        # 预处理报告缓存
        self._pre_report: Optional[AnalysisReport] = None
    
    def _ensure_initialized(self):
        """确保组件已初始化"""
        if self.llm is None:
            self.llm = get_default_llm()
        if self.data_source is None:
            self.data_source = get_data_source()
    
    async def collect_market_data(self, trade_date: Optional[str] = None) -> MarketData:
        """采集市场数据
        
        Args:
            trade_date: 交易日期（YYYYMMDD），默认今日
            
        Returns:
            MarketData 对象
        """
        self._ensure_initialized()
        
        if trade_date is None:
            trade_date = self.data_source.get_today_str()
        
        logger.info(f"开始采集市场数据: {trade_date}")
        
        data = MarketData(trade_date=trade_date)
        
        try:
            # 1. 获取指数数据
            if self.data_source.is_tushare:
                index_df = self.data_source.get_index_data(
                    ts_code="000001.SH",
                    start_date=trade_date,
                    end_date=trade_date,
                )
                if not index_df.empty:
                    row = index_df.iloc[0]
                    data.index_data = f"""
上证指数:
- 收盘价: {row['close']}
- 涨跌幅: {row['pct_chg']:.2f}%
- 成交量: {row['vol']:.0f} 手
- 成交额: {row['amount']:.0f} 万元
"""
            else:
                # AkShare 使用实时行情
                index_df = self.data_source.get_index_spot()
                if not index_df.empty:
                    sh_row = index_df[index_df['代码'].str.contains('000001|上证', na=False)]
                    if not sh_row.empty:
                        row = sh_row.iloc[0]
                        data.index_data = f"""
上证指数 (实时):
- 最新价: {row.get('最新价', 'N/A')}
- 涨跌幅: {row.get('涨跌幅', 'N/A')}%
- 成交量: {row.get('成交量', 'N/A')} 手
- 成交额: {row.get('成交额', 'N/A')} 元
"""
            
            # 2. 获取 Shibor 数据
            shibor_data = self.data_source.get_shibor(trade_date=trade_date)
            if shibor_data:
                data.macro_data = f"""
Shibor 利率:
- 隔夜: {shibor_data.get('on', 'N/A')}%
- 1周: {shibor_data.get('1w', 'N/A')}%
- 1月: {shibor_data.get('1m', 'N/A')}%
- 3月: {shibor_data.get('3m', 'N/A')}%
"""
            
            # 3. 获取北向资金
            north_data = self.data_source.get_north_flow(trade_date=trade_date)
            if north_data:
                data.northbound_data = f"""
北向资金:
- 沪股通净流入: {north_data.get('north_money', 0):.2f} 亿元
- 深股通净流入: {north_data.get('south_money', 0):.2f} 亿元
"""
            
            # 4. 集合竞价数据（需要更高权限的数据接口，这里用占位符）
            data.auction_data = "（集合竞价数据需要实时数据源接入）"
            
            # 5. 新闻数据（需要新闻 API，这里用占位符）
            data.news_data = "（新闻数据需要新闻源接入）"
            
        except Exception as e:
            logger.error(f"采集市场数据失败: {e}")
        
        return data
    
    async def generate_pre_report(self, data: MarketData) -> AnalysisReport:
        """生成预处理报告（80% 静态框架）
        
        在 9:00-9:15 执行，不包含集合竞价数据。
        
        Args:
            data: 市场数据
            
        Returns:
            预处理报告
        """
        self._ensure_initialized()
        
        logger.info("开始生成预处理报告...")
        
        # 渲染 Prompt
        prompt = render_prompt(
            ALPHA_PREDATOR_TEMPLATE,
            trade_date=data.trade_date,
            macro_data=data.macro_data or "暂无数据",
            index_data=data.index_data or "暂无数据",
            northbound_data=data.northbound_data or "暂无数据",
            auction_data="【预处理阶段】集合竞价数据将在增量更新阶段补充",
            news_data=data.news_data or "暂无重大新闻",
        )
        
        # 调用 LLM
        messages = [
            LLMMessage(role=MessageRole.SYSTEM, content=ALPHA_PREDATOR_TEMPLATE.system_prompt),
            LLMMessage(role=MessageRole.USER, content=prompt),
        ]
        
        response = await self.llm.chat(messages)
        
        report = AnalysisReport(
            title=f"📊 {data.trade_date} A股量化策略预处理报告",
            content=response.content,
            trade_date=data.trade_date,
            generated_at=datetime.now(),
            stage="pre",
        )
        
        # 缓存预处理报告
        self._pre_report = report
        
        logger.info("预处理报告生成完成")
        return report
    
    async def generate_incremental_update(
        self,
        auction_data: dict,
        timeout: float = 30.0,
    ) -> Optional[AnalysisReport]:
        """生成增量更新（基于集合竞价数据）
        
        在 9:25-9:30 执行，快速修正策略建议。
        
        Args:
            auction_data: 集合竞价数据
            timeout: 超时时间（秒）
            
        Returns:
            增量更新报告，超时返回 None
        """
        if self._pre_report is None:
            logger.warning("预处理报告不存在，无法进行增量更新")
            return None
        
        self._ensure_initialized()
        
        logger.info("开始生成增量更新...")
        
        # 渲染增量更新 Prompt
        prompt = render_prompt(
            INCREMENTAL_UPDATE_TEMPLATE,
            pre_report_summary=self._pre_report.content[:500] + "...",
            auction_realtime=str(auction_data),
            open_price=auction_data.get("open_price", "N/A"),
            auction_volume=auction_data.get("volume", "N/A"),
            volume_ratio=auction_data.get("volume_ratio", "N/A"),
            gap_pct=auction_data.get("gap_pct", "N/A"),
        )
        
        messages = [
            LLMMessage(role=MessageRole.SYSTEM, content=INCREMENTAL_UPDATE_TEMPLATE.system_prompt),
            LLMMessage(role=MessageRole.USER, content=prompt),
        ]
        
        try:
            response = await asyncio.wait_for(
                self.llm.chat(messages),
                timeout=timeout,
            )
            
            # 合并预处理报告和增量更新
            full_content = f"""{self._pre_report.content}

---

## 📌 集合竞价增量更新 ({datetime.now().strftime('%H:%M:%S')})

{response.content}
"""
            
            report = AnalysisReport(
                title=f"📊 {self._pre_report.trade_date} A股量化策略报告（完整版）",
                content=full_content,
                trade_date=self._pre_report.trade_date,
                generated_at=datetime.now(),
                stage="full",
            )
            
            logger.info("增量更新完成")
            return report
            
        except asyncio.TimeoutError:
            logger.warning(f"增量更新超时（{timeout}s），触发熔断")
            return None
    
    def generate_fallback_report(self, auction_data: dict) -> AnalysisReport:
        """生成降级报告（规则引擎模式）
        
        当 LLM 超时时，使用硬编码规则生成简单报告。
        
        Args:
            auction_data: 集合竞价数据
            
        Returns:
            降级报告
        """
        logger.warning("执行降级方案：规则引擎模式")
        
        # 构建简单的规则引擎输出
        high_open_list = auction_data.get("high_open_list", "暂无数据")
        sector_inflow = auction_data.get("sector_inflow", "暂无数据")
        northbound = auction_data.get("northbound_summary", "暂无数据")
        
        content = FALLBACK_TEMPLATE.format(
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            high_open_list=high_open_list,
            sector_inflow_top5=sector_inflow,
            northbound_summary=northbound,
        )
        
        return AnalysisReport(
            title="⚠️ 竞价异动快报（规则引擎模式）",
            content=content,
            trade_date=datetime.now().strftime("%Y%m%d"),
            generated_at=datetime.now(),
            is_fallback=True,
            stage="fallback",
        )
    
    async def run_morning_pipeline(
        self,
        send_notification: bool = True,
    ) -> AnalysisReport:
        """执行早盘完整流水线
        
        自动判断当前时间，执行相应阶段：
        - 9:00-9:15: 预处理阶段
        - 9:25-9:30: 增量更新阶段
        - 超时: 降级方案
        
        Args:
            send_notification: 是否发送通知
            
        Returns:
            最终报告
        """
        now = datetime.now()
        current_time = now.time()
        
        logger.info(f"执行早盘流水线, 当前时间: {now.strftime('%H:%M:%S')}")
        
        # 采集数据
        data = await self.collect_market_data()
        
        # 预处理阶段
        pre_report = await self.generate_pre_report(data)
        
        # 模拟集合竞价数据（实际应从实时数据源获取）
        auction_data = {
            "open_price": "3250.00",
            "volume": "1.5亿",
            "volume_ratio": "1.2",
            "gap_pct": "+0.5%",
            "high_open_list": "- 人工智能板块: 高开 2.3%\n- 稀土永磁: 高开 1.8%",
            "sector_inflow": "1. 科技 +5.2亿\n2. 金融 +3.1亿",
            "northbound_summary": "净流入 12.5 亿元",
        }
        
        # 检查是否需要触发熔断
        if current_time >= self.cutoff_time:
            logger.warning("已超过熔断时间，直接使用规则引擎")
            report = self.generate_fallback_report(auction_data)
        else:
            # 尝试增量更新
            report = await self.generate_incremental_update(auction_data, timeout=30.0)
            if report is None:
                # 超时，使用降级方案
                report = self.generate_fallback_report(auction_data)
        
        # 发送通知
        if send_notification:
            notifier = get_webhook_notifier()
            await notifier.send_all(report.title, report.content[:2000])
        
        return report
    
    async def generate_on_demand(
        self,
        trade_date: Optional[str] = None,
    ) -> AnalysisReport:
        """按需生成分析报告
        
        用户手动触发时调用。
        
        Args:
            trade_date: 交易日期
            
        Returns:
            分析报告
        """
        self._ensure_initialized()
        
        # 采集数据
        data = await self.collect_market_data(trade_date)
        
        # 直接生成完整报告
        prompt = render_prompt(
            ALPHA_PREDATOR_TEMPLATE,
            trade_date=data.trade_date,
            macro_data=data.macro_data or "暂无数据",
            index_data=data.index_data or "暂无数据",
            northbound_data=data.northbound_data or "暂无数据",
            auction_data=data.auction_data or "暂无数据",
            news_data=data.news_data or "暂无重大新闻",
        )
        
        messages = [
            LLMMessage(role=MessageRole.SYSTEM, content=ALPHA_PREDATOR_TEMPLATE.system_prompt),
            LLMMessage(role=MessageRole.USER, content=prompt),
        ]
        
        response = await self.llm.chat(messages)
        
        return AnalysisReport(
            title=f"📊 {data.trade_date} A股量化策略报告",
            content=response.content,
            trade_date=data.trade_date,
            generated_at=datetime.now(),
            stage="full",
        )
    
    async def analyze_sectors(self) -> dict:
        """分析热门板块
        
        Returns:
            结构化的板块分析结果
        """
        import json
        from src.ai.llm.prompts import SECTOR_ANALYSIS_TEMPLATE
        
        self._ensure_initialized()
        
        trade_date = self.data_source.get_today_str()
        logger.info(f"开始板块分析: {trade_date}")
        
        # 采集板块数据
        sector_flow_data = "暂无数据"
        index_data = "暂无数据"
        north_flow_data = "暂无数据"
        concept_data = "暂无数据"
        
        try:
            if self.data_source.is_akshare:
                from src.data.sources.ths_client import THSClient
                ths = THSClient()
                
                # 1. 获取行业板块资金流向排名
                sector_df = self.data_source.get_sector_flow()
                if not sector_df.empty:
                    top_sectors = sector_df.head(15)
                    sector_flow_data = top_sectors.to_string(index=False)
                    logger.info(f"获取板块资金流向: {len(sector_df)} 个板块")
                
                # 2. 获取概念板块涨幅排行
                try:
                    concept_df = ths.ak.stock_board_concept_name_em()
                    if concept_df is not None and not concept_df.empty:
                        concept_data = concept_df.head(15).to_string(index=False)
                        logger.info(f"获取概念板块: {len(concept_df)} 个")
                except Exception as e:
                    logger.warning(f"获取概念板块失败: {e}")
                
                # 3. 获取指数数据
                index_df = self.data_source.get_index_spot()
                if not index_df.empty:
                    index_data = index_df.head(10).to_string(index=False)
                
                # 4. 获取北向资金
                north_data = self.data_source.get_north_flow()
                if north_data:
                    value = north_data.get('value', 0)
                    # 单位转换（可能是万元）
                    if abs(value) > 10000:
                        north_flow_data = f"今日净流入: {value / 10000:.2f} 亿元"
                    else:
                        north_flow_data = f"今日净流入: {value:.2f} 万元"
                    
        except Exception as e:
            logger.error(f"采集板块数据失败: {e}")
        
        # 渲染 Prompt
        prompt = render_prompt(
            SECTOR_ANALYSIS_TEMPLATE,
            trade_date=trade_date,
            sector_flow_data=sector_flow_data,
            index_data=index_data,
            north_flow_data=north_flow_data,
        )
        
        # 追加概念板块数据
        if concept_data != "暂无数据":
            prompt += f"\n\n### 概念板块涨幅排行\n{concept_data}"
        
        # 调用 LLM
        messages = [
            LLMMessage(role=MessageRole.SYSTEM, content=SECTOR_ANALYSIS_TEMPLATE.system_prompt),
            LLMMessage(role=MessageRole.USER, content=prompt),
        ]
        
        try:
            response = await self.llm.chat(messages)
            content = response.content
            
            # 提取 JSON（处理 markdown 代码块）
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            
            result = json.loads(content.strip())
            result["trade_date"] = trade_date
            result["generated_at"] = datetime.now().isoformat()
            
            logger.info("板块分析完成")
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"解析 LLM 输出失败: {e}")
            return {
                "error": "解析失败",
                "raw_content": response.content if response else None,
                "market_summary": "分析结果解析失败，请重试",
                "sectors": [],
            }
    
    async def recommend_stocks(self, selected_sectors: list[str]) -> dict:
        """根据选定板块推荐股票
        
        Args:
            selected_sectors: 用户选择的板块列表
            
        Returns:
            结构化的股票推荐结果
        """
        import json
        from src.ai.llm.prompts import STOCK_RECOMMENDATION_TEMPLATE
        
        self._ensure_initialized()
        
        trade_date = self.data_source.get_today_str()
        logger.info(f"开始股票推荐: {trade_date}, 板块: {selected_sectors}")
        
        # 采集股票数据
        stock_quotes = "暂无数据"
        stock_money_flow = "暂无数据"
        stock_technicals = "暂无数据"
        sector_stock_list = "暂无数据"
        
        try:
            if self.data_source.is_akshare:
                from src.data.sources.ths_client import THSClient
                ths = THSClient()
                
                # 1. 获取板块成分股
                sector_stocks = []
                for sector in selected_sectors:
                    try:
                        # 获取行业板块成分股
                        df = ths.ak.stock_board_industry_cons_em(symbol=sector)
                        if df is not None and not df.empty:
                            sector_stocks.extend(df.head(10).to_dict('records'))
                    except Exception as e:
                        logger.warning(f"获取板块 {sector} 成分股失败: {e}")
                        continue
                
                if sector_stocks:
                    sector_stock_list = str(sector_stocks[:20])
                
                # 2. 获取板块内热门股票行情
                hot_stocks = self.data_source.get_hot_stocks()
                if not hot_stocks.empty:
                    stock_quotes = hot_stocks.head(30).to_string(index=False)
                
                # 3. 获取个股资金流向排行
                try:
                    flow_df = ths.ak.stock_individual_fund_flow_rank(indicator="今日")
                    if flow_df is not None and not flow_df.empty:
                        stock_money_flow = flow_df.head(20).to_string(index=False)
                except Exception as e:
                    logger.warning(f"获取资金流向排行失败: {e}")
                
                # 4. 获取涨停股（技术强势股）
                try:
                    zt_df = ths.get_zt_pool()
                    if zt_df is not None and not zt_df.empty:
                        stock_technicals = f"今日涨停: {len(zt_df)} 只\n" + zt_df.head(10).to_string(index=False)
                except Exception as e:
                    logger.warning(f"获取涨停板数据失败: {e}")
                    
        except Exception as e:
            logger.error(f"采集股票数据失败: {e}")
        
        # 渲染 Prompt
        prompt = render_prompt(
            STOCK_RECOMMENDATION_TEMPLATE,
            trade_date=trade_date,
            selected_sectors=", ".join(selected_sectors),
            stock_quotes=stock_quotes,
            stock_money_flow=stock_money_flow,
            stock_technicals=stock_technicals,
        )
        
        # 在 prompt 中追加板块成分股信息
        if sector_stock_list != "暂无数据":
            prompt += f"\n\n### 板块成分股参考\n{sector_stock_list}"
        
        # 调用 LLM
        messages = [
            LLMMessage(role=MessageRole.SYSTEM, content=STOCK_RECOMMENDATION_TEMPLATE.system_prompt),
            LLMMessage(role=MessageRole.USER, content=prompt),
        ]
        
        try:
            response = await self.llm.chat(messages)
            content = response.content
            
            # 提取 JSON
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            
            result = json.loads(content.strip())
            result["trade_date"] = trade_date
            result["selected_sectors"] = selected_sectors
            result["generated_at"] = datetime.now().isoformat()
            
            logger.info(f"股票推荐完成，共推荐 {len(result.get('recommendations', []))} 只")
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"解析 LLM 输出失败: {e}")
            return {
                "error": "解析失败",
                "raw_content": response.content if response else None,
                "analysis_summary": "分析结果解析失败，请重试",
                "recommendations": [],
            }

