"""技术指标测试"""

import sys
sys.path.insert(0, "/Users/dxx/Coding/stock_trading")

import pandas as pd
import numpy as np

from src.analysis.technical import TechnicalIndicators, PatternRecognizer, SignalDetector


def create_sample_data(days: int = 60) -> pd.DataFrame:
    """创建模拟数据"""
    np.random.seed(42)
    
    # 生成随机价格数据（上涨趋势）
    base_price = 10.0
    returns = np.random.randn(days) * 0.02 + 0.001  # 轻微上涨趋势
    prices = base_price * np.exp(np.cumsum(returns))
    
    # 生成 OHLCV
    data = {
        "open": prices * (1 + np.random.randn(days) * 0.005),
        "high": prices * (1 + np.abs(np.random.randn(days) * 0.01)),
        "low": prices * (1 - np.abs(np.random.randn(days) * 0.01)),
        "close": prices,
        "volume": np.random.randint(1000000, 10000000, days),
    }
    
    return pd.DataFrame(data)


def test_indicators():
    """测试技术指标"""
    print("\n" + "=" * 50)
    print("测试技术指标计算")
    print("=" * 50)
    
    df = create_sample_data()
    indicators = TechnicalIndicators(df)
    
    # MACD
    macd = indicators.macd()
    print(f"\nMACD:")
    print(f"  DIF: {macd.macd.iloc[-1]:.4f}")
    print(f"  DEA: {macd.signal.iloc[-1]:.4f}")
    print(f"  金叉: {macd.is_golden_cross}")
    print(f"  零轴上方: {macd.is_above_zero}")
    
    # KDJ
    kdj = indicators.kdj()
    print(f"\nKDJ:")
    print(f"  K: {kdj.k.iloc[-1]:.2f}")
    print(f"  D: {kdj.d.iloc[-1]:.2f}")
    print(f"  J: {kdj.j.iloc[-1]:.2f}")
    print(f"  金叉: {kdj.is_golden_cross}")
    
    # 均线
    sma = indicators.sma()
    print(f"\n均线:")
    for period, values in sma.items():
        print(f"  SMA{period}: {values.iloc[-1]:.2f}")
    
    print(f"\n多头排列: {indicators.is_bullish_alignment()}")
    print(f"空头排列: {indicators.is_bearish_alignment()}")
    
    # 综合摘要
    summary = indicators.get_summary()
    print(f"\n量比: {summary['volume']['ratio']:.2f}")
    print(f"支撑位: {summary['levels']['supports']}")
    print(f"阻力位: {summary['levels']['resistances']}")
    
    print("\n✅ 技术指标测试通过")


def test_patterns():
    """测试 K 线形态识别"""
    print("\n" + "=" * 50)
    print("测试 K 线形态识别")
    print("=" * 50)
    
    # 创建包含早晨之星形态的数据
    data = {
        "open":  [10.0, 9.2, 9.0, 9.3, 9.8],
        "high":  [10.1, 9.3, 9.1, 9.8, 10.2],
        "low":   [9.0, 9.0, 8.9, 9.0, 9.3],
        "close": [9.1, 9.0, 9.0, 9.7, 10.0],
        "volume": [1000000] * 5,
    }
    df = pd.DataFrame(data)
    
    recognizer = PatternRecognizer(df)
    
    # 扫描所有形态
    patterns = recognizer.scan_all_patterns()
    
    print(f"\n识别到 {len(patterns)} 个形态:")
    for p in patterns:
        print(f"  - {p.name} ({p.name_en}): {p.pattern_type.value}, 置信度: {p.confidence:.2f}")
    
    # 测试连续阳线
    yang_data = {
        "open":  [10.0, 10.5, 11.0, 11.5, 12.0],
        "high":  [10.6, 11.1, 11.6, 12.1, 12.6],
        "low":   [9.9, 10.4, 10.9, 11.4, 11.9],
        "close": [10.5, 11.0, 11.5, 12.0, 12.5],
        "volume": [1000000] * 5,
    }
    df_yang = pd.DataFrame(yang_data)
    
    recognizer_yang = PatternRecognizer(df_yang)
    yang_patterns = recognizer_yang.scan_all_patterns()
    
    print(f"\n连续阳线测试:")
    for p in yang_patterns:
        print(f"  - {p.name}: {p.description}")
    
    print("\n✅ K 线形态测试通过")


def test_signals():
    """测试信号检测"""
    print("\n" + "=" * 50)
    print("测试综合信号检测")
    print("=" * 50)
    
    df = create_sample_data(100)
    detector = SignalDetector(df)
    
    signal = detector.detect()
    
    print(f"\n综合信号:")
    print(f"  方向: {signal.direction.value.upper()}")
    print(f"  强度: {signal.strength.value}")
    print(f"  评分: {signal.score}")
    
    print(f"\n信号理由:")
    for reason in signal.reasons:
        print(f"  - {reason}")
    
    # 共振状态
    resonance = detector.get_resonance_status()
    print(f"\n共振状态:")
    print(f"  MACD 多头: {resonance['macd']['bullish']}")
    print(f"  KDJ 多头: {resonance['kdj']['bullish']}")
    print(f"  均线多头: {resonance['ma']['bullish']}")
    print(f"  多头共振: {resonance['resonance']['is_bullish_resonance']}")
    
    print("\n✅ 信号检测测试通过")


def main():
    """运行所有测试"""
    print("\n🚀 开始技术分析测试\n")
    
    test_indicators()
    test_patterns()
    test_signals()
    
    print("\n" + "=" * 50)
    print("🎉 所有技术分析测试通过！")
    print("=" * 50)


if __name__ == "__main__":
    main()
