"""QuantumAlpha 主入口"""

import asyncio
import os
import sys

# 确保从项目根目录加载 .env
from pathlib import Path
from dotenv import load_dotenv

# 加载 .env 配置
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

from loguru import logger

from src.config import get_settings


def configure_logging():
    """配置日志"""
    settings = get_settings()
    
    # 移除默认处理器
    logger.remove()
    
    # 添加控制台输出
    logger.add(
        sys.stderr,
        level=settings.log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
               "<level>{level: <8}</level> | "
               "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
               "<level>{message}</level>",
    )
    
    # 添加文件输出
    logger.add(
        "logs/quantumalpha_{time:YYYY-MM-DD}.log",
        level="DEBUG",
        rotation="00:00",
        retention="30 days",
        encoding="utf-8",
    )


async def run_demo():
    """运行演示"""
    from src.ai.llm import get_default_llm
    from src.data.sources.tushare_client import get_tushare_client
    
    logger.info("=" * 50)
    logger.info("QuantumAlpha 系统演示")
    logger.info("=" * 50)
    
    # 测试 LLM 连接
    logger.info("\n[1] 测试 LLM 连接...")
    try:
        llm = get_default_llm()
        response = await llm.generate(
            prompt="请用一句话介绍什么是量化交易？",
            system_prompt="你是一个金融助手，回答要简洁。",
        )
        logger.info(f"LLM 响应: {response[:100]}...")
        logger.info("✅ LLM 连接成功")
    except Exception as e:
        logger.error(f"❌ LLM 连接失败: {e}")
    
    # 测试 Tushare 连接
    logger.info("\n[2] 测试 Tushare 连接...")
    try:
        client = get_tushare_client()
        df = client.get_index_daily(ts_code="000001.SH", start_date="20260110", end_date="20260112")
        if not df.empty:
            logger.info(f"获取到 {len(df)} 条上证指数数据")
            logger.info(f"最新收盘价: {df.iloc[0]['close']}")
        logger.info("✅ Tushare 连接成功")
    except Exception as e:
        logger.error(f"❌ Tushare 连接失败: {e}")
    
    # 测试技术指标计算
    logger.info("\n[3] 测试技术指标计算...")
    try:
        from src.analysis.technical import TechnicalIndicators, SignalDetector
        import pandas as pd
        
        # 使用真实数据
        if 'df' in dir() or 'client' in dir():
            df = client.get_daily(ts_code="000001.SZ", start_date="20251101", end_date="20260112")
            if not df.empty:
                df = df.sort_values("trade_date")
                
                indicators = TechnicalIndicators(df)
                summary = indicators.get_summary()
                
                logger.info(f"MACD 状态: DIF={summary['macd']['dif']:.4f}, 金叉={summary['macd']['golden_cross']}")
                logger.info(f"KDJ 状态: J={summary['kdj']['j']:.2f}, 超卖={summary['kdj']['oversold']}")
                
                detector = SignalDetector(df)
                signal = detector.detect()
                logger.info(f"综合信号: {signal.direction.value.upper()}, 评分: {signal.score}")
                
        logger.info("✅ 技术指标计算成功")
    except Exception as e:
        logger.error(f"❌ 技术指标计算失败: {e}")
    
    logger.info("\n" + "=" * 50)
    logger.info("演示完成！使用 'uvicorn src.api.main:app --reload' 启动 API 服务")
    logger.info("=" * 50)


def main():
    """主入口"""
    configure_logging()
    
    settings = get_settings()
    logger.info(f"QuantumAlpha 启动，LLM 提供商: {settings.default_llm_provider.value}")
    
    # 运行演示
    asyncio.run(run_demo())


if __name__ == "__main__":
    main()
