"""技术指标计算模块

基于 ta 库（纯 Python 实现）封装常用技术指标，包括：
- 趋势指标：MACD、EMA、SMA
- 震荡指标：KDJ、RSI、BOLL
- 量价指标：量比、换手率
"""

from dataclasses import dataclass
from typing import Optional, Tuple

import numpy as np
import pandas as pd
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.trend import MACD, EMAIndicator, SMAIndicator
from ta.volatility import BollingerBands


@dataclass
class MACDResult:
    """MACD 计算结果"""
    macd: pd.Series          # MACD 线 (DIF)
    signal: pd.Series        # 信号线 (DEA)
    histogram: pd.Series     # 柱状图 (MACD 柱)
    
    @property
    def is_golden_cross(self) -> bool:
        """是否出现金叉（最近一根 K 线）"""
        if len(self.macd) < 2:
            return False
        # 昨日 DIF < DEA，今日 DIF > DEA
        return (self.macd.iloc[-2] < self.signal.iloc[-2] and 
                self.macd.iloc[-1] > self.signal.iloc[-1])
    
    @property
    def is_death_cross(self) -> bool:
        """是否出现死叉"""
        if len(self.macd) < 2:
            return False
        return (self.macd.iloc[-2] > self.signal.iloc[-2] and 
                self.macd.iloc[-1] < self.signal.iloc[-1])
    
    @property
    def is_above_zero(self) -> bool:
        """MACD 是否在零轴上方"""
        return self.macd.iloc[-1] > 0
    
    @property
    def histogram_expanding(self) -> bool:
        """红柱是否放大"""
        if len(self.histogram) < 2:
            return False
        return (self.histogram.iloc[-1] > 0 and 
                self.histogram.iloc[-1] > self.histogram.iloc[-2])


@dataclass
class KDJResult:
    """KDJ 计算结果"""
    k: pd.Series
    d: pd.Series
    j: pd.Series
    
    @property
    def is_golden_cross(self) -> bool:
        """是否出现金叉"""
        if len(self.k) < 2:
            return False
        return (self.k.iloc[-2] < self.d.iloc[-2] and 
                self.k.iloc[-1] > self.d.iloc[-1])
    
    @property
    def is_death_cross(self) -> bool:
        """是否出现死叉"""
        if len(self.k) < 2:
            return False
        return (self.k.iloc[-2] > self.d.iloc[-2] and 
                self.k.iloc[-1] < self.d.iloc[-1])
    
    @property
    def is_oversold(self) -> bool:
        """是否超卖（J < 20）"""
        return self.j.iloc[-1] < 20
    
    @property
    def is_overbought(self) -> bool:
        """是否超买（J > 80）"""
        return self.j.iloc[-1] > 80
    
    @property
    def is_low_golden_cross(self) -> bool:
        """是否低位金叉（J < 50 时金叉）"""
        return self.is_golden_cross and self.j.iloc[-1] < 50


@dataclass
class BOLLResult:
    """布林带计算结果"""
    upper: pd.Series    # 上轨
    middle: pd.Series   # 中轨
    lower: pd.Series    # 下轨
    
    def get_position(self, price: float) -> str:
        """获取价格在布林带中的位置"""
        upper = self.upper.iloc[-1]
        lower = self.lower.iloc[-1]
        middle = self.middle.iloc[-1]
        
        if price > upper:
            return "above_upper"
        elif price > middle:
            return "upper_half"
        elif price > lower:
            return "lower_half"
        else:
            return "below_lower"


