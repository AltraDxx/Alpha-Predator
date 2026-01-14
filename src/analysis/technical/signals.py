"""交易信号检测模块

基于多指标共振检测交易信号，支持：
- MACD + KDJ 共振
- 均线多头/空头排列
- 量价配合分析
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional

import pandas as pd

from src.analysis.technical.indicators import TechnicalIndicators
from src.analysis.technical.patterns import PatternRecognizer, PatternResult


class SignalStrength(str, Enum):
    """信号强度"""
    STRONG = "strong"       # 强信号
    MODERATE = "moderate"   # 中等信号
    WEAK = "weak"           # 弱信号


class SignalDirection(str, Enum):
    """信号方向"""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"


@dataclass
class TradingSignal:
    """交易信号"""
    direction: SignalDirection
    strength: SignalStrength
    score: float              # 综合评分 (-100 到 100)
    reasons: list[str]        # 信号理由
    indicators: dict          # 指标状态
    patterns: list[dict]      # 识别到的形态
    
    def to_dict(self) -> dict:
        return {
            "direction": self.direction.value,
            "strength": self.strength.value,
            "score": self.score,
            "reasons": self.reasons,
            "indicators": self.indicators,
            "patterns": self.patterns,
        }


class SignalDetector:
    """交易信号检测器"""
    
    def __init__(self, df: pd.DataFrame):
        """初始化
        
        Args:
            df: 包含 OHLCV 数据的 DataFrame
        """
        self.df = df.copy()
        self.indicators = TechnicalIndicators(df)
        self.patterns = PatternRecognizer(df)
    
    def detect(self) -> TradingSignal:
        """检测综合交易信号
        
        综合考虑：
        1. MACD 状态
        2. KDJ 状态
        3. 均线排列
        4. 量价关系
        5. K线形态
        
        Returns:
            TradingSignal 对象
        """
        score = 0.0
        reasons = []
        
        # 获取技术指标状态
        indicator_summary = self.indicators.get_summary()
        macd = indicator_summary["macd"]
        kdj = indicator_summary["kdj"]
        ma = indicator_summary["ma_alignment"]
        volume = indicator_summary["volume"]
        
        # ==================== MACD 评分 ====================
        # MACD 在零轴上方
        if macd["above_zero"]:
            score += 10
            reasons.append("MACD 处于零轴上方强势区域")
        else:
            score -= 10
        
        # MACD 金叉/死叉
        if macd["golden_cross"]:
            score += 20
            reasons.append("MACD 出现金叉")
        elif macd["death_cross"]:
            score -= 20
            reasons.append("MACD 出现死叉")
        
        # 红柱放大
        if macd["histogram"] > 0:
            score += 5
        else:
            score -= 5
        
        # ==================== KDJ 评分 ====================
        # KDJ 金叉/死叉
        if kdj["golden_cross"]:
            score += 15
            if kdj["j"] < 50:
                score += 10  # 低位金叉加分
                reasons.append("KDJ 低位金叉（高胜率信号）")
            else:
                reasons.append("KDJ 金叉")
        elif kdj["death_cross"]:
            score -= 15
            if kdj["j"] > 50:
                score -= 10
                reasons.append("KDJ 高位死叉（高胜率信号）")
            else:
                reasons.append("KDJ 死叉")
        
        # 超买超卖
        if kdj["oversold"]:
            score += 10
            reasons.append("KDJ 进入超卖区域")
        elif kdj["overbought"]:
            score -= 10
            reasons.append("KDJ 进入超买区域")
        
        # ==================== 均线评分 ====================
        if ma["bullish"]:
            score += 15
            reasons.append("均线多头排列")
        elif ma["bearish"]:
            score -= 15
            reasons.append("均线空头排列")
        
        # ==================== 量能评分 ====================
        vol_ratio = volume["ratio"]
        if vol_ratio > 2:
            # 放量，需结合方向判断
            if score > 0:
                score += 10
                reasons.append(f"放量上攻（量比 {vol_ratio:.1f}）")
            else:
                score -= 5
                reasons.append(f"放量下跌（量比 {vol_ratio:.1f}）")
        elif vol_ratio < 0.5:
            reasons.append(f"缩量整理（量比 {vol_ratio:.1f}）")
        
        # ==================== K线形态评分 ====================
        detected_patterns = self.patterns.scan_all_patterns()
        pattern_dicts = [p.to_dict() for p in detected_patterns]
        
        for pattern in detected_patterns:
            if pattern.pattern_type.value == "bullish":
                score += pattern.confidence * 15
                reasons.append(f"出现看涨形态：{pattern.name}")
            elif pattern.pattern_type.value == "bearish":
                score -= pattern.confidence * 15
                reasons.append(f"出现看跌形态：{pattern.name}")
        
        # ==================== MACD + KDJ 共振加分 ====================
        if macd["golden_cross"] and kdj["golden_cross"]:
            score += 15
            reasons.insert(0, "⚡ MACD + KDJ 金叉共振（强烈买入信号）")
        elif macd["death_cross"] and kdj["death_cross"]:
            score -= 15
            reasons.insert(0, "⚡ MACD + KDJ 死叉共振（强烈卖出信号）")
        
        # ==================== 确定信号方向和强度 ====================
        score = max(-100, min(100, score))
        
        if score >= 30:
            direction = SignalDirection.BUY
            if score >= 60:
                strength = SignalStrength.STRONG
            elif score >= 45:
                strength = SignalStrength.MODERATE
            else:
                strength = SignalStrength.WEAK
        elif score <= -30:
            direction = SignalDirection.SELL
            if score <= -60:
                strength = SignalStrength.STRONG
            elif score <= -45:
                strength = SignalStrength.MODERATE
            else:
                strength = SignalStrength.WEAK
        else:
            direction = SignalDirection.HOLD
            strength = SignalStrength.WEAK
            if not any("共振" in r for r in reasons):
                reasons.append("信号不明确，建议观望")
        
        return TradingSignal(
            direction=direction,
            strength=strength,
            score=round(score, 1),
            reasons=reasons,
            indicators=indicator_summary,
            patterns=pattern_dicts,
        )
    
    def get_resonance_status(self) -> dict:
        """获取多指标共振状态
        
        Returns:
            共振状态字典
        """
        macd_result = self.indicators.macd()
        kdj_result = self.indicators.kdj()
        
        # MACD 共振
        macd_bullish = macd_result.is_golden_cross or (
            macd_result.is_above_zero and macd_result.histogram_expanding
        )
        macd_bearish = macd_result.is_death_cross or (
            not macd_result.is_above_zero and not macd_result.histogram_expanding
        )
        
        # KDJ 共振
        kdj_bullish = kdj_result.is_golden_cross or kdj_result.is_oversold
        kdj_bearish = kdj_result.is_death_cross or kdj_result.is_overbought
        
        # 均线共振
        ma_bullish = self.indicators.is_bullish_alignment()
        ma_bearish = self.indicators.is_bearish_alignment()
        
        # 综合共振
        bullish_count = sum([macd_bullish, kdj_bullish, ma_bullish])
        bearish_count = sum([macd_bearish, kdj_bearish, ma_bearish])
        
        return {
            "macd": {"bullish": macd_bullish, "bearish": macd_bearish},
            "kdj": {"bullish": kdj_bullish, "bearish": kdj_bearish},
            "ma": {"bullish": ma_bullish, "bearish": ma_bearish},
            "resonance": {
                "bullish_count": bullish_count,
                "bearish_count": bearish_count,
                "is_bullish_resonance": bullish_count >= 2,
                "is_bearish_resonance": bearish_count >= 2,
            },
        }