class TechnicalIndicators:
    """技术指标计算器"""
    
    def __init__(self, df: pd.DataFrame):
        """初始化
        
        Args:
            df: 包含 OHLCV 数据的 DataFrame
                必须包含列：open, high, low, close, volume
        """
        self.df = df.copy()
        self._validate_columns()
    
    def _validate_columns(self):
        """验证必要的列是否存在"""
        required = ["open", "high", "low", "close", "volume"]
        # 支持大写列名
        if all(col.upper() in [c.upper() for c in self.df.columns] for col in required):
            # 统一转为小写
            self.df.columns = self.df.columns.str.lower()
        missing = [col for col in required if col not in self.df.columns]
        if missing:
            raise ValueError(f"缺少必要列: {missing}")
    
    def macd(
        self,
        fast: int = 12,
        slow: int = 26,
        signal: int = 9,
    ) -> MACDResult:
        """计算 MACD 指标
        
        Args:
            fast: 快线周期，默认 12
            slow: 慢线周期，默认 26
            signal: 信号线周期，默认 9
            
        Returns:
            MACDResult 对象
        """
        indicator = MACD(
            close=self.df["close"],
            window_fast=fast,
            window_slow=slow,
            window_sign=signal,
        )
        
        return MACDResult(
            macd=indicator.macd(),
            signal=indicator.macd_signal(),
            histogram=indicator.macd_diff(),
        )
    
    def kdj(
        self,
        n: int = 9,
        m1: int = 3,
        m2: int = 3,
    ) -> KDJResult:
        """计算 KDJ 指标
        
        使用 Stochastic Oscillator 计算 KD，然后推导 J。
        
        Args:
            n: RSV 周期，默认 9
            m1: K 线平滑周期，默认 3
            m2: D 线平滑周期，默认 3
            
        Returns:
            KDJResult 对象
        """
        stoch = StochasticOscillator(
            high=self.df["high"],
            low=self.df["low"],
            close=self.df["close"],
            window=n,
            smooth_window=m1,
        )
        
        k = stoch.stoch()
        d = stoch.stoch_signal()
        j = 3 * k - 2 * d  # J = 3K - 2D
        
        return KDJResult(k=k, d=d, j=j)
    
    def rsi(self, periods: list[int] = [6, 12, 24]) -> dict[int, pd.Series]:
        """计算 RSI 指标
        
        Args:
            periods: RSI 周期列表
            
        Returns:
            周期到 RSI 值的映射
        """
        result = {}
        for period in periods:
            indicator = RSIIndicator(close=self.df["close"], window=period)
            result[period] = indicator.rsi()
        return result
    
    def bollinger(
        self,
        window: int = 20,
        std_dev: float = 2.0,
    ) -> BOLLResult:
        """计算布林带
        
        Args:
            window: 移动平均周期
            std_dev: 标准差倍数
            
        Returns:
            BOLLResult 对象
        """
        indicator = BollingerBands(
            close=self.df["close"],
            window=window,
            window_dev=std_dev,
        )
        
        return BOLLResult(
            upper=indicator.bollinger_hband(),
            middle=indicator.bollinger_mavg(),
            lower=indicator.bollinger_lband(),
        )
    
    def sma(self, periods: list[int] = [5, 10, 20, 60]) -> dict[int, pd.Series]:
        """计算简单移动平均线
        
        Args:
            periods: MA 周期列表
            
        Returns:
            周期到 MA 值的映射
        """
        result = {}
        for period in periods:
            indicator = SMAIndicator(close=self.df["close"], window=period)
            result[period] = indicator.sma_indicator()
        return result
    
    def ema(self, periods: list[int] = [5, 10, 20, 60]) -> dict[int, pd.Series]:
        """计算指数移动平均线
        
        Args:
            periods: EMA 周期列表
            
        Returns:
            周期到 EMA 值的映射
        """
        result = {}
        for period in periods:
            indicator = EMAIndicator(close=self.df["close"], window=period)
            result[period] = indicator.ema_indicator()
        return result
    
    def is_bullish_alignment(self, ma_periods: list[int] = [5, 10, 20, 60]) -> bool:
        """判断是否多头排列
        
        多头排列：短期均线在上，长期均线在下
        
        Args:
            ma_periods: 均线周期列表（从短到长排序）
            
        Returns:
            True 表示多头排列
        """
        ma_dict = self.sma(ma_periods)
        
        # 获取最新的均线值
        latest_values = [ma_dict[p].iloc[-1] for p in sorted(ma_periods)]
        
        # 检查是否依次递减（短期 > 长期）
        for i in range(len(latest_values) - 1):
            if latest_values[i] <= latest_values[i + 1]:
                return False
        return True
    
    def is_bearish_alignment(self, ma_periods: list[int] = [5, 10, 20, 60]) -> bool:
        """判断是否空头排列
        
        空头排列：长期均线在上，短期均线在下
        """
        ma_dict = self.sma(ma_periods)
        latest_values = [ma_dict[p].iloc[-1] for p in sorted(ma_periods)]
        
        for i in range(len(latest_values) - 1):
            if latest_values[i] >= latest_values[i + 1]:
                return False
        return True
    
    def volume_ratio(self, period: int = 5) -> float:
        """计算量比
        
        量比 = 现成交量 / 过去 N 日平均成交量
        
        Args:
            period: 平均周期
            
        Returns:
            量比值
        """
        if len(self.df) < period + 1:
            return 1.0
        
        current_volume = self.df["volume"].iloc[-1]
        avg_volume = self.df["volume"].iloc[-period-1:-1].mean()
        
        if avg_volume == 0:
            return 0.0
        
        return current_volume / avg_volume
    
    def get_support_resistance(
        self,
        lookback: int = 60,
        num_levels: int = 3,
    ) -> Tuple[list[float], list[float]]:
        """计算支撑位和阻力位
        
        基于近期高低点识别关键价位。
        
        Args:
            lookback: 回看周期
            num_levels: 返回的价位数量
            
        Returns:
            (支撑位列表, 阻力位列表)
        """
        recent = self.df.tail(lookback)
        current_price = recent["close"].iloc[-1]
        
        # 找出局部极值点
        highs = recent["high"].values
        lows = recent["low"].values
        
        # 简单方法：使用分位数作为支撑阻力
        supports = []
        resistances = []
        
        for pct in [0.1, 0.25, 0.5]:
            low_level = np.percentile(lows, pct * 100)
            if low_level < current_price:
                supports.append(round(low_level, 2))
        
        for pct in [0.5, 0.75, 0.9]:
            high_level = np.percentile(highs, pct * 100)
            if high_level > current_price:
                resistances.append(round(high_level, 2))
        
        return supports[:num_levels], resistances[:num_levels]
    
    def get_summary(self) -> dict:
        """获取技术指标综合摘要
        
        Returns:
            包含各项指标状态的字典
        """
        macd_result = self.macd()
        kdj_result = self.kdj()
        
        supports, resistances = self.get_support_resistance()
        
        return {
            "price": {
                "close": round(self.df["close"].iloc[-1], 2),
                "change_pct": round(
                    (self.df["close"].iloc[-1] / self.df["close"].iloc[-2] - 1) * 100, 2
                ) if len(self.df) > 1 else 0,
            },
            "macd": {
                "dif": round(macd_result.macd.iloc[-1], 4),
                "dea": round(macd_result.signal.iloc[-1], 4),
                "histogram": round(macd_result.histogram.iloc[-1], 4),
                "golden_cross": macd_result.is_golden_cross,
                "death_cross": macd_result.is_death_cross,
                "above_zero": macd_result.is_above_zero,
            },
            "kdj": {
                "k": round(kdj_result.k.iloc[-1], 2),
                "d": round(kdj_result.d.iloc[-1], 2),
                "j": round(kdj_result.j.iloc[-1], 2),
                "golden_cross": kdj_result.is_golden_cross,
                "death_cross": kdj_result.is_death_cross,
                "oversold": kdj_result.is_oversold,
                "overbought": kdj_result.is_overbought,
            },
            "ma_alignment": {
                "bullish": self.is_bullish_alignment(),
                "bearish": self.is_bearish_alignment(),
            },
            "volume": {
                "ratio": round(self.volume_ratio(), 2),
            },
            "levels": {
                "supports": supports,
                "resistances": resistances,
            },
        }
